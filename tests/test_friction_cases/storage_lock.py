from __future__ import annotations

from .common import *
from .common import _IsolatedRepoTestCase

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


class _VirtualClock:
    """``time.monotonic`` and ``time.sleep`` over a counter.

    The retry budget is arithmetic over these two calls, so spending it is
    a property of the code and not of how loaded the host is. Measuring
    real elapsed seconds instead measured the machine: under a runner that
    shards modules across processes the reading is contended, and the only
    repair available to a wall-clock assertion is a larger threshold, which
    is the assertion giving up. Advancing a virtual clock spends the whole
    budget in no real time and reads the same number every run.
    """

    def __init__(self):
        self.now = 0.0
        self.slept = []

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.now += seconds


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
        with mock.patch.object(friction, "msvcrt", fake), mock.patch.object(
            friction, "time", _VirtualClock()
        ):
            friction._append_line(path, "second line\n")  # must not raise
            rc, out = self._run_main(["observed thing", "expected thing"])
        self.assertEqual(0, rc)
        self.assertEqual("friction logged", out.strip())
        lines = path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(["first line", "second line"], lines[:2])
        self.assertEqual("observed thing", json.loads(lines[2])["observed"])
        self.assertNotIn("acquire", fake.thread_events(threading.current_thread().name))

    def test_the_unacquired_path_returns_inside_a_budget_under_one_second(self):
        """The one-second ceiling rules/improvement.md §1 holds this logger
        to, read off the retry arithmetic rather than off a stopwatch: the
        budget bounds the wait, the loop never runs past it, and the line is
        written when it runs out."""

        fake = _FakeMsvcrt(always_refuse=True)
        clock = _VirtualClock()
        path = self._prepared_log()
        with mock.patch.object(friction, "msvcrt", fake), mock.patch.object(
            friction, "time", clock
        ):
            friction._append_line(path, "second line\n")
        self.assertLess(
            friction.APPEND_LOCK_BUDGET_SECONDS, 1.0, "the budget itself breaks the ceiling"
        )
        self.assertLessEqual(
            clock.now,
            friction.APPEND_LOCK_BUDGET_SECONDS,
            "the retry loop waited past the budget it declares",
        )
        self.assertEqual(
            {friction.APPEND_LOCK_RETRY_SECONDS},
            set(clock.slept),
            "the loop slept for something other than its own retry interval",
        )
        self.assertGreater(
            fake.thread_events(threading.current_thread().name).count("refused"),
            1,
            "the retry budget was never spent, so the bound proves nothing",
        )
        self.assertEqual(
            ["first line", "second line"], path.read_text(encoding="utf-8").splitlines()
        )
