"""friction.py resolves .orch to the main checkout, one per repository, and
appends to it under a lock that never blocks and never fails."""
from __future__ import annotations

import ast
import contextlib
import errno
import importlib.util
import io
import json
import os
import sys
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
FRICTION_PY = ROOT / "scripts" / "friction.py"
TICKETS_PY = ROOT / "scripts" / "tickets.py"
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


OUTSIDE_FD = -1


class _FakeMsvcrt:
    """The Windows locking API, on a platform that has none.

    POSIX ``O_APPEND`` is atomic, so here an unlocked append loses nothing and
    no end-to-end concurrency test can tell a locked append from an unlocked
    one -- the precedent is in this repository, where the lost-note test at
    ``6c3b7aa:907`` passed before the lock it was written for existed. So the
    tests that discriminate drive the mechanism through this stand-in: it
    grants byte-zero exclusion, refuses a second holder exactly as
    ``LK_NBLCK`` does, and records every call, so an append that takes no lock
    records nothing and fails outright rather than passing vacuously.
    """

    LK_LOCK = 1  # never expected: it blocks ~10s and then raises
    LK_NBLCK = 2
    LK_UNLCK = 0

    def __init__(self, always_refuse=False):
        self._always_refuse = always_refuse
        self._guard = threading.Lock()
        self._holder = None
        self.events = []  # (event, thread name)
        self.modes = []
        self.offsets = []  # the file offset each call was made at
        self.refused = threading.Event()

    def locking(self, fd, mode, nbytes):
        who = threading.current_thread().name
        with self._guard:
            self.modes.append(mode)
            if fd != OUTSIDE_FD:
                self.offsets.append(os.lseek(fd, 0, os.SEEK_CUR))
            if nbytes != 1:
                raise AssertionError(f"expected a one-byte lock, got {nbytes}")
            if mode == self.LK_UNLCK:
                self._holder = None
                self.events.append(("release", who))
                return
            if self._always_refuse or self._holder is not None:
                self.events.append(("refused", who))
                self.refused.set()
                raise OSError(errno.EDEADLK, "Resource deadlock avoided")
            self._holder = who
            self.events.append(("acquire", who))

    def thread_events(self, name):
        return [event for event, who in self.events if who == name]


