"""friction.py logs to the one user-scope sink, from every repository."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
# friction.py imports its resolver as `scripts.state_root` in-repo, falling
# back to a flat `state_root` beside it once installed. Neither name is
# importable from `tests/` alone, so put the repository root on the path
# before the module body runs.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_spec = importlib.util.spec_from_file_location(
    "friction", ROOT / "scripts" / "friction.py"
)
friction = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_spec and friction)

STATE_HOME_ENV_VAR = "ORCHFLOWS_STATE_HOME"

REQUIRED_ENTRY_KEYS = {
    "ts", "cwd", "git_rev", "host", "session",
    "category", "skill", "ticket", "run", "observed", "expected",
}


class TestTargetPath(unittest.TestCase):
    """The target is the sink's, and the cwd has no say in it.

    ``scripts/state_root.py`` owns the resolver itself and
    ``tests/test_state_root.py`` grades it; what belongs here is that
    friction.py asks it, rather than deciding for itself.
    """

    def setUp(self):
        # Register the tempdir cleanup via addCleanup (not a `with` block):
        # addCleanup runs LIFO, so a chdir-back registered after it fires
        # first. A `with tempfile.TemporaryDirectory()` wrapping a chdir
        # into itself has its own __exit__ run before any addCleanup, and on
        # Windows rmtree of the current working directory raises
        # PermissionError — that ordering bug is what this guards against.
        tmp_ctx = tempfile.TemporaryDirectory()
        self.addCleanup(tmp_ctx.cleanup)
        self.tmp = Path(tmp_ctx.name).resolve()
        self.sink = self.tmp / "sink"
        patcher = mock.patch.dict(os.environ, {STATE_HOME_ENV_VAR: str(self.sink)})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.stamp = friction.datetime.now(friction.timezone.utc).strftime("%Y-%m")

    def _chdir(self, target: Path):
        before = os.getcwd()
        os.chdir(target)
        self.addCleanup(os.chdir, before)

    def _target(self) -> Path:
        return friction._target_path(friction.datetime.now(friction.timezone.utc))

    def test_the_target_is_the_sinks_friction_stream(self):
        self.assertEqual(self.sink / "friction" / f"{self.stamp}.jsonl", self._target())

    def test_a_worktree_a_main_checkout_and_no_repository_agree(self):
        main = self.tmp / "main"
        (main / ".git" / "worktrees" / "wt").mkdir(parents=True)
        wt = self.tmp / "wt"
        wt.mkdir()
        (wt / ".git").write_text(
            f"gitdir: {main / '.git' / 'worktrees' / 'wt'}\n", encoding="utf-8"
        )
        bare = self.tmp / "bare"
        bare.mkdir()
        seen = []
        for cwd in (main, wt, bare):
            before = os.getcwd()
            os.chdir(cwd)
            try:
                seen.append(self._target())
            finally:
                os.chdir(before)
        self.assertEqual([self.sink / "friction" / f"{self.stamp}.jsonl"] * 3, seen)

    def test_the_override_is_honoured_after_the_module_was_imported(self):
        moved = self.tmp / "moved-sink"
        os.environ[STATE_HOME_ENV_VAR] = str(moved)
        self.assertEqual(moved / "friction" / f"{self.stamp}.jsonl", self._target())


class _IsolatedRepoTestCase(unittest.TestCase):
    """Base for tests that run friction.main() against a synthetic repo root.

    Never touches the real sink — ``ORCHFLOWS_STATE_HOME`` is pointed at a
    fresh tempdir for the duration, and cwd is pinned to a repository
    inside it and restored via addCleanup even if the test body raises.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name).resolve()
        self.repo = self.tmp / "repo"
        (self.repo / ".git").mkdir(parents=True)
        self.sink = self.tmp / "sink"
        patcher = mock.patch.dict(os.environ, {STATE_HOME_ENV_VAR: str(self.sink)})
        patcher.start()
        self.addCleanup(patcher.stop)
        before = os.getcwd()
        os.chdir(self.repo)
        self.addCleanup(os.chdir, before)

    def _log_path(self):
        stamp = friction.datetime.now(friction.timezone.utc).strftime("%Y-%m")
        return self.sink / "friction" / f"{stamp}.jsonl"

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

    def test_a_worktree_and_its_main_checkout_append_to_one_stream(self):
        # Build a linked worktree of a separate main checkout and log from
        # both: one stream, two lines, and no `.orch/` in either tree.
        main = self.tmp / "main-checkout"
        (main / ".git" / "worktrees" / "wt").mkdir(parents=True)
        wt = self.tmp / "wt"
        wt.mkdir()
        (wt / ".git").write_text(
            f"gitdir: {main / '.git' / 'worktrees' / 'wt'}\n", encoding="utf-8"
        )
        os.chdir(main)
        self.assertEqual(0, self._run_main(["from the main checkout", "e"])[0])
        os.chdir(wt)
        self.assertEqual(0, self._run_main(["from the worktree", "e"])[0])
        lines = self._log_path().read_text(encoding="utf-8").splitlines()
        self.assertEqual(
            ["from the main checkout", "from the worktree"],
            [json.loads(line)["observed"] for line in lines],
        )
        self.assertFalse((main / ".orch").exists())
        self.assertFalse((wt / ".orch").exists())

    def test_the_entry_carries_the_project_it_arose_in_as_a_field(self):
        # One stream for every repository, so the cwd is how an entry says
        # where it came from. It is a field, never the location.
        self._run_main(["o", "e"])
        entry = json.loads(self._log_path().read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual(str(self.repo), entry["cwd"])


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
        # Pre-create the sink root as a plain file so mkdir(parents=True)
        # for the friction/ subdirectory raises FileExistsError.
        self.sink.write_text("blocked", encoding="utf-8")
        rc, out = self._run_main(["o", "e"])
        self.assertEqual(rc, 0)
        self.assertEqual(out, "")

    def test_an_unwritable_sink_is_never_traded_for_a_writable_cwd(self):
        # There is no fallback at this seam. A blocked sink loses the entry;
        # it does not resurrect the per-repository `.orch/` this run retired.
        self.sink.write_text("blocked", encoding="utf-8")
        before = sorted(p.name for p in self.repo.iterdir())
        self._run_main(["o", "e"])
        self.assertEqual(before, sorted(p.name for p in self.repo.iterdir()))
        self.assertFalse((self.repo / ".orch").exists())

    def test_a_resolver_that_cannot_be_imported_is_swallowed(self):
        # The two-arm import lives inside a function precisely so main()'s
        # broad except can catch its failure. At module scope this would
        # traceback before there was a main() to swallow it.
        with mock.patch.object(
            friction, "_state_root", side_effect=ImportError("no state_root")
        ):
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
