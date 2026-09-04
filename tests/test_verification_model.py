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
        # The Details prescribe/deviate rule is contracts/work-item.md's and
        # the launch prompt's; a third copy here was the same law thrice.
        self.assertNotIn("Details prescribes", execute)
        self.assertRegex(execute, r"Stream the\s+executor\s+record")
        self.assertIn("reserved outcome", execute)
        result_contract = " ".join(read("contracts/result.md").split())
        self.assertIn("do not change the semantic assignment digest", result_contract)

    def test_callable_bodies_do_not_resolve_the_craft_themselves(self):
        # One fact, one owner: the launch prompt hands the craft path and
        # the artifact kind, so neither callable restates how a craft is
        # projected. `packs.py cells` itself is not retired -- the
        # vocabulary still owns it -- only its second owner here.
        for skill in ("orch-do", "orch-judge"):
            with self.subTest(skill=skill):
                body = read(f"skills/kernel/{skill}/SKILL.md")
                self.assertNotIn("packs.py cells", body)

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
                craft = read(f"packs/orch-{pack}-pack/SKILL.md")
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
        # The sentence this once pinned ("`## Lens` owns the review
        # criteria") was keyed by artifact kind: the entry, not the whole
        # section, is what a judge checks against. Same fact, new spelling.
        self.assertIn(
            "names the `## Lens` entry you check against", normalized_check
        )

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


class CraftLensKeyTest(unittest.TestCase):
    """`## Lens` is keyed by artifact kind
    (`research/lens-keying-2026-09-02.md`).

    The four non-exemplar packs only: `orch-code-pack` is the exemplar
    migrated beside the contract, validator and scaffold that read this
    shape, and `validate_craft_sections` is where every pack including
    that one answers for it. Pinning the code craft here too would give
    one fact two owners and make this file red for a change it does not
    own.
    """

    PACKS = (
        "orch-content-pack",
        "orch-data-pack",
        "orch-design-pack",
        "orch-research-pack",
    )

    def craft(self, pack: str) -> str:
        return read(f"packs/{pack}/SKILL.md")

    def test_craft_sections_are_the_migrated_set(self):
        for pack in self.PACKS:
            with self.subTest(pack=pack):
                headings = re.findall(r"(?m)^## (.+?)\s*$", self.craft(pack))
                self.assertEqual(
                    ["Making", "Vocabulary", "Workspace", "Spec fields",
                     "Lens", "Stages"],
                    headings,
                )

    def test_lens_keys_are_root_cut_then_the_adapter_artifact_kind(self):
        # The kind comes from the adapter the pack declares, never from a
        # list written out here: a hand-copied kind is exactly the fact
        # that went stale between the design outline and this tree.
        from scripts.tickets_adapters import adapter_spec

        for pack in self.PACKS:
            with self.subTest(pack=pack):
                lens = re.search(
                    r"(?ms)^## Lens\s*$(.*?)(?=^## |\Z)", self.craft(pack),
                )
                self.assertIsNotNone(lens, f"{pack} craft has no ## Lens section")
                keys = re.findall(r"(?m)^### (.+?)\s*$", lens.group(1))
                self.assertEqual(
                    ["root", "cut", adapter_spec(pack).artifact_kind], keys,
                )


class BlockingLawOwnershipTest(unittest.TestCase):
    """What `blocking` means is library law with one owner; how findings
    weigh against each other is each craft's own.

    The two halves were one paragraph in `orch-code-pack`'s `### git`
    entry, which left the four other packs' judges with a field to fill
    and nothing to read for it. The law is now `rules/verification.md`
    §9 and no craft restates it.
    """

    # Anchors, not sentences: each is a backticked field value or a
    # phrase the clause cannot drop without dropping the fact. A reword
    # that keeps the law keeps these; a deletion or a second copy is what
    # goes red.
    LAW_ANCHORS = ("`blocking: true`", "`blocking: false`", "never repaired")
    # Either half of the weighting vocabulary the five crafts use: an
    # explicit precedence ("outranks") or a deferral to the criteria list
    # ("listed order").
    WEIGHT_ANCHOR = re.compile(r"outranks|listed order")

    def packs(self):
        return sorted(path.parent.name for path in (ROOT / "packs").glob("*/SKILL.md"))

    def lens_entry(self, pack: str, kind: str) -> str:
        craft = read(f"packs/{pack}/SKILL.md")
        lens = re.search(r"(?ms)^## Lens\s*$(.*?)(?=^## |\Z)", craft)
        self.assertIsNotNone(lens, f"{pack} craft has no ## Lens section")
        entry = re.search(
            r"(?ms)^### %s\s*$(.*?)(?=^### |\Z)" % re.escape(kind), lens.group(1)
        )
        self.assertIsNotNone(entry, f"{pack} craft has no `### {kind}` entry")
        return entry.group(1)

    def test_the_rule_owns_the_law_and_no_craft_restates_it(self):
        rule = " ".join(read("rules/verification.md").split())
        clause = re.search(r"(?s)\b9\. (.*?)(?=\s\d{1,2}\. |\Z)", rule)
        self.assertIsNotNone(clause, "rules/verification.md carries no clause 9")
        for anchor in self.LAW_ANCHORS:
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, clause.group(1))
        self.assertEqual(5, len(self.packs()))
        for pack in self.packs():
            with self.subTest(pack=pack):
                self.assertNotIn(
                    "blocking", read(f"packs/{pack}/SKILL.md")
                )

    def test_the_judge_points_at_the_clause_that_carries_the_law(self):
        body = " ".join(read("skills/kernel/orch-judge/SKILL.md").split())
        self.assertIn("`rules/verification.md` §9", body)

    def test_every_deliverable_lens_entry_weighs_its_findings_once(self):
        """The kind comes from the pack's own adapter, so the entry this
        reads is the one the launch prompt names -- never a list of kinds
        copied here, which is the fact that goes stale."""

        from scripts.tickets_adapters import adapter_spec

        for pack in self.packs():
            with self.subTest(pack=pack):
                entry = self.lens_entry(pack, adapter_spec(pack).artifact_kind)
                self.assertEqual(
                    1,
                    len(self.WEIGHT_ANCHOR.findall(entry)),
                    "one weighting sentence per deliverable entry",
                )


if __name__ == "__main__":
    unittest.main()
