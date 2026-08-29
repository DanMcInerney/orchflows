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

SPEC_POLICY_REQUIREMENTS = {
    "Evidence identities": (
        r"\bcite\b.*\bby identity\b",
        r"\bnever\b.*\binline rationale\b",
    ),
    "Root contents": (
        r"\bcarry only settled observable behavior\b",
        r"\bexecutor cannot infer\b",
    ),
    "Executor authority": (
        r"\bleave\b.*\bfiles\b.*\bschemas\b.*\btests\b",
        r"\bproof methods\b.*\binternal mechanics\b.*\bto the executor\b",
    ),
    "Seal blockers": (
        r"\bvague quality adjectives settle nothing\b",
        r"\bdo not seal\b.*\bchoice\b.*\bcontradiction\b.*\bimpossible acceptance threshold\b",
    ),
    "Reference resolution": (
        r"\bvalidate fixed identities\b.*\bcanonical-owner references\b.*\bbefore seal\b",
        r"\blocators must resolve\b",
    ),
    "Review eligibility": (
        r"\brecommend one outside blocker-only review only when\b",
        r"\bseveral independent semantic policies\b|\bcross-cutting\b.*\bcontract surfaces\b",
    ),
    "Review finality": (
        r"\bcorrected root\b.*\balready addresses a review\b.*\bnever recommends another critique\b",
        r"\bdeterministic admission\b.*\bdownstream verification decide what follows\b",
    ),
}

SPEC_POLICY_INVERSIONS = {
    "Evidence identities": "Inline long evidence and rationale; identities are optional.",
    "Root contents": "Carry inferred implementation details and omit settled behavior.",
    "Executor authority": "The planner prescribes files, schemas, tests, proof methods, and mechanics.",
    "Seal blockers": "Seal while choices, contradictions, or impossible thresholds remain.",
    "Reference resolution": "Seal without validating fixed identities or resolving locators.",
    "Review eligibility": "Always recommend outside blocker-only review, even for one simple policy.",
    "Review finality": "A corrected root recommends another critique before admission or verification.",
}


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class GoalEvidenceContractTest(unittest.TestCase):
    def assert_spec_semantics(self, fields):
        self.assertEqual(set(SPEC_POLICY_REQUIREMENTS), set(fields))
        for name, patterns in SPEC_POLICY_REQUIREMENTS.items():
            value = " ".join(fields[name].lower().split())
            for pattern in patterns:
                self.assertRegex(value, pattern, msg=f"{name} lost semantic policy: {pattern}")

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
        self.assert_spec_semantics(fields)
        for name in SPEC_POLICY_REQUIREMENTS:
            with self.subTest(policy=name, mutation="removed"):
                removed = {**fields, name: ""}
                with self.assertRaises(AssertionError):
                    self.assert_spec_semantics(removed)
            with self.subTest(policy=name, mutation="inverted"):
                inverted = {**fields, name: SPEC_POLICY_INVERSIONS[name]}
                with self.assertRaises(AssertionError):
                    self.assert_spec_semantics(inverted)

        all_values_erased = dict.fromkeys(fields, "x")
        with self.assertRaises(AssertionError):
            self.assert_spec_semantics(all_values_erased)


class SpecSuccessorLifecycleTest(unittest.TestCase):
    def test_topology_references_resolve_to_current_numbered_clauses(self):
        spec = read("skills/workflows/orch-spec/SKILL.md")
        topology = read("rules/topology.md")
        clauses = set(re.findall(r"(?m)^(\d+)\.", topology))
        references = re.findall(
            r"\[[^]]*topology(?:\.md)?\]\([^)]*rules/topology\.md\)"
            r"\s*(?:§§?)?\s*(\d+[a-z]?)",
            spec,
            flags=re.IGNORECASE,
        )
        self.assertTrue(references, "orch-spec must cite the topology owner")
        self.assertEqual(
            [],
            [reference for reference in references if reference not in clauses],
            "orch-spec cites a topology clause that does not exist",
        )

    def test_successor_trigger_has_a_fresh_authorized_materialization_path(self):
        spec = " ".join(read("skills/workflows/orch-spec/SKILL.md").split())
        required = (
            "materialization run",
            "planner ticket bound to this exact skill",
            "`tickets.py dispatch`",
            "`tickets.py dispatch-receive`",
            "durable accepted receipt",
            "accepted predecessor `## Result` identity",
            "fresh successor run",
            "`root_generation` ordinal `1`",
            "`tickets.py new`",
            "`tickets.py stamp-generation`",
            "`tickets.py draft-validate`",
            "`tickets.py seal`",
            "`planned` to `opened`",
            "next entry `planned`",
            "`orch-integrate`",
            "`orch-frontier`",
        )
        for token in required:
            with self.subTest(token=token):
                self.assertIn(token, spec)
        self.assertIn("never send a follow-up", spec.lower())
        self.assertIn("predecessor bytes", spec)
        self.assertIn("never create a second root in the same run", spec.lower())


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
