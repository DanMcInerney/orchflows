"""friction.py resolves .orch to the main checkout, one per repository."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "friction", ROOT / "scripts" / "friction.py"
)
friction = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_spec and friction)

REQUIRED_ENTRY_KEYS = {
    "ts", "cwd", "git_rev", "host", "session",
    "category", "skill", "ticket", "run", "observed", "expected",
}


class TestFindRepoRoot(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name).resolve()

    def tearDown(self):
        self._tmp.cleanup()

    def _make_main(self, name="main"):
        main = self.tmp / name
        (main / ".git").mkdir(parents=True)
        return main

    def test_main_checkout_resolves_to_itself(self):
        main = self._make_main()
        sub = main / "skills" / "kernel"
        sub.mkdir(parents=True)
        self.assertEqual(friction._find_repo_root(sub), main)

    def test_linked_worktree_resolves_to_main_checkout(self):
        main = self._make_main()
        (main / ".git" / "worktrees" / "wt").mkdir(parents=True)
        wt = self.tmp / "wt"
        wt.mkdir()
        (wt / ".git").write_text(
            f"gitdir: {main / '.git' / 'worktrees' / 'wt'}\n", encoding="utf-8"
        )
        self.assertEqual(friction._find_repo_root(wt), main)

    def test_relative_gitdir_pointer_resolves_to_superproject(self):
        super_repo = self._make_main("super")
        (super_repo / ".git" / "modules" / "mod").mkdir(parents=True)
        mod = super_repo / "mod"
        mod.mkdir()
        (mod / ".git").write_text("gitdir: ../.git/modules/mod\n", encoding="utf-8")
        self.assertEqual(friction._find_repo_root(mod), super_repo)

    def test_unparseable_git_file_falls_back_to_walk_up_result(self):
        main = self._make_main()
        wt = main / "vendored"
        wt.mkdir()
        (wt / ".git").write_text("not a gitdir pointer\n", encoding="utf-8")
        self.assertEqual(friction._find_repo_root(wt), wt)

    def test_no_repository_returns_none(self):
        bare = self.tmp / "bare"
        bare.mkdir()
        self.assertIsNone(friction._find_repo_root(bare))


class TestTargetPath(unittest.TestCase):
    def test_entry_from_worktree_lands_in_main_checkout(self):
        # Register the tempdir cleanup via addCleanup too (not a `with`
        # block): addCleanup runs LIFO, so the chdir-back registered after
        # it fires first. A `with tempfile.TemporaryDirectory()` wrapping a
        # chdir into itself has its own __exit__ run before any addCleanup,
        # and on Windows rmtree of the current working directory raises
        # PermissionError — that ordering bug is what this guards against.
        tmp_ctx = tempfile.TemporaryDirectory()
        self.addCleanup(tmp_ctx.cleanup)
        tmp_path = Path(tmp_ctx.name).resolve()
        main = tmp_path / "main"
        (main / ".git" / "worktrees" / "wt").mkdir(parents=True)
        wt = tmp_path / "wt"
        wt.mkdir()
        (wt / ".git").write_text(
            f"gitdir: {main / '.git' / 'worktrees' / 'wt'}\n", encoding="utf-8"
        )
        before = os.getcwd()
        os.chdir(wt)
        self.addCleanup(os.chdir, before)
        target = friction._target_path(friction.datetime.now(friction.timezone.utc))
        self.assertEqual(target.parent.parent.parent, main)


class _IsolatedRepoTestCase(unittest.TestCase):
    """Base for tests that run friction.main() against a synthetic repo root.

    Never touches the real .orch/ — cwd is pinned to a fresh tempdir
    containing its own fake .git, and restored via addCleanup even if
    the test body raises.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = Path(self._tmp.name).resolve() / "repo"
        (self.repo / ".git").mkdir(parents=True)
        before = os.getcwd()
        os.chdir(self.repo)
        self.addCleanup(os.chdir, before)

    def _log_path(self):
        stamp = friction.datetime.now(friction.timezone.utc).strftime("%Y-%m")
        return self.repo / ".orch" / "friction" / f"{stamp}.jsonl"

    def _run_main(self, argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = friction.main(argv)
        return rc, buf.getvalue()


class TestMainWritesEntry(_IsolatedRepoTestCase):
    def test_appends_exactly_one_json_line_with_required_keys(self):
        rc, out = self._run_main(["observed thing", "expected thing", "--category", "tool-failure"])
        self.assertEqual(rc, 0)
        self.assertEqual(out.strip(), "friction logged")
        lines = self._log_path().read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)
        entry = json.loads(lines[0])
        self.assertEqual(set(entry), REQUIRED_ENTRY_KEYS)
        self.assertEqual(entry["observed"], "observed thing")
        self.assertEqual(entry["expected"], "expected thing")
        self.assertEqual(entry["category"], "tool-failure")

    def test_second_call_appends_a_second_line_not_a_rewrite(self):
        self._run_main(["first observed", "first expected"])
        self._run_main(["second observed", "second expected"])
        lines = self._log_path().read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 2)
        self.assertEqual(json.loads(lines[0])["observed"], "first observed")
        self.assertEqual(json.loads(lines[1])["observed"], "second observed")

    def test_flag_equals_value_forms_parse(self):
        rc, _ = self._run_main([
            "o", "e",
            "--category=workaround", "--skill=orch-tdd",
            "--ticket=t2-friction-hardening", "--run=20260717T161634Z-adversarial-test-sweep",
        ])
        self.assertEqual(rc, 0)
        entry = json.loads(self._log_path().read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual(entry["category"], "workaround")
        self.assertEqual(entry["skill"], "orch-tdd")
        self.assertEqual(entry["ticket"], "t2-friction-hardening")
        self.assertEqual(entry["run"], "20260717T161634Z-adversarial-test-sweep")

    def test_mixed_space_and_equals_flag_forms_parse_together(self):
        rc, _ = self._run_main(["o", "e", "--category", "misrouting", "--skill=orch-tdd"])
        self.assertEqual(rc, 0)
        entry = json.loads(self._log_path().read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual(entry["category"], "misrouting")
        self.assertEqual(entry["skill"], "orch-tdd")

    def test_omitted_category_defaults_to_uncategorized(self):
        rc, _ = self._run_main(["o", "e"])
        self.assertEqual(rc, 0)
        entry = json.loads(self._log_path().read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual(entry["category"], "uncategorized")
        self.assertIsNone(entry["skill"])

    def test_git_lookup_missing_executable_still_appends_entry(self):
        with mock.patch.object(friction.subprocess, "run", side_effect=FileNotFoundError("git")):
            rc, out = self._run_main(["o", "e"])
        self.assertEqual(rc, 0)
        self.assertEqual(out.strip(), "friction logged")
        entry = json.loads(self._log_path().read_text(encoding="utf-8").splitlines()[-1])
        self.assertIsNone(entry["git_rev"])

    def test_git_lookup_timeout_still_appends_entry(self):
        timeout_error = friction.subprocess.TimeoutExpired(cmd="git", timeout=friction.GIT_REV_TIMEOUT_SECONDS)
        with mock.patch.object(friction.subprocess, "run", side_effect=timeout_error):
            rc, out = self._run_main(["o", "e"])
        self.assertEqual(rc, 0)
        self.assertEqual(out.strip(), "friction logged")
        entry = json.loads(self._log_path().read_text(encoding="utf-8").splitlines()[-1])
        self.assertIsNone(entry["git_rev"])

    def test_git_lookup_nonzero_exit_yields_none_git_rev(self):
        result = mock.Mock(returncode=1, stdout=b"")
        with mock.patch.object(friction.subprocess, "run", return_value=result):
            rc, _ = self._run_main(["o", "e"])
        self.assertEqual(rc, 0)
        entry = json.loads(self._log_path().read_text(encoding="utf-8").splitlines()[-1])
        self.assertIsNone(entry["git_rev"])

    def test_worktree_cwd_resolves_log_to_main_checkout(self):
        # Reshape self.repo into a linked worktree of a separate main checkout,
        # and confirm main() writes to the main checkout's log, not the worktree.
        base = self.repo.parent
        main = base / "main-checkout"
        (main / ".git" / "worktrees" / "wt").mkdir(parents=True)
        wt = base / "wt"
        wt.mkdir()
        (wt / ".git").write_text(
            f"gitdir: {main / '.git' / 'worktrees' / 'wt'}\n", encoding="utf-8"
        )
        os.chdir(wt)
        rc, _ = self._run_main(["o", "e"])
        self.assertEqual(rc, 0)
        stamp = friction.datetime.now(friction.timezone.utc).strftime("%Y-%m")
        main_log = main / ".orch" / "friction" / f"{stamp}.jsonl"
        wt_log = wt / ".orch" / "friction" / f"{stamp}.jsonl"
        self.assertTrue(main_log.exists())
        self.assertFalse(wt_log.exists())


class TestMainMalformedArgvIsSilentNoop(_IsolatedRepoTestCase):
    def _assert_noop(self, argv):
        rc, out = self._run_main(argv)
        self.assertEqual(rc, 0)
        self.assertEqual(out, "")
        self.assertFalse(self._log_path().exists())

    def test_zero_positional_args(self):
        self._assert_noop([])

    def test_one_positional_arg(self):
        self._assert_noop(["only one"])

    def test_three_positional_args(self):
        self._assert_noop(["a", "b", "c"])

    def test_dangling_known_flag_missing_its_value(self):
        self._assert_noop(["o", "e", "--category"])

    def test_unknown_flag_is_absorbed_as_positional_and_rejected(self):
        self._assert_noop(["--bogus", "value", "o", "e"])

    def test_unknown_equals_flag_is_absorbed_as_positional_and_rejected(self):
        self._assert_noop(["--bogus=value", "o", "e"])


class TestMainAdversarialFailuresStaySilentAndExitZero(_IsolatedRepoTestCase):
    def test_unwritable_target_directory(self):
        # Pre-create `.orch` as a plain file so mkdir(parents=True) for the
        # friction/ subdirectory raises FileExistsError.
        (self.repo / ".orch").write_text("blocked", encoding="utf-8")
        rc, out = self._run_main(["o", "e"])
        self.assertEqual(rc, 0)
        self.assertEqual(out, "")

    def test_lone_surrogate_value_does_not_raise_or_corrupt_the_log(self):
        rc, out = self._run_main(["bad \udcff value", "expected"])
        self.assertEqual(rc, 0)
        self.assertEqual(out, "")
        log = self._log_path()
        if log.exists():
            content = log.read_text(encoding="utf-8")
            for line in content.splitlines():
                json.loads(line)  # any line present must be a complete, valid entry


if __name__ == "__main__":
    unittest.main()
