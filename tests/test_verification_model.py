"""Regressions for Goal-led evidence, critique, and repair boundaries."""

from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import tickets_dispatch_gate
from scripts.tickets_issue_render import _render_ticket


ROOT = Path(__file__).resolve().parents[1]

# `SPEC_POLICY_REQUIREMENTS`/`SPEC_POLICY_INVERSIONS` and the semantic-root
# policy tests they drove (once here) pinned `orch-outline`'s "Semantic root
# policy" bullets and its successor-lifecycle paragraph. W2b (verbs-rename)
# retired `orch-outline` with no successor skill body -- the policy survives
# only in the tombstone's remedy text pointing at a planning `orch-do`, not
# as executable prose anywhere in the tree -- so there is nothing left here
# to pin. Restoring these guards is a later wave's job, once a planning
# `orch-do` body states the policy again.


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class GoalEvidenceContractTest(unittest.TestCase):
    def test_ticket_has_no_extra_success_schema(self):
        contract = read("contracts/work-item.md")
        semantic = contract.split("## System-owned metadata", 1)[0]
        self.assertEqual(1, semantic.count("`## Goal`"))
        self.assertEqual(1, semantic.count("`## Context`"))
        self.assertEqual(1, semantic.count("`## Details`"))
        self.assertNotIn("## Done When", contract)
        self.assertNotIn("## Completion test", contract)
        self.assertNotIn("named oracle", contract)

    def test_execute_consumes_pack_craft_and_records_post_work_evidence(self):
        execute = read("skills/kernel/orch-do/SKILL.md")
        self.assertIn("whole craft document", execute)
        self.assertRegex(execute, r"Details prescribes[\s\S]*deviate and\s+report")
        self.assertRegex(execute, r"Stream the\s+executor record")
        self.assertIn("reserved outcome", execute)
        result_contract = " ".join(read("contracts/result.md").split())
        self.assertIn("do not change the semantic assignment digest", result_contract)

    def test_non_code_packs_define_artifact_evidence_without_code_tests(self):
        expected = {
            "content": ("audience", "lint"),
            "design": ("interaction", "accessibility"),
            "research": ("sources", "uncertainty"),
        }
        for pack, anchors in expected.items():
            with self.subTest(pack=pack):
                craft = read(f"packs/orch-{pack}-pack/references/craft.md")
                match = re.search(r"(?ms)^## Evidence\s*$(.*?)(?=^## |\Z)", craft)
                self.assertIsNotNone(match, f"{pack} craft has no ## Evidence section")
                body = match.group(1)
                self.assertTrue(all(anchor in body for anchor in anchors))
                self.assertNotIn("code tests are required", body.lower())


class CritiqueContractTest(unittest.TestCase):
    def test_check_owns_blockers_and_verification(self):
        check = read("skills/kernel/orch-judge/SKILL.md")
        self.assertIn("A critique enumerates evidence-backed findings", check)
        self.assertIn("one thread per shared cause", check)
        self.assertIn("extinguishes the class", check)
        self.assertIn("Write the complete\nseven-field findings array to one JSON file", check)

    def test_critique_is_read_only_and_keeps_costly_fix_sentence(self):
        check = read("skills/kernel/orch-judge/SKILL.md")
        self.assertIn("Never: edit the artifact", check)
        self.assertIn("mix a review stage with another kind", check)
        self.assertIn("`## Lens` owns\nthe review criteria", check)

    def test_live_ticket_review_surfaces_drop_stale_authority_and_oracle_model(self):
        surfaces = (
            "rules/verification.md",
            "skills/kernel/orch-judge/SKILL.md",
            "scripts/tickets_dispatch_gate.py",
            "scripts/tickets_assignment.py",
            "contracts/pack-signature.md",
        )
        forbidden = (
            "named oracle",
            "authored-here",
            "pre-existing-only",
            "reviewer-corrector",
            "orch-repair",
            "oracle_policy",
        )
        joined = "\n".join(read(path) for path in surfaces)
        for phrase in forbidden:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, joined)


class SeparateRepairGateTest(unittest.TestCase):
    @staticmethod
    def _ticket_text(ticket_id, executor, depends_on=()):
        fields = {
            "id": ticket_id,
            "run": "run",
            "status": "pending",
            "admission": "pending",
            "executor": executor,
            "pack": "orch-code-pack",
            "independence": "gate",
            "depends_on": list(depends_on),
            "isolation": "required" if executor == "orch-do" else "none",
            "bound": "20m",
            "root_generation": "root:root:1:sha256:test",
        }
        return _render_ticket(fields, [
            ("Goal", f"{ticket_id} delivers an observable result."),
            ("Context", "[]"),
            ("Result", ""),
            ("Verification", ""),
            ("Feedback", "[]"),
            ("Risks", "[]"),
        ])

    def test_single_lens_gate_emits_distinct_critique_and_repair_tickets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / "run"
            run_dir.mkdir()
            (run_dir / "root.md").write_text(
                self._ticket_text("root", "orch-slice"), encoding="utf-8"
            )
            (run_dir / "root.01.md").write_text(
                self._ticket_text("root.01", "orch-do"), encoding="utf-8"
            )
            (run_dir / "root.02.md").write_text(
                self._ticket_text("root.02", "orch-do", ("root.01",)),
                encoding="utf-8",
            )
            with mock.patch.object(tickets_dispatch_gate, "_tickets_root", return_value=root):
                result = tickets_dispatch_gate._gate_under_run_lock(["run", "root", "--lens", "code"])
            self.assertNotIn("error", result)
            self.assertEqual([
                "root.gate.critique.code",
                "root.gate.repair",
            ], result["gate"]["tickets"])
            self.assertFalse((run_dir / "root.gate.verify.md").exists())
            critique = (run_dir / "root.gate.critique.code.md").read_text(encoding="utf-8")
            repair = (run_dir / "root.gate.repair.md").read_text(encoding="utf-8")
            self.assertNotIn("sequence:", critique)
            self.assertIn("executor: orch-do", repair)
            self.assertIn("review_kind: repair", repair)
            self.assertIn("depends_on: [root.01, root.02]", critique)

    def test_a_single_executor_result_does_not_trigger_a_composite_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / "run"
            run_dir.mkdir()
            (run_dir / "root.md").write_text(
                self._ticket_text("root", "orch-slice"), encoding="utf-8"
            )
            (run_dir / "root.01.md").write_text(
                self._ticket_text("root.01", "orch-do"), encoding="utf-8"
            )
            with mock.patch.object(tickets_dispatch_gate, "_tickets_root", return_value=root):
                result = tickets_dispatch_gate._gate_under_run_lock(["run", "root"])
            self.assertIn("two or more executor results", result["error"])
            self.assertEqual([], list(run_dir.glob("root.gate.*.md")))

    def test_a_direct_single_root_does_not_take_the_graph_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / "run"
            run_dir.mkdir()
            (run_dir / "root.md").write_text(
                self._ticket_text("root", "orch-do"), encoding="utf-8"
            )
            for suffix in ("01", "02"):
                (run_dir / f"root.{suffix}.md").write_text(
                    self._ticket_text(f"root.{suffix}", "orch-do"),
                    encoding="utf-8",
                )
            with mock.patch.object(tickets_dispatch_gate, "_tickets_root", return_value=root):
                result = tickets_dispatch_gate._gate_under_run_lock(["run", "root"])
            self.assertIn("decomposed root", result["error"])
            self.assertEqual([], list(run_dir.glob("root.gate.*.md")))


if __name__ == "__main__":
    unittest.main()
