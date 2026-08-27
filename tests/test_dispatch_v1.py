"""Atomic execution-attempt and committed-record protocol regressions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts import tickets
from scripts.tickets_format import parse_canonical_json


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


if __name__ == "__main__":
    unittest.main()