class FrictionAppendLockTest(_IsolatedRepoTestCase):
    """A concurrent append loses no line, and the lock that buys that never
    blocks the logger and never fails it."""

    def _prepared_log(self, first_line="first line\n"):
        path = self._log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(first_line, encoding="utf-8")
        return path

    def test_concurrent_writers_lose_no_line(self):
        # Corroboration, not proof: on POSIX this passes with or without the
        # lock. The mechanism tests below carry the information.
        observed = [f"writer-{i} " + "x" * 2000 for i in range(8)]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), mock.patch.object(
            friction.subprocess, "run", return_value=mock.Mock(returncode=1, stdout=b"")
        ):
            with ThreadPoolExecutor(max_workers=8) as pool:
                codes = list(pool.map(lambda text: friction.main([text, "expected"]), observed))
        self.assertEqual([0] * 8, codes)
        lines = self._log_path().read_text(encoding="utf-8").splitlines()
        self.assertEqual(sorted(observed), sorted(json.loads(line)["observed"] for line in lines))

    def test_a_held_lock_serialises_the_append_instead_of_losing_the_line(self):
        fake = _FakeMsvcrt()
        path = self._prepared_log()
        with mock.patch.object(friction, "msvcrt", fake), mock.patch.object(
            friction, "APPEND_LOCK_BUDGET_SECONDS", 5.0
        ):
            fake.locking(OUTSIDE_FD, fake.LK_NBLCK, 1)  # an outside appender holds byte zero
            writer = threading.Thread(
                target=friction._append_line, args=(path, "second line\n"), name="appender"
            )
            writer.start()
            try:
                self.assertTrue(fake.refused.wait(5.0), "the append never contended for the lock")
                self.assertEqual("first line\n", path.read_text(encoding="utf-8"))
            finally:
                fake.locking(OUTSIDE_FD, fake.LK_UNLCK, 1)
                writer.join(10.0)
        self.assertFalse(writer.is_alive(), "the append never returned")
        self.assertEqual(
            ["first line", "second line"], path.read_text(encoding="utf-8").splitlines()
        )
        events = fake.thread_events("appender")
        self.assertEqual("refused", events[0])
        self.assertEqual(["acquire", "release"], events[-2:])
        self.assertNotIn("refused", events[events.index("acquire") :])
        self.assertEqual({fake.LK_NBLCK, fake.LK_UNLCK}, set(fake.modes))
        self.assertEqual({0}, set(fake.offsets), "the lock must be taken on byte zero")

    def test_an_unacquirable_lock_still_writes_and_never_raises(self):
        fake = _FakeMsvcrt(always_refuse=True)
        path = self._prepared_log()
        with mock.patch.object(friction, "msvcrt", fake):
            friction._append_line(path, "second line\n")  # must not raise
            rc, out = self._run_main(["observed thing", "expected thing"])
        self.assertEqual(0, rc)
        self.assertEqual("friction logged", out.strip())
        lines = path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(["first line", "second line"], lines[:2])
        self.assertEqual("observed thing", json.loads(lines[2])["observed"])
        self.assertNotIn("acquire", fake.thread_events(threading.current_thread().name))

    def test_the_unacquired_path_is_bounded_below_one_second(self):
        fake = _FakeMsvcrt(always_refuse=True)
        path = self._prepared_log()
        with mock.patch.object(friction, "msvcrt", fake):
            started = time.monotonic()
            friction._append_line(path, "second line\n")
            elapsed = time.monotonic() - started
        self.assertLess(elapsed, 1.0, f"the unacquired append took {elapsed:.3f}s")
        self.assertGreater(
            fake.thread_events(threading.current_thread().name).count("refused"),
            1,
            "the retry budget was never spent, so the bound proves nothing",
        )
        self.assertEqual(
            ["first line", "second line"], path.read_text(encoding="utf-8").splitlines()
        )


def top_level_imports(path):
    """Every module the file imports, from its syntax rather than its prose."""

    imported = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and not node.level:
            imported.add((node.module or "").split(".")[0])
    return imported


def function_source(path, name):
    """The exact source of one top-level function, sliced from the file's own
    bytes. A whole-file diff would say nothing: these two files share two
    functions and nothing else."""

    source = path.read_text(encoding="utf-8")
    for node in ast.parse(source).body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(source, node)
    return None


class FrictionDuplicationTest(unittest.TestCase):
    """friction.py must never fail, so it imports nothing that can fail --
    including scripts/tickets.py, which workspace.py imports instead
    (tests/test_workspace.py:391). The price is two copied root resolvers, and
    the price of a copy nobody compares is a silent divergence, so compare
    them here.

    The lock is not a third comparand. tickets.py has no lock helper to
    compare against: its lock is inlined in ``_append_one_line`` and takes
    ``LK_LOCK``, the blocking mode ``rules/improvement.md`` §1 forbids this
    logger, so byte-identity there would contradict the mechanism itself.
    """

    def test_friction_imports_only_the_standard_library(self):
        imported = top_level_imports(FRICTION_PY)
        self.assertEqual(
            {
                "__future__", "datetime", "json", "msvcrt", "os",
                "pathlib", "subprocess", "sys", "time",
            },
            imported,
            f"friction.py must stay standalone: {sorted(imported)}",
        )
        stdlib = getattr(sys, "stdlib_module_names", None)
        if stdlib is not None:  # 3.10+; under the 3.9 floor the pin above stands alone
            self.assertEqual(set(), imported - set(stdlib))

    def test_the_copied_root_resolvers_are_byte_identical_to_the_tickets_originals(self):
        for name in ("_main_checkout_root", "_find_repo_root"):
            copied = function_source(FRICTION_PY, name)
            original = function_source(TICKETS_PY, name)
            self.assertIsNotNone(copied, f"friction.py no longer defines {name}")
            self.assertIsNotNone(original, f"tickets.py no longer defines {name}")
            self.assertEqual(
                original,
                copied,
                f"{name} has diverged from the tickets.py original it was copied from",
            )


if __name__ == "__main__":
    unittest.main()
