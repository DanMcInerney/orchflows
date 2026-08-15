"""The `assembly` cell's permitted forms and the cross-pack cell linter.

Every wrong result is built in an isolated tree beside the real one
(rules/verification.md §8): the real packs/ are never mutated to prove a
branch.
"""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tools.validate as validate  # noqa: E402

VALIDATE = ROOT / "tools" / "validate.py"
CONTRACTS = ROOT / "contracts"

VERBATIM = "cell content duplicated verbatim"
NEAR = "cell content near-duplicate"

# packs/orch-*-pack/SKILL.md:12 verbatim -- the four rows the form must admit.
REAL_ASSEMBLY_ROWS = {
    "orch-code-pack": "none — the repository is the assembly",
    "orch-design-pack": "none — the merged revision's rendered views are the assembly",
    "orch-content-pack": "`orch-edit`",
    "orch-research-pack": "`orch-synthesize`",
}

PACK_TEMPLATE = """---
name: {name}
description: synthetic pack built beside the tree to exercise one validator branch.
---

Cells per [contracts/pack-signature.md](../../contracts/pack-signature.md):

| cell | binding |
| --- | --- |
| slicing | [references/slicing.md](references/slicing.md) |
| executor | `{name}executor` |
| assembly | {assembly} |
| lens | inline: none |
| oracle_policy | [references/oracles.md](references/oracles.md) |
| workspace | {workspace} |
| required_spec_fields | inline: none |
| craft | [references/craft.md](references/craft.md) |
"""


