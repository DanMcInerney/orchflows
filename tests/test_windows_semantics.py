"""The guard that makes POSIX refuse what Windows refuses.

A guard nothing exercises is a guard that can stop working without
anyone noticing, and this one's whole value is that it fires on a host
where the underlying platform never would. Both sides are asserted: the
shape that killed a pull request on CI's one Windows leg, and the
shape the suite uses everywhere and must never flag.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

# S1 exception: computed locally, not imported from tests._repo_root.
# This file forces `import tests` below so the guard installs even
# under a bare `unittest discover -s tests` run -- so this walk must
# not itself depend on `tests` already being importable.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Absolute, not relative: `unittest discover -s tests` makes `tests` the
# top-level directory and imports these as bare modules, with no parent
# package to be relative to. Importing the package by name is also what
# installs the guard, and discovery imports every module before running
# any test -- so this line is what guarantees the guard is in place for
# the whole suite under a runner that never imports the package itself.
import tests as tests_package  # noqa: E402
from tests import _windows_semantics as guard  # noqa: E402

ON_WINDOWS = os.name == "nt"
WHY_SKIPPED = "the guard is not installed on Windows: the platform enforces this itself"


class CurrentCITopologyDocumentationTest(unittest.TestCase):
    def test_scoped_docstrings_name_ci_s_one_windows_leg(self):
        for module_doc in (tests_package.__doc__, guard.__doc__, __doc__):
            with self.subTest(module_doc=module_doc):
                flat = " ".join(module_doc.split())
                self.assertIn("one Windows leg", flat)
                self.assertNotIn("three Windows cells", flat)


class StandsElsewhere(unittest.TestCase):
    """Base for tests that move the process and must put it back.

    The restore is registered after the tree, so LIFO runs it first --
    the pattern the guard exists to require, used here on itself.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tree = Path(self._tmp.name).resolve()
        self.addCleanup(os.chdir, os.getcwd())


@unittest.skipIf(ON_WINDOWS, WHY_SKIPPED)
class TestTheGuardRefusesDeletingTheCwd(StandsElsewhere):
    def test_rmtree_of_the_directory_the_process_stands_in(self):
        os.chdir(self.tree)
        with self.assertRaises(guard.WindowsWouldRefuse):
            shutil.rmtree(self.tree)
        self.assertTrue(self.tree.is_dir(), "refused, so nothing was removed")

    def test_rmtree_of_an_ancestor_of_the_directory_the_process_stands_in(self):
        # Windows refuses the ancestor too: the handle on the child keeps
        # the parent non-empty, so the recursive delete cannot finish.
        deep = self.tree / "a" / "b"
        deep.mkdir(parents=True)
        os.chdir(deep)
        with self.assertRaises(guard.WindowsWouldRefuse):
            shutil.rmtree(self.tree / "a")

    def test_temporary_directory_cleanup_of_the_directory_it_moved_into(self):
        holder = tempfile.TemporaryDirectory()
        os.chdir(holder.name)
        with self.assertRaises(guard.WindowsWouldRefuse):
            holder.cleanup()
        os.chdir(self.tree)
        holder.cleanup()

    def test_os_rmdir_and_path_rmdir_and_removedirs(self):
        # `Path.rmdir` is patched separately from `os.rmdir` because
        # pathlib binds the latter at class-definition time through 3.9;
        # one assertion per entry point is what proves both landed.
        for remove in (os.rmdir, Path.rmdir, os.removedirs):
            with self.subTest(remove=getattr(remove, "__qualname__", remove)):
                here = self.tree / "leaf"
                here.mkdir()
                os.chdir(here)
                with self.assertRaises(guard.WindowsWouldRefuse):
                    remove(here)
                os.chdir(self.tree)
                here.rmdir()

    def test_the_refusal_is_not_an_oserror(self):
        # A caller guarding its own cleanup with `except OSError`, or a
        # TemporaryDirectory built with ignore_cleanup_errors, would
        # swallow the report if it were one.
        os.chdir(self.tree)
        with self.assertRaises(guard.WindowsWouldRefuse) as caught:
            shutil.rmtree(self.tree)
        self.assertNotIsInstance(caught.exception, OSError)

    def test_the_message_names_the_tree_the_cwd_and_the_way_out(self):
        os.chdir(self.tree)
        with self.assertRaises(guard.WindowsWouldRefuse) as caught:
            shutil.rmtree(self.tree)
        message = str(caught.exception)
        self.assertIn(str(self.tree), message)
        self.assertIn("addCleanup", message)
        self.assertIn(guard.SKIP_ENV, message)


@unittest.skipIf(ON_WINDOWS, WHY_SKIPPED)
class TestTheGuardPassesEverythingElse(StandsElsewhere):
    def test_a_sibling_tree_is_removed_normally(self):
        sibling = self.tree / "sibling"
        sibling.mkdir()
        (sibling / "f.txt").write_text("x", encoding="utf-8")
        os.chdir(self.tree)
        shutil.rmtree(sibling)
        self.assertFalse(sibling.exists())

    def test_a_prefix_match_that_is_not_a_parent_is_not_refused(self):
        # `/tmp/x` is a string prefix of `/tmp/xy` and an ancestor of
        # neither; a naive startswith would refuse this one.
        (self.tree / "x").mkdir()
        (self.tree / "xy").mkdir()
        os.chdir(self.tree / "xy")
        (self.tree / "x").rmdir()
        self.assertFalse((self.tree / "x").exists())

    def test_the_restored_cwd_pattern_this_suite_uses_is_never_flagged(self):
        # tests/test_friction.py's setUp, in miniature.
        holder = tempfile.TemporaryDirectory()
        repo = Path(holder.name).resolve() / "repo"
        repo.mkdir()
        before = os.getcwd()
        os.chdir(repo)
        try:
            self.assertTrue(Path.cwd().name == "repo")
        finally:
            os.chdir(before)
        holder.cleanup()
        self.assertFalse(repo.exists())

    def test_a_missing_or_unanswerable_path_is_left_to_the_real_call(self):
        # The guard reports on Windows semantics, never on whether a path
        # exists: that answer stays the platform's, unchanged.
        os.chdir(self.tree)
        with self.assertRaises(FileNotFoundError):
            os.rmdir(self.tree / "never-made")
        self.assertFalse(guard._holds_the_cwd(os.devnull))


class TestInstallation(unittest.TestCase):
    def test_installing_twice_does_not_wrap_twice(self):
        before = shutil.rmtree
        guard.install()
        self.assertIs(shutil.rmtree, before)

    def test_importing_the_package_installed_it(self):
        # The package `__init__` is the one import every runner makes;
        # if the guard moved out of it, this is what says so.
        self.assertEqual(not ON_WINDOWS, guard._installed)
