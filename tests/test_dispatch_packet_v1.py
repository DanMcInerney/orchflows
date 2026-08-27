"""Committed dispatch-v1 packet projection and receipt regressions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts import tickets
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

    def project(self, form="reference"):
        return tickets._dispatch([
            "dispatch-packet", "run", "T", "--dispatch-id", "D1",
            "--reply-to", "root", "--workspace", "C:/candidate",
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

    def ticket_state(self):
        path = Path(self.temporary.name) / "tickets" / "run" / "T.md"
        encoded = next(
            line.partition(":")[2].strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.startswith("dispatch_v1:")
        )
        return parse_canonical_json(encoded)

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

        self.assertEqual(first, self.project())
        records = self.ticket_state()["attempts"][0]["records"]
        self.assertEqual(["dispatch-packet"], [item["record_id"] for item in records])

        receipt = self.receive(packet)
        self.assertEqual("accepted", receipt["receipt"]["outcome"])
        self.assertEqual("reference", receipt["receipt"]["form"])

    def test_inline_snapshot_receives_without_the_state_sink(self):
        packet = self.project(form="inline")["packet"]
        self.assertEqual("inline", packet["form"])
        self.assertEqual("ticket", packet["durability"])
        self.assertIn("inline sealed assignment", packet["prompt"])
        self.assertNotIn("tickets.py result", packet["prompt"])
        self.assertEqual(
            packet["assignment_seal"], packet["inline"]["assignment_seal"]
        )

        missing = str(Path(self.temporary.name) / "not-mounted")
        with mock.patch.dict(os.environ, {"ORCHFLOWS_STATE_HOME": missing}):
            receipt = self.receive(packet)
        self.assertEqual("accepted", receipt["receipt"]["outcome"])
        self.assertFalse(receipt["receipt"]["state_sink_checked"])

    def test_packet_only_inline_is_explicitly_ephemeral(self):
        packet = self.project(form="inline")["packet"]
        packet["durability"] = "ephemeral"
        packet.pop("source")
        missing = str(Path(self.temporary.name) / "not-mounted")
        with mock.patch.dict(os.environ, {"ORCHFLOWS_STATE_HOME": missing}):
            receipt = self.receive(packet)
        self.assertEqual("accepted", receipt["receipt"]["outcome"])
        self.assertEqual("ephemeral", receipt["receipt"]["durability"])
        self.assertFalse(receipt["receipt"]["state_sink_checked"])

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
            "--dispatch-id", "D1", "--record-id", "retire-1",
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
        reference = self.project()["packet"]
        path = Path(self.temporary.name) / "tickets" / "run" / "T.md"
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace("Deliver the behavior.", "Changed."), encoding="utf-8")
        self.assertEqual("assignment-divergent", self.receive(reference)["code"])


if __name__ == "__main__":
    unittest.main()
