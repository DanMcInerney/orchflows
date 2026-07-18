"""Ticket script: the `suspended` status is a valid non-terminal wait
(contracts/work-item.md) — set-status accepts it, unknown statuses are
still rejected, and a suspended ticket keeps its claim on disk."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.tickets as tickets_mod  # noqa: E402

TICKETS_PY = ROOT / "scripts" / "tickets.py"

TICKET = """---
id: T1
run: testrun
status: claimed
executor: orch-tdd
depends_on: []
write_scope: scratch/T1.txt
bound: 30m
claimed_by: agent-a
claimed_at: 2026-07-18T00:00:00Z
---

## Objective

Test ticket.
"""


def make_repo(tmp: Path) -> Path:
    (tmp / ".git").mkdir()
    run_dir = tmp / ".orch" / "tickets" / "testrun"
    run_dir.mkdir(parents=True)
    (run_dir / "T1.md").write_text(TICKET, encoding="utf-8")
    return run_dir


def run_full(cwd: Path, *args):
    return subprocess.run(
        [sys.executable, str(TICKETS_PY), *args],
        capture_output=True, text=True, encoding="utf-8",
        errors="replace", cwd=str(cwd),
    )


class TestSuspendedStatus(unittest.TestCase):
    def test_suspended_is_a_valid_status(self):
        self.assertIn("suspended", tickets_mod.VALID_STATUSES)

    def test_set_status_accepts_suspended_and_keeps_the_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_repo(tmp)
            result = run_full(tmp, "set-status", "testrun", "T1", "suspended")
            self.assertEqual(0, result.returncode)
            payload = json.loads(result.stdout)
            self.assertEqual("suspended", payload["set_status"]["status"])
            text = (run_dir / "T1.md").read_text(encoding="utf-8")
            self.assertIn("status: suspended", text)
            # the ticket stays claimed: the claim fields survive suspension
            self.assertIn("claimed_by: agent-a", text)
            self.assertIn("claimed_at: 2026-07-18T00:00:00Z", text)

    def test_set_status_still_rejects_an_unknown_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_repo(tmp)
            result = run_full(tmp, "set-status", "testrun", "T1", "paused")
            self.assertEqual(0, result.returncode)
            payload = json.loads(result.stdout)
            self.assertIn("error", payload)
            self.assertIn("status: claimed", (run_dir / "T1.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
