"""Ticket script: pending promotion, status enum, and adversarial coverage
(claim races, malformed input, repo-boundary errors)."""

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.tickets as tickets_mod  # noqa: E402

TICKETS_PY = ROOT / "scripts" / "tickets.py"

TICKET = """---
id: {tid}
run: testrun
status: {status}
executor: orch-tdd
depends_on: {deps}
write_scope: scratch/{tid}.txt
bound: 30m
---

## Objective

Test ticket.
"""


def make_repo(tmp: Path, tickets: dict) -> Path:
    (tmp / ".git").mkdir()
    run_dir = tmp / ".orch" / "tickets" / "testrun"
    run_dir.mkdir(parents=True)
    for tid, (status, deps) in tickets.items():
        (run_dir / f"{tid}.md").write_text(
            TICKET.format(tid=tid, status=status, deps=deps), encoding="utf-8"
        )
    return run_dir


def run_full(cwd: Path, *args):
    return subprocess.run(
        [sys.executable, str(TICKETS_PY), *args],
        capture_output=True, text=True, encoding="utf-8",
        errors="replace", cwd=str(cwd),
    )


def run_cmd(cwd: Path, *args):
    return json.loads(run_full(cwd, *args).stdout)


class TestPendingPromotion(unittest.TestCase):
    def test_pending_with_complete_deps_is_promoted_and_persisted(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_repo(tmp, {
                "T1": ("complete", "[]"),
                "T2": ("pending", "[T1]"),
            })
            payload = run_cmd(tmp, "ready", "--run", "testrun")
            ids = [t["id"] for t in payload["ready"]]
            self.assertEqual(["T2"], ids)
            self.assertEqual("ready", payload["ready"][0]["status"])
            self.assertIn("status: ready", (run_dir / "T2.md").read_text(encoding="utf-8"))

    def test_pending_with_incomplete_deps_stays_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_repo(tmp, {
                "T1": ("ready", "[]"),
                "T2": ("pending", "[T1]"),
            })
            payload = run_cmd(tmp, "ready", "--run", "testrun")
            ids = sorted(t["id"] for t in payload["ready"])
            self.assertEqual(["T1"], ids)
            self.assertIn("status: pending", (run_dir / "T2.md").read_text(encoding="utf-8"))

    def test_set_status_accepts_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_repo(tmp, {"T1": ("ready", "[]")})
            payload = run_cmd(tmp, "set-status", "testrun", "T1", "pending")
            self.assertEqual("pending", payload["set_status"]["status"])
            self.assertIn("status: pending", (run_dir / "T1.md").read_text(encoding="utf-8"))


class TestClaim(unittest.TestCase):
    def test_claim_happy_path_transitions_ready_to_claimed(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_repo(tmp, {"T1": ("ready", "[]")})
            payload = run_cmd(tmp, "claim", "testrun", "T1", "--by", "agent-a")
            self.assertEqual("agent-a", payload["claimed"]["claimed_by"])
            self.assertEqual("T1", payload["claimed"]["id"])
            text = (run_dir / "T1.md").read_text(encoding="utf-8")
            self.assertIn("status: claimed", text)
            self.assertIn("claimed_by: agent-a", text)
            self.assertRegex(text, r"claimed_at: \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")

    def test_claim_on_fresh_claim_is_rejected_not_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, {"T1": ("ready", "[]")})
            first = run_cmd(tmp, "claim", "testrun", "T1", "--by", "agent-a")
            self.assertIn("claimed", first)
            second = run_cmd(tmp, "claim", "testrun", "T1", "--by", "agent-b")
            self.assertIn("error", second)

    def test_stale_claim_is_reclaimed(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_repo(tmp, {"T1": ("ready", "[]")})
            ticket_path = run_dir / "T1.md"
            first = run_cmd(tmp, "claim", "testrun", "T1", "--by", "agent-a")
            self.assertIn("claimed", first)
            # backdate the claim well past the ticket's 30m bound so it reads stale
            text = ticket_path.read_text(encoding="utf-8")
            text = tickets_mod._set_frontmatter_field(text, "claimed_at", "2020-01-01T00:00:00Z")
            ticket_path.write_text(text, encoding="utf-8")
            second = run_cmd(tmp, "claim", "testrun", "T1", "--by", "agent-b")
            self.assertEqual("agent-b", second["claimed"]["claimed_by"])
            self.assertIn("claimed_by: agent-b", ticket_path.read_text(encoding="utf-8"))

    def test_two_writer_claim_race_yields_exactly_one_winner(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_repo(tmp, {"T1": ("ready", "[]")})
            ticket_path = run_dir / "T1.md"
            # Both writers "read" the identical pre-claim snapshot before either
            # writes, modelling two processes racing to claim the same ticket.
            prior_text = ticket_path.read_text(encoding="utf-8")
            now = datetime.now(timezone.utc)

            result_a = tickets_mod._do_claim(ticket_path, prior_text, "writer-a", now)
            result_b = tickets_mod._do_claim(ticket_path, prior_text, "writer-b", now)

            outcomes = [result_a, result_b]
            winners = [r for r in outcomes if "claimed" in r]
            losers = [r for r in outcomes if "error" in r]
            self.assertEqual(1, len(winners), outcomes)
            self.assertEqual(1, len(losers), outcomes)

            final_text = ticket_path.read_text(encoding="utf-8")
            winner_name = winners[0]["claimed"]["claimed_by"]
            self.assertIn(f"claimed_by: {winner_name}", final_text)
            loser_name = "writer-b" if winner_name == "writer-a" else "writer-a"
            self.assertNotIn(f"claimed_by: {loser_name}", final_text)


class TestInvalidStatus(unittest.TestCase):
    def test_set_status_rejects_invalid_status_as_error_json_exit_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_repo(tmp, {"T1": ("ready", "[]")})
            result = run_full(tmp, "set-status", "testrun", "T1", "bogus-status")
            self.assertEqual(0, result.returncode)
            payload = json.loads(result.stdout)
            self.assertIn("error", payload)
            self.assertIn("status: ready", (run_dir / "T1.md").read_text(encoding="utf-8"))


class TestMalformedFrontmatter(unittest.TestCase):
    def test_list_handles_ticket_with_no_frontmatter_delimiters(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / ".git").mkdir()
            run_dir = tmp / ".orch" / "tickets" / "testrun"
            run_dir.mkdir(parents=True)
            (run_dir / "T1.md").write_text(
                "# Not a ticket\n\nNo frontmatter delimiters at all.\n", encoding="utf-8"
            )
            result = run_full(tmp, "list", "--run", "testrun")
            self.assertEqual(0, result.returncode)
            payload = json.loads(result.stdout)
            self.assertEqual(1, len(payload["tickets"]))
            self.assertIsNone(payload["tickets"][0]["status"])

    def test_set_status_on_unterminated_frontmatter_returns_error_not_raise(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / ".git").mkdir()
            run_dir = tmp / ".orch" / "tickets" / "testrun"
            run_dir.mkdir(parents=True)
            (run_dir / "T1.md").write_text("---\nid: T1\nstatus: ready\n", encoding="utf-8")
            result = run_full(tmp, "set-status", "testrun", "T1", "complete")
            self.assertEqual(0, result.returncode)
            payload = json.loads(result.stdout)
            self.assertIn("error", payload)

    def test_claim_on_unterminated_frontmatter_returns_error_not_raise(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / ".git").mkdir()
            run_dir = tmp / ".orch" / "tickets" / "testrun"
            run_dir.mkdir(parents=True)
            (run_dir / "T1.md").write_text("---\nid: T1\nstatus: ready\n", encoding="utf-8")
            result = run_full(tmp, "claim", "testrun", "T1", "--by", "agent-a")
            self.assertEqual(0, result.returncode)
            payload = json.loads(result.stdout)
            self.assertIn("error", payload)


class TestRunFilter(unittest.TestCase):
    def test_run_filter_scopes_list_to_named_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, {"A1": ("ready", "[]")})
            other_dir = tmp / ".orch" / "tickets" / "otherrun"
            other_dir.mkdir(parents=True)
            (other_dir / "B1.md").write_text(
                "---\nid: B1\nrun: otherrun\nstatus: ready\ndepends_on: []\n"
                "write_scope: scratch/B1.txt\nbound: 30m\n---\n\n## Objective\n\nTest ticket.\n",
                encoding="utf-8",
            )

            payload_testrun = run_cmd(tmp, "list", "--run", "testrun")
            self.assertEqual(["A1"], [t["id"] for t in payload_testrun["tickets"]])

            payload_otherrun = run_cmd(tmp, "list", "--run", "otherrun")
            self.assertEqual(["B1"], [t["id"] for t in payload_otherrun["tickets"]])

            payload_all = run_cmd(tmp, "list")
            self.assertEqual(["A1", "B1"], sorted(t["id"] for t in payload_all["tickets"]))

    def test_run_filter_on_unknown_run_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, {"A1": ("ready", "[]")})
            payload = run_cmd(tmp, "list", "--run", "nonexistent-run")
            self.assertEqual([], payload["tickets"])


class TestNotInsideARepo(unittest.TestCase):
    def test_list_outside_a_repo_returns_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            # deliberately no .git anywhere under this tempdir
            result = run_full(tmp, "list")
            self.assertEqual(0, result.returncode)
            payload = json.loads(result.stdout)
            self.assertEqual({"error": "not inside a git repository"}, payload)

    def test_claim_outside_a_repo_returns_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            result = run_full(tmp, "claim", "testrun", "T1", "--by", "agent-a")
            self.assertEqual(0, result.returncode)
            payload = json.loads(result.stdout)
            self.assertEqual({"error": "not inside a git repository"}, payload)


if __name__ == "__main__":
    unittest.main()
