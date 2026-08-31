"""Deterministic routing grades for issued ticket graphs."""

from __future__ import annotations

import unittest
import os
import tempfile
from pathlib import Path
from unittest import mock

from scripts import tickets
from scripts import tickets_grade
from scripts.tickets_grade import grade_snapshot, GradeError
from scripts import tickets_review


def ticket(ticket_id: str, executor: str, *, goal: str = "Deliver the result.", context: str = "The repository is fixed.", loop: str = "", done: str = "") -> str:
    return "\n".join((
        "---",
        f"id: {ticket_id}",
        f"executor: {executor}",
        *((f"loop: {loop}",) if loop else ()),
        *((f"done: {done}",) if done else ()),
        "pack: orch-code-pack",
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
    def test_graph_grade_counts_executor_members_and_reports_pack_fields(self):
        snapshot = {
            "R": ticket(
                "R", "orch-slice",
                goal="Deliver an observable result for the target repository.",
                context="The standards owner is documented by pointer.",
            ),
            "R.01": ticket("R.01", "orch-tdd"),
            "R.02": ticket("R.02", "orch-tdd"),
            "R.03": ticket("R.03", "orch-tdd"),
            "R.04": ticket("R.04", "orch-tdd"),
            "R.gate.critique.code": ticket("R.gate.critique.code", "orch-critique"),
        }
        self.assertEqual(
            {
                "width": 4,
                "shape": "graph",
                "unmentioned_spec_fields": [],
                "deterministic_gate": True,
                "over_decomposed": False,
            },
            grade_snapshot("R", snapshot),
        )

    def test_one_member_decomposition_is_refused(self):
        snapshot = {
            "R": ticket("R", "orch-slice"),
            "R.01": ticket("R.01", "orch-tdd"),
        }
        with self.assertRaisesRegex(GradeError, "over-decomposition"):
            grade_snapshot("R", snapshot)

    def test_direct_and_loop_shapes_have_one_result_width(self):
        direct = {"R": ticket("R", "orch-tdd")}
        loop = {"R": ticket(
            "R", "orch-do",
            loop="true", done='{"form":"command","value":"exit 0"}',
        )}
        self.assertEqual("single", grade_snapshot("R", direct)["shape"])
        self.assertEqual(1, grade_snapshot("R", direct)["width"])
        self.assertEqual("loop", grade_snapshot("R", loop)["shape"])
        self.assertEqual(1, grade_snapshot("R", loop)["width"])

    def test_the_ledger_ends_at_the_repair_and_admits_no_verification_record(self):
        """The chain's last link is `RepairOutcome`.

        A `Verification` record carried a prose verdict a join parsed out of
        a child's evidence. There is no such verdict: land runs the ticket's
        `done` predicate and an exit code answers, so the record kind is not
        one the schema knows and a ledger appending one is refused.
        """

        plan = tickets_review._record(
            "GatePlan", None, artifact="artifact", criteria=[{
                "identity": "sha256:criterion", "lens": "code",
                "order": 0, "ticket": "R.gate.critique.code",
            }], isolation="none", mode="gate", pack="orch-code-pack",
            root="R", workspace=str(Path.cwd()),
        )
        finding = {
            "blocking": False, "class": "correctness", "evidence": ["e"],
            "goal_impact": "none", "id": "B1", "repair": "none",
            "summary": "none",
        }
        adjudication = tickets_review._record(
            "CritiqueAdjudication", plan["identity"], accepted=[],
            adjudicated_by="agent", artifact="artifact", findings=[finding],
            lens="code",
        )
        repair = tickets_review._record(
            "RepairOutcome", adjudication["identity"], accepted=[],
            artifact="artifact", by="agent", input_artifact="artifact",
            no_op=True, result="none",
        )
        closed = tickets_review._review_state([plan, adjudication, repair])
        self.assertEqual(repair, closed["records"][-1])
        self.assertFalse(hasattr(tickets_review, "verification_outcome"))

        with self.assertRaises(tickets_review.ReviewError):
            tickets_review._review_state([
                plan, adjudication, repair,
                tickets_review._record(
                    "Verification", repair["identity"], artifact="artifact",
                    by="agent", evidence="PASS: unchanged", verdict="PASS",
                ),
            ])

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
        self.environment = mock.patch.dict(
            os.environ, {"ORCHFLOWS_STATE_HOME": self.temporary.name}
        )
        self.environment.start()

    def tearDown(self):
        self.environment.stop()
        self.temporary.cleanup()

    def test_grade_command_reads_one_exact_run_snapshot(self):
        run_dir = Path(self.temporary.name) / "tickets" / "run"
        run_dir.mkdir(parents=True)
        (run_dir / "R.md").write_text(ticket(
            "R", "orch-slice",
            goal="Deliver an observable result for the target repository.",
            context="The standards owner is documented by pointer.",
        ), encoding="utf-8")
        for item in ("R.01", "R.02"):
            (run_dir / f"{item}.md").write_text(
                ticket(item, "orch-tdd"), encoding="utf-8"
            )
        result = tickets._dispatch(["grade", "run", "R"])
        self.assertNotIn("error", result, result)
        self.assertEqual(2, result["grade"]["width"])
        self.assertEqual("graph", result["grade"]["shape"])


if __name__ == "__main__":
    unittest.main()
