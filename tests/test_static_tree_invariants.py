"""Invariants of the committed tree that hold without running anything: the
frozen role census, tier and folder shape, the dependency-ordered overlap
clause, skill anatomy order, composition link resolution, and the benchmark
architecture's call graph.

Merged from test_roles.py, test_tree.py, test_adaptive_delivery.py and
test_benchmark_architecture.py, which walked the tree four times over. Every
test here reads committed files; the only subprocess is the one git index read
that no filesystem check can substitute for.
"""
import ast
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tools.validate as validate  # noqa: E402

SKILL_TIERS = ("kernel", "engines", "workflows", "instances", "utilities")

DECOMPOSE = ROOT / "skills" / "kernel" / "orch-decompose" / "SKILL.md"
CODE_SLICING = ROOT / "packs" / "orch-code-pack" / "references" / "slicing.md"
DESIGN_SLICING = ROOT / "packs" / "orch-design-pack" / "references" / "slicing.md"
OVERLAP_RULE = "a write scope overlapping only siblings it is dependency-ordered with"

COMPOSITIONS = ROOT / "compositions"
EVAL_DESIGN = ROOT / "skills" / "workflows" / "orch-eval-design" / "SKILL.md"
PANEL = ROOT / "skills" / "engines" / "orch-panel" / "SKILL.md"
EVOLVE = COMPOSITIONS / "evolve.md"
EVOLVE_GENERATION = COMPOSITIONS / "references" / "evolve-generation.md"
TOURNAMENT = COMPOSITIONS / "skill-tournament.md"

CALL_EDGE_RE = re.compile(r"`(orch-[a-z0-9-]+)`")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
FRONTMATTER_RE = re.compile(r"---\n(.*?)\n---\n(.*)", re.DOTALL)

# The frozen role census. Its criterion is owned by rules/roles.md clause 2
# (planner is judgment, worker is execution) and clause 4 (a skill's declared
# role is what a dispatch resolves against); tools/validate.py enforces the
# structural half -- `role` present, in ROLE_VALUES, and `none` for every
# engines/workflows skill. What it cannot enforce, and what this table is, is
# which of planner and worker each kernel, instances and utilities skill was
# assigned, plus a census tripwire: a skill added, removed or renamed without
# a deliberate role decision fails here.
ROLE_TABLE = {
    # none: all engines
    "orch-compose": "none",
    "orch-loop": "none",
    "orch-panel": "none",
    "orch-task": "none",
    "orch-frontier": "none",
    # none: all workflows (orch-fix, orch-evolve, orch-benchmaker were
    # demoted to compositions/, which carry no role)
    "orch-build": "none",
    "orch-diagnose": "none",
    "orch-eval-design": "none",
    "orch-fixture": "none",
    "orch-repair": "none",
    "orch-self-improve": "none",
    "orch-spec": "none",
    "orch-triage": "none",
    # none: named kernel
    "orch-delegate": "none",
    "orch-elicit": "none",
    "orch-integrate": "none",
    "orch-worklog": "none",
    # none: named utility
    "orch-off": "none",
    "orch-search-plan": "none",
    # planner
    "orch-critique": "planner",
    "orch-judge": "planner",
    "orch-synthesize": "planner",
    "orch-decompose": "planner",
    # worker
    "orch-check": "worker",
    "orch-investigate": "worker",
    "orch-verify": "worker",
    "orch-mechanize": "worker",
    "orch-workspace": "worker",
    "orch-tdd": "worker",
    "orch-draft": "worker",
    "orch-render": "worker",
    "orch-edit": "worker",
    "orch-resolve-conflicts": "worker",
    "orch-visualize": "worker",
}

_PACKAGES = None


def packages():
    """One `discover_packages()` walk for the whole module."""
    global _PACKAGES
    if _PACKAGES is None:
        _PACKAGES = validate.discover_packages()
    return _PACKAGES


def frontmatter_name(skill_md: Path):
    """The declared name, read without validate.py's parser: this is the
    independent oracle for the same rule validate.py enforces."""
    for line in skill_md.read_text(encoding="utf-8").split("\n"):
        if line.startswith("name:"):
            return line.split(":", 1)[1].strip()
    return None


def read_flat(path: Path) -> str:
    """File text with whitespace collapsed, so wrapped clauses match."""
    return re.sub(r"\s+", " ", path.read_text(encoding="utf-8"))


