"""Executable draft, validation, seal, and correction lifecycle contract."""

import ast
import inspect
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import tickets_admission as admission
from scripts import tickets_generations as generations
from scripts import tickets_lifecycle as lifecycle
from scripts import tickets
from scripts.tickets_dispatch import _dispatch
from scripts.tickets_format import _parse_frontmatter, _set_frontmatter_field
from scripts.tickets_issue_render import _render_ticket

ROOT = Path(__file__).resolve().parents[2]


def ticket(ticket_id, *, executor="orch-tdd", goal="deliver", result=""):
    fields = {
        "id": ticket_id, "run": "run", "status": "pending",
        "admission": "pending", "executor": executor, "pack": "orch-code-pack",
        "independence": "gate", "depends_on": [],
        "isolation": "required" if executor == "orch-tdd" else "none",
        "bound": "30m", "claimed_by": "", "claimed_at": "",
    }
    sections = [
        ("Goal", goal), ("Context", "Use the exact sealed run snapshot."),
        ("Result", result), ("Verification", ""), ("Feedback", "[]"),
        ("Risks", "[]"),
    ]
    return _render_ticket(fields, sections)


def snapshot():
    return {
        "00-root": ticket("00-root", executor="orch-decompose", goal="root"),
        "00-root.01": ticket("00-root.01"),
    }


class GenerationIdentityTest(unittest.TestCase):
    def test_public_facade_exposes_generation_engine(self):
        self.assertIs(tickets.draft_snapshot, generations.draft_snapshot)
        self.assertIs(tickets.assignment_digest, generations.assignment_digest)

    def test_root_and_cut_identities_cover_assignment_not_bookkeeping(self):
        original = snapshot()
        draft = generations.draft_snapshot("00-root", original)
        self.assertRegex(draft["root_generation"], r"^root:00-root:1:sha256:[0-9a-f]{64}$")
        self.assertRegex(draft["cut_generation"], r"^cut:00-root:1:sha256:[0-9a-f]{64}$")
        bookkeeping = dict(original)
        bookkeeping["00-root.01"] = _set_frontmatter_field(bookkeeping["00-root.01"], "status", "ready")
        self.assertEqual(draft, generations.draft_snapshot("00-root", bookkeeping))
        executor_output = dict(original)
        executor_output["00-root.01"] = executor_output["00-root.01"].replace("## Result\n\n", "## Result\n\noutput\n")
        self.assertEqual(draft, generations.draft_snapshot("00-root", executor_output))
        assignment = dict(original)
        assignment["00-root.01"] = assignment["00-root.01"].replace("deliver", "deliver exactly")
        changed = generations.draft_snapshot("00-root", assignment)
        self.assertNotEqual(draft["cut_generation"], changed["cut_generation"])
        self.assertEqual(draft["root_generation"], changed["root_generation"])


