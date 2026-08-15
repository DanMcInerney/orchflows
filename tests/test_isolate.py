"""Checks for scripts/isolate.py, the verification-isolation harness."""

import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import isolate  # noqa: E402
import state_root  # noqa: E402
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


class IsolateFixture(unittest.TestCase):
    """Each case builds a throwaway repository and a throwaway state sink;
    none reads this repository or this machine's own sink."""
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
        self.sink = self.tmp / "sink"
        self.sink.mkdir()
        sink_env = mock.patch.dict(os.environ, {state_root.ENV_VAR: str(self.sink)})
        sink_env.start()
        self.addCleanup(sink_env.stop)
        self.repo.mkdir()
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "t@example.invalid")
        git(self.repo, "config", "user.name", "t")
        write(self.repo / "kept.md", "committed\n")
        write(self.repo / "changed.md", "committed\n")
        write(self.repo / "gone.md", "committed\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "base")
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

    def write_run(self, run: str, text: str = "state\n") -> Path:
        """One run's worklog in the temporary sink, where the harness reads."""
        write(self.sink / "runs" / run / "worklog.md", text)
        return self.sink / "runs" / run

    def copied(self, run: str) -> Path:
        return self.dest / isolate.SINK_COPY / "runs" / run / "worklog.md"


class IsolateTest(IsolateFixture):

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

    def test_the_named_run_is_copied_out_of_the_sink_git_never_held_it(self):
        self.write_run("R1")
        self.assertEqual(0, self.run_isolate("--orch-run", "R1"))
        self.assertEqual("state\n", self.copied("R1").read_text())

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
        """`--orch-run ../../secret` wrote outside the runs root and said 0
        problems."""
        self.write_run("R1")
        write(self.repo / "docs" / "a.md", "committed\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "docs")
        write(self.sink / "secret" / "s.md", "private\n")
        self.assertEqual(1, self.run_isolate("--orch-run", "../../secret"))
        self.assertFalse((self.dest / "secret").exists())
        # The sibling variant raised an unhandled FileExistsError instead.
        self.assertEqual(1, self.run_isolate("--orch-run", "../../docs", "--force"))

    def test_a_run_directory_it_cannot_copy_is_refused_by_name(self):
        """A file where the snapshot goes: a named refusal, not a traceback."""
        target = "{}/runs/R1".format(isolate.SINK_COPY)
        write(self.repo / target, "a file, not a directory\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "snapshot path as a file")
        self.write_run("R1")
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


class TestIsolateCopiesFromSink(IsolateFixture):
    """Item 05 criterion 3. The run state a check reads in the isolated tree
    comes out of the one user-scope sink, not out of the repository being
    exported -- which, after this run, holds none."""

    def test_a_run_in_the_sink_alone_is_copied_into_the_tree(self):
        self.write_run("20260814T124222Z-centralize-state", "one worklog line\n")
        self.assertFalse((self.repo / ".orch").exists())

        self.assertEqual(
            0, self.run_isolate("--orch-run", "20260814T124222Z-centralize-state")
        )

        self.assertEqual(
            "one worklog line\n",
            self.copied("20260814T124222Z-centralize-state").read_text(),
        )

    def test_the_snapshot_keeps_the_sinks_own_layout(self):
        """`ORCHFLOWS_STATE_HOME` pointed at the snapshot resolves the run
        exactly as it resolves it in the real sink, so a check in the tree
        needs no second recipe."""

        source = self.write_run("R1")
        self.assertEqual(0, self.run_isolate("--orch-run", "R1"))

        snapshot = self.dest / isolate.SINK_COPY
        with mock.patch.dict(os.environ, {state_root.ENV_VAR: str(snapshot)}):
            self.assertEqual(snapshot / "runs" / "R1", state_root.runs_root() / "R1")
        self.assertEqual(
            source.relative_to(self.sink), (snapshot / "runs" / "R1").relative_to(snapshot)
        )

    def test_the_report_names_where_the_snapshot_landed(self):
        self.write_run("R1")
        self.assertEqual(0, self.run_isolate("--orch-run", "R1"))
        self.assertIn(isolate.SINK_COPY, self.out.getvalue())
        # Nothing copied, nothing promised: a named empty snapshot invites a
        # check to point at one.
        self.assertEqual(0, self.run_isolate("--force"))
        self.assertNotIn(isolate.SINK_COPY, self.out.getvalue())

    def test_several_runs_are_copied_and_each_keeps_its_own_directory(self):
        self.write_run("R1", "first\n")
        self.write_run("R2", "second\n")
        self.assertEqual(0, self.run_isolate("--orch-run", "R1", "--orch-run", "R2"))
        self.assertEqual("first\n", self.copied("R1").read_text())
        self.assertEqual("second\n", self.copied("R2").read_text())

    def test_a_run_absent_from_the_sink_is_the_named_refusal(self):
        """Not a silent empty copy: a tree missing the state a check reads
        grades the check against nothing and calls it green."""

        self.write_run("R1")

        self.assertEqual(1, self.run_isolate("--orch-run", "R2"))

        self.assertIn("no run directory in the state sink", self.err.getvalue())
        self.assertIn("runs/R2", self.err.getvalue())
        self.assertFalse((self.dest / isolate.SINK_COPY).exists())

    def test_a_run_present_only_in_the_repository_is_refused(self):
        """The old source, kept on disk by item 08's copy-never-move rule, is
        no longer a source: reading it would resurrect the per-repository
        state this run removes."""

        write(self.repo / ".orch" / "runs" / "R1" / "worklog.md", "stale\n")

        self.assertEqual(1, self.run_isolate("--orch-run", "R1"))

        self.assertIn("no run directory in the state sink", self.err.getvalue())

    def test_the_sink_is_read_and_never_written(self):
        self.write_run("R1")
        before = sorted(
            (p.relative_to(self.sink).as_posix(), p.is_dir())
            for p in self.sink.rglob("*")
        )

        self.assertEqual(0, self.run_isolate("--orch-run", "R1"))

        self.assertEqual(
            before,
            sorted(
                (p.relative_to(self.sink).as_posix(), p.is_dir())
                for p in self.sink.rglob("*")
            ),
        )

    def test_the_source_names_no_state_path_of_its_own(self):
        """Item 05 criterion 6 for this file: the sink comes from the
        resolver, and no `.orch` literal composes a path here."""

        source = (ROOT / "scripts" / "isolate.py").read_text(encoding="utf-8")
        self.assertIn("state_root.runs_root()", source)
        self.assertNotIn('".orch/runs"', source)
        self.assertNotIn('".orch"', source)


if __name__ == "__main__":
    unittest.main()
