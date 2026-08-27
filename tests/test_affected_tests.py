"""Compatibility collector for the partitioned affected-test resolver suite.

The three case modules carry the resolver's edge-kind and CLI grading over a
synthetic non-git tree. What lives here is what needs a *committed* tree to be
graded at all: the measured import graph, and the purity of selection with
respect to everything the commit does not record.
"""
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.test_affected_tests_cases.fixture_tree import *  # noqa: F401,F403
from tests.test_affected_tests_cases.live_repo import *  # noqa: F401,F403
from tests.test_affected_tests_cases.runner_scope import *  # noqa: F401,F403

from tests.test_affected_tests_cases.common import run_cli

from tools import affected_tests  # noqa: E402

# One file per import shape the resolver must follow. Nothing here is imported
# by the resolver; it is committed, then read back out of the commit.
GIT_FIXTURE_SOURCES = {
    # The runtime directory is gitignored here for the same reason it is in
    # this repository: it is where a run's own state goes, and no commit
    # records it.
    ".gitignore": ".orch/\n",
    "scripts/__init__.py": '"""Fixture package."""\n',
    # The facade shape: the shard names only ``scripts.facade``, and the file
    # it must select is reached by a relative import one level down.
    "scripts/facade.py": (
        '"""Fixture: a facade whose fan-out is a relative import."""\n'
        "from . import hidden_lint\n"
    ),
    "scripts/hidden_lint.py": 'VALUE = "hidden lint"\n',
    "scripts/hidden_deep.py": 'THING = "deep"\n',
    "scripts/shared_target.py": 'VALUE = "shared"\n',
    "scripts/deep/__init__.py": '"""Fixture subpackage."""\n',
    "scripts/deep/inner.py": (
        '"""Fixture: a two-level relative import."""\n'
        "from ..hidden_deep import THING\n"
    ),
    "tests/__init__.py": '"""Fixture suite package."""\n',
    "tests/test_facade_edge.py": (
        '"""Fixture: reaches hidden_lint only through the facade."""\n'
        "import scripts.facade\n"
    ),
    "tests/test_deep_edge.py": (
        '"""Fixture: reaches hidden_deep only through a relative import."""\n'
        "import scripts.deep.inner\n"
    ),
    "tests/test_owner_cases/__init__.py": '"""Fixture case package."""\n',
    "tests/test_owner_cases/common.py": (
        '"""Fixture: the shared fixture module two shards import."""\n'
        "from scripts import shared_target\n"
    ),
    "tests/test_owner.py": (
        '"""Fixture: the shard whose case package owns the fixture module."""\n'
        "from tests.test_owner_cases.common import *  # noqa: F401,F403\n"
    ),
    "tests/test_consumer.py": (
        '"""Fixture: a second shard consuming another shard\'s fixture."""\n'
        "from tests.test_owner_cases.common import *  # noqa: F401,F403\n"
    ),
    # ``inner`` names ``scripts/deep/inner.py``, which reaches
    # ``scripts/hidden_deep.py``. As a *literal* it is a fact about the file
    # that spells it and selects nothing. Admitted as a *graph edge* -- the
    # rejected design variant -- it drags this shard in behind ``inner``, and
    # the control below fails. That is the only thing separating the two
    # designs on this tree, so without it the control cannot fail at all.
    "tests/test_stranger.py": (
        '"""Fixture: a shard that reaches none of the targets."""\n'
        'NOTE = "inner"\n'
    ),
    # ``mypkgdir_notes`` contains ``pkgdir`` as a substring but sits under no
    # such directory. Whether the scope ``pkgdir`` is a directory therefore
    # decides this shard: a loose substring match takes it, the directory
    # branch does not. An untracked ``pkgdir/`` flips that answer -- which is
    # exactly the tree state selection must not read.
    "tests/test_decoy_dir.py": (
        '"""Fixture: a literal a directory scope must not take."""\n'
        'NOTE = "mypkgdir_notes"\n'
    ),
}


def git(root, *arguments) -> str:
    """Run one git command in ``root``, refusing to continue past a failure."""

    done = subprocess.run(
        ["git", "-c", "user.name=affected", "-c", "user.email=a@b.invalid",
         "-c", "commit.gpgsign=false", *arguments],
        cwd=str(root),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
    )
    if done.returncode != 0:
        raise AssertionError("git %s: %s" % (" ".join(arguments), done.stdout))
    return done.stdout.strip()


def write(root: Path, relative: str, source: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


class GitFixtureCase(unittest.TestCase):
    """A committed fixture repository, built once per test."""

    def setUp(self):
        self._scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self._scratch.cleanup)
        self.root = Path(self._scratch.name) / "repo"
        self.root.mkdir(parents=True)
        git(self.root, "init", "-q")
        for relative, source in GIT_FIXTURE_SOURCES.items():
            write(self.root, relative, source)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "fixture")

    def modules(self, *scope):
        return affected_tests.affected(scope, root=self.root)["modules"]


