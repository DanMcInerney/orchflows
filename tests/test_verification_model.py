"""Regressions for Goal-led evidence, critique, and repair boundaries."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import tickets_dispatch_gate
from scripts.tickets_issue_render import _render_ticket


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class GoalEvidenceContractTest(unittest.TestCase):
    def test_ticket_has_no_extra_success_schema(self):
        contract = read("contracts/work-item.md")
        semantic = contract.split("## System-owned metadata", 1)[0]
        self.assertEqual(1, semantic.count("`## Goal`"))
        self.assertEqual(1, semantic.count("`## Context`"))
        self.assertEqual(1, semantic.count("`## Suggested files`"))
        self.assertNotIn("## Done When", contract)
        self.assertNotIn("## Completion test", contract)
        self.assertNotIn("named oracle", contract)

    def test_tdd_chooses_tests_and_records_post_work_evidence(self):
        tdd = read("skills/instances/orch-tdd/SKILL.md")
        self.assertIn("Derive tests from Goal", tdd)
        self.assertIn("watch\nit fail", tdd)
        self.assertIn("make it pass", tdd)
        self.assertIn("evidence record", tdd)
        self.assertIn("result.md", tdd)
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
                body = read(f"packs/orch-{pack}-pack/references/evidence.md")
                self.assertTrue(all(anchor in body for anchor in anchors))
                self.assertNotIn("code tests are required", body.lower())
        spec = read("skills/workflows/orch-spec/SKILL.md")
        self.assertIn("consistency observations", spec)


class CritiqueContractTest(unittest.TestCase):
    def test_critique_is_two_pass_blocker_only_synthesis(self):
        critique = read("skills/kernel/orch-critique/SKILL.md")
        enumerate_at = critique.index("First enumerate every material issue")
        synthesize_at = critique.index("Then make a separate synthesis pass")
        self.assertLess(enumerate_at, synthesize_at)
        self.assertIn("smallest architectural repair set", critique)
        self.assertIn("Goal harm, evidence strength, and\nrepair coverage", critique)
        self.assertIn("preferences, cosmetic nits, speculative improvements", critique)

    def test_critique_is_read_only_and_keeps_costly_fix_sentence(self):
        critique = read("skills/kernel/orch-critique/SKILL.md")
        self.assertIn("Never soften a finding because fixing it is costly", critique)
        self.assertIn("Never: edit the artifact", critique)
        self.assertIn("Any repair voids this critique context's verdicts", critique)
        self.assertIn("no second critique or correction pass", critique)

    def test_live_ticket_review_surfaces_drop_stale_authority_and_oracle_model(self):
        surfaces = (
            "rules/verification.md",
            "skills/kernel/orch-critique/SKILL.md",
            "skills/engines/orch-frontier/SKILL.md",
            "scripts/tickets_dispatch_gate.py",
            "scripts/tickets_packet.py",
            "contracts/pack-signature.md",
        )
        forbidden = (
            "named oracle",
            "authored-here",
            "pre-existing-only",
            "reviewer-corrector",
            "critique then orch-repair",
            "oracle_policy",
        )
        joined = "\n".join(read(path) for path in surfaces)
        for phrase in forbidden:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, joined)


class SeparateRepairGateTest(unittest.TestCase):
    def test_single_lens_gate_emits_distinct_critique_repair_verify_tickets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / "run"
            run_dir.mkdir()
            fields = {
                "id": "root",
                "run": "run",
                "status": "pending",
                "admission": "pending",
                "executor": "orch-decompose",
                "pack": "orch-code-pack",
                "independence": "gate",
                "depends_on": [],
                "isolation": "none",
                "bound": "<= 20 tool calls",
                "claimed_by": "",
                "claimed_at": "",
                "root_generation": "root:root:1:sha256:test",
            }
            root_text = _render_ticket(fields, [
                ("Goal", "An observable result exists."),
                ("Context", "[]"),
                ("Result", ""),
                ("Verification", ""),
                ("Feedback", "[]"),
                ("Risks", "[]"),
            ])
            (run_dir / "root.md").write_text(root_text, encoding="utf-8")
            with mock.patch.object(tickets_dispatch_gate, "_tickets_root", return_value=root):
                result = tickets_dispatch_gate._gate_under_run_lock(["run", "root", "--lens", "code"])
            self.assertNotIn("error", result)
            self.assertEqual([
                "root.gate.critique.code",
                "root.gate.repair",
                "root.gate.verify",
            ], result["gate"]["tickets"])
            critique = (run_dir / "root.gate.critique.code.md").read_text(encoding="utf-8")
            repair = (run_dir / "root.gate.repair.md").read_text(encoding="utf-8")
            self.assertNotIn("sequence:", critique)
            self.assertIn("executor: orch-repair", repair)


if __name__ == "__main__":
    unittest.main()