def split_document(path: Path):
    """(frontmatter fields, body). A references file carries no frontmatter
    and is all body."""
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.fullmatch(text)
    if match is None:
        return {}, text
    fields = {}
    for line in match.group(1).splitlines():
        key, value = line.split(":", 1)
        fields[key] = value.strip()
    return fields, match.group(2)


def bodies(*paths: Path) -> str:
    return "".join(split_document(path)[1] for path in paths)


class TestFrozenRoleTable(unittest.TestCase):
    def test_table_covers_exactly_every_skill(self):
        skill_names = {pkg["path"].name for pkg in packages() if not pkg["is_pack"]}
        self.assertEqual(skill_names, set(ROLE_TABLE))

    def test_each_skill_declares_its_frozen_role(self):
        diag = validate.Diagnostics()
        for pkg in packages():
            if pkg["is_pack"]:
                continue
            text = validate._read_source(pkg["skill_md"])
            fm, _ = validate.parse_frontmatter(text, validate.rel(pkg["skill_md"]), diag)
            name = pkg["path"].name
            self.assertEqual(
                ROLE_TABLE[name], fm.get("role"),
                f"{name}: declared role does not match the frozen table",
            )


class TestTierDirectoriesExist(unittest.TestCase):
    def test_every_skill_tier_directory_exists(self):
        for tier in SKILL_TIERS:
            self.assertTrue((ROOT / "skills" / tier).is_dir(), f"missing skills/{tier}")


class TestPackageNamesMatchFolders(unittest.TestCase):
    def test_every_skill_folder_matches_its_frontmatter_name(self):
        for tier in SKILL_TIERS:
            tier_dir = ROOT / "skills" / tier
            for pkg_dir in sorted(p for p in tier_dir.iterdir() if p.is_dir()):
                skill_md = pkg_dir / "SKILL.md"
                self.assertTrue(skill_md.is_file(), f"{pkg_dir} has no SKILL.md")
                name = frontmatter_name(skill_md)
                self.assertEqual(name, pkg_dir.name, f"{skill_md} name {name!r} != folder {pkg_dir.name!r}")

    def test_every_pack_folder_matches_its_frontmatter_name(self):
        packs_dir = ROOT / "packs"
        if not packs_dir.is_dir():
            self.skipTest("no packs/ directory")
        for pkg_dir in sorted(p for p in packs_dir.iterdir() if p.is_dir()):
            skill_md = pkg_dir / "SKILL.md"
            self.assertTrue(skill_md.is_file(), f"{pkg_dir} has no SKILL.md")
            name = frontmatter_name(skill_md)
            self.assertEqual(name, pkg_dir.name, f"{skill_md} name {name!r} != folder {pkg_dir.name!r}")


class TestRootShellEntryPointsAreExecutable(unittest.TestCase):
    """README documents `./install.sh`. Committed without the execute bit it
    answers `permission denied` on every fresh clone, which is how it shipped.

    Reads the index mode, never the filesystem: git checks out POSIX
    permissions only where the platform has them, so an `os.access` check
    would fail on the Windows leg for a tree that is correct.

    `install.cmd` stays 100644 on purpose -- Windows resolves it by extension
    and has no execute bit to set. `install.py` likewise: README invokes it as
    `python install.py`.
    """

    def test_every_root_shell_script_is_committed_executable(self):
        try:
            listing = subprocess.run(
                ["git", "ls-files", "-s"],
                cwd=ROOT, capture_output=True, text=True, check=True,
            ).stdout
        except (OSError, subprocess.CalledProcessError) as exc:
            self.skipTest(f"not a git checkout, so no index mode to read: {exc}")

        checked = []
        for line in listing.splitlines():
            meta, _, path = line.partition("\t")
            if "/" in path or not path.endswith(".sh"):
                continue
            checked.append(path)
            self.assertEqual(
                "100755", meta.split()[0],
                f"{path} is committed {meta.split()[0]}; README documents "
                f"./{path}, which needs the execute bit to run as written",
            )

        # Without this the test passes when the parse or the filter breaks.
        self.assertTrue(checked, "found no root-level *.sh to check")


