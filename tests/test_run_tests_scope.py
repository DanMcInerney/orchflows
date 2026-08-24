"""The scoped runner's own oracle: what ``--scope`` admits, selects, refuses.

Every unit's completion decision flows through this branch, so its failure
mode is a false green rather than a red: a scope the shell split, an
admission over sources the run never named, a selection taken from a tree
the run is not deciding. Each is graded here as a refusal, by name.
"""

from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import run_tests, run_tests_scope  # noqa: E402


def answer(modules=(), no_tests=(), unreadable=(), source="git", tree="0123456789ab"):
    """One ``affected_tests.affected`` record, in the shape it returns."""

    return {
        "root": REPO_ROOT.as_posix(), "scope": [], "modules": list(modules),
        "no_tests": list(no_tests), "unreadable": list(unreadable),
        "discovery": {"source": source, "tree": tree, "cached": False},
    }


class TestScopeSpelling(unittest.TestCase):
    """``--scope a b c`` binds one path and demotes the rest to MODULEs.

    Measured: "2 modules, 19 tests: OK" at exit 0 where the comma spelling
    ran 22 modules and surfaced a red. The runner refuses the spelling
    instead of answering a question nobody asked.
    """

    def test_a_space_separated_scope_is_refused_and_names_what_it_dropped(self):
        with self.assertRaises(SystemExit) as raised:
            run_tests_scope.refuse_positional("tools/a.py", ["tools/b.py", "tools/c.py"])
        message = str(raised.exception.code)
        self.assertIn("tools/b.py", message)
        self.assertIn("tools/c.py", message)
        self.assertIn("tools/a.py,tools/b.py,tools/c.py", message)

    def test_a_scope_by_itself_is_accepted(self):
        self.assertIsNone(run_tests_scope.refuse_positional("tools/a.py", []))

    def test_modules_by_themselves_are_accepted(self):
        self.assertIsNone(run_tests_scope.refuse_positional(None, ["tests.test_x"]))

    def test_the_runner_refuses_the_spelling_before_it_reads_anything(self):
        """A mis-spelled scope costs one message, never a suite that was not
        the one asked for: the refusal precedes every other reading."""

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit) as raised:
                run_tests.main(["--tests-dir", tmp, "--scope", "tools/a.py", "tools/b.py"])
        self.assertIn("tools/b.py", str(raised.exception.code))


class TestScopedAdmission(unittest.TestCase):
    """The source-size admission covers what the invocation names.

    Measured: one sibling's over-cap committed file failed every unit's
    scoped oracle on a shared branch, whatever that unit had changed. An
    admission wider than the run is a red the run did not earn.
    """

    def test_a_scoped_run_admits_its_own_paths_only(self):
        self.assertEqual(
            ["tools/run_tests.py", "tests/test_run_tests.py"],
            run_tests_scope.admission_paths(
                "tools/run_tests.py,tests/test_run_tests.py",
                ["tests.test_run_tests"], True))

    def test_a_whole_suite_run_admits_the_whole_tree(self):
        self.assertEqual([], run_tests_scope.admission_paths(None, [], True))

    def test_an_explicit_module_run_admits_nothing(self):
        self.assertIsNone(
            run_tests_scope.admission_paths(None, ["tests.test_run_tests"], True))

    def test_a_custom_tests_directory_admits_nothing(self):
        self.assertIsNone(run_tests_scope.admission_paths(None, [], False))

    def test_the_scoped_admission_reads_the_scope_not_the_selected_modules(self):
        """The modules a scope selected are not the sources it named: the
        admission is owed over the paths, which is what --scope carries."""

        self.assertEqual(
            ["tools/run_tests_scope.py"],
            run_tests_scope.admission_paths(
                "tools/run_tests_scope.py",
                ["tests.test_run_tests", "tests.test_affected_tests"], True))