class TestMeasuredImportEdges(GitFixtureCase):
    """A shard is selected for what its imports actually reach, transitively."""

    def test_a_file_reached_only_through_a_facade_selects_its_shard(self):
        # The shard names ``scripts.facade`` and nothing else; a per-file scan
        # cannot see what the facade imports on its behalf.
        self.assertEqual(
            ["tests.test_facade_edge"], self.modules("scripts/hidden_lint.py")
        )

    def test_a_file_reached_only_through_a_relative_import_selects_its_shard(self):
        # ``from ..hidden_deep import THING`` -- the shape the ``node.level``
        # guard dropped outright.
        self.assertEqual(
            ["tests.test_deep_edge"], self.modules("scripts/hidden_deep.py")
        )

    def test_a_shared_fixture_module_carries_every_shard_that_imports_it(self):
        # ``test_consumer`` imports another shard's case module; the file that
        # case module imports is reached by both shards, not only its owner.
        self.assertEqual(
            ["tests.test_consumer", "tests.test_owner"],
            self.modules("scripts/shared_target.py"),
        )

    def test_a_shard_reaching_none_of_the_targets_is_never_selected(self):
        # A resolver answering "every shard" would satisfy the three above.
        for scope in ("scripts/hidden_lint.py", "scripts/hidden_deep.py",
                      "scripts/shared_target.py"):
            self.assertNotIn("tests.test_stranger", self.modules(scope), scope)


class TestSelectionPurity(GitFixtureCase):
    """Selection is a function of the commit, and of nothing else."""

    def test_an_untracked_test_module_does_not_change_selection(self):
        # Scoped at the file the shard imports outright, so an untracked
        # module reaching it is one a working-tree scan does take.
        before = self.modules("scripts/facade.py")
        self.assertEqual(["tests.test_facade_edge"], before)
        write(
            self.root,
            "tests/test_untracked_edge.py",
            '"""Untracked: reaches the target, and is not committed."""\n'
            "import scripts.facade\n",
        )
        self.assertEqual(before, self.modules("scripts/facade.py"))

    def test_an_uncommitted_edit_does_not_change_selection(self):
        before = self.modules("scripts/facade.py")
        write(
            self.root,
            "tests/test_stranger.py",
            GIT_FIXTURE_SOURCES["tests/test_stranger.py"] + "import scripts.facade\n",
        )
        self.assertEqual(before, self.modules("scripts/facade.py"))

    def test_an_untracked_directory_does_not_change_a_directory_scope(self):
        # ``describe`` asked the filesystem whether a scope path was a
        # directory, and the two branches disagree about ``mypkgdir_notes``.
        # Creating the directory must not move the answer.
        before = self.modules("pkgdir")
        self.assertEqual(["tests.test_decoy_dir"], before)
        write(self.root, "pkgdir/note.md", "untracked\n")
        self.assertEqual(before, self.modules("pkgdir"))

    def test_the_same_scope_run_twice_in_one_worktree_yields_one_answer(self):
        first = run_cli("--root", str(self.root), "scripts/hidden_lint.py")
        second = run_cli("--root", str(self.root), "scripts/hidden_lint.py")
        self.assertEqual(0, first.returncode, first.stderr)
        self.assertEqual(0, second.returncode, second.stderr)
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(["tests.test_facade_edge"], first.stdout.split())


