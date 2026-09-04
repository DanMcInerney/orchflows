"""The typed pack cells and the cross-pack cell linter.

Every wrong result is built in an isolated tree beside the real one
(rules/verification.md §8): the real packs/ are never mutated to prove a
branch.
"""
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests._repo_root import ROOT
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tools.validate as validate  # noqa: E402

VALIDATE = ROOT / "tools" / "validate.py"
CONTRACTS = ROOT / "contracts"

VERBATIM = "standard section duplicated verbatim"
NEAR = "standard section near-duplicate"
# validate.py's other duplication finding: the same clause comparison run
# across the library's tiers rather than across one signature cell. Named
# here because this module owns both ratchets.
CROSS_TIER = "cross-tier near-duplicate"

_REAL_TREE_RUN = None


def validate_the_real_tree():
    """One argument-free `tools/validate.py` run over this repository,
    shared by every case that reads it.

    Three cases below assert over the real tree's report, and three
    separate subprocesses spent 1.8s producing the same bytes three
    times. validate.py only reads a tree, so one result is every
    reader's result."""
    global _REAL_TREE_RUN
    if _REAL_TREE_RUN is None:
        _REAL_TREE_RUN = subprocess.run(
            [sys.executable, str(VALIDATE)], capture_output=True, text=True
        )
    return _REAL_TREE_RUN

PACK_TEMPLATE = """---
name: {name}
description: synthetic standard built beside the tree to exercise one branch.
adapter: git
---
"""

# A root's required sections, in the contract's order. Every default a
# synthetic standard supplies is under the clause floor, so a test compares
# only the content it writes itself.
CRAFT_SECTION_ORDER = (
    "Making",
    "Vocabulary",
    "Workspace",
    "Spec fields",
    "Lens",
)

# `## Lens`'s `###` entries: the two library kinds plus the one
# PACK_TEMPLATE's `adapter: git` frontmatter emits. The linter compares `##`
# sections, so every entry here lands in one "Lens" bucket -- which is why a
# test that wants two standards compared under a made-up section writes into
# an entry, not a new heading.
CRAFT_LENS_ORDER = ("root", "cut", "git")


_TEMPLATE_DIR = None
_TEMPLATE = None


def setUpModule():
    """contracts/ + tools/validate.py, built once.

    Every `_IsolatedTree` case starts from the same two, and building them
    per test copied a tree that is byte-identical every time. Built once
    here and copied per test, so each case still owns a private, mutable
    tree to write its synthetic packs into. Same hoist as
    tests/test_cutcheck.py:828, at module scope because three classes
    share it."""
    global _TEMPLATE_DIR, _TEMPLATE
    _TEMPLATE_DIR = tempfile.TemporaryDirectory()
    _TEMPLATE = Path(_TEMPLATE_DIR.name) / "tree"
    shutil.copytree(CONTRACTS, _TEMPLATE / "contracts")
    (_TEMPLATE / "tools").mkdir()
    shutil.copy(VALIDATE, _TEMPLATE / "tools" / "validate.py")
    # The compiler asks `scripts/doclint.py` whether two clauses are one
    # clause (ARCHITECTURE.md), so a tree that runs the copy carries it.
    (_TEMPLATE / "scripts").mkdir()
    shutil.copy(ROOT / "scripts" / "doclint.py", _TEMPLATE / "scripts" / "doclint.py")


def tearDownModule():
    _TEMPLATE_DIR.cleanup()


