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

    def test_spec_distills_evidence_into_one_executable_semantic_root(self):
        spec = read("skills/workflows/orch-spec/SKILL.md")
        match = re.search(r"(?s)Semantic root policy:\n\n(.*?)\n\nLifecycle:", spec)
        self.assertIsNotNone(match)
        fields = {}
        for line in match.group(1).splitlines():
            field = re.match(r"^- \*\*([^*]+)\*\*: (.*)$", line)
            if field:
                fields[field.group(1)] = field.group(2)
            elif line.startswith("  ") and fields:
                latest = next(reversed(fields))
                fields[latest] += " " + line.strip()
        self.assertEqual({
            "Evidence identities",
            "Root contents",
            "Executor authority",
            "Seal blockers",
            "Reference resolution",
            "Review eligibility",
            "Review finality",
        }, set(fields))
        self.assertTrue(all(value.strip() for value in fields.values()))


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
            "isolation": "required" if executor == "orch-tdd" else "none",
            "bound": "20m",
            "claimed_by": "",
            "claimed_at": "",
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

    def test_single_lens_gate_emits_distinct_critique_repair_verify_tickets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / "run"
            run_dir.mkdir()
            (run_dir / "root.md").write_text(
                self._ticket_text("root", "orch-decompose"), encoding="utf-8"
            )
            (run_dir / "root.01.md").write_text(
                self._ticket_text("root.01", "orch-tdd"), encoding="utf-8"
            )
            (run_dir / "root.02.md").write_text(
                self._ticket_text("root.02", "orch-tdd", ("root.01",)),
                encoding="utf-8",
            )
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
            self.assertIn("depends_on: [root.01, root.02]", critique)

    def test_a_single_executor_result_does_not_trigger_a_composite_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / "run"
            run_dir.mkdir()
            (run_dir / "root.md").write_text(
                self._ticket_text("root", "orch-decompose"), encoding="utf-8"
            )
            (run_dir / "root.01.md").write_text(
                self._ticket_text("root.01", "orch-tdd"), encoding="utf-8"
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
                self._ticket_text("root", "orch-tdd"), encoding="utf-8"
            )
            for suffix in ("01", "02"):
                (run_dir / f"root.{suffix}.md").write_text(
                    self._ticket_text(f"root.{suffix}", "orch-tdd"),
                    encoding="utf-8",
                )
            with mock.patch.object(tickets_dispatch_gate, "_tickets_root", return_value=root):
                result = tickets_dispatch_gate._gate_under_run_lock(["run", "root"])
            self.assertIn("decomposed root", result["error"])
            self.assertEqual([], list(run_dir.glob("root.gate.*.md")))


if __name__ == "__main__":
    unittest.main()