class DraftValidateSealLifecycleTest(unittest.TestCase):
    def test_only_exact_validated_snapshot_seals_and_becomes_admissible(self):
        current = snapshot()
        draft = generations.draft_snapshot("00-root", current)
        receipt = generations.validate_draft("00-root", current, draft)
        sealed = generations.seal_assignments("00-root", current, draft, receipt)
        unit = _parse_frontmatter(sealed["00-root.01"])
        root = _parse_frontmatter(sealed["00-root"])
        self.assertEqual(draft["root_generation"], unit["root_generation"])
        self.assertEqual(draft["cut_generation"], unit["cut_generation"])
        self.assertEqual(generations.assignment_digest("00-root.01", sealed["00-root.01"]), unit["assignment_seal"])
        self.assertEqual(generations.assignment_digest("00-root", sealed["00-root"]), root["assignment_seal"])
        grade = admission.grade_admission("00-root.01", sealed["00-root.01"], sealed)
        self.assertIn("seal-state-unavailable", {item["code"] for item in grade["findings"]})
        changed = dict(current)
        changed["00-root.01"] = changed["00-root.01"].replace("deliver", "moved target")
        with self.assertRaises(generations.GenerationError):
            generations.seal_assignments("00-root", changed, draft, receipt)

    def test_commands_validate_seal_and_release_units_to_ready(self):
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(os.environ, {"ORCHFLOWS_STATE_HOME": directory}):
                run_dir = Path(directory) / "tickets" / "run"
                run_dir.mkdir(parents=True)
                for ticket_id, text in snapshot().items():
                    (run_dir / f"{ticket_id}.md").write_text(text, encoding="utf-8")
                self.assertNotIn("error", _dispatch(["stamp-generation", "run", "00-root"]))
                validated = _dispatch(["draft-validate", "run", "00-root"])
                self.assertEqual("validated", validated["draft_validation"]["state"])
                cut = validated["draft_validation"]["cut_generation"]
                sealed = _dispatch(["seal", "run", "00-root", "--cut-generation", cut])
                self.assertEqual(cut, sealed["assignment_seal"]["cut_generation"])
                ready = _dispatch(["ready", "--run", "run"])
                self.assertIn("00-root.01", {item["id"] for item in ready["ready"]})

    def test_cut_binds_gate_assignments_and_membership(self):
        current = snapshot()
        current["00-root.gate.verify"] = ticket(
            "00-root.gate.verify", executor="orch-verify", goal="verify exact"
        )
        first = generations.draft_snapshot("00-root", current)
        changed_gate = dict(current)
        changed_gate["00-root.gate.verify"] = changed_gate["00-root.gate.verify"].replace(
            "verify exact", "verify the exact artifact"
        )
        self.assertNotEqual(
            first["cut_generation"],
            generations.draft_snapshot("00-root", changed_gate)["cut_generation"],
        )
        self.assertNotEqual(
            first["cut_generation"],
            generations.draft_snapshot("00-root", snapshot())["cut_generation"],
        )

    def test_readiness_has_no_post_seal_root_checker_path(self):
        tree = ast.parse(inspect.getsource(lifecycle))
        functions = {
            node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)
        }
        self.assertNotIn("_unchecked_cut", functions)
        ready_names = {
            node.id for node in ast.walk(functions["_cmd_ready"])
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
        }
        self.assertNotIn("CHECKED_BY_KEY", ready_names)

    def test_user_graph_surfaces_have_no_root_rereview_route(self):
        paths = (
            ROOT / "README.md",
            ROOT / "rules" / "verification.md",
            ROOT / "skills" / "kernel" / "orch-integrate" / "SKILL.md",
            ROOT / "skills" / "workflows" / "orch-spec" / "SKILL.md",
        )
        forbidden = ("cut" + " reader", "cut" + "-reader")
        findings = []
        for path in paths:
            lowered = path.read_text(encoding="utf-8").lower()
            findings.extend(
                f"{path.relative_to(ROOT)}:{token}"
                for token in forbidden if token in lowered
            )
        self.assertEqual([], findings)
        readme = paths[0].read_text(encoding="utf-8")
        self.assertIn('dec --> frontier["orch-frontier — dispatch ready units"]', readme)

class CorrectionGenerationPolicyTest(unittest.TestCase):
    def test_one_default_correction_and_recurrence_suspends_immediately(self):
        first = generations.correction_decision([{"code": "coverage", "field": "map"}], [], 1)
        self.assertEqual("new-generation", first["disposition"])
        self.assertEqual(2, first["next_ordinal"])
        repeated = generations.correction_decision([{"field": "map", "code": "coverage"}], first["history"], 1)
        self.assertEqual("suspend", repeated["disposition"])
        self.assertEqual("recurring-validation-failure", repeated["reason"])
        bounded = generations.correction_decision([{"code": "other", "field": "assignment"}], first["history"], 1)
        self.assertEqual("correction-bound-exhausted", bounded["reason"])

    def test_command_path_applies_bound_and_recurring_failure_policy(self):
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(os.environ, {"ORCHFLOWS_STATE_HOME": directory}):
                run_dir = Path(directory) / "tickets" / "run"
                run_dir.mkdir(parents=True)
                (run_dir / "00-root.md").write_text(
                    ticket("00-root", executor="orch-decompose"), encoding="utf-8"
                )
                first = _dispatch(["draft-validate", "run", "00-root", "--correction-bound", "2"])
                self.assertEqual("new-generation", first["correction"]["disposition"])
                repeated = _dispatch(["draft-validate", "run", "00-root", "--correction-bound", "2"])
                self.assertEqual("recurring-validation-failure", repeated["correction"]["reason"])


if __name__ == "__main__":
    unittest.main()
