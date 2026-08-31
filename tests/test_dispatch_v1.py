"""Atomic execution-attempt and committed-record protocol regressions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from tests._candidate_checkout import (
    git_checkout, record_established_workspace,
)
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
        self.candidate = self._candidate_checkout()
        ticket = Path(self.temporary.name) / "tickets" / "run" / "T.md"
        established = ticket.read_text(encoding="utf-8")
        for key, value in (
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

    def _candidate_checkout(self) -> Path:
        return git_checkout(Path(self.temporary.name) / "candidate")

    def _establishes(self):
        """Stand in for `workspace.py establish`: record on the open attempt,
        then answer exactly as the real verb answers."""

        def establish(run, ticket_id, _workspace):
            record_established_workspace(
                Path(self.temporary.name) / "tickets" / run / f"{ticket_id}.md",
                self.candidate, strict=False,
            )
            return {"establish": {"workspace_path": str(self.candidate)}}

        return establish

    def project_packet(self, dispatch_id="D1"):
        """Commit the packet this attempt's execution records enter behind.

        The establishment records the tree on the open attempt first, which
        is the order the dispatch facade runs those two steps in.
        """

        record_established_workspace(
            Path(self.temporary.name) / "tickets" / "run" / "T.md", self.candidate
        )
        projected = tickets._dispatch([
            "dispatch-packet", "run", "T", "--dispatch-id", dispatch_id,
            "--workspace", str(self.candidate),
        ])
        self.assertNotIn("error", projected, projected)
        return projected["packet"]

    def retire(self, dispatch_id="D1", record_id="lifecycle:retire-1", seal=None):
        return tickets._dispatch([
            "dispatch-retire", "run", "T", "--dispatch-id", dispatch_id,
            "--assignment-seal", seal or self.opened_seal,
            "--record-id", record_id,
        ])

    def replace(
        self, dispatch_id="D1", replacement="D2", lease=None, by="worker-2",
        record_id="lifecycle:replace-1", seal=None, supersede_live=False,
    ):
        arguments = [
            "dispatch-replace", "run", "T",
            "--dispatch-id", dispatch_id,
            "--assignment-seal", seal or self.opened_seal,
            "--record-id", record_id,
            "--replacement-dispatch-id", replacement,
            "--by", by,
            "--lease-expires-at", lease or self.lease,
        ]
        if supersede_live:
            arguments.append("--supersede-live")
        return tickets._dispatch(arguments)

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

    def evidence_file(self, name: str, body: str) -> str:
        path = Path(self.temporary.name) / f"outcome-{name}.txt"
        path.write_text(body, encoding="utf-8")
        return str(path)

    def outcome(self, *, status="complete", result="delivered"):
        """Close through typed evidence files; `--content` was removed."""

        arguments = [
            "dispatch-outcome", "run", "T", "--status", status,
            "--result-file", self.evidence_file("result", result),
            "--verification-file", self.evidence_file("verification", "verified"),
        ]
        if status == "suspended":
            arguments += ["--handoff-file", self.evidence_file("handoff", "resume here")]
        return tickets._dispatch(arguments)

    def test_replace_help_states_lifecycle_record_id_namespace(self):
        payload = tickets._dispatch(["dispatch-replace", "--help"])

        self.assertIn(
            "--record-id <lifecycle:id>", payload["help"]["usage"],
        )

    def test_an_exact_reopen_replays_before_the_assignment_seal_is_graded(self):
        """contracts/dispatch.md's attempt precedence, which `dispatch-open`
        was the one operation not to keep: an exact committed identity returns
        its stored success first, and only an unseen open may then be refused
        as `assignment-mismatch`. Graded the other way round, the retry of the
        very call that opened an attempt was refused for a divergence that
        arrived after it."""

        opened = self.open()
        self.assertEqual("opened", opened["dispatch"]["outcome"])
        ticket = Path(self.temporary.name) / "tickets" / "run" / "T.md"
        ticket.write_text(
            self.ticket_text().replace(
                "Deliver the behavior.", "Deliver a different behavior."
            ),
            encoding="utf-8",
        )
        diverged = self.ticket_text()
        self.assertIn("Deliver a different behavior.", diverged)

        replayed = self.open()
        self.assertEqual("replayed", replayed["dispatch"]["outcome"])
        self.assertEqual(
            dict(opened["dispatch"], outcome="replayed"), replayed["dispatch"]
        )
        self.assertEqual(diverged, self.ticket_text())

        unseen = self.open(dispatch_id="D2")
        self.assertEqual("assignment-mismatch", unseen["code"])
        self.assertEqual(diverged, self.ticket_text())

    def test_a_non_root_join_leaves_the_runs_terminal_timing_unwritten(self):
        """The run identity's terminal timing is written once and never
        rewritten, so the first member to join terminal used to freeze the
        whole run's elapsed time at its own moment."""

        opened = self.open()
        self.opened_seal = opened["dispatch"]["assignment_seal"]
        self.project_packet()
        self.assertNotIn("error", self.outcome())
        # written after the outcome, so admission grades the sealed member
        # alone: from here the run has a root, and `T` is one of its items
        (Path(self.temporary.name) / "tickets" / "run" / "R.md").write_text(
            "---\nid: R\nrun: run\nstatus: pending\nexecutor: orch-decompose\n"
            "depends_on: []\n---\n\n## Objective\n\nThe run's root.\n",
            encoding="utf-8",
        )

        joined = tickets._dispatch([
            "dispatch-join", "run", "T",
            "--assignment-seal", self.opened_seal,
            "--dispatch-id", "D1", "--outcome-record-id", "outcome",
            "--by", "root-join",
        ])

        self.assertEqual("complete", joined["join"]["status"])
        identity = json.loads(
            (Path(self.temporary.name) / "runs" / "run" / "run.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertNotIn("terminal_at", identity)
        self.assertNotIn("terminal_ticket_id", identity)

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

        replaced = self.replace(supersede_live=True)
        self.assertEqual("replaced", replaced["dispatch"]["outcome"])
        self.assertEqual("D2", replaced["dispatch"]["dispatch_id"])
        self.assertEqual("D1", replaced["dispatch"]["replaces"])
        self.assertEqual(replaced, self.replace(supersede_live=True))

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

    def test_replacing_work_inside_its_own_lease_must_be_declared(self):
        """A caller cannot observe a child think.  Quiet is not evidence that
        it stopped -- the bound it was opened under is the only evidence the
        protocol has -- so superseding still-authorized work is a declaration
        the caller makes, never one the transition infers from silence."""

        opened = self.open()
        self.opened_seal = opened["dispatch"]["assignment_seal"]
        self.project_packet()
        before = self.ticket_text()

        undeclared = self.replace()

        self.assertEqual("supersession-undeclared", undeclared["code"])
        self.assertIn(self.lease, undeclared["error"])
        self.assertEqual(before, self.ticket_text())

        declared = self.replace(supersede_live=True)

        self.assertEqual("replaced", declared["dispatch"]["outcome"])
        state = parse_canonical_json(
            _parse_frontmatter(self.ticket_text())["dispatch_v1"]
        )
        self.assertEqual(["replaced", "live"], [item["state"] for item in state["attempts"]])

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

    def test_a_claim_without_a_dispatch_record_is_refused(self):
        # A live claim exists only as a dispatch-v1 attempt: a ticket whose
        # status says claimed with no record is off protocol, not a lease.
        path = Path(self.temporary.name) / "tickets" / "run" / "T.md"
        mangled = tickets._set_frontmatter_field(
            path.read_text(encoding="utf-8"), "status", "claimed"
        )
        path.write_text(mangled, encoding="utf-8")
        before = self.ticket_text()
        refusal = self.open()
        self.assertEqual("claim-without-dispatch", refusal["code"])
        self.assertEqual(before, self.ticket_text())
        self.opened_seal = _parse_frontmatter(before)["assignment_seal"]
        result_refusal = self.result(by="anyone")
        self.assertEqual("claim-without-dispatch", result_refusal["code"])
        self.assertEqual(before, self.ticket_text())

    def test_result_write_and_receipt_are_one_replayable_operation(self):
        opened = self.open()
        self.opened_seal = opened["dispatch"]["assignment_seal"]
        self.project_packet()

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
        self.project_packet()
        before = self.ticket_text()

        wrong_seal = self.result(seal="sha256:not-the-assignment")
        self.assertEqual("assignment-mismatch", wrong_seal["code"])
        self.assertEqual(before, self.ticket_text())

        wrong_writer = self.result(by="reused-human-name")
        self.assertEqual("identity-mismatch", wrong_writer["code"])
        self.assertEqual(before, self.ticket_text())

        committed = self.result()
        replaced = self.replace(supersede_live=True)
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
        self.project_packet()
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
        self.project_packet()
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
        self.project_packet()
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
        state = parse_canonical_json(data["dispatch_v1"])
        # The retained claimant observation IS the retired attempt.
        self.assertEqual("worker", state["attempts"][0]["owner"])
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
        self.project_packet()
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

    def test_persisted_execution_without_a_packet_is_a_byte_preserving_refusal(self):
        opened = self.open()
        self.opened_seal = opened["dispatch"]["assignment_seal"]
        self.project_packet()
        self.outcome()
        path = Path(self.temporary.name) / "tickets" / "run" / "T.md"
        text = path.read_text(encoding="utf-8")
        state = parse_canonical_json(_parse_frontmatter(text)["dispatch_v1"])
        records = state["attempts"][0]["records"]
        state["attempts"][0]["records"] = [
            record for record in records if record["record_id"] != "dispatch-packet"
        ]
        path.write_text(
            _set_frontmatter_field(text, "dispatch_v1", canonical_json(state)),
            encoding="utf-8",
        )
        before = path.read_bytes()

        refusal = self.commit(record_id="probe-after-missing-packet")

        self.assertEqual("dispatch-record-invalid", refusal["code"])
        self.assertIn("committed packet", refusal["error"])
        self.assertEqual(before, path.read_bytes())

    def test_persisted_packet_after_outcome_is_a_byte_preserving_refusal(self):
        opened = self.open()
        self.opened_seal = opened["dispatch"]["assignment_seal"]
        self.project_packet()
        self.outcome()
        path = Path(self.temporary.name) / "tickets" / "run" / "T.md"
        text = path.read_text(encoding="utf-8")
        state = parse_canonical_json(_parse_frontmatter(text)["dispatch_v1"])
        records = state["attempts"][0]["records"]
        packet = next(record for record in records if record["kind"] == "packet")
        state["attempts"][0]["records"] = [
            record for record in records if record is not packet
        ] + [packet]
        path.write_text(
            _set_frontmatter_field(text, "dispatch_v1", canonical_json(state)),
            encoding="utf-8",
        )
        before = path.read_bytes()

        refusal = self.commit(record_id="probe-after-reordered-packet")

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
                "_workspace_establish",
                side_effect=self._establishes(),
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
 "--workspace", str(self.candidate),
            ])

        self.assertEqual(refusal, result)
        ready.assert_called_once_with(["--run", "run"])
        open_call.assert_called_once_with([
            "run", "T", "--by", "worker", "--dispatch-id", "D1",
            "--lease-expires-at", self.lease,
        ], _lock_held=True)
        packet.assert_called_once_with([
            "run", "T", "--dispatch-id", "D1",
            "--workspace", str(self.candidate),
        ], _lock_held=True)
        retire.assert_called_once_with([
            "run", "T", "--assignment-seal", "seal", "--dispatch-id", "D1",
            "--record-id", "lifecycle:dispatch-facade-D1",
        ], _lock_held=True)

    def test_dispatch_facade_returns_the_committed_packet(self):
        with mock.patch.object(
            tickets._tickets_dispatch_facade_module,
            "_workspace_establish",
            side_effect=self._establishes(),
        ):
            result = tickets._dispatch([
                "dispatch", "run", "T", "--by", "worker",
                "--dispatch-id", "D1", "--lease-expires-at", self.lease,
 "--workspace", str(self.candidate),
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
            tickets._tickets_dispatch_facade_module, "_workspace_establish",
        ) as workspace:
            result = tickets._dispatch([
                "dispatch", "run", "T", "--by", "worker",
                "--dispatch-id", "D1", "--lease-expires-at", self.lease,
            ])

        self.assertEqual(refusal, result)
        ready.assert_called_once_with(["--run", "run"])
        workspace.assert_not_called()

    def test_dispatch_facade_preserves_ticket_bytes_on_a_pre_open_refusal(self):
        """Workspace establishment stamps the ticket, so it must not run
        before the attempt is open: a refused dispatch that had already
        written `workspace_path` would leave a mutation behind it."""

        refusal = {"error": "admission refused", "code": "admission-invalid"}
        before = self.ticket_text()
        with (
            mock.patch.object(tickets, "_cmd_ready", return_value={"ready": []}),
            mock.patch.object(
                tickets, "_cmd_dispatch_open", return_value=refusal,
            ),
            mock.patch.object(
                tickets._tickets_dispatch_facade_module, "_workspace_establish",
            ) as workspace,
        ):
            result = tickets._dispatch([
                "dispatch", "run", "T", "--by", "worker",
                "--dispatch-id", "D1", "--lease-expires-at", self.lease,
 "--workspace", str(self.candidate),
            ])

        self.assertEqual(refusal, result)
        workspace.assert_not_called()
        self.assertEqual(before, self.ticket_text())

    def test_dispatch_facade_surfaces_a_retirement_that_failed_to_resolve(self):
        """A projection refusal retires the attempt it opened.  When that
        retirement itself fails the attempt is left live, and returning the
        projection alone would report a refusal that quietly fenced the
        ticket against every later dispatch."""

        opened = {
            "dispatch": {
                "outcome": "opened",
                "assignment_seal": "seal",
                "dispatch_id": "D1",
            }
        }
        projection = {"error": "projection refused", "code": "review-invalid"}
        retirement = {"error": "retire refused", "code": "attempt-invalid"}
        with (
            mock.patch.object(tickets, "_cmd_ready", return_value={"ready": []}),
            mock.patch.object(
                tickets._tickets_dispatch_facade_module,
                "_workspace_establish",
                side_effect=self._establishes(),
            ),
            mock.patch.object(tickets, "_cmd_dispatch_open", return_value=opened),
            mock.patch.object(
                tickets, "_cmd_dispatch_packet", return_value=projection,
            ),
            mock.patch.object(
                tickets, "_cmd_dispatch_retire", return_value=retirement,
            ),
        ):
            result = tickets._dispatch([
                "dispatch", "run", "T", "--by", "worker",
                "--dispatch-id", "D1", "--lease-expires-at", self.lease,
 "--workspace", str(self.candidate),
            ])

        self.assertEqual("dispatch-retirement-failed", result["code"])
        self.assertEqual(projection, result["projection"])
        self.assertEqual(retirement, result["retirement"])

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

        def launch_precheck(_run, _ticket, host):
            # before the first side effect: an attempt opened for a launch
            # that cannot resolve is an attempt nobody can start
            events.append(("launch-precheck", host))
            return {"id": host, "launch": {"verb": "Agent"}}, None

        def workspace(_run, _ticket, _workspace):
            events.append("workspace")
            return {"establish": {"workspace_path": str(self.candidate)}}

        def open_attempt(_args, *, _lock_held=False):
            events.append(("open", _lock_held))
            return opened

        def packet(_args, *, _lock_held=False):
            events.append(("packet", _lock_held))
            return {"packet": {"dispatch_id": "D1"}}

        def launch(_record, _packet, *, packet_file=None):
            events.append("launch")
            return {"verb": "Agent"}, None

        def prepare(_run, _ticket, _workspace):
            events.append("prepare")
            return {"frontend": "skipped: no-lockfile"}

        with (
            mock.patch.object(tickets._tickets_dispatch_facade_module, "_run_lock", return_value=Lock()),
            mock.patch.object(tickets._tickets_dispatch_facade_module, "_cmd_ready", side_effect=ready),
            mock.patch.object(tickets._tickets_dispatch_facade_module, "precheck", side_effect=launch_precheck),
            mock.patch.object(tickets._tickets_dispatch_facade_module, "_workspace_establish", side_effect=workspace),
            mock.patch.object(tickets._tickets_dispatch_facade_module, "_workspace_prepare", side_effect=prepare),
            mock.patch.object(tickets._tickets_dispatch_facade_module, "_cmd_dispatch_open", side_effect=open_attempt),
            mock.patch.object(tickets._tickets_dispatch_facade_module, "_cmd_dispatch_packet", side_effect=packet),
            mock.patch.object(tickets._tickets_dispatch_facade_module, "launch_spec", side_effect=launch),
        ):
            result = tickets._tickets_dispatch_facade_module._cmd_dispatch([
                "run", "T", "--by", "worker", "--dispatch-id", "D1",
                "--lease-expires-at", self.lease,
                "--workspace", str(self.candidate),
            ])

        self.assertEqual(
            {
                "packet": {"dispatch_id": "D1"},
                "launch": {"verb": "Agent"},
                "prepare": {"frontend": "skipped: no-lockfile"},
            },
            result,
        )
        # `ready` sits outside the lock because promotion takes that same
        # lock per admitted ticket and `_run_lock` is not reentrant; every
        # mutating step of this ticket's own transaction is inside it. The
        # tree preparation sits outside it at the other end, and for the
        # opposite reason: it decides nothing and costs a package manager's
        # minutes, which inside the lock every sibling of the run waited out.
        self.assertEqual(
            ["ready", "lock-enter", ("launch-precheck", "claude"), ("open", True),
             "workspace", ("packet", True), "launch", "lock-exit", "prepare"],
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
                "_workspace_establish",
                side_effect=self._establishes(),
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
 "--workspace", str(self.candidate),
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
