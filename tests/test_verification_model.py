"""Regressions for Goal-led evidence, critique, and repair boundaries."""

from __future__ import annotations

import re
import unittest


from tests._repo_root import ROOT

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
        """What proves a deliverable is stated under the Lens entry keyed by
        the kind the pack's adapter emits, not in a section beside it: the
        checking verb reads one entry, so evidence outside it is evidence
        no verb is pointed at."""

        expected = {
            "content": ("doc", ("audience", "lint")),
            "design": ("git", ("interaction", "accessibility")),
            "research": ("evidence", ("sources", "uncertainty")),
        }
        for pack, (kind, anchors) in expected.items():
            with self.subTest(pack=pack):
                craft = read(f"packs/orch-{pack}-pack/references/craft.md")
                lens = re.search(r"(?ms)^## Lens\s*$(.*?)(?=^## |\Z)", craft)
                self.assertIsNotNone(lens, f"{pack} craft has no ## Lens section")
                match = re.search(
                    r"(?ms)^### %s\s*$(.*?)(?=^###? |\Z)" % kind, lens.group(1)
                )
                self.assertIsNotNone(
                    match, f"{pack} craft has no ## Lens `### {kind}` entry"
                )
                body = match.group(1)
                self.assertTrue(all(anchor in body for anchor in anchors))
                self.assertNotIn("code tests are required", body.lower())


class CritiqueContractTest(unittest.TestCase):
    def test_check_owns_blockers_and_verification(self):
        check = read("skills/kernel/orch-judge/SKILL.md")
        normalized_check = " ".join(check.split())
        # Two anchors either side of the hyphen in "evidence-backed", not
        # one crossing it: a real reflow (an editor, `fmt`) breaks at a
        # hyphen by default, and a mutant that forbids doing so would grade
        # an easier file than the one that will exist (A5).
        self.assertIn("A critique enumerates evidence", normalized_check)
        self.assertIn("backed findings, then", normalized_check)
        self.assertIn("one thread per shared cause", normalized_check)
        self.assertIn("extinguishes the class", normalized_check)
        self.assertIn("Write the findings to one JSON file", normalized_check)
        self.assertIn("print `findings: <path>` in the report", normalized_check)

    def test_critique_is_read_only_and_keeps_costly_fix_sentence(self):
        check = read("skills/kernel/orch-judge/SKILL.md")
        normalized_check = " ".join(check.split())
        self.assertIn("Never: edit the artifact", normalized_check)
        self.assertIn("mix a review stage with another kind", normalized_check)
        self.assertIn("`## Lens` owns the review criteria", normalized_check)

    def test_live_ticket_review_surfaces_drop_stale_authority_and_oracle_model(self):
        surfaces = (
            "rules/verification.md",
            "skills/kernel/orch-judge/SKILL.md",
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
        joined = " ".join("\n".join(read(path) for path in surfaces).split())
        for phrase in forbidden:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, joined)


if __name__ == "__main__":
    unittest.main()