class TestSelectionIsAnAnswerNotASample(unittest.TestCase):
    """Three runs over one fixed tree agree, or the odd one out refuses.

    The resolver answers from the committed revision and the runner
    discovers from disk. Where those two disagree the selection is a
    sample of a tree nobody is deciding, and sampling is how one revision
    reported 28 modules and 1918 tests once and 29 and 1927 the next time.
    """

    def setUp(self):
        self._scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self._scratch.cleanup)
        self.root = Path(self._scratch.name)
        (self.root / "tests").mkdir()

    def select(self, record, scope="scripts/thing.py", discovered=("tests.test_alpha",),
               carried=None):
        """Select, with the revision's answer about a path's existence fixed.

        ``carried`` is what ``git ls-tree`` returns for a scope path: None
        where git cannot be asked at all, "" where the revision answers that
        it has no such path, and a listing where it carries one.
        """

        with mock.patch.object(
            run_tests_scope.affected_tests, "affected", return_value=record
        ), mock.patch.object(
            run_tests_scope.affected_tests, "git", return_value=carried
        ):
            return run_tests_scope.select(scope, self.root / "tests", list(discovered))

    def test_a_revision_answer_is_accepted(self):
        self.assertEqual(["tests.test_alpha"], self.select(answer(["tests.test_alpha"])))

    def test_a_working_tree_answer_inside_a_git_checkout_is_refused(self):
        """git could not answer, so the resolver read the disk instead --
        including every half-written file a concurrent worker owns. The
        silent fallback is the sampling; the refusal is the fix."""

        (self.root / ".git").write_text("gitdir: elsewhere\n", encoding="utf-8")
        with self.assertRaises(SystemExit) as raised:
            self.select(answer(["tests.test_alpha"], source="filesystem", tree=None))
        self.assertIn("working tree", str(raised.exception.code))

    def test_a_checkout_with_no_git_still_answers_from_the_working_tree(self):
        self.assertEqual(
            ["tests.test_alpha"],
            self.select(answer(["tests.test_alpha"], source="filesystem", tree=None)))

    def test_a_shard_on_disk_the_revision_does_not_carry_is_refused(self):
        """A test module the resolver cannot see is never selected, so a
        scope naming it would run green having run none of it."""

        with self.assertRaises(SystemExit) as raised:
            self.select(
                answer(["tests.test_alpha"], no_tests=["tests/test_new.py"]),
                scope="tests/test_new.py",
                discovered=("tests.test_alpha", "tests.test_new"))
        message = str(raised.exception.code)
        self.assertIn("tests/test_new.py", message)
        self.assertIn("commit", message)

    def test_a_scope_path_the_revision_does_not_carry_is_refused(self):
        """Reproduced by a sibling unit: --scope over two files that unit had
        just created printed "no affected module" for both and exited 0. The
        resolver had never read either file, which is a different answer from
        "no test covers this path" and must not be reported as that one."""

        with self.assertRaises(SystemExit) as raised:
            self.select(answer(["tests.test_alpha"], no_tests=["scripts/new.py"]),
                        scope="scripts/new.py", carried="")
        message = str(raised.exception.code)
        self.assertIn("scripts/new.py", message)
        self.assertIn("commit", message)

    def test_a_scope_path_the_revision_carries_stays_a_note(self):
        self.assertEqual(
            ["tests.test_alpha"],
            self.select(answer(["tests.test_alpha"], no_tests=["docs/thing.md"]),
                        scope="docs/thing.md", carried="docs/thing.md\n"))

    def test_a_path_git_cannot_be_asked_about_stays_a_note(self):
        """Absence of an answer is not an answer of absence: where git cannot
        be asked, the resolver's own reading stands."""

        self.assertEqual(
            ["tests.test_alpha"],
            self.select(answer(["tests.test_alpha"], no_tests=["docs/thing.md"]),
                        scope="docs/thing.md", carried=None))

    def test_the_selection_names_the_revision_it_decided_over(self):
        """Two runs that disagree are then attributable rather than
        mysterious: the summary carries the tree the answer came from."""

        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            self.select(answer(["tests.test_alpha"]))
        self.assertIn("0123456789ab", stream.getvalue())

    def test_the_selection_line_does_not_claim_to_be_running_anything(self):
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            self.select(answer(["tests.test_alpha"]))
        self.assertNotIn("running", stream.getvalue())


if __name__ == "__main__":
    unittest.main()