class TestSkillAnatomyOrder(unittest.TestCase):
    """tools/validate.py requires `Require:`, `Never:` and `Return:` to be
    present; rules/composition.md orders them Require, procedure, Never,
    Return, and nothing enforced that order. A body carrying its Never after
    its Return still passes validate.py while reading as a different contract.
    Packs are exempt: their SKILL.md is a craft index, not a dispatchable
    contract, and carries none of the three.
    """

    def test_every_skill_body_orders_require_then_never_then_return(self):
        for pkg in packages():
            if pkg["is_pack"]:
                continue
            with self.subTest(skill=pkg["path"].name):
                _, body = split_document(pkg["skill_md"])
                self.assertLess(body.index("Require:"), body.index("Never:"))
                self.assertLess(body.index("Never:"), body.index("Return:"))


class TestDependencyOrderedOverlap(unittest.TestCase):
    """An item's write scope may overlap only siblings it is dependency-ordered
    with, so items with no dependency path between them can never collide
    however the frontier schedules them.

    The rule has one owner, `orch-decompose`, and only there is its wording
    asserted: requiring the same sentence in both slicing cells made the
    duplication mandatory, which is what SPEC-ticket-set.md P2 and
    REVIEW-2026-08-15 T2 invert (tests pin shapes, not sentences; the
    validator forbids copies instead of syncing them). What every cut is
    still held to is the absence of the two older rules a cell could regress
    to -- neither of which any owner states, so neither is a copy.
    """

    def test_the_owner_permits_overlap_along_dependency_order(self):
        self.assertIn(
            OVERLAP_RULE, read_flat(DECOMPOSE),
            "orch-decompose, the rule's one owner, does not permit overlap "
            "only along dependency order",
        )

    def test_no_cut_states_a_superseded_overlap_rule(self):
        for label, path in (
            ("orch-decompose", DECOMPOSE),
            ("code pack slicing", CODE_SLICING),
            ("design pack slicing", DESIGN_SLICING),
        ):
            text = read_flat(path)
            self.assertNotIn(
                "disjoint from its siblings", text,
                f"{label} still states the old global-disjointness rule, which "
                "forces layer-shaped cuts",
            )
            self.assertNotIn(
                "sharing its frontier", text,
                f"{label} still scopes overlap by frontier; siblings in "
                "different frontiers can be concurrently in flight and collide",
            )

    def test_the_code_cut_puts_the_riskiest_seam_first(self):
        self.assertIn(
            "the first frontier carries the riskiest seam's tracer",
            read_flat(CODE_SLICING),
            "code pack slicing does not put the riskiest seam's tracer in the "
            "first frontier",
        )


class TestCompositionLinks(unittest.TestCase):
    """tools/validate.py resolves reference links for packages only
    (validate_reference_links runs inside the package loop), so a composition
    citing a file that does not exist validates clean and breaks at read time.
    """

    def test_every_composition_link_resolves(self):
        checked = 0
        for path in sorted(COMPOSITIONS.rglob("*.md")):
            for target in LINK_RE.findall(path.read_text(encoding="utf-8")):
                if target.startswith(("http://", "https://", "#", "mailto:")):
                    continue
                checked += 1
                resolved = (path.parent / target.split("#")[0]).resolve()
                with self.subTest(source=path.name, target=target):
                    self.assertTrue(
                        resolved.is_file(),
                        f"{path} cites {target}, which does not exist",
                    )
        self.assertTrue(checked, "found no composition links to resolve")


def _called_name(node):
    """The bare name of a call's target: `os.chdir` and `chdir` both give
    `chdir`, so a module's import style does not decide what is checked."""

    function = node.func
    if isinstance(function, ast.Attribute):
        return function.attr
    return function.id if isinstance(function, ast.Name) else None


def _calls_named(node, name):
    return any(
        isinstance(child, ast.Call) and _called_name(child) == name
        for child in ast.walk(node)
    )


