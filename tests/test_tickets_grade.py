"""Deterministic routing grades for issued ticket graphs."""

from __future__ import annotations

import unittest
import json
import hashlib
import os
import tempfile
from pathlib import Path
from unittest import mock

from scripts import tickets
from scripts.tickets_issue_render import _render_ticket
from scripts.tickets_format import _set_frontmatter_field
from scripts.tickets_grade import fixed_gate_snapshot, grade_snapshot, GradeError
from scripts import tickets_review


def ticket(ticket_id: str, executor: str, *, goal: str = "Deliver the result.", context: str = "The repository is fixed.", loop: str = "") -> str:
    return "\n".join((
        "---",
        f"id: {ticket_id}",
        f"executor: {executor}",
        *((f"loop: {loop}",) if loop else ()),
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
                "R", "orch-decompose",
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
            "R": ticket("R", "orch-decompose"),
            "R.01": ticket("R.01", "orch-tdd"),
        }
        with self.assertRaisesRegex(GradeError, "over-decomposition"):
            grade_snapshot("R", snapshot)

    def test_direct_and_loop_shapes_have_one_result_width(self):
        direct = {"R": ticket("R", "orch-tdd")}
        loop = {"R": ticket(
            "R", "orch-execute",
            loop='{"done":{"form":"command","value":"exit 0"}}',
        )}
        self.assertEqual("single", grade_snapshot("R", direct)["shape"])
        self.assertEqual(1, grade_snapshot("R", direct)["width"])
        self.assertEqual("loop", grade_snapshot("R", loop)["shape"])
        self.assertEqual(1, grade_snapshot("R", loop)["width"])

    def test_fixed_gate_reuses_only_when_all_covers_match(self):
        ledger = {"protocol": "orchflows.review.v1", "records": [{
            "kind": "Verification",
            "verdict": "PASS",
            "covers": {
                "base": "sha256:base",
                "result": "sha256:result",
                "dependencies": [],
            },
        }]}
        snapshot = {
            "R": {
                "id": "R",
                "assignment_seal": "sha256:base",
                "result_identity": "sha256:result",
                "depends_on": [],
                "review_v1": json.dumps(ledger),
            },
        }
        self.assertTrue(fixed_gate_snapshot("R", snapshot)["reusable"])
        snapshot["R"]["assignment_seal"] = "sha256:changed"
        self.assertFalse(fixed_gate_snapshot("R", snapshot)["reusable"])

    def test_review_verification_accepts_optional_closed_covers(self):
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
        verification = tickets_review._record(
            "Verification", repair["identity"], artifact="artifact", by="agent",
            evidence="PASS: unchanged", verdict="PASS",
            covers={"base": "sha256:base", "dependencies": []},
        )
        state = tickets_review._review_state(
            [plan, adjudication, repair, verification]
        )
        self.assertEqual(verification, state["records"][-1])

    def test_review_verification_rejects_empty_closed_covers(self):
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
        with self.assertRaises(tickets_review.ReviewError):
            tickets_review._review_state([
                plan, adjudication, repair,
                tickets_review._record(
                    "Verification", repair["identity"], artifact="artifact",
                    by="agent", evidence="PASS: unchanged", verdict="PASS",
                    covers={},
                ),
            ])

    def test_prose_verification_covers_are_read_as_fixed_result_evidence(self):
        text = "\n".join((
            "---", "id: R", "assignment_seal: sha256:base",
            "workspace_baseline: sha256:base", "---", "",
            "## Goal", "Deliver the result.", "",
            "## Context", "The repository is fixed.", "",
            "## Result", "Fixed result identity: " + "a" * 40, "",
            "## Verification",
            "PASS: checks are green; covers: base sha256:base; result " + "a" * 40 + "; dependencies none",
            "",
        ))
        result = fixed_gate_snapshot("R", {"R": text})
        self.assertEqual("PASS", result["verdict"])
        self.assertTrue(result["reusable"])

    def test_prose_covers_can_use_workspace_baseline_and_result_tip(self):
        base, result_identity = "b" * 7, "c" * 7
        text = "\n".join((
            "---", "id: R", f"workspace_baseline: {base} clean", "---", "",
            "## Goal", "Deliver the result.", "",
            "## Context", "The repository is fixed.", "",
            "## Result", f"Tip of the worktree: {result_identity}", "",
            "## Verification",
            f"PASS: checks are green; covers: base `{base}`; result `{result_identity}`; no dependencies.",
            "",
        ))
        result = fixed_gate_snapshot("R", {"R": text})
        self.assertTrue(result["reusable"])

    def test_fixed_gate_invalidates_when_a_dependency_assignment_changes(self):
        snapshot = {
            "R": {
                "id": "R", "assignment_seal": "sha256:base",
                "result_identity": "sha256:result", "depends_on": ["D"],
                "review_v1": json.dumps({"records": [{
                    "kind": "Verification", "verdict": "PASS", "covers": {
                        "base": "sha256:base", "result": "sha256:result",
                        "dependencies": ["sha256:dep"],
                    },
                }]}),
            },
            "D": {"id": "D", "assignment_seal": "sha256:dep"},
        }
        self.assertTrue(fixed_gate_snapshot("R", snapshot)["reusable"])
        snapshot["D"]["assignment_seal"] = "sha256:changed"
        self.assertFalse(fixed_gate_snapshot("R", snapshot)["reusable"])


class FixedGateCommandTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.environment = mock.patch.dict(
            os.environ, {"ORCHFLOWS_STATE_HOME": self.temporary.name}
        )
        self.environment.start()

    def tearDown(self):
        self.environment.stop()
        self.temporary.cleanup()

    def _write_target(self, assignment_seal: str):
        result_identity = "sha256:" + hashlib.sha256(
            "The fixed artifact.".encode("utf-8")
        ).hexdigest()
        ledger = {
            "protocol": "orchflows.review.v1",
            "records": [{
                "kind": "Verification",
                "verdict": "PASS",
                "covers": {
                    "base": assignment_seal,
                    "result": result_identity,
                    "dependencies": [],
                },
            }],
        }
        fields = {
            "id": "R", "run": "run", "status": "complete",
            "admission": "git:sha256:admission", "executor": "orch-tdd",
            "pack": "orch-code-pack", "independence": "checker",
            "isolation": "required", "depends_on": [], "bound": "30m",
            "root_generation": "root:R",
            "cut_generation": "cut:R", "assignment_seal": assignment_seal,
        }
        text = _render_ticket(fields, [
            ("Goal", "Deliver the result."),
            ("Context", "The repository is fixed."),
            ("Result", "The fixed artifact."),
            ("Verification", json.dumps(ledger, separators=(",", ":"))),
            ("Feedback", "[]"), ("Risks", "[]"),
        ])
        run_dir = Path(self.temporary.name) / "tickets" / "run"
        run_dir.mkdir(parents=True)
        (run_dir / "R.md").write_text(text, encoding="utf-8")
        return run_dir / "R.md"

    def test_unchanged_fixed_result_does_not_emit_checker_and_changed_one_does(self):
        path = self._write_target("sha256:base")
        reused = tickets._dispatch(["gate", "run", "R"])
        self.assertEqual("reused", reused["gate"]["outcome"])
        self.assertFalse(path.with_name("R.check.md").exists())

        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "assignment_seal: sha256:base", "assignment_seal: sha256:changed"
            ),
            encoding="utf-8",
        )
        stale = tickets._dispatch(["gate", "run", "R"])
        self.assertEqual("checker-emitted", stale["gate"]["outcome"])
        self.assertTrue(path.with_name("R.check.md").exists())

    def test_grade_command_reads_one_exact_run_snapshot(self):
        run_dir = Path(self.temporary.name) / "tickets" / "run"
        run_dir.mkdir(parents=True)
        (run_dir / "R.md").write_text(ticket(
            "R", "orch-decompose",
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
