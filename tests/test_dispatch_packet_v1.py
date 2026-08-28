"""Committed dispatch-v1 packet projection and receipt regressions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from scripts import tickets, tickets_review
from scripts.tickets_packet import workspace_establishment_finding
from scripts.tickets_format import canonical_json, parse_canonical_json


class DispatchPacketV1Test(unittest.TestCase):
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
            "--pack", "orch-code-pack", "--profile", "orch-worker",
            "--isolation", "required",
        )
        self.dispatch("stamp-generation", "run", "T")
        validated = self.dispatch("draft-validate", "run", "T")
        self.dispatch(
            "seal", "run", "T", "--cut-generation",
            validated["draft_validation"]["cut_generation"],
        )
        self.dispatch("ready", "--run", "run")
        self.ticket_path = Path(self.temporary.name) / "tickets" / "run" / "T.md"
        established = self.ticket_path.read_text(encoding="utf-8")
        for key, value in (
            ("workspace_path", "C:/candidate"),
            ("workspace_branch", "candidate-branch"),
            ("workspace_baseline", "0123456789abcdef clean"),
        ):
            established = tickets._set_frontmatter_field(established, key, value)
        self.ticket_path.write_text(established, encoding="utf-8")
        self.lease = (
            datetime.now(timezone.utc) + timedelta(hours=1)
        ).isoformat().replace("+00:00", "Z")
        opened = self.dispatch(
            "dispatch-open", "run", "T", "--by", "worker",
            "--dispatch-id", "D1", "--lease-expires-at", self.lease,
        )
        self.assignment_seal = opened["dispatch"]["assignment_seal"]

    def tearDown(self):
        self.environment.stop()
        self.temporary.cleanup()

    def dispatch(self, *arguments):
        result = tickets._dispatch(list(arguments))
        self.assertNotIn("error", result, result)
        return result

    def project(self, form="reference", workspace="C:/candidate"):
        return tickets._dispatch([
            "dispatch-packet", "run", "T", "--dispatch-id", "D1",
            "--reply-to", "root", "--workspace", workspace,
            "--form", form,
        ])

    def receive(self, packet, **overrides):
        actual = {
            "role": "worker", "profile": "orch-worker", "by": "worker",
            "reply_to": "root", "workspace": "C:/candidate",
        }
        actual.update(overrides)
        arguments = [
            "dispatch-receive", "--content", canonical_json(packet),
            "--role", actual["role"], "--profile", actual["profile"],
            "--by", actual["by"], "--reply-to", actual["reply_to"],
            "--workspace", actual["workspace"],
        ]
        return tickets._dispatch(arguments)

    def receive_file(self, path, **overrides):
        actual = {
            "role": "worker", "profile": "orch-worker", "by": "worker",
            "reply_to": "root", "workspace": "C:/candidate",
        }
        actual.update(overrides)
        return tickets._dispatch([
            "dispatch-receive", "--file", str(path),
            "--role", actual["role"], "--profile", actual["profile"],
            "--by", actual["by"], "--reply-to", actual["reply_to"],
            "--workspace", actual["workspace"],
        ])

    def ticket_state(self):
        path = Path(self.temporary.name) / "tickets" / "run" / "T.md"
        encoded = next(
            line.partition(":")[2].strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.startswith("dispatch_v1:")
        )
        return parse_canonical_json(encoded)

    def ticket_bytes(self):
        return (
            Path(self.temporary.name) / "tickets" / "run" / "T.md"
        ).read_bytes()

    def test_reference_projection_is_committed_and_exact_retry_replays(self):
        first = self.project()
        self.assertNotIn("error", first, first)
        packet = first["packet"]
        self.assertEqual("orchflows.dispatch.v1", packet["protocol"])
        self.assertEqual("reference", packet["form"])
        self.assertEqual("D1", packet["dispatch_id"])
        self.assertEqual("worker", packet["assigned_name"])
        self.assertEqual("worker", packet["role"])
        self.assertEqual({"run": "run", "id": "T"}, packet["reference"])
        self.assertNotIn("inline", packet)
        self.assertIn(
            f"--assignment-seal {packet['assignment_seal']} --dispatch-id D1 "
            "--record-id RECORD_ID --by worker",
            packet["prompt"],
        )
        self.assertNotIn("workspace.py", packet["prompt"])

        self.assertEqual(first, self.project())
        records = self.ticket_state()["attempts"][0]["records"]
        self.assertEqual(["dispatch-packet"], [item["record_id"] for item in records])

        receipt = self.receive(packet)
        self.assertEqual("accepted", receipt["receipt"]["outcome"])
        self.assertEqual("reference", receipt["receipt"]["form"])

    def test_uncommitted_projection_still_runs_current_review_validation(self):
        before = self.ticket_bytes()
        owner = tickets._tickets_dispatch_packet_module
        with mock.patch.object(
            owner, "packet_state_result", return_value=(None, "current review is invalid"),
        ):
            refusal = self.project()

        self.assertEqual("review-invalid", refusal["code"])
        self.assertEqual(before, self.ticket_bytes())
        self.assertEqual([], self.ticket_state()["attempts"][0]["records"])

    def test_legacy_gate_repair_replays_stored_packet_across_head_change(self):
        committed = self.project()
        old_head = subprocess.run(
            ["git", "rev-parse", "HEAD^"], cwd=Path(__file__).resolve().parents[1],
            text=True, capture_output=True, check=True,
        ).stdout.strip()
        current_head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=Path(__file__).resolve().parents[1],
            text=True, capture_output=True, check=True,
        ).stdout.strip()
        self.assertNotEqual(old_head, current_head)

        legacy_id = "T.gate.repair"
        stored_packet = dict(committed["packet"])
        stored_packet.update({
            "executor": "orch-repair",
            "reference": {"id": legacy_id, "run": "run"},
            "source": {"id": legacy_id, "run": "run"},
        })
        stored = {"packet": stored_packet}
        text = self.ticket_path.read_text(encoding="utf-8")
        data = tickets._parse_frontmatter(text)
        state = parse_canonical_json(data["dispatch_v1"])
        packet_record = state["attempts"][0]["records"][0]
        packet_record["content"] = canonical_json(stored)
        packet_record["success"] = {"committed_record": {
            "content": stored, "dispatch_id": "D1", "id": legacy_id,
            "protocol": "orchflows.dispatch.v1", "record_id": "dispatch-packet",
            "run": "run",
        }}
        legacy_plan = tickets_review._record(
            "GatePlan", None, artifact=f"git:{old_head}",
            criteria=[{
                "identity": "sha256:" + "a" * 64, "lens": "code",
                "order": 0, "ticket": "T.gate.critique.code",
            }],
            isolation="none", mode="gate", pack="orch-code-pack", root="T",
        )
        text = tickets._set_frontmatter_field(text, "id", legacy_id)
        text = tickets._set_frontmatter_field(text, "executor", "orch-repair")
        text = tickets._set_frontmatter_field(
            text, "dispatch_v1", canonical_json(state),
        )
        text = tickets._set_frontmatter_field(
            text, "review_v1", canonical_json({
                "protocol": "orchflows.review.v1", "records": [legacy_plan],
            }),
        )
        legacy_path = self.ticket_path.with_name(f"{legacy_id}.md")
        legacy_path.write_text(text, encoding="utf-8")
        before = legacy_path.read_bytes()

        replayed = tickets._dispatch([
            "dispatch-packet", "run", legacy_id, "--dispatch-id", "D1",
            "--reply-to", "root", "--workspace", "C:/candidate",
            "--artifact", f"git:{old_head}", "--form", "reference",
        ])

        self.assertEqual(stored, replayed)
        self.assertEqual(packet_record["content"], canonical_json(replayed))
        self.assertEqual(before, legacy_path.read_bytes())

    def test_projection_refuses_an_unrecorded_candidate_workspace(self):
        text = self.ticket_path.read_text(encoding="utf-8")
        text = "\n".join(
            line for line in text.splitlines()
            if not line.startswith("workspace_path:")
        ) + "\n"
        self.ticket_path.write_text(text, encoding="utf-8")

        refusal = self.project()

        self.assertEqual("workspace-unestablished", refusal["code"])
        self.assertNotIn("packet", refusal)

    def test_projection_refuses_a_workspace_other_than_the_recorded_candidate(self):
        refusal = self.project(workspace="C:/other")

        self.assertEqual("workspace-mismatch", refusal["code"])
        self.assertNotIn("packet", refusal)

    def test_research_projection_requires_the_recorded_store_to_exist(self):
        with tempfile.TemporaryDirectory() as store:
            data = {
                "pack": "orch-research-pack",
                "workspace_path": store,
            }
            self.assertIsNone(workspace_establishment_finding(data, store))
        finding = workspace_establishment_finding(data, store)
        self.assertEqual("workspace-unestablished", finding[0])

    def test_inline_snapshot_requires_the_authoritative_state_sink(self):
        packet = self.project(form="inline")["packet"]
        self.assertEqual("inline", packet["form"])
        self.assertEqual("ticket", packet["durability"])
        self.assertIn("inline sealed assignment", packet["prompt"])
        self.assertNotIn("tickets.py result", packet["prompt"])
        self.assertTrue(packet["inline"]["envelope_seal"].startswith("sha256:"))
        self.assertEqual("outcome", packet["outcome_record_id"])
        self.assertIn("dispatch-outcome", packet["prompt"])

        missing = str(Path(self.temporary.name) / "not-mounted")
        before = self.ticket_state()
        with mock.patch.dict(os.environ, {"ORCHFLOWS_STATE_HOME": missing}):
            refusal = self.receive(packet)
        self.assertEqual("state-inaccessible", refusal["code"])
        self.assertEqual(before, self.ticket_state())

    def test_accepted_receipt_is_a_durable_replayable_attempt_record(self):
        packet = self.project()["packet"]

        accepted = self.receive(packet)
        self.assertEqual("accepted", accepted["receipt"]["outcome"])
        self.assertTrue(accepted["receipt"]["state_sink_checked"])

        records = self.ticket_state()["attempts"][0]["records"]
        self.assertEqual(
            ["dispatch-packet", "dispatch-receipt"],
            [item["record_id"] for item in records],
        )
        receipt_record = records[-1]
        self.assertEqual("receipt", receipt_record["kind"])
        self.assertEqual(accepted, receipt_record["success"])
        self.assertEqual(accepted, self.receive(packet))
        self.assertEqual(2, len(self.ticket_state()["attempts"][0]["records"]))

    def test_result_outcome_and_join_require_the_accepted_receipt(self):
        packet = self.project()["packet"]
        outcome = {
            "assignment_seal": self.assignment_seal,
            "by": "worker",
            "dispatch_id": "D1",
            "evidence": {
                "Result": "delivered",
                "Verification": "verified",
                "Feedback": "[]",
                "Risks": "[]",
                "Handoff": "",
            },
            "id": "T",
            "outcome_record_id": "outcome",
            "protocol": "orchflows.dispatch.v1",
            "run": "run",
            "status": "complete",
        }
        operations = (
            [
                "result", "run", "T", "--assignment-seal", self.assignment_seal,
                "--dispatch-id", "D1", "--record-id", "result-1",
                "--by", "worker", "--section", "Result", "--text", "delivered",
            ],
            [
                "dispatch-outcome", "run", "T", "--content",
                canonical_json(outcome),
            ],
            [
                "dispatch-join", "run", "T", "--assignment-seal",
                self.assignment_seal, "--dispatch-id", "D1",
                "--outcome-record-id", "outcome", "--by", "root",
            ],
        )
        before = self.ticket_bytes()
        for operation in operations:
            with self.subTest(operation=operation[0]):
                refusal = tickets._dispatch(operation)
                self.assertEqual("receipt-required", refusal["code"], refusal)
                self.assertEqual(before, self.ticket_bytes())

        self.assertEqual("accepted", self.receive(packet)["receipt"]["outcome"])
        committed = tickets._dispatch(operations[0])
        self.assertNotIn("error", committed, committed)

    def test_file_and_standard_input_carry_the_packet_without_shell_reconstruction(self):
        packet = self.project()["packet"]
        path = Path(self.temporary.name) / "packet.json"
        path.write_text(canonical_json(packet), encoding="utf-8")

        accepted = self.receive_file(path)
        self.assertEqual("accepted", accepted["receipt"]["outcome"])

        script = Path(__file__).resolve().parents[1] / "scripts" / "tickets.py"
        completed = subprocess.run(
            [
                sys.executable, str(script), "dispatch-receive", "--file", "-",
                "--role", "worker", "--profile", "orch-worker", "--by", "worker",
                "--reply-to", "root", "--workspace", "C:/candidate",
            ],
            input=canonical_json(packet).encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertEqual(accepted, json.loads(completed.stdout.decode("ascii")))

    def test_wrapper_and_malformed_file_refuse_without_ticket_mutation(self):
        packet = self.project()["packet"]
        path = Path(self.temporary.name) / "packet.json"
        before = self.ticket_bytes()

        path.write_text(canonical_json({"packet": packet}), encoding="utf-8")
        wrapper = self.receive_file(path)
        self.assertEqual("packet-invalid", wrapper["code"])
        self.assertIn(".packet", wrapper["error"])
        self.assertEqual(before, self.ticket_bytes())

        path.write_bytes(b'{"protocol":"orchflows.dispatch.v1","prompt":"\x97"}')
        malformed = self.receive_file(path)
        self.assertEqual("packet-invalid", malformed["code"])
        self.assertEqual(before, self.ticket_bytes())

    def test_packet_command_emits_codepage_independent_canonical_ascii(self):
        packet = self.project()["packet"]
        self.assertIn("—", packet["prompt"])
        script = Path(__file__).resolve().parents[1] / "scripts" / "tickets.py"
        completed = subprocess.run(
            [
                sys.executable, str(script), "dispatch-packet", "run", "T",
                "--dispatch-id", "D1", "--reply-to", "root",
                "--workspace", "C:/candidate", "--form", "reference",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        decoded = completed.stdout.decode("ascii")
        response = json.loads(decoded)
        self.assertEqual(packet, response["packet"])
        expected = json.dumps(
            response, ensure_ascii=True, separators=(",", ":"), sort_keys=True,
        ) + "\n"
        self.assertEqual(expected, decoded)

    def test_ticket_inline_cannot_be_downgraded_to_ephemeral(self):
        packet = self.project(form="inline")["packet"]
        packet["durability"] = "ephemeral"
        missing = str(Path(self.temporary.name) / "not-mounted")
        with mock.patch.dict(os.environ, {"ORCHFLOWS_STATE_HOME": missing}):
            refusal = self.receive(packet)
        self.assertEqual("assignment-divergent", refusal["code"])

    def test_reference_ticket_packet_cannot_be_downgraded_to_ephemeral(self):
        packet = self.project()["packet"]
        before = self.ticket_bytes()
        packet["durability"] = "ephemeral"

        refusal = self.receive(packet)

        self.assertEqual("idempotency-conflict", refusal["code"])
        self.assertIn("not the committed projection", refusal["error"])
        self.assertEqual(before, self.ticket_bytes())

    def test_reference_without_state_sink_is_a_structured_refusal(self):
        packet = self.project()["packet"]
        missing = str(Path(self.temporary.name) / "not-mounted")
        with mock.patch.dict(os.environ, {"ORCHFLOWS_STATE_HOME": missing}):
            refusal = self.receive(packet)
        self.assertEqual("state-inaccessible", refusal["code"])

    def test_receipt_refuses_identity_profile_and_authority_mismatches(self):
        packet = self.project()["packet"]
        cases = (
            ({"by": "other"}, "identity-mismatch"),
            ({"role": "planner"}, "role-mismatch"),
            ({"profile": "orch-planner"}, "profile-mismatch"),
            ({"reply_to": "other"}, "authority-mismatch"),
            ({"workspace": "C:/other"}, "authority-mismatch"),
        )
        for overrides, code in cases:
            with self.subTest(overrides=overrides):
                refusal = self.receive(packet, **overrides)
                self.assertEqual(code, refusal["code"], refusal)

    def test_committed_projection_replay_precedes_retirement_and_conflict(self):
        committed = self.project()
        self.dispatch(
            "dispatch-retire", "run", "T",
            "--assignment-seal", self.assignment_seal,
            "--dispatch-id", "D1", "--record-id", "lifecycle:retire-1",
        )

        self.assertEqual(committed, self.project())
        changed = tickets._dispatch([
            "dispatch-packet", "run", "T", "--dispatch-id", "D1",
            "--reply-to", "other", "--workspace", "C:/candidate",
            "--form", "reference",
        ])
        self.assertEqual("idempotency-conflict", changed["code"])

    def test_inline_tampering_and_reference_divergence_refuse(self):
        inline = self.project(form="inline")["packet"]
        inline["inline"]["assignment"]["semantic"]["goal"] = "Changed."
        self.assertEqual("assignment-divergent", self.receive(inline)["code"])

        self.tearDown()
        self.setUp()
        routing = self.project(form="inline")["packet"]
        routing["executor"] = "orch-repair"
        missing = str(Path(self.temporary.name) / "not-mounted")
        with mock.patch.dict(os.environ, {"ORCHFLOWS_STATE_HOME": missing}):
            refusal = self.receive(routing)
        self.assertEqual("assignment-divergent", refusal["code"])

        self.tearDown()
        self.setUp()
        origin = self.project(form="inline")["packet"]
        origin["source"]["run"] = "missing"
        missing = str(Path(self.temporary.name) / "not-mounted")
        with mock.patch.dict(os.environ, {"ORCHFLOWS_STATE_HOME": missing}):
            refusal = self.receive(origin)
        self.assertEqual("assignment-divergent", refusal["code"])

        self.tearDown()
        self.setUp()
        reference = self.project()["packet"]
        path = Path(self.temporary.name) / "tickets" / "run" / "T.md"
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace("Deliver the behavior.", "Changed."), encoding="utf-8")
        self.assertEqual("assignment-divergent", self.receive(reference)["code"])


if __name__ == "__main__":
    unittest.main()
