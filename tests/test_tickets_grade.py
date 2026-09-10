"""Deterministic routing grades for issued ticket graphs."""

from __future__ import annotations

import unittest
import os
import tempfile
from pathlib import Path
from unittest import mock

from scripts import state_root
from scripts import tickets
from scripts import tickets_grade
from scripts.tickets_grade import grade_snapshot, GradeError

from tests.test_ticket_callables import CODE_STANDARD, standards_field


def ticket(ticket_id: str, executor: str, *, goal: str = "Deliver the result.", context: str = "The repository is fixed.", loop: str = "", done: str = "") -> str:
    return "\n".join((
        "---",
        f"id: {ticket_id}",
        f"executor: {executor}",
        *((f"loop: {loop}",) if loop else ()),
        *((f"done: {done}",) if done else ()),
        "standards: [" + ", ".join(standards_field(CODE_STANDARD)) + "]",
        "---",
        "",
        "## Goal",
        goal,
        "",
        "## Context",
        context,
        "",
    ))


class GradeSnapshotTest(unittest.TestCase):
    def test_a_root_with_executor_result_members_is_refused(self):
        """The graph shape retired with `orch-slice`, its only minter: a
        root's own descendants are review plumbing or nothing, never
        independent executor-result members grade still counts."""

        snapshot = {
            "R": ticket(
                "R", "orch-tdd",
                goal="Deliver an observable result for the target repository.",
                context="The standards owner is documented by pointer.",
            ),
            "R.01": ticket("R.01", "orch-tdd"),
            "R.02": ticket("R.02", "orch-tdd"),
        }
        with self.assertRaisesRegex(GradeError, "direct root with executor-result members"):
            grade_snapshot("R", snapshot)

    def test_one_member_decomposition_is_refused(self):
        snapshot = {
            "R": ticket("R", "orch-tdd"),
            "R.01": ticket("R.01", "orch-tdd"),
        }
        with self.assertRaisesRegex(GradeError, "direct root with executor-result members"):
            grade_snapshot("R", snapshot)

    def test_a_direct_root_has_one_result_width(self):
        """`loop` was the third shape; there is no loop lane to grade.

        A ticket carrying a `done` predicate is graded `single` like any
        other direct root -- the predicate says what `land` evaluates, not
        what shape the graph is.
        """

        direct = {"R": ticket("R", "orch-tdd")}
        with_done = {"R": ticket(
            "R", "orch-do", done='{"form":"command","value":"exit 0"}',
        )}
        self.assertEqual("single", grade_snapshot("R", direct)["shape"])
        self.assertEqual(1, grade_snapshot("R", direct)["width"])
        self.assertEqual("single", grade_snapshot("R", with_done)["shape"])
        self.assertEqual(1, grade_snapshot("R", with_done)["width"])

    def test_the_legacy_review_protocol_is_rejected(self):
        """A reused module name must not restore the retired ledger protocol."""
        import importlib
        from scripts import tickets_format
        with self.assertRaises(ModuleNotFoundError):
            importlib.import_module("scripts.tickets_review")
        with self.assertRaises(ModuleNotFoundError):
            importlib.import_module("scripts.tickets_review_schema")
        legacy = ticket("B1", "orch-do").replace(
            "executor: orch-do", 'executor: orch-do\nreview_v1: {"GatePlan":{},"CritiqueAdjudication":{}}')
        defect = "unknown ticket frontmatter field 'review_v1'"
        self.assertIn(defect, tickets_format.ticket_defects(legacy))
        # Contrary schema reading: admitting the legacy field defeats this
        # retirement guard, without modifying the source under test.
        with mock.patch.object(tickets_format, "ALLOWED_TICKET_KEYS",
                               tickets_format.ALLOWED_TICKET_KEYS | {"review_v1"}):
            self.assertNotIn(defect, tickets_format.ticket_defects(legacy))

    def test_no_reader_reconstructs_a_verdict_out_of_a_report(self):
        """The fixed-result probe is gone, not repointed.

        It read a stored `PASS`/`FAIL` and covers list out of two homes that
        no longer exist -- a `Verification` review record the ledger stopped
        admitting, and a `## Verification` section the one-channel return
        replaced. A reader of a shape nothing writes reuses nothing, so
        `gate` materializes and nothing scrapes a verdict out of prose.
        """

        self.assertFalse(hasattr(tickets_grade, "fixed_gate_snapshot"))
        self.assertFalse(hasattr(tickets, "_cmd_fixed_gate"))


class GradeCommandTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        # ORCHFLOWS_WORKTREES_HOME rides beside the sink: unset, a derived
        # candidate would hang off the parent of a bare tempdir -- the
        # machine-shared system temp root -- instead of staying inside
        # this fixture's own tree.
        self.environment = mock.patch.dict(
            os.environ,
            {
                state_root.ENV_VAR: self.temporary.name,
                "ORCHFLOWS_WORKTREES_HOME": str(
                    Path(self.temporary.name) / "worktrees"
                ),
            },
        )
        self.environment.start()

    def tearDown(self):
        self.environment.stop()
        self.temporary.cleanup()

    def test_grade_command_reads_one_exact_run_snapshot(self):
        run_dir = Path(self.temporary.name) / "tickets" / "run"
        run_dir.mkdir(parents=True)
        (run_dir / "R.md").write_text(ticket(
            "R", "orch-tdd",
            goal="Deliver an observable result for the target repository.",
            context="The standards owner is documented by pointer.",
        ), encoding="utf-8")
        result = tickets._dispatch(["grade", "run", "R"])
        self.assertNotIn("error", result, result)
        self.assertEqual(1, result["grade"]["width"])
        self.assertEqual("single", result["grade"]["shape"])


if __name__ == "__main__":
    unittest.main()
