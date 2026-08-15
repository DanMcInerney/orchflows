"""Checks for scripts/isolate.py, the verification-isolation harness."""

import contextlib
import io
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import isolate  # noqa: E402
from tests.tree_removal import remove_repo_tree  # noqa: E402  the removal's one owner


def git(repo, *args):
    subprocess.run(
        ["git", "-C", str(repo)] + list(args),
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class IsolateTest(unittest.TestCase):
    """Each case gets its own throwaway repository; none reads this one."""

    @classmethod
    def setUpClass(cls):
        """The base repository costs six git subprocesses, and every case
        needs the same one: built per test that was ~108 git invocations for
        eighteen cases, over half the module's runtime. Built once here and
        copied per test instead, so each case still owns a private, mutable
        repository -- isolate.py's own subject rewrites it -- without paying
        git again. Same hoist as tests/test_cutcheck.py:828."""

        cls._template_root = Path(tempfile.mkdtemp(prefix="isolate-template-"))
        cls.addClassCleanup(remove_repo_tree, str(cls._template_root))
        template = cls._template_root / "repo"
        template.mkdir()
        git(template, "init", "-q")
        git(template, "config", "user.email", "t@example.invalid")
        git(template, "config", "user.name", "t")
        # The template is read by every test's copy and written by none.
        # Auto-gc and background maintenance would still write to it --
        # a lock file under `.git/objects` that exists when copytree
        # lists the directory and is gone when it reaches the entry.
        git(template, "config", "gc.auto", "0")
        git(template, "config", "maintenance.auto", "false")
        write(template / "kept.md", "committed\n")
        write(template / "changed.md", "committed\n")
        write(template / "gone.md", "committed\n")
        write(template / ".gitignore", ".orch/\n")
        git(template, "add", "-A")
        git(template, "commit", "-qm", "base")
        cls._template = template

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="isolate-test-"))
        self.addCleanup(remove_repo_tree, str(self.tmp))
        self.repo = self.tmp / "repo"
        self.dest = self.tmp / "out"
        # `*.lock` is never copied: a lock names a write in progress, so
        # carrying one into a fresh repository would be wrong even if it
        # survived the copy. Belt to the template's braces above -- a git
        # this suite did not configure is still git.
        shutil.copytree(
            self._template,
            self.repo,
            symlinks=True,
            ignore=shutil.ignore_patterns("*.lock"),
        )

    def run_isolate(self, *args):
        """The harness's own report is captured, not interleaved with ours."""
        self.out, self.err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(self.out), contextlib.redirect_stderr(self.err):
            return isolate.main([str(self.dest), "--repo", str(self.repo)] + list(args))

    # --- the three the ticket names -----------------------------------

    def test_an_empty_path_set_exports_the_revision_and_nothing_else(self):
        write(self.repo / "changed.md", "dirty\n")
        write(self.repo / "untracked.md", "dirty\n")
        self.assertEqual(0, self.run_isolate())
        self.assertEqual("committed\n", (self.dest / "changed.md").read_text())
        self.assertEqual("committed\n", (self.dest / "kept.md").read_text())
        self.assertFalse((self.dest / "untracked.md").exists())

    def test_a_path_set_naming_a_deleted_file_removes_it_from_the_export(self):
        (self.repo / "gone.md").unlink()
        self.assertEqual(0, self.run_isolate("--path", "gone.md"))
        self.assertFalse((self.dest / "gone.md").exists())
        self.assertEqual("committed\n", (self.dest / "kept.md").read_text())

    def test_the_named_orch_run_directory_is_copied_though_git_ignores_it(self):
        write(self.repo / ".orch" / "runs" / "R1" / "worklog.md", "state\n")
        self.assertEqual(0, self.run_isolate("--orch-run", "R1"))
        self.assertEqual(
            "state\n",
            (self.dest / ".orch" / "runs" / "R1" / "worklog.md").read_text(),
        )

    # --- the overlay is real, not decorative --------------------------

    def test_a_named_modified_path_carries_the_working_tree_bytes(self):
        write(self.repo / "changed.md", "dirty\n")
        self.assertEqual(0, self.run_isolate("--path", "changed.md"))
        self.assertEqual("dirty\n", (self.dest / "changed.md").read_text())
        self.assertEqual("committed\n", (self.dest / "kept.md").read_text())

    def test_dirty_takes_every_working_tree_change_including_a_rename(self):
        write(self.repo / "changed.md", "dirty\n")
        (self.repo / "gone.md").unlink()
        git(self.repo, "mv", "kept.md", "moved.md")
        write(self.repo / "untracked.md", "new\n")
        self.assertEqual(0, self.run_isolate("--dirty"))
        self.assertEqual("dirty\n", (self.dest / "changed.md").read_text())
        self.assertEqual("committed\n", (self.dest / "moved.md").read_text())
        self.assertFalse((self.dest / "kept.md").exists())
        self.assertFalse((self.dest / "gone.md").exists())
        self.assertEqual("new\n", (self.dest / "untracked.md").read_text())

    def test_a_renamed_directory_leaves_no_empty_ghost_behind(self):
        """A directory scanner still sees an emptied directory as a case."""
        write(self.repo / "nest" / "deep" / "a.md", "committed\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "nest")
        git(self.repo, "mv", "nest", "moved")
        self.assertEqual(0, self.run_isolate("--dirty"))
        self.assertEqual("committed\n", (self.dest / "moved" / "deep" / "a.md").read_text())
        self.assertFalse((self.dest / "nest").exists())
        self.assertTrue((self.dest / "kept.md").exists())

    def test_an_excluded_prefix_stays_at_the_revision(self):
        write(self.repo / "changed.md", "dirty\n")
        self.assertEqual(0, self.run_isolate("--dirty", "--exclude", "changed.md"))
        self.assertEqual("committed\n", (self.dest / "changed.md").read_text())

    def test_an_excluded_prefix_is_a_path_prefix_not_a_string_prefix(self):
        """`--exclude docs` takes `docs/`, never `docsmith/`."""
        write(self.repo / "docs" / "a.md", "committed\n")
        write(self.repo / "docsmith" / "b.md", "committed\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "trees")
        write(self.repo / "docs" / "a.md", "dirty\n")
        write(self.repo / "docsmith" / "b.md", "dirty\n")
        self.assertEqual(0, self.run_isolate("--dirty", "--exclude", "docs"))
        self.assertEqual("committed\n", (self.dest / "docs" / "a.md").read_text())
        self.assertEqual("dirty\n", (self.dest / "docsmith" / "b.md").read_text())

    def test_baseline_ignores_the_path_set_so_both_readings_share_a_harness(self):
        write(self.repo / "changed.md", "dirty\n")
        self.assertEqual(0, self.run_isolate("--dirty", "--baseline"))
        self.assertEqual("committed\n", (self.dest / "changed.md").read_text())

    def test_a_named_directory_is_overlaid_whole(self):
        write(self.repo / "tree" / "a.md", "new\n")
        self.assertEqual(0, self.run_isolate("--path", "tree"))
        self.assertEqual("new\n", (self.dest / "tree" / "a.md").read_text())

    # --- refusals: a harness that cannot do its job says so -----------

    def test_an_orch_run_that_does_not_exist_is_refused_not_skipped(self):
        self.assertEqual(1, self.run_isolate("--orch-run", "absent"))

    def test_an_orch_run_escaping_the_run_directory_is_refused(self):
        """`--orch-run ../../secret` wrote outside `.orch/runs/` and said 0 problems."""
        write(self.repo / ".orch" / "runs" / "R1" / "worklog.md", "state\n")
        write(self.repo / "docs" / "a.md", "committed\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "docs")
        write(self.repo / "secret" / "s.md", "private\n")
        self.assertEqual(1, self.run_isolate("--orch-run", "../../secret"))
        self.assertFalse((self.dest / "secret").exists())
        # The sibling variant raised an unhandled FileExistsError instead.
        self.assertEqual(1, self.run_isolate("--orch-run", "../../docs", "--force"))

    def test_a_run_directory_it_cannot_copy_is_refused_by_name(self):
        """A file where the run directory goes: a named refusal, not a traceback."""
        write(self.repo / ".orch" / "runs" / "R1", "a file, not a directory\n")
        git(self.repo, "add", "-f", ".orch/runs/R1")
        git(self.repo, "commit", "-qm", "run path as a file")
        (self.repo / ".orch" / "runs" / "R1").unlink()
        write(self.repo / ".orch" / "runs" / "R1" / "worklog.md", "state\n")
        self.assertEqual(1, self.run_isolate("--orch-run", "R1"))
        self.assertIn("isolate:", self.err.getvalue())

    def test_a_path_escaping_the_repository_is_refused(self):
        self.assertEqual(1, self.run_isolate("--path", "../elsewhere.md"))
        self.assertEqual(1, self.run_isolate("--path", str(self.tmp / "x.md")))

    def test_baseline_validates_the_path_set_it_ignores(self):
        """A gate that disappears with an unrelated flag is not a gate."""
        self.assertEqual(1, self.run_isolate("--baseline", "--path", "../elsewhere.md"))

    def test_a_path_in_neither_the_working_tree_nor_the_export_is_refused(self):
        """A typo'd `--path` overlaid nothing, exited 0, and the tree read baseline."""
        write(self.repo / "changed.md", "dirty\n")
        self.assertEqual(1, self.run_isolate("--path", "chagned.md"))
        self.assertEqual(1, self.run_isolate("--path", "nowhere/at/all.md", "--force"))

    def test_an_unknown_revision_is_refused(self):
        self.assertEqual(1, self.run_isolate("--rev", "no-such-rev"))

    def test_a_non_empty_destination_is_refused_without_force(self):
        self.assertEqual(0, self.run_isolate())
        self.assertEqual(1, self.run_isolate())
        self.assertEqual(0, self.run_isolate("--force"))


if __name__ == "__main__":
    unittest.main()