class _IsolatedTree(unittest.TestCase):
    """contracts/ + tools/validate.py + whatever packs the test writes.
    The real packs/ and skills/ trees are absent, so only the synthetic
    packages reach the checks under test. Every default the template
    supplies is under the clause floor, so a test compares only the
    content it writes itself."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)
        shutil.copytree(CONTRACTS, self.tmp_path / "contracts")
        (self.tmp_path / "tools").mkdir()
        shutil.copy(VALIDATE, self.tmp_path / "tools" / "validate.py")
        self._run("--pin")  # matching pins so only synthetic packages can fail

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, *args):
        return subprocess.run(
            [sys.executable, str(self.tmp_path / "tools" / "validate.py"), *args],
            capture_output=True,
            text=True,
        )

    def _write_pack(self, name, assembly=None, workspace="inline: none", files=None):
        pack_dir = self.tmp_path / "packs" / name
        (pack_dir / "references").mkdir(parents=True)
        (pack_dir / "SKILL.md").write_text(
            PACK_TEMPLATE.format(
                name=name,
                assembly="`orch-%s-assembly`" % name if assembly is None else assembly,
                workspace=workspace,
            ),
            encoding="utf-8",
        )
        defaults = {
            "references/craft.md": "# Craft\n\nOnly %s terms.\n" % name,
            "references/slicing.md": "# Slicing\n\nCut into %s widgets.\n" % name,
            "references/oracles.md": "# Oracles\n\nOne %s row.\n" % name,
        }
        defaults.update(files or {})
        for rel_path, content in defaults.items():
            (pack_dir / rel_path).write_text(content, encoding="utf-8")


class TestAssemblyForm(_IsolatedTree):
    def test_bare_none_without_a_gloss_is_rejected(self):
        self._write_pack("noglosspack", assembly="none")
        result = self._run()
        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn("assembly cell", result.stdout)
        self.assertIn("packs/noglosspack/SKILL.md", result.stdout)

    def test_backticked_none_is_rejected(self):
        self._write_pack("tickednonepack", assembly="`none` — the tree is the assembly")
        self.assertIn("assembly cell", self._run().stdout)

    def test_free_prose_is_rejected(self):
        self._write_pack("prosepack", assembly="the tree is the assembly")
        self.assertIn("assembly cell", self._run().stdout)

    def test_hyphen_instead_of_an_em_dash_is_rejected(self):
        self._write_pack("hyphenpack", assembly="none - the tree is the assembly")
        self.assertIn("assembly cell", self._run().stdout)

    def test_empty_cell_is_rejected(self):
        self._write_pack("emptypack", assembly="")
        self.assertIn("assembly cell", self._run().stdout)

    def test_the_two_legal_forms_are_accepted(self):
        self._write_pack("glosspack", assembly="none — the tree is the assembly")
        self._write_pack("skillpack", assembly="`orch-edit`")
        self.assertNotIn("assembly cell", self._run().stdout)

    def test_all_four_real_pack_rows_are_accepted(self):
        for pack, row in sorted(REAL_ASSEMBLY_ROWS.items()):
            with self.subTest(pack=pack):
                self.assertTrue(validate.assembly_form_ok(row), row)

    def test_the_real_tree_reports_no_assembly_form_error(self):
        result = subprocess.run([sys.executable, str(VALIDATE)], capture_output=True, text=True)
        self.assertNotIn("assembly cell", result.stdout)


class TestCellClauseSplitter(unittest.TestCase):
    def test_a_semicolon_cuts_one_bullet_into_two_clauses(self):
        self.assertEqual(
            ["write scopes are path sets", "conflict binding is named here"],
            validate.cell_clauses("write scopes are path sets; conflict binding is named here"),
        )

    def test_a_comma_does_not_cut(self):
        self.assertEqual(
            ["identities are revisions, isolation is a branch or a worktree"],
            validate.cell_clauses("identities are revisions, isolation is a branch or a worktree"),
        )

    def test_line_wrapping_normalizes_away(self):
        wrapped = "each frontier item gets its own worktree branched\nfrom the run's current revision at dispatch"
        flat = "each frontier item gets its own worktree branched from the run's current revision at dispatch"
        self.assertEqual(validate.cell_clauses(flat), validate.cell_clauses(wrapped))

    def test_table_header_and_delimiter_rows_are_dropped(self):
        table = (
            "| criterion kind | oracle | oracle_class | provenance |\n"
            "| --- | --- | --- | --- |\n"
            "| behavior | the ticket's named test commands | deterministic | pre-existing |\n"
        )
        self.assertEqual(
            ["behavior the ticket's named test commands deterministic pre-existing"],
            validate.cell_clauses(table),
        )

    def test_headings_and_short_labels_are_not_content(self):
        self.assertEqual([], validate.cell_clauses("## Shape\n\nTerms per [craft](craft.md).\n"))

    def test_a_clause_citing_an_owner_outside_the_pack_is_not_content(self):
        self.assertEqual(
            [],
            validate.cell_clauses(
                "Read [rules/token-economy.md](../../../rules/token-economy.md) §10 for the "
                "shape principles every domain shares."
            ),
        )

    def test_a_pointer_clause_keeps_its_exemption_after_the_split(self):
        """packs/orch-code-pack/references/craft.md:3-6 verbatim: one
        sentence whose citation sits in the first semicolon half and whose
        stated deviation sits in the second. Cutting at the ';' before the
        exemption is applied throws away the half carrying the citation and
        convicts the survivor -- the deviation half is the other end of the
        same pointer, and rules/visibility.md §3 requires both."""
        self.assertEqual(
            [],
            validate.cell_clauses(
                "Read [rules/token-economy.md](../../../rules/token-economy.md) §10 for "
                "the shape principles every domain shares; the bullets under Shape are "
                "code's own."
            ),
        )


class TestCellDuplication(_IsolatedTree):
    SHARED = (
        "each frontier item gets its own worktree branched from the run's "
        "current revision at dispatch"
    )

    def test_a_verbatim_clause_in_two_packs_is_an_error(self):
        self._write_pack("alphapack", workspace="git: %s" % self.SHARED)
        self._write_pack("betapack", workspace="git: %s" % self.SHARED)
        out = self._run().stdout
        self.assertIn(VERBATIM, out)
        self.assertIn("packs/alphapack/SKILL.md", out)
        self.assertIn("packs/betapack/SKILL.md", out)
        self.assertIn(self.SHARED, out)

    def test_a_verbatim_clause_wrapped_differently_is_still_an_error(self):
        body = "# Slicing\n\n- Item extensions beyond the core:\n  %s.\n"
        wrapped = (
            "each frontier item gets its own worktree branched\n  from the run's "
            "current revision at dispatch"
        )
        self._write_pack("wrapapack", files={"references/slicing.md": body % self.SHARED})
        self._write_pack("wrapbpack", files={"references/slicing.md": body % wrapped})
        self.assertIn(VERBATIM, self._run().stdout)

    def test_near_duplicate_clauses_warn_naming_both_sites(self):
        self._write_pack("nearapack", workspace="the workspace's linter or validator decides standards shape")
        self._write_pack("nearbpack", workspace="the workspace's linter or formatter decides standards shape")
        out = self._run().stdout
        self.assertIn(NEAR, out)
        self.assertIn("packs/nearapack/SKILL.md", out)
        self.assertIn("packs/nearbpack/SKILL.md", out)
        self.assertNotIn(VERBATIM, out)

    def test_unrelated_clauses_are_not_reported(self):
        self._write_pack("farapack", workspace="identities are document revisions inside one outline")
        self._write_pack("farbpack", workspace="every claim carries the provenance of its evidence")
        out = self._run().stdout
        self.assertNotIn(VERBATIM, out)
        self.assertNotIn(NEAR, out)

    def test_a_shared_table_header_row_is_not_reported(self):
        table = (
            "# Oracles\n\n"
            "| criterion kind | oracle | oracle_class | provenance |\n"
            "| --- | --- | --- | --- |\n"
            "| %s |\n"
        )
        self._write_pack("hdrapack", files={"references/oracles.md": table % (
            "behavior | the ticket's named test commands | deterministic | pre-existing")})
        self._write_pack("hdrbpack", files={"references/oracles.md": table % (
            "audience fit | a named reader reads the draft aloud | judged | authored-here")})
        self.assertNotIn(VERBATIM, self._run().stdout)

    def test_a_pointer_cell_is_compared_on_its_reference_file(self):
        """Both packs' `craft` rows are byte-identical -- a linter over
        cell text would convict the row validate_pack_signature mandates
        at :758-760. The finding must name the reference files instead."""
        shared = "# Craft\n\nThe unit is a module at roughly one-read size, understood in one sitting.\n"
        self._write_pack("ptrapack", files={"references/craft.md": shared})
        self._write_pack("ptrbpack", files={"references/craft.md": shared})
        out = self._run().stdout
        self.assertIn(VERBATIM, out)
        self.assertIn("packs/ptrapack/references/craft.md", out)
        self.assertIn("packs/ptrbpack/references/craft.md", out)
        self.assertNotIn("[references/craft.md](references/craft.md)", out)

    def test_identical_pointer_rows_over_different_references_are_clean(self):
        self._write_pack("difapack", files={
            "references/craft.md": "# Craft\n\nA module is the unit of code review here.\n"})
        self._write_pack("difbpack", files={
            "references/craft.md": "# Craft\n\nEvidence packets carry provenance for every claim.\n"})
        out = self._run().stdout
        self.assertNotIn(VERBATIM, out)
        self.assertNotIn(NEAR, out)


class TestMandatedEchoExemption(_IsolatedTree):
    """Three echoes an owner outside the pack mandates, so two packs
    carrying them carry them by obligation. Each pair below is the real
    tree's own pair with the domain nouns swapped for synthetic ones, so
    the synthetic clauses have the real ones' shape and length."""

    # packs/orch-code-pack/SKILL.md:12 and packs/orch-design-pack/SKILL.md:12.
    ASSEMBLY = (
        "none — the repository is the assembly",
        "none — the merged revision's rendered views are the assembly",
    )
    # packs/orch-code-pack/references/oracles.md and the design pack's:
    # both rows end in verdict.md's oracle_class and work-item.md's
    # provenance, and there are three of the first and two of the second.
    ORACLE_ROWS = (
        "| behavior | the ticket's named test commands | deterministic | pre-existing |",
        "| accessibility floor | the accessibility bar's check command at every "
        "covered identity | deterministic | pre-existing |",
    )
    ORACLE_TABLE = (
        "# Oracles\n\n"
        "| criterion kind | oracle | oracle_class | provenance |\n"
        "| --- | --- | --- | --- |\n"
        "%s\n"
    )
    # packs/*/references/craft.md:3 -- the opener naming the cell the file
    # satisfies, which every pointer cell's reference carries.
    CRAFT_OPENER = "# Craft\n\nThe %s domain's terms and shape, per the signature's craft cell.\n"

    # A pack not exercising the assembly echo still needs a legal assembly
    # that resolves without skills/ and is nobody else's verbatim twin: a
    # per-pack gloss, since no backticked skill resolves in this tree.
    def _inert(self, name):
        return "none — %s stands in" % name

    def test_the_craft_opener_the_assembly_form_and_the_oracle_enums_are_exempt(self):
        for name, domain in (("openerapack", "alpha"), ("openerbpack", "beta")):
            self._write_pack(name, assembly=self._inert(name),
                             files={"references/craft.md": self.CRAFT_OPENER % domain})
        self._write_pack("formapack", assembly=self.ASSEMBLY[0])
        self._write_pack("formbpack", assembly=self.ASSEMBLY[1])
        for name, row in (("enumapack", self.ORACLE_ROWS[0]), ("enumbpack", self.ORACLE_ROWS[1])):
            self._write_pack(name, assembly=self._inert(name),
                             files={"references/oracles.md": self.ORACLE_TABLE % row})
        result = self._run()
        self.assertEqual(0, result.returncode, result.stdout)
        self.assertNotIn(VERBATIM, result.stdout)
        self.assertNotIn(NEAR, result.stdout)


