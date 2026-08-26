"""The one-shot errand command authors one admitted delivery ticket."""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import tickets, tickets_errand
from tests.test_tickets_cases.common import repo_root_of, use_sink


def git(repo: Path, *args):
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    )


def repository(root: Path) -> Path:
    repo = root / "repo"
    repo.mkdir()
    git(repo, "init")
    git(repo, "config", "user.email", "errand@example.test")
    git(repo, "config", "user.name", "Errand Test")
    (repo / "README.md").write_text("baseline\n", encoding="utf-8")
    git(repo, "add", "README.md")
    git(repo, "commit", "-m", "baseline")
    return repo


def dispatch(repo: Path, *args):
    with repo_root_of(repo):
        return tickets._dispatch([str(arg) for arg in args])


def ticket_text(sink: Path, run="run", ticket_id="job") -> str:
    return (sink / "tickets" / run / f"{ticket_id}.md").read_text(
        encoding="utf-8"
    )


class ErrandAuthoringTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.sink = use_sink(self.root)
        self.repo = repository(self.root)

    def tearDown(self):
        self.temporary.cleanup()

    def test_a_pre_existing_oracle_authors_one_ready_admitted_worker_ticket(self):
        payload = dispatch(
            self.repo,
            "errand", "run", "job",
            "--task", "Add the small formatter.",
            "--executor", "orch-tdd",
            "--path", "scripts/formatter.py",
            "--bound", "20m",
            "--pre-existing-oracle", "unit=uv run --no-project python -m unittest -v tests.test_formatter",
        )
        self.assertNotIn("error", payload, payload)
        self.assertEqual(["job"], payload["errand"]["ids"])
        self.assertEqual("ready", payload["errand"]["status"])
        text = ticket_text(self.sink)
        data = tickets._parse_frontmatter(text)
        self.assertEqual("ready", data["status"])
        self.assertRegex(data["admission"], r"^v1:git:sha256:[0-9a-f]{64}$")
        self.assertEqual("orch-tdd", data["executor"])
        self.assertEqual("orch-code-pack", data["pack"])
        self.assertEqual(["scripts/formatter.py"], data["write_scope"])
        self.assertEqual(["create:scripts/formatter.py"], data["mutations"])
        self.assertEqual("20m", data["bound"])
        self.assertNotIn("checked_by", data)
        self.assertIn('"name":"simple-task"', text)
        self.assertIn('"name":"unit"', text)
        self.assertIn("provenance: pre-existing", text)
        self.assertEqual(
            ["job.md"],
            sorted(path.name for path in (self.sink / "tickets" / "run").glob("*.md")),
        )

    def test_tdd_errand_requires_its_own_workspace_from_either_checkout_kind(self):
        for caller_is_isolated in (False, True):
            with self.subTest(caller_is_isolated=caller_is_isolated):
                ticket_id = f"isolated-{str(caller_is_isolated).lower()}"
                with mock.patch.object(
                    tickets_errand,
                    "_caller_is_isolated",
                    return_value=caller_is_isolated,
                ):
                    payload = dispatch(
                        self.repo,
                        "errand", "run", ticket_id,
                        "--task", "Add the small formatter.",
                        "--executor", "orch-tdd",
                        "--path", "scripts/formatter.py",
                        "--bound", "20m",
                        "--pre-existing-oracle", "unit=uv run --no-project python -m unittest -v tests.test_formatter",
                    )
                self.assertNotIn("error", payload, payload)
                data = tickets._parse_frontmatter(
                    ticket_text(self.sink, ticket_id=ticket_id)
                )
                self.assertEqual("required", data["isolation"])

    def test_an_ordered_sequence_keeps_its_head_as_executor(self):
        payload = dispatch(
            self.repo,
            "errand", "run", "chain",
            "--task", "Add and admit the helper.",
            "--sequence", "orch-tdd,orch-build",
            "--path", "scripts/helper.py",
            "--bound", "30m",
            "--born-red-oracle", "unit=uv run --no-project python -m unittest -v tests.test_helper",
        )
        self.assertNotIn("error", payload, payload)
        data = tickets._parse_frontmatter(ticket_text(self.sink, ticket_id="chain"))
        self.assertEqual("orch-tdd", data["executor"])
        self.assertEqual(["orch-tdd", "orch-build"], data["sequence"])

    def test_an_authored_here_oracle_selects_the_existing_same_claim_checker(self):
        payload = dispatch(
            self.repo,
            "errand", "run", "checked",
            "--task", "Add a behavior and its test.",
            "--executor", "orch-tdd",
            "--path", "scripts/behavior.py",
            "--path", "tests/test_behavior.py",
            "--bound", "30m",
            "--authored-here-oracle", "unit=uv run --no-project python -m unittest -v tests.test_behavior",
        )
        self.assertNotIn("error", payload, payload)
        text = ticket_text(self.sink, ticket_id="checked")
        data = tickets._parse_frontmatter(text)
        self.assertEqual("checker", data["independence"])
        self.assertIn("provenance: authored-here", text)
        claim = dispatch(self.repo, "claim", "run", "checked", "--by", "worker-a")
        self.assertNotIn("error", claim, claim)
        checker = dispatch(
            self.repo, "packet", "run", "checked", "--reply-to", "root",
            "--by", "checker-a", "--executor", "orch-critique",
        )
        self.assertNotIn("error", checker, checker)
        self.assertEqual("orch-critique", checker["packet"]["executor"])

    def test_a_refused_errand_writes_no_ticket(self):
        payload = dispatch(
            self.repo,
            "errand", "run", "bad",
            "--task", "Escape the repository.",
            "--executor", "orch-tdd",
            "--path", "../outside.py",
            "--bound", "20m",
            "--pre-existing-oracle", "unit=uv run --no-project python -m unittest",
        )
        self.assertIn("error", payload)
        run_dir = self.sink / "tickets" / "run"
        self.assertFalse(run_dir.exists() and any(run_dir.glob("*.md")))


if __name__ == "__main__":
    unittest.main()
