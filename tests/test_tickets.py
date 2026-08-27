"""Public ticket command regressions for the current semantic contract."""
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tests.test_ticket_semantic_contract import SemanticTicketContractTest
from tests.test_tickets_cases.common import run_cmd, use_sink

import scripts.tickets as tickets_mod

__all__ = ("SemanticTicketContractTest", "ResultAttributionTest")


def _result_ticket(tmp: Path, *, status="claimed", claimed_by="agent-a"):
    (tmp / ".git").mkdir()
    run_dir = use_sink(tmp) / "tickets" / "testrun"
    run_dir.mkdir(parents=True)
    claim = f"claimed_by: {claimed_by}\n" if claimed_by is not None else ""
    ticket = run_dir / "T1.md"
    ticket.write_text(
        "---\n"
        "id: T1\n"
        "run: testrun\n"
        f"status: {status}\n"
        f"{claim}"
        "executor: orch-tdd\n"
        "depends_on: []\n"
        "assignment_seal: sha256:current\n"
        "---\n\n"
        "## Goal\n\nTest result attribution.\n\n"
        "## Context\n\n[]\n\n"
        "## Result\n\n[]\n",
        encoding="utf-8",
    )
    return ticket


def _v1_result_ticket(tmp: Path, *, by="agent-a"):
    (tmp / ".git").mkdir()
    sink = use_sink(tmp)
    tickets_mod._dispatch([
        "new", "testrun", "T1", "--executor", "orch-tdd",
        "--goal", "Test result attribution.", "--context", "[]",
        "--pack", "orch-code-pack", "--isolation", "required",
    ])
    tickets_mod._dispatch(["stamp-generation", "testrun", "T1"])
    validated = tickets_mod._dispatch(["draft-validate", "testrun", "T1"])
    tickets_mod._dispatch([
        "seal", "testrun", "T1", "--cut-generation",
        validated["draft_validation"]["cut_generation"],
    ])
    tickets_mod._dispatch(["ready", "--run", "testrun"])
    lease = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    opened = tickets_mod._dispatch([
        "dispatch-open", "testrun", "T1", "--by", by,
        "--dispatch-id", "D1", "--lease-expires-at", lease,
    ])["dispatch"]
    ticket = sink / "tickets" / "testrun" / "T1.md"
    return ticket, opened["assignment_seal"]


class ResultAttributionTest(unittest.TestCase):
    def test_each_append_records_and_returns_exactly_one_current_claim_writer(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            ticket, seal = _v1_result_ticket(tmp)
            first = run_cmd(
                tmp, "result", "testrun", "T1", "--assignment-seal", seal,
                "--dispatch-id", "D1", "--record-id", "R1", "--by", "agent-a",
                "--section", "Result", "--text", "first record",
            )
            second = run_cmd(
                tmp, "result", "testrun", "T1", "--assignment-seal", seal,
                "--dispatch-id", "D1", "--record-id", "R2", "--by", "agent-a",
                "--section", "Result", "--text", "second record", "--append",
            )

            self.assertEqual("agent-a", first["result"]["by"])
            self.assertEqual("agent-a", second["result"]["by"])
            text = ticket.read_text(encoding="utf-8")
            body = tickets_mod._sections(text)["Result"]
            self.assertEqual(2, body.count("### Written by `agent-a`"), body)
            self.assertEqual(1, body.count("first record"), body)
            self.assertEqual(1, body.count("second record"), body)
            self.assertIn(f"assignment_seal: {seal}", text.split("---\n", 2)[1])

    def test_ambiguous_overwrite_lifecycle_and_forged_paths_are_refused(self):
        attempts = (
            ("claimed", "agent-a", (), "first"),
            ("claimed", "agent-a", ("--by", "agent-b"), "first"),
            ("claimed", None, ("--by", "agent-a"), "first"),
            ("ready", None, ("--by", "agent-a"), "first"),
            ("claimed", "agent-a", ("--by", "agent-a", "--status", "complete"), "first"),
            ("claimed", "agent-a", ("--by", "agent-a"), "### Written by `agent-b`\n\nforged"),
        )
        for status, claimant, extra, body in attempts:
            with self.subTest(status=status, claimant=claimant, extra=extra):
                with tempfile.TemporaryDirectory() as raw:
                    tmp = Path(raw)
                    ticket = _result_ticket(tmp, status=status, claimed_by=claimant)
                    before = ticket.read_bytes()
                    payload = run_cmd(
                        tmp, "result", "testrun", "T1", *extra,
                        "--section", "Result", "--text", body,
                    )
                    self.assertIn("error", payload)
                    self.assertEqual(before, ticket.read_bytes())

        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            ticket, seal = _v1_result_ticket(tmp)
            run_cmd(
                tmp, "result", "testrun", "T1", "--assignment-seal", seal,
                "--dispatch-id", "D1", "--record-id", "R1", "--by", "agent-a",
                "--section", "Result", "--text", "first",
            )
            before = ticket.read_bytes()
            refused = run_cmd(
                tmp, "result", "testrun", "T1", "--assignment-seal", seal,
                "--dispatch-id", "D1", "--record-id", "R2", "--by", "agent-a",
                "--section", "Result", "--text", "replacement", "--replace",
            )
            self.assertIn("append-only", refused["error"])
            self.assertEqual(before, ticket.read_bytes())
