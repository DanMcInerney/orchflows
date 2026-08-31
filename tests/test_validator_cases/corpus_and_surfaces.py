"""Duplication, lens, links, and surface-budget regression cases."""
import subprocess
import sys
import unittest

from .support import ROOT, VALIDATE, _IsolatedTree, validate

class TestDuplicationCorpus(_IsolatedTree):
    """validate_cross_tier_duplication's corpus and its one licensed pair.

    The check read packs, skills, rules, contracts and the host block —
    example-workflows/ and docs/ were outside it, which is why seven templates
    could copy a reference they were told to link, and two skills could
    carry a byte-identical clause with the linter flagging each of them
    against an innocent third file instead of against each other.
    """

    CLAUSE = "\n- The cut names the acceptance the executor is graded on.\n"

    def _write_skill(self, name: str, body: str = "", tier: str = "kernel"):
        skill_dir = self.tmp_path / "skills" / tier / name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: a synthetic package\nrole: worker\n---\n"
            f"Require: an input.\nNever: overreach.\nReturn: status; result.\n{body}",
            encoding="utf-8",
        )

    def _write(self, relative: str, text: str):
        path = self.tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def duplicates(self, stdout, *labels):
        return [
            line for line in stdout.splitlines()
            if "near-duplicate" in line
            and all(label in line.replace("\\", "/") for label in labels)
        ]

    def test_a_template_stub_restating_a_rule_is_reported(self):
        self._write_skill("orch-real")
        self._write("rules/synthetic.md", "# Rule\n" + self.CLAUSE)
        self._write("example-workflows/demo/00-step.md", "# Stub\n" + self.CLAUSE)
        result = self._run()
        self.assertTrue(
            self.duplicates(result.stdout, "example-workflows/demo/00-step.md",
                            "rules/synthetic.md"),
            result.stdout,
        )

    def test_a_doc_restating_a_rule_is_reported(self):
        self._write_skill("orch-real")
        self._write("rules/synthetic.md", "# Rule\n" + self.CLAUSE)
        self._write("docs/guide.md", "# Guide\n" + self.CLAUSE)
        result = self._run()
        self.assertTrue(
            self.duplicates(result.stdout, "docs/guide.md", "rules/synthetic.md"),
            result.stdout,
        )

    def test_two_skills_carrying_one_clause_are_reported_against_each_other(self):
        """Same-tier pairs were skipped whole, on the reasoning that one
        tier's internal business is the pack linter's — which is true of
        packs and false of skills, where no per-tier linter runs at all. So
        two byte-identical skill clauses were invisible while each was
        flagged against some unrelated pack cell."""

        self._write_skill("orch-real", self.CLAUSE)
        self._write_skill("orch-other", self.CLAUSE, tier="workflows")
        result = self._run()
        self.assertTrue(
            self.duplicates(
                result.stdout,
                "skills/workflows/orch-other/SKILL.md",
                "skills/kernel/orch-real/SKILL.md",
            ),
            result.stdout,
        )


class TestLicensedCopies(unittest.TestCase):
    """A copy the library licensed and named an owner for is not a finding.

    templates/host-block.md carries rules/visibility.md §6's untrusted-data
    clause on purpose — the block is the one text a host reads before it can
    reach the rule — and names the owner one line above the copy. Counting
    it as an unowned duplication asks for the copy to be deleted, which
    would delete the licence with it."""

    def test_the_visibility_copy_in_the_host_block_is_licensed(self):
        pairs = {
            frozenset((left, right)) for left, right, _ in validate.LICENSED_COPIES
        }
        self.assertIn(
            frozenset(("rules/visibility.md", "templates/host-block.md")), pairs
        )

    def test_the_licensed_pair_is_not_reported_against_the_real_tree(self):
        result = subprocess.run(
            [sys.executable, str(VALIDATE)], capture_output=True, text=True,
        )
        # the reported file and the file it is reported against, not any
        # line that happens to quote either path inside a clause
        pair = ("rules/visibility.md", "templates/host-block.md")
        reported = [
            line for line in result.stdout.splitlines()
            if "near-duplicate" in line
            and any(
                line.replace("\\", "/").startswith(f"WARN {owner}:")
                and f"with {copy}:" in line.replace("\\", "/")
                for owner, copy in (pair, pair[::-1])
            )
        ]
        self.assertEqual([], reported, result.stdout)