class TestAllowlist(unittest.TestCase):
    def test_exactly_one_family(self):
        self.assertEqual(1, len(validate.CELL_DUPLICATION_ALLOWLIST))

    def test_the_family_records_the_deferred_decision(self):
        reason = validate.CELL_DUPLICATION_ALLOWLIST[0]["reason"]
        self.assertIn("third", reason)
        self.assertIn("consciously", reason)

    def test_the_real_tree_carries_no_unallowed_verbatim_duplication(self):
        result = subprocess.run([sys.executable, str(VALIDATE)], capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stdout)
        self.assertNotIn(VERBATIM, result.stdout)


# --- the warning ratchet ---------------------------------------------
#
# tools/validate.py:1559 returns has_errors inverted, so exit 0 is blind to
# every WARN it printed. Until this ceiling, nothing anywhere read the
# count: the tree could slide back to any number and stay green. The
# ceiling is the claim exit 0 now carries.
#
# 47 is what the tree reported at ff30d60, every one of them a
# near-duplicate cell clause. WARNING_CEILING is the count the tree
# reports now, set with no headroom on purpose: headroom is a standing
# licence to regress into it, and every warning still under the ceiling is
# a duplication nobody has argued for yet. It ratchets down as those are
# fixed. Raising it is a decision, and it belongs in the commit message
# that raises it.
BASELINE_WARNINGS = 47
WARNING_CEILING = 30