class _IsolatedTree(unittest.TestCase):
    """contracts/ + tools/validate.py + whatever packs the test writes.
    The real packs/ and skills/ trees are absent, so only the synthetic
    packages reach the checks under test. Every default the template
    supplies is under the clause floor, so a test compares only the
    content it writes itself."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name) / "tree"
        shutil.copytree(_TEMPLATE, self.tmp_path, symlinks=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, *args):
        return subprocess.run(
            [sys.executable, str(self.tmp_path / "tools" / "validate.py"), *args],
            capture_output=True,
            text=True,
        )

    def _write_pack(self, name, workspace="inline: none",
                    sections=None, entries=None, lead=""):
        """One synthetic standard: a `SKILL.md`
        carrying every mandatory section and every `## Lens` entry
        (validate_craft_sections errors on a missing one, and on a Lens key
        the standard's adapter never emits). `sections` overrides a
        section's body by `##` heading and `entries` a Lens entry's by
        artifact kind; `lead` is the paragraph before the first heading."""
        pack_dir = self.tmp_path / "packs" / name
        pack_dir.mkdir(parents=True)
        bodies = {
            "Making": "Make one %s well." % name,
            "Vocabulary": "Only %s terms." % name,
            "Workspace": workspace,
            "Spec fields": "one %s field" % name,
            "Lens": "",
        }
        bodies.update(sections or {})
        lens = {
            "root": "Freeze one %s root." % name,
            "cut": "Cut into %s widgets." % name,
            "git": "criteria; one %s method." % name,
        }
        lens.update(entries or {})
        craft = PACK_TEMPLATE.format(name=name) + "\n# %s\n\n" % name
        if lead:
            craft += lead.rstrip("\n") + "\n\n"
        for heading in CRAFT_SECTION_ORDER:
            craft += "## %s\n\n" % heading
            body = bodies[heading].rstrip("\n")
            if body:
                craft += "%s\n\n" % body
            if heading != "Lens":
                continue
            for kind in CRAFT_LENS_ORDER:
                craft += "### %s\n\n%s\n\n" % (kind, lens[kind].rstrip("\n"))
        (pack_dir / "SKILL.md").write_text(craft, encoding="utf-8")


class CurrentWorkspaceBindingTest(unittest.TestCase):
    EXPECTED = {
        "orch-code-pack": (
            "git",
            ("git:", "identities are commits", "ordinary diffs", "Git conflicts"),
        ),
        "orch-content-pack": (
            "document-tree",
            (
                "document tree:", "identities are document revisions",
                "actual candidate changes", "section overlap",
            ),
        ),
        "orch-data-pack": (
            "git",
            (
                "git:", "committed manifests pin dataset bytes by digest",
                "raw data living outside the repository",
                "re-materializes any derived output in contention",
            ),
        ),
        "orch-design-pack": (
            "git",
            (
                "git:", "the pair is the view identity",
                "fresh captures", "render conflicts",
            ),
        ),
        "orch-research-pack": (
            "evidence-store",
            (
                "evidence store:", "identities are evidence packets",
                "run-scoped lane directory", "actual lane packets",
            ),
        ),
    }

    WORKSPACE_SECTION = re.compile(r"(?ms)^## Workspace\s*$(.*?)(?=^## |\Z)")

    def test_every_shipped_workspace_binds_the_current_ticket_protocol(self):
        packs = {}
        for path in sorted((ROOT / "packs").glob("*/SKILL.md")):
            text = path.read_text(encoding="utf-8")
            declared = dict(
                re.findall(r"(?m)^([a-z_]+):\s*(.+?)\s*$", text.split("---", 2)[1])
            )
            match = self.WORKSPACE_SECTION.search(text)
            self.assertIsNotNone(match, path.parent.name)
            packs[path.parent.name] = (declared, " ".join(match.group(1).split()))
        self.assertEqual(set(self.EXPECTED), set(packs))
        for pack, (adapter, substrate) in self.EXPECTED.items():
            with self.subTest(pack=pack):
                declared, workspace = packs[pack]
                self.assertEqual(adapter, declared["adapter"])
                for fragment in substrate:
                    self.assertIn(fragment, workspace)
                # Assignment metadata, candidate authority, and Suggested
                # files law are contracts/work-item.md's and rules/topology.md
                # §9's; a workspace section repeating them was a copy, so the
                # binding proof is the adapter key plus the section's own
                # domain semantics above.


class TestCellClauseSplitter(unittest.TestCase):
    def test_a_semicolon_cuts_one_bullet_into_two_clauses(self):
        self.assertEqual(
            ["one clause states a fact", "the next clause states another"],
            validate.cell_clauses("one clause states a fact; the next clause states another"),
        )

    def test_a_comma_does_not_cut(self):
        self.assertEqual(
            ["identities are revisions, isolation is a branch or a worktree"],
            validate.cell_clauses("identities are revisions, isolation is a branch or a worktree"),
        )

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
        """packs/orch-code-pack/SKILL.md's `## Making` verbatim: one
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
    # Synthetic, and deliberately so: the linter's subject is any clause two
    # packs both carry, so the case needs a clause of that shape and length
    # and no shipped sentence in particular. A real cell copied in here
    # would read as a claim about the tree, and would go stale the day its
    # pack reworded it.
    SHARED = (
        "each widget batch gets its own bench cleared from the bay's "
        "current stock at handoff"
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
        body = "- Item extensions beyond the core:\n  %s.\n"
        wrapped = (
            "each widget batch gets its own bench cleared\n  from the bay's "
            "current stock at handoff"
        )
        self._write_pack("wrapapack", entries={"cut": body % self.SHARED})
        self._write_pack("wrapbpack", entries={"cut": body % wrapped})
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
            "| artifact kind | method | observation |\n"
            "| --- | --- | --- |\n"
            "| %s |\n"
        )
        self._write_pack("hdrapack", entries={"git": table % (
            "code | derived tests | red and green results")})
        self._write_pack("hdrbpack", entries={"git": table % (
            "document | audience reading | fit observations")})
        self.assertNotIn(VERBATIM, self._run().stdout)

    def test_a_clause_is_compared_inside_its_named_section(self):
        """Both manifests carry the same section headings -- a linter over
        headings would convict the section table itself. The finding
        compares same-named sections of the two manifests and names them."""
        shared = "The unit is a module at roughly one-read size, understood in one sitting."
        self._write_pack("ptrapack", sections={"Vocabulary": shared})
        self._write_pack("ptrbpack", sections={"Vocabulary": shared})
        out = self._run().stdout
        self.assertIn(VERBATIM, out)
        self.assertIn("packs/ptrapack/SKILL.md", out)
        self.assertIn("packs/ptrbpack/SKILL.md", out)
        self.assertIn("Vocabulary: standard section duplicated", out)

    def test_the_same_clause_under_different_sections_is_not_compared(self):
        """The section heading scopes the comparison the way the cell name
        did: one pack's slicing taste showing up in another's vocabulary is
        not the same fact twice."""
        shared = "The unit is a module at roughly one-read size, understood in one sitting."
        self._write_pack("secapack", sections={"Vocabulary": shared})
        self._write_pack("secbpack", sections={"Spec fields": shared})
        out = self._run().stdout
        self.assertNotIn(VERBATIM, out)
        self.assertNotIn(NEAR, out)

    def test_identical_rows_over_different_craft_content_are_clean(self):
        self._write_pack("difapack", sections={
            "Vocabulary": "A module is the unit of code review here."})
        self._write_pack("difbpack", sections={
            "Vocabulary": "Evidence packets carry provenance for every claim."})
        out = self._run().stdout
        self.assertNotIn(VERBATIM, out)
        self.assertNotIn(NEAR, out)


class TestOutsideCitationExemption(_IsolatedTree):
    """An echo that cites an owner outside the pack, so two packs carrying
    it carry it by obligation. The pair below has the real tree's shape
    with the domain noun swapped for a synthetic one."""

    # packs/*/SKILL.md's shared opener: a sentence citing the owner outside
    # the standard (`](../`), which every standard may carry once the fact
    # moved to one owner.
    CITATION = (
        "The shape principles every %s shares are "
        "[rules/token-economy.md](../../rules/token-economy.md) §10's."
    )

    def test_the_outside_citation_is_exempt(self):
        self._write_pack("openerapack",
                         sections={"Vocabulary": self.CITATION % "alpha"})
        self._write_pack("openerbpack",
                         sections={"Vocabulary": self.CITATION % "beta"})
        result = self._run()
        self.assertEqual(0, result.returncode, result.stdout)
        self.assertNotIn(VERBATIM, result.stdout)
        self.assertNotIn(NEAR, result.stdout)


class TestAllowlist(unittest.TestCase):
    def test_every_allowlisted_clause_is_in_the_form_the_matcher_compares(self):
        """tools/validate.py:1108-1118 matches allowlisted clauses against
        `cell_clauses` output exactly. An entry written in any other form
        -- wrapped across lines, carrying its bullet marker, or holding a
        semicolon the splitter would cut -- matches nothing, so it exempts
        nothing while reading as though it does, and the finding it was
        written to excuse comes back with no trace of why."""
        for family in validate.CELL_DUPLICATION_ALLOWLIST:
            for clause in family["clauses"]:
                with self.subTest(family=family["family"], clause=clause[:40]):
                    self.assertEqual([clause], validate.cell_clauses(clause))

    def test_the_real_tree_carries_no_unallowed_verbatim_duplication(self):
        result = validate_the_real_tree()
        self.assertEqual(0, result.returncode, result.stdout)
        self.assertNotIn(VERBATIM, result.stdout)


# --- the warning ratchets ---------------------------------------------
#
# tools/validate.py returns has_errors inverted, so exit 0 is blind to
# every WARN it printed. Until these ceilings, nothing anywhere read the
# count: the tree could slide back to any number and stay green. The
# ceilings are the claim exit 0 now carries.
#
# One ceiling per kind of finding, never one over the total. A total
# counted two unrelated claims as one number, so a new kind of check could
# not be added without either raising the cell ratchet -- which is what it
# exists to forbid -- or being suppressed. A kind with no ceiling of its
# own is simply not ratcheted, which is the decision made out loud rather
# than by arithmetic.
#
# 47 is what the tree reported at ff30d60, every one of them a
# near-duplicate cell clause. WARNING_CEILING is the count of those the
# tree reports now, set with no headroom on purpose: headroom is a
# standing licence to regress into it, and every warning still under the
# ceiling is a duplication nobody has argued for yet. It ratchets down as
# those are fixed. Raising it is a decision, and it belongs in the commit
# message that raises it.
BASELINE_WARNINGS = 47
WARNING_CEILING = 0

# The cross-tier linter's own ratchet (validate.py's
# validate_cross_tier_duplication). Every one of these is a clause two
# tiers carry -- a fact with two owners -- and the number ratchets to 0,
# at which point validate.py's CROSS_TIER_DUPLICATE_LEVEL flips to
# "ERROR" and a new copy is refused outright rather than counted
# (REVIEW-2026-08-15 T2). No headroom, for the
# same reason as above. Raised once, at the P4 gate join (2026-08-16),
# from 12 to the count the widened corpus reports: the check now reads
# docs/ (vocabulary.md excepted -- the definitional owner) and
# example-workflows/ and compares skills against skills. V2 deliberately binds
# names across tier owners; its exact count has no headroom and only falls.
CROSS_TIER_WARNING_CEILING = 29

# A clone is the whole tree minus version control, runtime state and
# caches -- never an extract of the directories the check happens to read
# today, which would stop grading whatever it left out. Two payload
# directories are skipped as well, and only because the skip is itself
# checked: benchmarks/ and tests/fixtures/ hold 1275 of the tree's 1492
# files and eight tenths of the copy's cost, and the case below asserts
# the clone's report equals the real tree's line for line -- so anything
# in them that validate.py grades fails there, loudly, instead of quietly
# going ungraded.
CLONE_SKIPS = shutil.ignore_patterns(
    ".git", ".claude", ".orch", "__pycache__", "*.pyc", ".venv", ".mypy_cache",
    "benchmarks", "fixtures",
)


def run_validate(root):
    """tools/validate.py over the tree at `root`. ROOT is validate.py's
    own parent.parent, so the copy in a clone grades the clone."""
    return subprocess.run(
        [sys.executable, str(Path(root) / "tools" / "validate.py")],
        capture_output=True,
        text=True,
    )


def warning_lines(stdout, kind=None):
    """Every WARN in a validate.py report, or every WARN of one kind.

    The kind is the finding's own words -- NEAR, CROSS_TIER -- because that
    is what a ceiling is about. Counting whatever a run printed makes one
    check's regression indistinguishable from another check's arrival."""
    return [
        line for line in stdout.splitlines()
        if line.startswith("WARN") and (kind is None or kind in line)
    ]
