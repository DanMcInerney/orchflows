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

    def commit(self, dispatch_id="D1", record_id="R1", content='{"value":1}'):
        return tickets._dispatch([
            "dispatch-commit", "run", "T",
            "--dispatch-id", dispatch_id,
            "--record-id", record_id,
            "--content", content,
        ])

    def retire(self, dispatch_id="D1"):
        return tickets._dispatch([
            "dispatch-retire", "run", "T", "--dispatch-id", dispatch_id,
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
        self.assertNotIn("error", self.open())
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


if __name__ == "__main__":
    unittest.main()
