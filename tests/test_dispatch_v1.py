"""Atomic execution-attempt and committed-record protocol regressions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts import tickets
from scripts.tickets_format import (
    _parse_frontmatter, _sections, _set_frontmatter_field, parse_canonical_json,
)


class DispatchV1Test(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.environment = mock.patch.dict(
            os.environ, {"ORCHFLOWS_STATE_HOME": self.temporary.name}
        )
        self.environment.start()
        self.dispatch(
            "new", "run", "T", "--executor", "orch-tdd",
            "--goal", "Deliver the behavior.",
            "--context", "The repository is authoritative.",
            "--pack", "orch-code-pack", "--isolation", "required",
        )
        self.dispatch("stamp-generation", "run", "T")
        validated = self.dispatch("draft-validate", "run", "T")
        self.dispatch(
            "seal", "run", "T", "--cut-generation",
            validated["draft_validation"]["cut_generation"],
        )
        self.dispatch("ready", "--run", "run")
        self.lease = (
            datetime.now(timezone.utc) + timedelta(hours=1)
        ).isoformat().replace("+00:00", "Z")

    def tearDown(self):
        self.environment.stop()
        self.temporary.cleanup()

    def dispatch(self, *arguments):
        result = tickets._dispatch(list(arguments))
        self.assertNotIn("error", result, result)
        return result

    def open(self, dispatch_id="D1", lease=None, by="worker"):
        return tickets._dispatch([
            "dispatch-open", "run", "T", "--by", by,
            "--dispatch-id", dispatch_id,
            "--lease-expires-at", lease or self.lease,
        ])

    def ticket_text(self):
        return (
            Path(self.temporary.name) / "tickets" / "run" / "T.md"
        ).read_text(encoding="utf-8")

    def commit(self, dispatch_id="D1", record_id="R1", content='{"value":1}'):
        return tickets._dispatch([
            "dispatch-commit", "run", "T",
            "--dispatch-id", dispatch_id,
            "--record-id", record_id,
            "--content", content,
        ])

    def retire(self, dispatch_id="D1", record_id="lifecycle:retire-1", seal=None):
        return tickets._dispatch([
            "dispatch-retire", "run", "T", "--dispatch-id", dispatch_id,
            "--assignment-seal", seal or self.opened_seal,
            "--record-id", record_id,
        ])

    def replace(
        self, dispatch_id="D1", replacement="D2", lease=None, by="worker-2",
        record_id="lifecycle:replace-1", seal=None,
    ):
        return tickets._dispatch([
            "dispatch-replace", "run", "T",
            "--dispatch-id", dispatch_id,
            "--assignment-seal", seal or self.opened_seal,
            "--record-id", record_id,
            "--replacement-dispatch-id", replacement,
            "--by", by,
            "--lease-expires-at", lease or self.lease,
        ])

    def result(
        self, *, dispatch_id="D1", record_id="result-1", by="worker",
        seal=None, section="Result", body="delivered", append=False,
    ):
        arguments = [
            "result", "run", "T",
            "--assignment-seal", seal or self.opened_seal,
            "--dispatch-id", dispatch_id,
            "--record-id", record_id,
            "--by", by,
            "--section", section,
            "--text", body,
        ]
        if append:
            arguments.append("--append")
        return tickets._dispatch(arguments)

    def outcome(self, *, status="complete", by="worker", dispatch_id="D1", seal=None):
        content = {
            "assignment_seal": seal or self.opened_seal,
            "by": by,
            "dispatch_id": dispatch_id,
            "evidence": {
                "Result": "delivered",
                "Verification": "verified",
                "Feedback": "[]",
                "Risks": "[]",
                "Handoff": "resume here" if status == "suspended" else "",
            },
            "id": "T",
            "outcome_record_id": "outcome",
            "protocol": "orchflows.dispatch.v1",
            "run": "run",
            "status": status,
        }
        return tickets._dispatch([
            "dispatch-outcome", "run", "T", "--content",
            json.dumps(content, sort_keys=True, separators=(",", ":")),
        ])

    def test_open_is_atomic_replayable_and_fences_a_second_live_attempt(self):
        opened = self.open()
        self.assertEqual("opened", opened["dispatch"]["outcome"])
        self.assertEqual("orchflows.dispatch.v1", opened["dispatch"]["protocol"])
        self.assertEqual("D1", opened["dispatch"]["dispatch_id"])
        self.assertEqual(self.lease, opened["dispatch"]["lease_expires_at"])

        text = self.ticket_text()
        self.assertIn("status: claimed", text)
        encoded = next(
            line.partition(":")[2].strip()
            for line in text.splitlines()
            if line.startswith("dispatch_v1:")
        )
        state = parse_canonical_json(encoded)
        self.assertEqual("D1", state["attempts"][0]["dispatch_id"])
        self.assertEqual("live", state["attempts"][0]["state"])

        replay = self.open()
        self.assertEqual("replayed", replay["dispatch"]["outcome"])
        self.assertEqual(text, self.ticket_text())

        changed = self.open(lease="2099-01-01T00:00:00Z")
        self.assertEqual("idempotency-conflict", changed["code"])
        self.assertIn("error", changed)
        self.assertEqual(text, self.ticket_text())

        second = self.open(dispatch_id="D2")
        self.assertEqual("live-attempt", second["code"])
        self.assertIn("error", second)
        self.assertEqual(text, self.ticket_text())

    def test_committed_record_replay_precedes_conflict_retirement_and_mismatch(self):
        opened = self.open()
        self.assertNotIn("error", opened)
        self.opened_seal = opened["dispatch"]["assignment_seal"]
        committed = self.commit()
        self.assertEqual("R1", committed["committed_record"]["record_id"])
        self.assertEqual({"value": 1}, committed["committed_record"]["content"])

        retired = self.retire()
        self.assertEqual("retired", retired["dispatch"]["outcome"])

        replay = self.commit()
        self.assertEqual(committed, replay)

        conflict = self.commit(content='{"value":2}')
        self.assertEqual("idempotency-conflict", conflict["code"])
        self.assertIn("error", conflict)

        stale = self.commit(record_id="R2")
        self.assertEqual("stale-attempt", stale["code"])
        self.assertIn("error", stale)

        mismatch = self.commit(dispatch_id="never-opened", record_id="R2")
        self.assertEqual("dispatch-mismatch", mismatch["code"])
        self.assertIn("error", mismatch)

    def test_replacement_is_atomic_and_old_commits_obey_replay_first_precedence(self):
        opened = self.open()
        self.assertNotIn("error", opened)
        self.opened_seal = opened["dispatch"]["assignment_seal"]
        committed = self.commit()

        replaced = self.replace()
        self.assertEqual("replaced", replaced["dispatch"]["outcome"])
        self.assertEqual("D2", replaced["dispatch"]["dispatch_id"])
        self.assertEqual("D1", replaced["dispatch"]["replaces"])
        self.assertEqual(replaced, self.replace())

        self.assertEqual(committed, self.commit())
        stale = self.commit(record_id="unseen")
        self.assertEqual("stale-attempt", stale["code"])
        current = self.commit(dispatch_id="D2", record_id="new")
        self.assertEqual("new", current["committed_record"]["record_id"])

        state = parse_canonical_json(next(
            line.partition(":")[2].strip()
            for line in self.ticket_text().splitlines()
            if line.startswith("dispatch_v1:")
        ))
        self.assertEqual(["replaced", "live"], [item["state"] for item in state["attempts"]])

    def test_retirement_allows_a_unique_new_attempt(self):
        opened = self.open()
        self.assertNotIn("error", opened)
        self.opened_seal = opened["dispatch"]["assignment_seal"]
        self.assertNotIn("error", self.retire())
        reopened = self.open(dispatch_id="D2", by="worker-2")
        self.assertEqual("opened", reopened["dispatch"]["outcome"])

    def test_expired_attempt_rejects_unseen_records_without_mutation(self):
        opened = self.open()
        self.assertNotIn("error", opened)
        self.opened_seal = opened["dispatch"]["assignment_seal"]
        before = self.ticket_text()

        class Later(datetime):
            @classmethod
            def now(cls, tz=None):
                value = datetime(2100, 1, 1, tzinfo=timezone.utc)
                return value if tz is None else value.astimezone(tz)

        with mock.patch("scripts.tickets_attempts.datetime", Later):
            stale = self.commit(record_id="after-expiry")
            stale_result = self.result(record_id="result-after-expiry")
        self.assertEqual("stale-attempt", stale["code"])
        self.assertEqual("stale-attempt", stale_result["code"])
        self.assertEqual(before, self.ticket_text())

    def test_pre_v1_live_claim_requires_owner_cutover(self):
        claimed = tickets._cmd_claim(["run", "T", "--by", "legacy-owner"])
        self.assertNotIn("error", claimed, claimed)
        before = self.ticket_text()
        refusal = self.open()
        self.assertEqual("legacy-live-claim", refusal["code"])
        self.assertEqual(before, self.ticket_text())
        self.opened_seal = _parse_frontmatter(before)["assignment_seal"]
        result_refusal = self.result(by="legacy-owner")
        self.assertEqual("legacy-live-claim", result_refusal["code"])
        self.assertEqual(before, self.ticket_text())

    def test_result_write_and_receipt_are_one_replayable_operation(self):
        opened = self.open()
        self.opened_seal = opened["dispatch"]["assignment_seal"]

        committed = self.result()
        self.assertEqual("orchflows.dispatch.v1", committed["result"]["protocol"])
        self.assertEqual("D1", committed["result"]["dispatch_id"])
        self.assertEqual("result-1", committed["result"]["record_id"])
        self.assertEqual("worker", committed["result"]["by"])
        written = self.ticket_text()
        result_body = _sections(written)["Result"]
        self.assertEqual(1, result_body.count("### Written by `worker`"), result_body)
        self.assertEqual(1, result_body.count("delivered"), result_body)

        self.assertNotIn("error", self.retire())
        retired = self.ticket_text()
        self.assertEqual(committed, self.result())
        self.assertEqual(retired, self.ticket_text())

        conflict = self.result(body="different")
        self.assertEqual("idempotency-conflict", conflict["code"])
        self.assertEqual(retired, self.ticket_text())
        stale = self.result(record_id="result-2", body="later", append=True)
        self.assertEqual("stale-attempt", stale["code"])
        self.assertEqual(retired, self.ticket_text())

    def test_result_refuses_attempt_identity_and_writer_mismatches_without_mutation(self):
        opened = self.open()
        self.opened_seal = opened["dispatch"]["assignment_seal"]
        before = self.ticket_text()

        wrong_seal = self.result(seal="sha256:not-the-assignment")
        self.assertEqual("assignment-mismatch", wrong_seal["code"])
        self.assertEqual(before, self.ticket_text())

        wrong_writer = self.result(by="reused-human-name")
        self.assertEqual("identity-mismatch", wrong_writer["code"])
        self.assertEqual(before, self.ticket_text())

        committed = self.result()
        replaced = self.replace()
        self.assertNotIn("error", replaced)
        replaced_text = self.ticket_text()
        self.assertEqual(committed, self.result())
        self.assertEqual(replaced_text, self.ticket_text())
        stale = self.result(record_id="unseen-after-replacement")
        self.assertEqual("stale-attempt", stale["code"])
        self.assertEqual(replaced_text, self.ticket_text())

    def test_lifecycle_operation_replay_precedes_conflict_and_retirement(self):
        opened = self.open()
        self.opened_seal = opened["dispatch"]["assignment_seal"]

        retired = self.retire()
        retired_text = self.ticket_text()
        self.assertEqual(retired, self.retire())
        self.assertEqual(retired_text, self.ticket_text())

        conflict = self.retire(seal="sha256:changed")
        self.assertEqual("idempotency-conflict", conflict["code"])
        unseen = self.retire(record_id="lifecycle:retire-2")
        self.assertEqual("stale-attempt", unseen["code"])
        self.assertEqual(retired_text, self.ticket_text())

    def test_join_consumes_a_fixed_result_identity_and_replays_after_retirement(self):
        opened = self.open()
        self.opened_seal = opened["dispatch"]["assignment_seal"]
        outcome = self.outcome()
        self.assertNotIn("error", outcome)

        arguments = [
            "dispatch-join", "run", "T",
            "--assignment-seal", self.opened_seal,
            "--dispatch-id", "D1",
            "--outcome-record-id", "outcome",
            "--by", "root-join",
        ]
        joined = tickets._dispatch(arguments)
        self.assertEqual("complete", joined["join"]["status"])
        joined_text = self.ticket_text()
        data = _parse_frontmatter(joined_text)
        self.assertEqual("complete", data["status"])
        state = parse_canonical_json(data["dispatch_v1"])
        self.assertEqual("retired", state["attempts"][0]["state"])
        identity = json.loads(
            (Path(self.temporary.name) / "runs" / "run" / "run.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual("complete", identity["terminal_status"])
        self.assertEqual("T", identity["terminal_ticket_id"])

        self.assertEqual(joined, tickets._dispatch(arguments))
        self.assertEqual(joined_text, self.ticket_text())
        self.assertEqual(outcome, self.outcome())

        changed_outcome = self.outcome(status="blocked")
        conflict = changed_outcome
        self.assertEqual("idempotency-conflict", conflict["code"])
        unseen = list(arguments)
        unseen[unseen.index("outcome")] = "another-outcome"
        mismatch = tickets._dispatch(unseen)
        self.assertEqual("outcome-record-mismatch", mismatch["code"])
        self.assertEqual(joined_text, self.ticket_text())

    def test_raw_terminal_and_suspension_writes_cannot_bypass_dispatch_join(self):
        opened = self.open()
        self.opened_seal = opened["dispatch"]["assignment_seal"]
        before = self.ticket_text()
        for status in ("pending", "suspended", "complete", "failed"):
            with self.subTest(status=status):
                refusal = tickets._dispatch(["set-status", "run", "T", status])
                self.assertEqual("dispatch-join-required", refusal["code"])
                self.assertEqual(before, self.ticket_text())

    def test_protocol_owned_record_ids_cannot_be_squatted(self):
        opened = self.open()
        self.opened_seal = opened["dispatch"]["assignment_seal"]
        before = self.ticket_text()
        for record_id in ("dispatch-packet", "outcome", "join:outcome", "lifecycle:x"):
            with self.subTest(record_id=record_id):
                refusal = self.commit(record_id=record_id)
                self.assertEqual("record-id-reserved", refusal["code"])
                self.assertEqual(before, self.ticket_text())
        result_refusal = self.result(record_id="outcome")
        self.assertEqual("record-id-reserved", result_refusal["code"])
        self.assertEqual(before, self.ticket_text())

    def test_malformed_persisted_attempt_is_a_structured_byte_preserving_refusal(self):
        self.open()
        path = Path(self.temporary.name) / "tickets" / "run" / "T.md"
        malformed = _set_frontmatter_field(
            path.read_text(encoding="utf-8"), "dispatch_v1",
            '{"attempts":[1],"protocol":"orchflows.dispatch.v1"}',
        )
        path.write_text(malformed, encoding="utf-8")
        before = path.read_bytes()
        refusal = self.commit()
        self.assertEqual("dispatch-record-invalid", refusal["code"])
        self.assertEqual(before, path.read_bytes())

    def test_noncanonical_persisted_state_is_a_byte_preserving_refusal(self):
        self.open()
        path = Path(self.temporary.name) / "tickets" / "run" / "T.md"
        text = path.read_text(encoding="utf-8")
        state = _parse_frontmatter(text)["dispatch_v1"]
        noncanonical = json.dumps(json.loads(state), sort_keys=False)
        self.assertNotEqual(state, noncanonical)
        path.write_text(
            _set_frontmatter_field(text, "dispatch_v1", noncanonical),
            encoding="utf-8",
        )
        before = path.read_bytes()

        refusal = self.commit()

        self.assertEqual("dispatch-record-invalid", refusal["code"])
        self.assertEqual(before, path.read_bytes())

    def test_forged_stored_success_is_refused_instead_of_replayed(self):
        self.open()
        committed = self.commit()
        path = Path(self.temporary.name) / "tickets" / "run" / "T.md"
        text = path.read_text(encoding="utf-8")
        data = _parse_frontmatter(text)
        state = parse_canonical_json(data["dispatch_v1"])
        state["attempts"][0]["records"][0]["success"] = {"forged": True}
        path.write_text(
            _set_frontmatter_field(text, "dispatch_v1", json.dumps(
                state, sort_keys=True, separators=(",", ":")
            )),
            encoding="utf-8",
        )
        before = path.read_bytes()

        refusal = self.commit()

        self.assertEqual("dispatch-record-invalid", refusal["code"])
        self.assertNotEqual(committed, refusal)
        self.assertEqual(before, path.read_bytes())

    def test_forged_outcome_success_cannot_drive_join(self):
        opened = self.open()
        self.opened_seal = opened["dispatch"]["assignment_seal"]
        self.outcome()
        path = Path(self.temporary.name) / "tickets" / "run" / "T.md"
        text = path.read_text(encoding="utf-8")
        data = _parse_frontmatter(text)
        state = parse_canonical_json(data["dispatch_v1"])
        record = state["attempts"][0]["records"][0]
        record["success"]["outcome"]["status"] = "ready"
        path.write_text(
            _set_frontmatter_field(text, "dispatch_v1", json.dumps(
                state, sort_keys=True, separators=(",", ":")
            )),
            encoding="utf-8",
        )
        before = path.read_bytes()

        refusal = tickets._dispatch([
            "dispatch-join", "run", "T",
            "--assignment-seal", self.opened_seal,
            "--dispatch-id", "D1", "--outcome-record-id", "outcome",
            "--by", "root-join",
        ])

        self.assertEqual("dispatch-record-invalid", refusal["code"])
        self.assertEqual(before, path.read_bytes())

    def test_orphan_replacement_edge_is_a_byte_preserving_refusal(self):
        self.open()
        path = Path(self.temporary.name) / "tickets" / "run" / "T.md"
        text = path.read_text(encoding="utf-8")
        data = _parse_frontmatter(text)
        state = parse_canonical_json(data["dispatch_v1"])
        state["attempts"][0]["replaces"] = "never-opened"
        path.write_text(
            _set_frontmatter_field(text, "dispatch_v1", json.dumps(
                state, sort_keys=True, separators=(",", ":")
            )),
            encoding="utf-8",
        )
        before = path.read_bytes()

        refusal = self.commit()

        self.assertEqual("dispatch-record-invalid", refusal["code"])
        self.assertEqual(before, path.read_bytes())

    def test_replacement_identity_injection_is_refused_without_mutation(self):
        opened = self.open()
        self.opened_seal = opened["dispatch"]["assignment_seal"]
        before = self.ticket_text()
        refusal = self.replace(by="evil\nstatus: complete")
        self.assertEqual("owner-invalid", refusal["code"])
        self.assertEqual(before, self.ticket_text())

    def test_legacy_role_bearing_facade_routes_are_absent(self):
        for command in ("claim", "packet"):
            refusal = tickets._dispatch([command, "run", "T"])
            self.assertIn("unknown subcommand", refusal["error"])


if __name__ == "__main__":
    unittest.main()
