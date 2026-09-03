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

    MANDATORY = ("Vocabulary", "Workspace", "Spec fields", "Lens")
    # `adapter | git` below, so `git` is the pack's own artifact kind
    # beside the two the library owns.
    LENS_KINDS = ("root", "cut", "git")

    def _write_pack(self, name: str, omit: str = "", adapter: str = "git",
                    kinds=None, extra: str = ""):
        pack_dir = self.tmp_path / "packs" / name
        (pack_dir / "references").mkdir(parents=True)
        (pack_dir / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: a synthetic pack\n---\n\n"
            "| cell | binding |\n| --- | --- |\n"
            f"| adapter | {adapter} |\n"
            "| stages | [stage] |\n"
            "| assembly | none |\n"
            "| craft | [references/craft.md](references/craft.md) |\n",
            encoding="utf-8",
        )
        craft = "# Craft\n\n"
        for section in self.MANDATORY:
            if section == omit:
                continue
            craft += "## %s\n\ncontent.\n\n" % section
            if section != "Lens":
                continue
            for kind in self.LENS_KINDS if kinds is None else kinds:
                craft += "### %s\n\ncriteria.\n\n" % kind
        craft += extra
        (pack_dir / "references" / "craft.md").write_text(craft, encoding="utf-8")

    def test_a_craft_without_a_mandatory_heading_is_an_error(self):
        for omit in ("Lens", "Workspace"):
            with self.subTest(omit=omit):
                self._write_pack("orch-synth-%s-pack" % omit.lower(), omit=omit)
        result = self._run()
        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn("no `## Lens` heading", result.stdout)
        self.assertIn("no `## Workspace` heading", result.stdout)

    def test_a_craft_with_every_mandatory_heading_is_clean(self):
        self._write_pack("orch-synth-pack")
        result = self._run()
        self.assertNotIn("craft carries no", result.stdout)
        self.assertNotIn("`## Lens` carries", result.stdout)

    def test_a_retired_heading_is_an_error(self):
        """The four sections `## Lens`'s entries absorbed are refused, not
        merely unread: a craft keeping one owns the fact twice, and the
        copy beside the entry is the one no verb is pointed at."""

        self._write_pack(
            "orch-synth-retired-pack",
            extra="## Outline\n\nthe old root taste.\n\n"
                  "## Shape\n\nthe old taste.\n\n",
        )
        result = self._run()
        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn("retired `## Outline` heading", result.stdout)
        self.assertIn("retired `## Shape` heading", result.stdout)

    def test_a_heading_outside_the_roster_is_an_error(self):
        """The `##` roster closes both ways, as the `###` keys already do:
        a section the signature table never named is content no verb is
        pointed at, and reads correct in the prose alone."""

        self._write_pack(
            "orch-synth-novel-pack",
            extra="## Notes\n\nasides the verbs never read.\n\n",
        )
        result = self._run()
        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn("unrecognized `## Notes` heading", result.stdout)

    def test_the_optional_stages_heading_is_clean(self):
        """`Stages` is the one section the table marks optional, so the
        roster loop reads it rather than the mandatory list alone."""

        self._write_pack(
            "orch-synth-stages-pack",
            extra="## Stages\n\nthe narrative behind the cell.\n\n",
        )
        result = self._run()
        self.assertNotIn("craft carries", result.stdout)

    def test_a_lens_missing_a_library_kind_is_an_error(self):
        self._write_pack("orch-synth-nocut-pack", kinds=("root", "git"))
        result = self._run()
        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn("no `### cut` entry", result.stdout)

    def test_a_lens_missing_the_adapter_kind_is_an_error(self):
        self._write_pack("orch-synth-nokind-pack", kinds=("root", "cut"))
        result = self._run()
        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn("no `### git` entry", result.stdout)

    def test_a_lens_key_the_adapter_never_produces_is_an_error(self):
        """The kind comes from the registry the runtime branches on, so a
        `doc` entry under a `git` adapter is criteria for an artifact this
        pack cannot emit -- and reads correct in the prose alone."""

        self._write_pack(
            "orch-synth-extra-pack", kinds=("root", "cut", "git", "doc"),
        )
        result = self._run()
        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn("`### doc` entry for an artifact kind", result.stdout)

    def test_the_adapter_decides_which_kind_the_lens_must_carry(self):
        """Same craft shape, a different registered adapter: the entry the
        `git` pack must carry is the one the `document-tree` pack must not.
        A hard-coded kind here would pass both."""

        self._write_pack(
            "orch-synth-doc-pack", adapter="document-tree",
            kinds=("root", "cut", "doc"),
        )
        result = self._run()
        self.assertNotIn("`## Lens` carries", result.stdout)


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
            (self.tmp_path / root).mkdir(parents=True, exist_ok=True)
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


class TestRoutingBlockBudget(unittest.TestCase):
    """rules/token-economy.md §11's project-routing-block default
    (`ROUTING_BLOCK_BUDGET`). No renderer or sync mechanism installs a
    project-scope routing block in this tree (the constant's own comment,
    tools/validate_support/common.py, carries the verified evidence), so
    the check is exercised directly against synthetic text -- the can-fail
    direction of rules/verification.md Section 8, matching
    tests/test_architecture_owners.py's padded-copy pattern for the same
    reason: there is no second tree to build."""

    def test_an_oversized_routing_block_is_refused(self):
        diag = validate.Diagnostics()
        oversized = " ".join(["word"] * (validate.ROUTING_BLOCK_BUDGET + 10))

        validate.validate_routing_block(oversized, "a-project/AGENTS.md", diag)

        self.assertTrue(diag.has_errors)
        self.assertIn("exceeds the every-turn budget", diag.lines()[0])

    def test_a_routing_block_inside_the_budget_passes(self):
        diag = validate.Diagnostics()
        in_budget = " ".join(["word"] * validate.ROUTING_BLOCK_BUDGET)

        validate.validate_routing_block(in_budget, "a-project/AGENTS.md", diag)

        self.assertFalse(diag.has_errors)