class TestDiscoveryCache(GitFixtureCase):
    """Discovery is recorded once per committed revision, keyed by the tree."""

    def tree(self) -> str:
        return git(self.root, "rev-parse", "HEAD^{tree}")

    def test_the_first_resolve_records_discovery_and_the_second_is_served(self):
        first = affected_tests.affected(["scripts/hidden_lint.py"], root=self.root)
        self.assertEqual("git", first["discovery"]["source"])
        self.assertEqual(self.tree(), first["discovery"]["tree"])
        self.assertFalse(first["discovery"]["cached"])
        second = affected_tests.affected(["scripts/hidden_lint.py"], root=self.root)
        self.assertTrue(second["discovery"]["cached"])
        self.assertEqual(first["modules"], second["modules"])

    def test_a_new_commit_is_a_new_key_and_is_discovered_again(self):
        affected_tests.affected(["scripts/hidden_lint.py"], root=self.root)
        before = self.tree()
        write(self.root, "tests/test_stranger.py", "import scripts.facade\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "second")
        after = affected_tests.affected(["scripts/hidden_lint.py"], root=self.root)
        self.assertNotEqual(before, self.tree())
        self.assertFalse(after["discovery"]["cached"])
        self.assertIn("tests.test_stranger", after["modules"])

    def test_the_record_is_runtime_state_and_never_a_repository_artifact(self):
        from tools import run_tests

        affected_tests.affected(["scripts/hidden_lint.py"], root=self.root)
        cache = affected_tests.cache_dir(self.root)
        entries = sorted(cache.glob("*.json"))
        self.assertEqual(1, len(entries), entries)
        # One repository, one runtime-state location: the directory is the
        # unit-test runner's own, asked of the runner that owns it.
        self.assertEqual(run_tests.CACHE_PATH.parent.name, cache.parent.name)
        self.assertEqual(self.root, cache.parent.parent)
        # No tracked file moved, and the checkout is clean under the ignore
        # convention a repository carrying that directory keeps.
        self.assertEqual("", git(self.root, "status", "--porcelain", "-uno"))
        self.assertEqual("", git(self.root, "status", "--porcelain"))

    def test_a_tree_that_cannot_answer_for_a_commit_falls_back_and_says_so(self):
        # The three case modules resolve over a tree with no git at all; the
        # record must name that, rather than claim a revision it never read.
        with tempfile.TemporaryDirectory() as scratch:
            plain = Path(scratch) / "plain"
            for relative, source in GIT_FIXTURE_SOURCES.items():
                write(plain, relative, source)
            resolved = affected_tests.affected(["scripts/hidden_lint.py"], root=plain)
        self.assertEqual("filesystem", resolved["discovery"]["source"])
        self.assertIsNone(resolved["discovery"]["tree"])


class TestLiveFacadeMappings(unittest.TestCase):
    """The two mappings the proposal names, over this checkout's committed tree."""

    @classmethod
    def setUpClass(cls):
        cls.root = Path(affected_tests.ROOT)
        # The denominator is read out of the commit, not off disk.
        # ``shard_files`` globs the working tree, so an untracked
        # ``tests/test_*.py`` would inflate it and make the bound below
        # *easier* to clear -- working-tree state weakening a check, in the
        # suite whose whole subject is that selection does not read it.
        cls.shards = affected_tests.discover(cls.root, cls.root / "tests")["shards"]
        cls.for_lint = affected_tests.affected(["scripts/tickets_lint.py"])
        cls.for_issue = affected_tests.affected(["scripts/tickets_issue.py"])

    def test_the_lint_owner_selects_the_current_protocol_suite(self):
        self.assertIn("tests.test_ticket_protocol", self.for_lint["modules"])

    def test_the_issue_owner_selects_the_current_admission_suite(self):
        self.assertIn("tests.test_ticket_semantic_contract", self.for_issue["modules"])

    def test_neither_owner_selects_the_whole_suite(self):
        # Both reach the ticket facade, so both are wide; "wide" is not "all",
        # and a resolver that answered "all" would pass the two above. This
        # bound decides that one claim and no more. Measured: it does *not*
        # discriminate against admitting literals as graph edges -- that
        # variant selects 70 of 71 here and clears ``< 71`` comfortably. The
        # check that does fail against it is
        # ``TestMeasuredImportEdges.test_a_shard_reaching_none_of_the_targets_is_never_selected``.
        for resolved in (self.for_lint, self.for_issue):
            self.assertLess(len(resolved["modules"]), len(self.shards))


class TestPublicSurfaceAnotherModuleBindsTo(unittest.TestCase):
    """The names another file in this repository reaches into this one for."""

    def test_read_facts_survives_the_rebinding_cutcheck_graph_performs(self):
        # ``scripts/cutcheck_graph.py`` loads this resolver by path and then
        # does ``module.read_facts = lru_cache(...)(module.read_facts)``
        # *outside* any ``try``. Nothing inside this module calls
        # ``read_facts``, so nothing else keeps the name alive: were it
        # dropped as dead code, that line would raise ``AttributeError``
        # through ``_affected_tool``, whose caller does not guard it -- a
        # crash for every cut reading, not a degraded one. This is the only
        # check standing between that and a tidy-up.
        import functools
        import importlib.util

        path = Path(affected_tests.__file__)
        spec = importlib.util.spec_from_file_location("checker_affected", str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.read_facts = functools.lru_cache(maxsize=None)(module.read_facts)

        with tempfile.TemporaryDirectory() as scratch:
            source = Path(scratch) / "sample.py"
            source.write_text(
                "from . import sibling\nNOTE = 'a literal'\n", encoding="utf-8"
            )
            imports, literals = module.read_facts(source, "pkg/sample.py")
        # Still reads a file, still resolves the relative import against the
        # ``rel`` it is handed, and is still hashable enough to be memoised.
        self.assertIn("pkg.sibling", imports)
        self.assertIn("a literal", literals)


if __name__ == "__main__":
    unittest.main()