# A clone is the whole tree minus version control, runtime state and
# caches -- never an extract of the directories the check happens to read
# today, which would stop grading whatever it left out.
CLONE_SKIPS = shutil.ignore_patterns(
    ".git", ".claude", ".orch", "__pycache__", "*.pyc", ".venv", ".mypy_cache"
)


def warning_lines(root):
    """Every WARN tools/validate.py reports for the tree at `root`.
    ROOT is validate.py's own parent.parent, so the copy in a clone grades
    the clone."""
    result = subprocess.run(
        [sys.executable, str(Path(root) / "tools" / "validate.py")],
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line.startswith("WARN")]


def ceiling_breach(count):
    """The ratchet's whole decision: None while the count holds, the
    sentence naming the breach once it does not. Both tests below call
    this one function, so the check that grades the real tree is the same
    check shown to fail against a wrong one."""
    if count > WARNING_CEILING:
        return "%d WARN, ceiling %d" % (count, WARNING_CEILING)
    return None


class WarningCeilingTest(unittest.TestCase):
    # One clause packs/orch-code-pack/references/slicing.md:8-11 already
    # owns, restated in a fifth place with a single noun changed. This is
    # what a regression here looks like: not a new kind of finding, one
    # more copy of a clause that has an owner.
    REGRESSION = (
        "\n- Each ticket: one observable behavior, provable by runnable checks "
        "from the spec's acceptance; a write scope overlapping only cousins it "
        "is dependency-ordered with and sufficient for its own completion test.\n"
    )

    def _clone_beside_the_tree(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        clone = Path(temporary.name) / "clone"
        shutil.copytree(ROOT, clone, ignore=CLONE_SKIPS, symlinks=True)
        return clone

    def test_the_tree_holds_at_or_under_the_ceiling(self):
        found = warning_lines(ROOT)
        self.assertIsNone(ceiling_breach(len(found)), "\n".join(found))
        self.assertLess(
            len(found),
            BASELINE_WARNINGS,
            "the ratchet must stand below the %d measured at ff30d60"
            % BASELINE_WARNINGS,
        )

    def test_a_count_above_the_ceiling_fails(self):
        clone = self._clone_beside_the_tree()
        held = warning_lines(clone)
        self.assertIsNone(
            ceiling_breach(len(held)),
            "the clone must start where the tree stands, or it grades nothing",
        )
        planted = clone / "packs" / "orch-research-pack" / "references" / "slicing.md"
        planted.write_text(
            planted.read_text(encoding="utf-8") + self.REGRESSION, encoding="utf-8"
        )
        raised = warning_lines(clone)
        self.assertGreater(len(raised), len(held), "the plant reported nothing")
        self.assertIsNotNone(
            ceiling_breach(len(raised)),
            "%d WARN in the clone did not breach the ceiling of %d"
            % (len(raised), WARNING_CEILING),
        )


if __name__ == "__main__":
    unittest.main()