class TestCraftSections(_IsolatedTree):
    """validate_craft_sections: a pack craft carries every mandatory section.

    Every verb reads the whole craft and acts under its named sections, so
    deleting a heading once left the validator at exit 0 and the suite
    green while the machinery pointed at a section that was not there.
    """

    MANDATORY = (
        "Vocabulary", "Workspace", "Spec fields", "Outline",
        "Slicing", "Evidence", "Lens",
    )

    def _write_pack(self, name: str, omit: str = ""):
        pack_dir = self.tmp_path / "packs" / name
        (pack_dir / "references").mkdir(parents=True)
        (pack_dir / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: a synthetic pack\n---\n\n"
            "| cell | binding |\n| --- | --- |\n"
            "| adapter | git |\n"
            "| stages | [stage] |\n"
            "| assembly | none |\n"
            "| craft | [references/craft.md](references/craft.md) |\n",
            encoding="utf-8",
        )
        craft = "# Craft\n\n" + "".join(
            "## %s\n\ncontent.\n\n" % section
            for section in self.MANDATORY
            if section != omit
        )
        (pack_dir / "references" / "craft.md").write_text(craft, encoding="utf-8")

    def test_a_craft_without_a_mandatory_heading_is_an_error(self):
        for omit in ("Lens", "Slicing"):
            with self.subTest(omit=omit):
                self._write_pack("orch-synth-%s-pack" % omit.lower(), omit=omit)
        result = self._run()
        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn("no `## Lens` heading", result.stdout)
        self.assertIn("no `## Slicing` heading", result.stdout)

    def test_a_craft_with_every_mandatory_heading_is_clean(self):
        self._write_pack("orch-synth-pack")
        result = self._run()
        self.assertNotIn("craft carries no", result.stdout)


class TestWordBudgetAndLinks(_IsolatedTree):
    """rules/composition.md §5 counts words with link targets stripped, and
    docs/documentation.md law 5's oracle resolves every markdown link."""

    def _write_skill(self, name, body, tier="kernel"):
        skill_dir = self.tmp_path / "skills" / tier / name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: a synthetic body\nrole: worker\n---\n"
            f"Require: one thing.\n\n{body}\n\nNever: another thing.\n\nReturn: a result.\n",
            encoding="utf-8",
        )

    def test_a_wide_body_over_the_word_budget_is_refused(self):
        wide = " ".join(["word"] * 320)  # one line, 320 words
        self._write_skill("orch-wide", wide)
        result = self._run()
        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn("words, exceeds the kernel budget of 300", result.stdout)

    def test_link_targets_do_not_count_and_a_narrow_body_under_budget_passes(self):
        links = "\n".join(
            f"- see [contract](../../../contracts/work-item.md#a-long-anchor-{i})"
            for i in range(60)
        )
        self._write_skill("orch-linky", links)
        result = self._run()
        self.assertNotIn("exceeds the kernel budget", result.stdout)

    def test_a_dangling_markdown_link_in_docs_is_an_error(self):
        for root in validate.LINKED_MD_ROOTS:
            (self.tmp_path / root).mkdir(exist_ok=True)
        docs = self.tmp_path / "docs"
        (docs / "x.md").write_text("see [gone](gone.md) and [ok](../contracts/verdict.md)\n", encoding="utf-8")
        result = self._run()
        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn("markdown link does not resolve: gone.md", result.stdout)
        # A resolving link raises no diagnostic — asserted on the target
        # the diagnostic names, not on membership of a bare name in a list
        # of lines no line can equal. (The copied contracts' own links to
        # ../docs and ../rules dangle in this synthetic tree by design.)
        self.assertNotIn("does not resolve: ../contracts/verdict.md", result.stdout)



class TestSurfaceBudgets(_IsolatedTree):
    """rules/token-economy.md §11: the every-turn surfaces carry the tightest
    ceilings, and the check reads them from the tree it runs in."""

    def test_a_host_block_over_its_budget_is_refused(self):
        (self.tmp_path / "templates").mkdir()
        (self.tmp_path / "templates" / "host-block.md").write_text(
            " ".join(["word"] * (validate.SURFACE_BUDGET["templates/host-block.md"] + 10)),
            encoding="utf-8",
        )
        result = self._run()
        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn("templates/host-block.md", result.stdout)
        self.assertIn("exceeds the every-turn budget", result.stdout)

    def test_the_real_surfaces_sit_under_their_ceilings(self):
        for name, limit in validate.SURFACE_BUDGET.items():
            with self.subTest(surface=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                self.assertLessEqual(validate.body_words(text), limit)
