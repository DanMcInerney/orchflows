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
    _parse_frontmatter, _sections, _set_frontmatter_field, canonical_json,
    parse_canonical_json,
)


class DispatchV1Test(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.environment = mock.patch.dict(
            os.environ, {"ORCHFLOWS_STATE_HOME": self.temporary.name}
        )
        self.environment.start()
        self.dispatch(
            "new", "run", "T", "--executor", "orch-execute",
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
        ticket = Path(self.temporary.name) / "tickets" / "run" / "T.md"
        established = ticket.read_text(encoding="utf-8")
        for key, value in (
            ("workspace_path", "C:/candidate"),
            ("workspace_branch", "candidate-branch"),
            ("workspace_baseline", "0123456789abcdef clean"),
        ):
            established = tickets._set_frontmatter_field(established, key, value)
        ticket.write_text(established, encoding="utf-8")
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

    def authorize(self, dispatch_id="D1", by="worker"):
        packet = tickets._dispatch([
            "dispatch-packet", "run", "T", "--dispatch-id", dispatch_id,
            "--reply-to", "root", "--workspace", "C:/candidate",
            "--form", "reference",
        ])["packet"]
        return tickets._dispatch([
            "dispatch-receive", "--content",
            json.dumps(packet, sort_keys=True, separators=(",", ":")),
            "--role", "worker", "--profile", "orch-worker",
            "--by", by, "--reply-to", "root",
            "--workspace", "C:/candidate",
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

    def outcome(
        self, *, status="complete", by="worker", dispatch_id="D1", seal=None,
        result="delivered",
    ):
        content = {
            "assignment_seal": seal or self.opened_seal,
            "by": by,
            "dispatch_id": dispatch_id,
            "evidence": {
                "Result": result,
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

    def test_replace_help_states_lifecycle_record_id_namespace(self):
        payload = tickets._dispatch(["dispatch-replace", "--help"])

        self.assertIn(
            "--record-id <lifecycle:id>", payload["help"]["usage"],
        )

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

    def test_open_requires_the_current_stored_admission_before_mutation(self):
        path = Path(self.temporary.name) / "tickets" / "run" / "T.md"
        text = path.read_text(encoding="utf-8")
        path.write_text(
            _set_frontmatter_field(text, "admission", "git:sha256:stale"),
            encoding="utf-8",
        )
        before = path.read_bytes()

        refusal = self.open()

        self.assertEqual("admission-mismatch", refusal["code"])
        self.assertEqual(before, path.read_bytes())

    def test_expiry_cannot_implicitly_open_a_successor(self):
        soon = (
            datetime.now(timezone.utc) + timedelta(minutes=1)
        ).isoformat().replace("+00:00", "Z")
        opened = self.open(lease=soon)
        self.opened_seal = opened["dispatch"]["assignment_seal"]
        before = self.ticket_text()

        class Later(datetime):
            @classmethod
            def now(cls, tz=None):
                value = datetime(2100, 1, 1, tzinfo=timezone.utc)
                return value if tz is None else value.astimezone(tz)

        with mock.patch("scripts.tickets_attempts.datetime", Later):
            refusal = self.open(
                dispatch_id="D2", by="worker-2", lease="2101-01-01T00:00:00Z"
            )

        self.assertEqual("lease-expired", refusal["code"])
        self.assertEqual(before, self.ticket_text())
        self.assertNotIn("error", self.retire())
        reopened = self.open(dispatch_id="D2", by="worker-2")
        self.assertEqual("opened", reopened["dispatch"]["outcome"])

    def test_expired_attempt_can_cross_the_explicit_atomic_replacement(self):
        soon = (
            datetime.now(timezone.utc) + timedelta(minutes=1)
        ).isoformat().replace("+00:00", "Z")
        opened = self.open(lease=soon)
        self.opened_seal = opened["dispatch"]["assignment_seal"]

        class Later(datetime):
            @classmethod
            def now(cls, tz=None):
                value = datetime(2100, 1, 1, tzinfo=timezone.utc)
                return value if tz is None else value.astimezone(tz)

        with mock.patch("scripts.tickets_attempts.datetime", Later):
            replaced = self.replace(
                replacement="D2", lease="2101-01-01T00:00:00Z", by="worker-2"
            )

        self.assertEqual("replaced", replaced["dispatch"]["outcome"])
        state = parse_canonical_json(_parse_frontmatter(self.ticket_text())["dispatch_v1"])
        self.assertEqual(["replaced", "live"], [item["state"] for item in state["attempts"]])

    def test_all_dispatch_state_operations_refuse_path_aliased_origins(self):
        opened = self.open()
        self.opened_seal = opened["dispatch"]["assignment_seal"]
        envelope = {
            "assignment_seal": self.opened_seal,
            "by": "worker", "dispatch_id": "D1",
            "evidence": {
                "Result": "delivered", "Verification": "verified",
                "Feedback": "[]", "Risks": "[]", "Handoff": "",
            },
            "id": "T", "outcome_record_id": "outcome",
            "protocol": "orchflows.dispatch.v1", "run": "run/../run",
            "status": "complete",
        }
        commands = (
            [
                "dispatch-outcome", "run/../run", "T", "--content",
                json.dumps(envelope, sort_keys=True, separators=(",", ":")),
            ],
            [
                "dispatch-retire", "run/../run", "T", "--dispatch-id", "D1",
                "--assignment-seal", self.opened_seal,
                "--record-id", "lifecycle:retire-alias",
            ],
            [
                "dispatch-replace", "run/../run", "T", "--dispatch-id", "D1",
                "--assignment-seal", self.opened_seal,
                "--record-id", "lifecycle:replace-alias",
                "--replacement-dispatch-id", "D2", "--by", "worker-2",
                "--lease-expires-at", self.lease,
            ],
        )
        path = Path(self.temporary.name) / "tickets" / "run" / "T.md"
        before = self.ticket_text()

        for command in commands:
            with self.subTest(command=command[0]):
                path.write_text(before, encoding="utf-8")
                refusal = tickets._dispatch(command)
                self.assertIn("unsafe run id", refusal["error"])
                self.assertEqual(before, self.ticket_text())

    def test_dispatch_operations_refuse_a_ticket_frontmatter_origin_mismatch(self):
        opened = self.open()
        path = Path(self.temporary.name) / "tickets" / "run" / "T.md"
        text = path.read_text(encoding="utf-8")
        path.write_text(_set_frontmatter_field(text, "id", "other"), encoding="utf-8")
        before = path.read_bytes()

        refusal = self.commit()

        self.assertEqual("origin-mismatch", refusal["code"])
        self.assertEqual(before, path.read_bytes())

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
        self.assertEqual("accepted", self.authorize()["receipt"]["outcome"])

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
        self.assertEqual("accepted", self.authorize()["receipt"]["outcome"])
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
        self.assertEqual("accepted", self.authorize()["receipt"]["outcome"])
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

    def test_outcome_materializes_only_unstreamed_evidence_once(self):
        opened = self.open()
        self.opened_seal = opened["dispatch"]["assignment_seal"]
        self.assertEqual("accepted", self.authorize()["receipt"]["outcome"])
        self.result(body="delivered")
        streamed = self.ticket_text()

        repeated = self.outcome(result="delivered")

        self.assertEqual("outcome-invalid", repeated["code"])
        self.assertEqual(streamed, self.ticket_text())

        committed = self.outcome(result="closing result delta")
        self.assertNotIn("error", committed)
        closed = self.ticket_text()
        result_body = _sections(closed)["Result"]
        self.assertEqual(1, result_body.count("delivered"))
        self.assertEqual(1, result_body.count("closing result delta"))
        self.assertEqual(committed, self.outcome(result="closing result delta"))
        self.assertEqual(closed, self.ticket_text())

    def test_suspended_join_retires_the_attempt_but_retains_claimant_observations(self):
        opened = self.open()
        self.opened_seal = opened["dispatch"]["assignment_seal"]
        self.assertEqual("accepted", self.authorize()["receipt"]["outcome"])
        self.outcome(status="suspended")

        joined = tickets._dispatch([
            "dispatch-join", "run", "T",
            "--assignment-seal", self.opened_seal,
            "--dispatch-id", "D1", "--outcome-record-id", "outcome",
            "--by", "root-join",
        ])

        self.assertEqual("suspended", joined["join"]["status"])
        data = _parse_frontmatter(self.ticket_text())
        self.assertEqual("suspended", data["status"])
        self.assertEqual("worker", data["claimed_by"])
        state = parse_canonical_json(data["dispatch_v1"])
        self.assertEqual("retired", state["attempts"][0]["state"])

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
            _set_frontmatter_field(text, "dispatch_v1", canonical_json(state)),
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
        self.assertEqual("accepted", self.authorize()["receipt"]["outcome"])
        self.outcome()
        path = Path(self.temporary.name) / "tickets" / "run" / "T.md"
        text = path.read_text(encoding="utf-8")
        data = _parse_frontmatter(text)
        state = parse_canonical_json(data["dispatch_v1"])
        record = next(
            item for item in state["attempts"][0]["records"]
            if item["record_id"] == "outcome"
        )
        record["success"]["outcome"]["status"] = "ready"
        path.write_text(
            _set_frontmatter_field(text, "dispatch_v1", canonical_json(state)),
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

    def test_persisted_execution_without_the_receipt_is_a_byte_preserving_refusal(self):
        opened = self.open()
        self.opened_seal = opened["dispatch"]["assignment_seal"]
        self.assertEqual("accepted", self.authorize()["receipt"]["outcome"])
        self.outcome()
        path = Path(self.temporary.name) / "tickets" / "run" / "T.md"
        text = path.read_text(encoding="utf-8")
        state = parse_canonical_json(_parse_frontmatter(text)["dispatch_v1"])
        records = state["attempts"][0]["records"]
        state["attempts"][0]["records"] = [
            record for record in records if record["record_id"] != "dispatch-receipt"
        ]
        path.write_text(
            _set_frontmatter_field(text, "dispatch_v1", canonical_json(state)),
            encoding="utf-8",
        )
        before = path.read_bytes()

        refusal = self.commit(record_id="probe-after-missing-receipt")

        self.assertEqual("receipt-required", refusal["code"])
        self.assertEqual(before, path.read_bytes())

    def test_persisted_receipt_after_outcome_is_a_byte_preserving_refusal(self):
        opened = self.open()
        self.opened_seal = opened["dispatch"]["assignment_seal"]
        self.assertEqual("accepted", self.authorize()["receipt"]["outcome"])
        self.outcome()
        path = Path(self.temporary.name) / "tickets" / "run" / "T.md"
        text = path.read_text(encoding="utf-8")
        state = parse_canonical_json(_parse_frontmatter(text)["dispatch_v1"])
        records = state["attempts"][0]["records"]
        receipt = next(record for record in records if record["kind"] == "receipt")
        state["attempts"][0]["records"] = [
            record for record in records if record is not receipt
        ] + [receipt]
        path.write_text(
            _set_frontmatter_field(text, "dispatch_v1", canonical_json(state)),
            encoding="utf-8",
        )
        before = path.read_bytes()

        refusal = self.commit(record_id="probe-after-reordered-receipt")

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

    def test_dispatch_facade_is_a_public_one_call_surface(self):
        payload = tickets._dispatch(["dispatch", "--help"])

        self.assertIn("dispatch <run> <id>", payload["help"]["usage"])

    def test_dispatch_facade_relays_packet_refusal_and_closes_new_attempt(self):
        refusal = {
            "code": "review-invalid",
            "error": "review projection is not current",
            "findings": ["stale artifact"],
        }
        opened = {
            "dispatch": {
                "outcome": "opened",
                "assignment_seal": "seal",
                "dispatch_id": "D1",
            }
        }
        with (
            mock.patch.object(tickets, "_cmd_ready", return_value={"ready": []}) as ready,
            mock.patch.object(
                tickets._tickets_dispatch_facade_module,
                "_workspace_start",
                return_value={"start": {"workspace_path": "C:/candidate"}},
            ),
            mock.patch.object(tickets, "_cmd_dispatch_open", return_value=opened) as open_call,
            mock.patch.object(
                tickets, "_cmd_dispatch_packet", return_value=refusal,
            ) as packet,
            mock.patch.object(
                tickets, "_cmd_dispatch_retire", return_value={"dispatch": {}}
            ) as retire,
        ):
            result = tickets._dispatch([
                "dispatch", "run", "T", "--by", "worker",
                "--dispatch-id", "D1", "--lease-expires-at", self.lease,
                "--reply-to", "root", "--workspace", "C:/candidate",
            ])

        self.assertEqual(refusal, result)
        ready.assert_called_once_with(["--run", "run"])
        open_call.assert_called_once_with([
            "run", "T", "--by", "worker", "--dispatch-id", "D1",
            "--lease-expires-at", self.lease,
        ], _lock_held=True)
        packet.assert_called_once_with([
            "run", "T", "--dispatch-id", "D1", "--reply-to", "root",
            "--workspace", "C:/candidate", "--form", "reference",
        ], _lock_held=True)
        retire.assert_called_once_with([
            "run", "T", "--assignment-seal", "seal", "--dispatch-id", "D1",
            "--record-id", "lifecycle:dispatch-facade-D1",
        ], _lock_held=True)

    def test_dispatch_facade_returns_the_committed_packet(self):
        with mock.patch.object(
            tickets._tickets_dispatch_facade_module,
            "_workspace_start",
            return_value={"start": {"workspace_path": "C:/candidate"}},
        ):
            result = tickets._dispatch([
                "dispatch", "run", "T", "--by", "worker",
                "--dispatch-id", "D1", "--lease-expires-at", self.lease,
                "--reply-to", "root", "--workspace", "C:/candidate",
            ])

        self.assertIn("packet", result, result)
        state = parse_canonical_json(
            _parse_frontmatter(self.ticket_text())["dispatch_v1"]
        )
        self.assertEqual("live", state["attempts"][0]["state"])
        self.assertEqual(
            ["dispatch-packet"],
            [record["record_id"] for record in state["attempts"][0]["records"]],
        )

    def test_dispatch_facade_returns_readiness_refusal_without_starting_workspace(self):
        refusal = {"error": "readiness failed", "code": "readiness-invalid"}
        with mock.patch.object(
            tickets, "_cmd_ready", return_value=refusal,
        ) as ready, mock.patch.object(
            tickets._tickets_dispatch_facade_module, "_workspace_start",
        ) as workspace:
            result = tickets._dispatch([
                "dispatch", "run", "T", "--by", "worker",
                "--dispatch-id", "D1", "--lease-expires-at", self.lease,
                "--reply-to", "root",
            ])

        self.assertEqual(refusal, result)
        ready.assert_called_once_with(["--run", "run"])
        workspace.assert_not_called()

    def test_dispatch_facade_holds_one_run_lock_across_every_mutating_step(self):
        events = []

        class Lock:
            def __enter__(self):
                events.append("lock-enter")
                return self

            def __exit__(self, *_):
                events.append("lock-exit")

        opened = {
            "dispatch": {
                "outcome": "opened",
                "assignment_seal": "seal",
                "dispatch_id": "D1",
            }
        }

        def ready(_args):
            events.append("ready")
            return {"ready": []}

        def workspace(_run, _ticket, _workspace):
            events.append("workspace")
            return {"start": {"workspace_path": "C:/candidate"}}

        def open_attempt(_args, *, _lock_held=False):
            events.append(("open", _lock_held))
            return opened

        def packet(_args, *, _lock_held=False):
            events.append(("packet", _lock_held))
            return {"packet": {"dispatch_id": "D1"}}

        with (
            mock.patch.object(tickets._tickets_dispatch_facade_module, "_run_lock", return_value=Lock()),
            mock.patch.object(tickets._tickets_dispatch_facade_module, "_cmd_ready", side_effect=ready),
            mock.patch.object(tickets._tickets_dispatch_facade_module, "_workspace_start", side_effect=workspace),
            mock.patch.object(tickets._tickets_dispatch_facade_module, "_cmd_dispatch_open", side_effect=open_attempt),
            mock.patch.object(tickets._tickets_dispatch_facade_module, "_cmd_dispatch_packet", side_effect=packet),
        ):
            result = tickets._tickets_dispatch_facade_module._cmd_dispatch([
                "run", "T", "--by", "worker", "--dispatch-id", "D1",
                "--lease-expires-at", self.lease, "--reply-to", "root",
                "--workspace", "C:/candidate",
            ])

        self.assertEqual({"packet": {"dispatch_id": "D1"}}, result)
        self.assertEqual(
            ["lock-enter", "ready", "workspace", ("open", True),
             ("packet", True), "lock-exit"],
            events,
        )

    def test_dispatch_facade_retires_when_projection_returns_no_packet(self):
        opened = {
            "dispatch": {
                "outcome": "opened",
                "assignment_seal": "seal",
                "dispatch_id": "D1",
            }
        }
        with (
            mock.patch.object(tickets, "_cmd_ready", return_value={"ready": []}),
            mock.patch.object(
                tickets._tickets_dispatch_facade_module,
                "_workspace_start",
                return_value={"start": {"workspace_path": "C:/candidate"}},
            ),
            mock.patch.object(tickets, "_cmd_dispatch_open", return_value=opened),
            mock.patch.object(tickets, "_cmd_dispatch_packet", return_value=None),
            mock.patch.object(
                tickets, "_cmd_dispatch_retire", return_value={"dispatch": {}}
            ) as retire,
        ):
            result = tickets._dispatch([
                "dispatch", "run", "T", "--by", "worker",
                "--dispatch-id", "D1", "--lease-expires-at", self.lease,
                "--reply-to", "root", "--workspace", "C:/candidate",
            ])

        self.assertEqual(
            {"error": "dispatch-packet returned a non-object response"}, result
        )
        retire.assert_called_once_with([
            "run", "T", "--assignment-seal", "seal", "--dispatch-id", "D1",
            "--record-id", "lifecycle:dispatch-facade-D1",
        ], _lock_held=True)


if __name__ == "__main__":
    unittest.main()