class TestNoTempTreeIsDeletedWhileItIsTheCwd(unittest.TestCase):
    """Windows refuses to delete a directory that is any process's current
    directory; POSIX allows it. So this shape passes every POSIX runner and
    fails every Windows one, deterministically:

        with tempfile.TemporaryDirectory() as raw:
            os.chdir(Path(raw) / "repo")
            self.addCleanup(os.chdir, before)

    The block deletes the tree when it exits, and `addCleanup` does not run
    until the whole test method has returned -- so the restore lands after
    the delete has already been attempted, and the delete dies on WinError
    32. The two safe shapes are both in this suite and both stay legal
    here: restore inside the block through `try/finally`, or hold the
    directory open (`tempfile.TemporaryDirectory()` bound to a name, its
    `cleanup` registered with `addCleanup` *before* the chdir's restore, so
    LIFO runs the restore first).

    Caught by CI three times in two days and never once locally, because
    the only host that can see it is the one this suite is least often run
    on. It is a shape, not a behavior, so a reader can see it here instead.
    """

    def test_no_chdir_inside_a_temporary_directory_block_defers_its_restore(self):
        offenders = []
        for path in sorted(Path(__file__).resolve().parent.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.With):
                    continue
                opens_temp_tree = any(
                    isinstance(item.context_expr, ast.Call)
                    and _called_name(item.context_expr) == "TemporaryDirectory"
                    for item in node.items
                )
                if not opens_temp_tree or not _calls_named(node, "chdir"):
                    continue
                # A restore anywhere in a `finally` inside the block runs
                # before the block's own cleanup, which is the whole point.
                restored = any(
                    isinstance(child, ast.Try)
                    and any(_calls_named(stmt, "chdir") for stmt in child.finalbody)
                    for child in ast.walk(node)
                )
                if not restored:
                    offenders.append(f"{path.name}:{node.lineno}")
        self.assertEqual([], offenders, "chdir inside a self-deleting temp tree")


class TestBenchmarkArchitecture(unittest.TestCase):
    """The benchmark architecture's shape: who may dispatch whom, and in what
    order. The prose these files carry is graded by tools/validate.py's cell
    and budget rules; what no other check reads is the call graph."""

    # (label, sources, exactly, at_least, never)
    CALL_EDGES = (
        (
            # orch-eval-design designs an evaluation and dispatches nothing:
            # it is the leaf that replaced orch-bench.
            "orch-eval-design", (EVAL_DESIGN,), frozenset(), frozenset(), frozenset(),
        ),
        (
            # The tournament binds the evolve campaign and its writer, never
            # evolve's internals.
            "skill-tournament", (TOURNAMENT,), frozenset(), frozenset(), frozenset(),
        ),
        (
            "orch-panel", (PANEL,),
            frozenset({"orch-judge", "orch-delegate", "orch-integrate"}),
            frozenset(), frozenset(),
        ),
        (
            "evolve", (EVOLVE, EVOLVE_GENERATION), None,
            frozenset({
                "orch-eval-design", "orch-loop", "orch-delegate", "orch-integrate",
                "orch-verify", "orch-panel", "orch-judge", "orch-search-plan",
                "orch-worklog",
            }),
            # The demoted skills stay demoted: a reappearing edge would route
            # a campaign into a skill that no longer exists.
            frozenset({"orch-bench", "orch-benchmaker"}),
        ),
    )

    def test_each_body_calls_exactly_the_edges_its_architecture_declares(self):
        for label, sources, exactly, at_least, never in self.CALL_EDGES:
            with self.subTest(body=label):
                calls = set(CALL_EDGE_RE.findall(bodies(*sources)))
                if exactly is not None:
                    self.assertEqual(set(exactly), calls)
                self.assertLessEqual(set(at_least), calls)
                self.assertEqual(set(), calls & set(never))

    def test_evolve_verifies_before_it_ranks_and_panels_before_it_judges(self):
        """Required eligibility is checked before survivors are ranked, and the
        panel's score cards exist before the judge's done-check reads them.
        Either inversion is a campaign that ranks ineligible candidates or
        judges nothing."""
        combined = bodies(EVOLVE, EVOLVE_GENERATION)
        self.assertLess(combined.index("`orch-verify`"), combined.index("`orch-panel`"))
        self.assertLess(combined.index("`orch-panel`"), combined.index("`orch-judge`"))

    def test_the_campaigns_stay_manual_only_entries(self):
        """`entry: named` is what keeps a campaign off the router. validate.py
        checks the value is one of routed | named | scheduled; which one each
        campaign carries is the decision."""
        for path in (EVOLVE, TOURNAMENT):
            with self.subTest(composition=path.name):
                self.assertEqual("named", split_document(path)[0].get("entry"))


if __name__ == "__main__":
    unittest.main()
