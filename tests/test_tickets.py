"""Ticket script: pending promotion, status enum, and adversarial coverage
(claim races, malformed input, repo-boundary errors)."""

import ast
import importlib.util
import inspect
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.tickets as tickets_mod  # noqa: E402

TICKETS_PY = ROOT / "scripts" / "tickets.py"
STATE_ROOT_PY = ROOT / "scripts" / "state_root.py"
WORKSPACE_PY = ROOT / "scripts" / "workspace.py"
STATE_HOME_ENV_VAR = "ORCHFLOWS_STATE_HOME"

TICKET = """---
id: {tid}
run: testrun
status: {status}
executor: orch-tdd
depends_on: {deps}
write_scope: scratch/{tid}.txt
bound: 30m
---

## Objective

Test ticket.
"""


def use_sink(tmp: Path) -> Path:
    """Point ``ORCHFLOWS_STATE_HOME`` at a sink under this test's tempdir.

    Sets the variable for the rest of the process rather than restoring
    it: every fixture below calls this before writing, and
    ``tests/__init__.py`` holds the floor at a temporary directory
    regardless, so the worst a stale value can do is fail a test, never
    reach the real sink. ``run_full`` passes no ``env``, so each child
    inherits whatever is in force when it is launched.
    """

    # resolved: a macOS tempdir is reached through a /var symlink, and a
    # payload that prints the sink path must match the path a test opens
    sink = (tmp / "state-sink").resolve()
    os.environ[STATE_HOME_ENV_VAR] = str(sink)
    return sink


def sink_root() -> Path:
    """Wherever ``use_sink`` last pointed. Never the real sink."""

    return Path(os.environ[STATE_HOME_ENV_VAR])


def make_tickets(run_dir: Path, tickets: dict) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    for tid, (status, deps) in tickets.items():
        (run_dir / f"{tid}.md").write_text(
            TICKET.format(tid=tid, status=status, deps=deps), encoding="utf-8"
        )
    return run_dir


def make_repo(tmp: Path, tickets: dict, *, sink: Path = None) -> Path:
    """A repository at ``tmp``, and its run of tickets in the sink.

    Tickets are user-scope state, so they land outside the checkout. Pass
    ``sink`` when the caller has already placed one — a worktree fixture
    puts it beside both trees rather than inside either.
    """

    (tmp / ".git").mkdir()
    if sink is None:
        sink = use_sink(tmp)
    return make_tickets(sink / "tickets" / "testrun", tickets)


def run_full(cwd: Path, *args):
    """A real process: argv, exit code, and one JSON document on stdout.

    The surface an in-process dispatch does not have, so every case that
    grades a return code or the shape of stdout keeps this.
    """

    return subprocess.run(
        [sys.executable, str(TICKETS_PY), *args],
        capture_output=True, text=True, encoding="utf-8",
        errors="replace", cwd=str(cwd),
    )


def run_json(cwd: Path, *args):
    """``run_full``'s payload, for the cases that need the process boundary
    and read only the payload: concurrent writers, which must be processes
    for the contention to be real, and the seams run against real git."""

    return json.loads(run_full(cwd, *args).stdout)


_REAL_CWD = tickets_mod._cwd
_pinned = threading.local()
_pin_lock = threading.Lock()
_pins_held = 0


def _cwd_or_pin():
    """What a pinned dispatch stands in: this thread's pin if it set one, the
    process's own directory otherwise, so an unpinned caller in another
    thread is unaffected."""

    pinned = getattr(_pinned, "cwd", None)
    return _REAL_CWD() if pinned is None else pinned


@contextmanager
def _the_pin_is_installed():
    """Hold ``tickets_mod._cwd`` swapped for as long as any thread holds a pin.

    Depth-counted under a lock because the counter and the attribute must
    move together: two threads pinning at once would otherwise have the first
    to finish restore the real accessor under the second, and two cases here
    dispatch from a thread pool.
    """

    global _pins_held
    with _pin_lock:
        _pins_held += 1
        if _pins_held == 1:
            tickets_mod._cwd = _cwd_or_pin
    try:
        yield
    finally:
        with _pin_lock:
            _pins_held -= 1
            if _pins_held == 0:
                tickets_mod._cwd = _REAL_CWD


@contextmanager
def repo_root_of(cwd: Path):
    """Run a dispatch as though the process were standing in ``cwd``.

    Pinning the one accessor rather than the resolvers around it: everything
    downstream -- which project, which workspace of it, whether there is a
    checkout at all -- is then the real resolution run against the fixture
    tree, a linked worktree's pointer file dereferenced exactly as it would
    be in a subprocess. What this replaces is ``os.chdir``, which is
    process-global and would stop this module being run beside anything
    else, its own thread pools included.
    """

    before = getattr(_pinned, "cwd", None)
    _pinned.cwd = Path(cwd).resolve()
    try:
        with _the_pin_is_installed():
            yield
    finally:
        _pinned.cwd = before


def run_main(cwd: Path, *args):
    """``main`` in this process: its real return code and the one JSON
    document it prints, in ``run_full``'s shape so a call site reads the same.

    ``_dispatch`` alone has neither -- the exit convention and ``main``'s own
    exception handling both live in ``main`` -- so the cases that grade an
    exit code keep grading one. What is not exercised here is the OS's own
    argv handoff, which is what the fidelity anchors on ``run_full`` keep.
    """

    argv = [str(arg) for arg in args]
    stream = io.StringIO()
    with repo_root_of(cwd), redirect_stdout(stream):
        code = tickets_mod.main(argv)
    return subprocess.CompletedProcess(
        [sys.executable, str(TICKETS_PY), *argv], code, stream.getvalue(), ""
    )


def run_cmd(cwd: Path, *args):
    """One dispatch in this process, returning what the script would print.

    ``main`` turns a raised exception into ``{"error": str(error)}`` and
    prints one JSON document; both are reproduced here, the round trip so a
    caller reads exactly what a reader of stdout reads.
    """

    with repo_root_of(cwd):
        try:
            payload = tickets_mod._dispatch([str(arg) for arg in args])
        except Exception as error:  # what `main` does with one
            payload = {"error": str(error)}
    return json.loads(json.dumps(payload, ensure_ascii=False))


class SequencedPath:
    """A ticket path whose read and write call the test back.

    ``_do_claim`` takes the path as an argument, so two threads can be given
    two instrumented paths onto one file and meet in a chosen interleaving
    instead of whichever one the scheduler happens to produce. Only the
    attributes ``_do_claim`` touches are forwarded -- the two calls, the
    stem it names a refusal by, and the fspath the staleness check stats
    for motion; the subject keeps its signature and its body.
    """

    def __init__(self, path: Path, before_read=None, after_read=None, after_write=None):
        self._path = path
        self._before_read = before_read
        self._after_read = after_read
        self._after_write = after_write

    @property
    def stem(self):
        return self._path.stem

    def __fspath__(self):
        return str(self._path)

    def read_text(self, *args, **kwargs):
        if self._before_read is not None:
            self._before_read()
        text = self._path.read_text(*args, **kwargs)
        if self._after_read is not None:
            self._after_read()
        return text

    def write_text(self, *args, **kwargs):
        written = self._path.write_text(*args, **kwargs)
        if self._after_write is not None:
            self._after_write()
        return written


@contextmanager
def refusing_to_read(path, error=None, after: int = 0):
    """``Path.read_text`` raising ``error`` for ``path`` alone, and nothing
    else changed.

    The portable way to reach an OSError on a file that is there: ``chmod``
    has no effect on Windows and none as root, so an assertion resting on it
    reports the platform rather than the handler. ``error`` of ``None``
    leaves the real read in place, so a case needing no seam reads the same
    line as one that does.

    ``after`` lets the first N reads succeed. Several handlers sit behind an
    earlier read of the same file that has its own guard, so a read failing
    from the first call is caught by the earlier one and the later handler is
    never reached -- ``after`` is what distinguishes "this file is
    unreadable" from "this file stopped being readable partway through", and
    only the second reaches those.
    """

    if error is None:
        yield
        return
    target = Path(path).resolve()
    original = Path.read_text
    survived = []

    def read_text(self, *args, **kwargs):
        if Path(self).resolve() == target:
            if len(survived) >= after:
                raise error(13, "Permission denied", str(self))
            survived.append(1)
        return original(self, *args, **kwargs)

    Path.read_text = read_text
    try:
        yield
    finally:
        Path.read_text = original


@contextmanager
def refusing_to_write(path, error=PermissionError):
    """``refusing_to_read``'s twin over ``Path.write_text``.

    A read that fails and a write that fails are different handlers with
    different messages, and a file that cannot be written is not reachable by
    making one on disk: an existing file is writable, and a path that is a
    directory fails the ``is_file`` check long before the write.
    """

    target = Path(path).resolve()
    original = Path.write_text

    def write_text(self, *args, **kwargs):
        if Path(self).resolve() == target:
            raise error(13, "Permission denied", str(self))
        return original(self, *args, **kwargs)

    Path.write_text = write_text
    try:
        yield
    finally:
        Path.write_text = original


class TestPendingPromotion(unittest.TestCase):
    def test_pending_with_complete_deps_is_promoted_and_persisted(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_repo(tmp, {
                "T1": ("complete", "[]"),
                "T2": ("pending", "[T1]"),
            })
            payload = run_cmd(tmp, "ready", "--run", "testrun")
            ids = [t["id"] for t in payload["ready"]]
            self.assertEqual(["T2"], ids)
            self.assertEqual("ready", payload["ready"][0]["status"])
            self.assertIn("status: ready", (run_dir / "T2.md").read_text(encoding="utf-8"))

    def test_pending_with_incomplete_deps_stays_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_repo(tmp, {
                "T1": ("ready", "[]"),
                "T2": ("pending", "[T1]"),
            })
            payload = run_cmd(tmp, "ready", "--run", "testrun")
            ids = sorted(t["id"] for t in payload["ready"])
            self.assertEqual(["T1"], ids)
            self.assertIn("status: pending", (run_dir / "T2.md").read_text(encoding="utf-8"))

    def test_set_status_accepts_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_repo(tmp, {"T1": ("ready", "[]")})
            payload = run_cmd(tmp, "set-status", "testrun", "T1", "pending")
            self.assertEqual("pending", payload["set_status"]["status"])
            self.assertIn("status: pending", (run_dir / "T1.md").read_text(encoding="utf-8"))


class TestClaim(unittest.TestCase):
    def test_claim_happy_path_transitions_ready_to_claimed(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_repo(tmp, {"T1": ("ready", "[]")})
            payload = run_cmd(tmp, "claim", "testrun", "T1", "--by", "agent-a")
            self.assertEqual("agent-a", payload["claimed"]["claimed_by"])
            self.assertEqual("T1", payload["claimed"]["id"])
            text = (run_dir / "T1.md").read_text(encoding="utf-8")
            self.assertIn("status: claimed", text)
            self.assertIn("claimed_by: agent-a", text)
            self.assertRegex(text, r"claimed_at: \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")

    def test_claim_on_fresh_claim_is_rejected_not_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, {"T1": ("ready", "[]")})
            first = run_cmd(tmp, "claim", "testrun", "T1", "--by", "agent-a")
            self.assertIn("claimed", first)
            second = run_cmd(tmp, "claim", "testrun", "T1", "--by", "agent-b")
            self.assertIn("error", second)

    def test_stale_claim_is_reclaimed(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_repo(tmp, {"T1": ("ready", "[]")})
            ticket_path = run_dir / "T1.md"
            first = run_cmd(tmp, "claim", "testrun", "T1", "--by", "agent-a")
            self.assertIn("claimed", first)
            # backdate the claim well past the ticket's 30m bound, and the
            # file with it: staleness is motion as well as the clock, so a
            # claim whose ticket was written a moment ago is still moving
            text = ticket_path.read_text(encoding="utf-8")
            text = tickets_mod._set_frontmatter_field(text, "claimed_at", "2020-01-01T00:00:00Z")
            ticket_path.write_text(text, encoding="utf-8")
            backdate(ticket_path, 10 * 24 * 60)
            second = run_cmd(tmp, "claim", "testrun", "T1", "--by", "agent-b")
            self.assertEqual("agent-b", second["claimed"]["claimed_by"])
            self.assertIn("claimed_by: agent-b", ticket_path.read_text(encoding="utf-8"))

    def test_two_writer_claim_race_yields_exactly_one_winner(self):
        """Two threads in flight at once over one ticket, both holding the
        same pre-claim snapshot, the loser's read released only once the
        winner's write has landed.

        That interleaving is the one ``_do_claim``'s snapshot check exists
        for, and the check is what decides it: the loser re-reads, finds the
        file no longer the text it was handed, and reports the lost race
        rather than overwriting the winner. Until now this ran ``_do_claim``
        twice in one thread, which is not a race at all -- there is only
        ever one runnable writer, so no scheduling could have produced any
        other answer.

        Deterministic on purpose, and one invocation: driven 200 times while
        this was written, one winner every time. The interleaving the check
        does *not* cover is
        ``test_both_claimants_win_when_neither_read_sees_the_others_write``.
        """

        winners, losers, final_text = self.race(release_loser_after_write=True)
        self.assertEqual(1, len(winners), (winners, losers))
        self.assertEqual(1, len(losers), (winners, losers))
        self.assertIn("lost the claim race", losers[0]["error"])

        winner_name = winners[0]["claimed"]["claimed_by"]
        self.assertIn(f"claimed_by: {winner_name}", final_text)
        loser_name = "writer-b" if winner_name == "writer-a" else "writer-a"
        self.assertNotIn(f"claimed_by: {loser_name}", final_text)

    def test_both_claimants_win_when_neither_read_sees_the_others_write(self):
        """The window the snapshot check does not close, recorded as it is.

        ``_do_claim`` re-reads and compares, then writes; the two are not one
        step. Align two writers so both re-reads complete before either write
        does and both compares pass, so both write and both report a claim --
        the state the check was added to prevent, reached by an interleaving
        it cannot see. Nothing forces this alignment in production, and
        nothing prevents it either.

        This is the current behavior pinned, not endorsed: a compare-and-swap
        that closed the window would fail this case, which is the point of
        having it here rather than in a note nobody reads.
        """

        winners, _losers, final_text = self.race(release_loser_after_write=False)
        self.assertEqual(2, len(winners), winners)
        # both wrote, and the file carries whichever landed last -- there is
        # no record left that the other believed it had won
        self.assertEqual(1, final_text.count("claimed_by: "))

    def race(self, release_loser_after_write: bool):
        """Two threads claiming one ticket from one snapshot, at one chosen
        interleaving. Returns the winners, the losers, and the final bytes.

        The barrier puts both writers in flight together; the ordering hooks
        ride on the path object ``_do_claim`` is handed, so the interleaving
        is chosen by this fixture rather than by the scheduler. No production
        signature or body is touched: the argument is the seam.
        """

        with tempfile.TemporaryDirectory() as tmp:
            run_dir = make_repo(Path(tmp), {"T1": ("ready", "[]")})
            ticket_path = run_dir / "T1.md"
            prior_text = ticket_path.read_text(encoding="utf-8")
            now = datetime.now(timezone.utc)

            in_flight = threading.Barrier(2)
            winner_wrote = threading.Event()
            both_read = threading.Barrier(2)
            outcomes = {}

            def claim(name, path):
                in_flight.wait(timeout=30)
                outcomes[name] = tickets_mod._do_claim(path, prior_text, name, now)

            if release_loser_after_write:
                paths = {
                    "writer-a": SequencedPath(ticket_path, after_write=winner_wrote.set),
                    "writer-b": SequencedPath(
                        ticket_path, before_read=lambda: winner_wrote.wait(timeout=30)
                    ),
                }
            else:
                paths = {
                    name: SequencedPath(
                        ticket_path, after_read=lambda: both_read.wait(timeout=30)
                    )
                    for name in ("writer-a", "writer-b")
                }

            threads = [
                threading.Thread(target=claim, args=(name, path), daemon=True)
                for name, path in paths.items()
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=30)
                self.assertFalse(thread.is_alive(), "a claimant never finished")

            return (
                [r for r in outcomes.values() if "claimed" in r],
                [r for r in outcomes.values() if "error" in r],
                ticket_path.read_text(encoding="utf-8"),
            )


class TestInvalidStatus(unittest.TestCase):
    def test_set_status_rejects_invalid_status_as_error_json_exit_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_repo(tmp, {"T1": ("ready", "[]")})
            result = run_main(tmp, "set-status", "testrun", "T1", "bogus-status")
            self.assertEqual(1, result.returncode)
            payload = json.loads(result.stdout)
            self.assertIn("error", payload)
            self.assertIn("status: ready", (run_dir / "T1.md").read_text(encoding="utf-8"))


def make_claimed_repo(tmp: Path, claims: dict) -> Path:
    """A repo of claimed tickets, each carrying its own ``bound`` and
    ``claimed_at``, and each with nothing moving.

    The fields staleness is computed from, and the ones `make_repo` holds
    fixed -- so anything grading a claim's age or its owner varies them
    here. Each ticket's mtime is put back to the moment it was claimed
    (far back when that moment is unreadable): staleness reads artifact
    motion as well as the clock, and a fixture that wrote its tickets a
    millisecond ago is a fixture where every claim is still moving.
    """

    run_dir = make_repo(tmp, {tid: ("claimed", "[]") for tid in claims})
    for tid, (bound, claimed_at) in claims.items():
        path = run_dir / f"{tid}.md"
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "bound: 30m",
                f"bound: {bound}\nclaimed_by: agent-a\nclaimed_at: {claimed_at}",
            ),
            encoding="utf-8",
        )
        claimed = tickets_mod._parse_iso(claimed_at)
        backdate(
            path,
            10 * 24 * 60
            if claimed is None
            else (datetime.now(timezone.utc) - claimed).total_seconds() / 60,
        )
    return run_dir


class TestSuspendedStatus(unittest.TestCase):
    """contracts/work-item.md: `suspended` is a valid non-terminal wait. A
    suspended ticket is still someone's, so the claim survives the
    transition -- were it dropped, the ticket would go back on offer while
    its holder was only waiting."""

    def test_set_status_accepts_suspended_and_keeps_the_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.assertIn("suspended", tickets_mod.VALID_STATUSES)
            run_dir = make_claimed_repo(tmp, {"T1": ("30m", "2026-07-18T00:00:00Z")})
            result = run_main(tmp, "set-status", "testrun", "T1", "suspended")
            self.assertEqual(0, result.returncode, result.stdout)
            self.assertEqual(
                "suspended", json.loads(result.stdout)["set_status"]["status"]
            )
            text = (run_dir / "T1.md").read_text(encoding="utf-8")
            self.assertIn("status: suspended", text)
            self.assertIn("claimed_by: agent-a", text)
            self.assertIn("claimed_at: 2026-07-18T00:00:00Z", text)


def minutes_ago(count: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=count)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


class TimeParseFallbackTest(unittest.TestCase):
    """What an unstated or unparsable `bound` and `claimed_at` do to
    staleness -- which is to say, to whether a claim can be taken away.

    Two fallbacks that read alike and point opposite ways: an unparsable
    bound lengthens the claim's protection, an unparsable timestamp removes
    it entirely. Pinned as they behave, not as they ought to.
    """

    def test_a_bound_the_pattern_does_not_match_falls_back_to_the_default(self):
        self.assertEqual(60, tickets_mod.DEFAULT_BOUND_MINUTES)
        for bound, minutes in (
            ("30m", 30),
            ("2h", 120),
            ("  45m  ", 45),
            ("0m", 0),
            ("banana", 60),
            ("30", 60),  # a number with no unit is not a duration here
            ("-5m", 60),  # the pattern has no sign
            ("", 60),
            (None, 60),
            ([], 60),  # not a string at all
        ):
            with self.subTest(bound=bound):
                self.assertEqual(minutes, tickets_mod._parse_bound_minutes(bound))

    def test_a_timestamp_it_cannot_read_is_none_and_never_a_raise(self):
        """`_parse_iso` answers or returns None; it never propagates. Its
        callers are a listing and a staleness check, and one unparsable field
        in one ticket may not take down a read of the whole run.

        The early `isinstance`/blank return is not what makes that true for
        the first four of these -- the `except Exception` below absorbs every
        one of them too, so that return is a guard whose removal changes
        nothing. What this pins is the contract, which only the `except`
        upholds.
        """

        for value in (None, "", "   ", 12345, [], object(),
                      "yesterday", "2020-13-45T99:99:99Z", "2026-07-18T00:00:00+banana"):
            with self.subTest(value=repr(value)):
                self.assertIsNone(tickets_mod._parse_iso(value))

    def test_a_naive_timestamp_is_read_as_utc_not_as_local_time(self):
        """Without this the subtraction in `_is_stale` raises rather than
        answers: an aware `now` minus a naive stamp is a TypeError, so a
        ticket whose `claimed_at` omitted its offset would crash the reader
        rather than be judged."""

        naive = tickets_mod._parse_iso("2026-07-18T00:00:00")
        self.assertEqual(timezone.utc, naive.tzinfo)
        self.assertEqual(tickets_mod._parse_iso("2026-07-18T00:00:00Z"), naive)

    def test_an_unreadable_claim_time_is_stale_and_a_readable_one_is_judged(self):
        now = datetime(2026, 8, 15, 12, 0, 0, tzinfo=timezone.utc)
        stale = tickets_mod._is_stale
        # no timestamp and an unparsable one both read as stale, which is the
        # fallback that hands a claim away rather than holding it
        self.assertTrue(stale(None, 30, now))
        self.assertTrue(stale("yesterday", 30, now))
        self.assertTrue(stale("2026-08-15T11:00:00Z", 30, now))
        self.assertFalse(stale("2026-08-15T11:45:00Z", 30, now))

    def test_a_nonsense_bound_protects_a_claim_longer_than_a_stated_one(self):
        """The end-to-end reading, and the answer to whether `bound: banana`
        is immediately reclaimable: it is not.

        The bound falls back to an hour, which is *longer* than the 30m these
        fixtures otherwise carry, so a bound no one can parse buys the holder
        more time than a bound they stated. `claimed_at: yesterday` is the
        field that does hand a ticket away on sight, because an unparsable
        timestamp is read as expired rather than as unknown.
        """

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_claimed_repo(tmp, {
                "T1": ("banana", minutes_ago(45)),  # inside the hour it fell back to
                "T2": ("banana", minutes_ago(75)),  # past it
                "T3": ("30m", "yesterday"),  # the stamp, not the bound, frees this
                "T4": ("30m", minutes_ago(5)),  # a live claim, stated bound
            })
            ready = {item["id"] for item in run_cmd(tmp, "ready")["ready"]}
        self.assertEqual({"T2", "T3"}, ready)


RESULT_TICKET = """---
id: {tid}
run: testrun
status: claimed
executor: orch-tdd
depends_on: []
write_scope: [{artifact}]
bound: {bound}
claimed_by: agent-a
claimed_at: {claimed_at}
---

## Objective

Test ticket.

## Result

Changed `{artifact}` on the workspace branch.
"""


def backdate(path: Path, minutes: int) -> None:
    """Move one file's mtime ``minutes`` into the past.

    A fixture that writes a ticket has just written it, so on disk that
    ticket is moving now. Every case that means "nothing has moved" has to
    say so, which is what this says.
    """

    when = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).timestamp()
    os.utime(path, (when, when))


class LeaseByArtifactMotionTest(unittest.TestCase):
    """REVIEW-2026-08-15.md T3: the lease is artifact motion, not the clock.

    A purely temporal `_is_stale` hands a lane's ticket away while that
    lane is still writing, which is the two-live-lanes rules/delegation.md
    §11 forbids. A claim is stale only when nothing has moved for longer
    than the lease -- neither the ticket's own sections nor any artifact
    path its `## Result` names.
    """

    def make(self, tmp: Path, *, bound: str = "30m", claimed_at: str = None,
             claim_age: int = 90, ticket_age: int = 90, artifact_age: int = 90,
             artifact: str = "scratch/built.txt") -> Path:
        sink = use_sink(tmp)
        (tmp / ".git").mkdir(exist_ok=True)
        target = tmp / artifact
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("built\n", encoding="utf-8")
        backdate(target, artifact_age)
        run_dir = sink / "tickets" / "testrun"
        run_dir.mkdir(parents=True, exist_ok=True)
        path = run_dir / "T1.md"
        path.write_text(
            RESULT_TICKET.format(
                tid="T1", artifact=artifact, bound=bound,
                claimed_at=minutes_ago(claim_age) if claimed_at is None else claimed_at,
            ),
            encoding="utf-8",
        )
        backdate(path, ticket_age)
        return run_dir

    def reclaimable(self, tmp: Path) -> bool:
        listed = [item["id"] for item in run_cmd(tmp, "ready", "--run", "testrun")["ready"]]
        return listed == ["T1"]

    def test_a_claim_past_its_lease_with_a_still_artifact_is_stale(self):
        """The baseline the two cases below are read against: nothing has
        moved since the claim, so the lease expires as it always did."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp)
            self.assertTrue(self.reclaimable(tmp))

    def test_a_moving_result_artifact_holds_the_claim_past_the_lease(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp, artifact_age=2)
            self.assertFalse(self.reclaimable(tmp))
            payload = run_cmd(tmp, "claim", "testrun", "T1", "--by", "agent-b")
            self.assertIn("error", payload)
            self.assertIn("claimed_by: agent-a", (tmp / "state-sink" / "tickets"
                          / "testrun" / "T1.md").read_text(encoding="utf-8"))

    def test_a_moving_ticket_holds_the_claim_past_the_lease(self):
        """The other half of the rule: an executor writing its own sections
        is motion, even when the artifact it names has not landed yet."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp, ticket_age=1)
            self.assertFalse(self.reclaimable(tmp))

    def test_an_artifact_the_result_does_not_name_moves_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp)
            stranger = tmp / "scratch" / "unnamed.txt"
            stranger.write_text("fresh\n", encoding="utf-8")
            self.assertTrue(self.reclaimable(tmp))

    def test_no_timestamp_is_stale_however_recently_the_artifact_moved(self):
        """The pre-existing rule, kept: a claim with no readable
        `claimed_at` is reclaimable on sight. Motion cannot rescue a claim
        whose age is unknown -- the lease it would be measured against has
        no start."""

        for claimed_at in ("", "yesterday"):
            with self.subTest(claimed_at=claimed_at), tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)
                self.make(tmp, claimed_at=claimed_at, artifact_age=0, ticket_age=0)
                self.assertTrue(self.reclaimable(tmp))

    def test_motion_is_read_against_the_lease_not_a_fixed_hour(self):
        """A stated bound still decides: the same two-hour-old motion is
        inside a `3h` lease and outside a `30m` one."""

        for bound, expected in (("3h", False), ("30m", True)):
            with self.subTest(bound=bound), tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)
                self.make(tmp, bound=bound, claim_age=200, ticket_age=120,
                          artifact_age=120)
                self.assertEqual(expected, self.reclaimable(tmp))

    def test_the_helper_takes_the_motion_it_is_given(self):
        now = datetime(2026, 8, 15, 12, 0, 0, tzinfo=timezone.utc)
        claimed = "2026-08-15T10:00:00Z"
        self.assertTrue(tickets_mod._is_stale(claimed, 30, now))
        self.assertFalse(
            tickets_mod._is_stale(
                claimed, 30, now, datetime(2026, 8, 15, 11, 45, tzinfo=timezone.utc)
            )
        )
        self.assertTrue(
            tickets_mod._is_stale(
                claimed, 30, now, datetime(2026, 8, 15, 11, 0, tzinfo=timezone.utc)
            )
        )


class OSErrorHandlerTest(unittest.TestCase):
    """Every `except OSError` in the script, entered and graded.

    Each turns a filesystem failure into a named JSON error rather than a
    traceback on a channel whose contract is one JSON document; none was
    entered by this suite before. The seams raise on one resolved path only,
    because `chmod` is a no-op on Windows and as root, and a test resting on
    it grades the platform.
    """

    def test_an_unreadable_ticket_is_a_named_error_beside_its_readable_peers(self):
        """`_load_ticket`: one file no one can read is not a run no one can
        list."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_repo(tmp, {"T1": ("ready", "[]"), "T2": ("ready", "[]")})
            with refusing_to_read(run_dir / "T1.md", PermissionError):
                payload = run_cmd(tmp, "list")
            by_id = {item["id"]: item for item in payload["tickets"]}
            self.assertIn("unreadable ticket", by_id["T1"]["error"])
            self.assertNotIn("error", by_id["T2"])

    def test_a_promotion_that_cannot_be_persisted_leaves_the_ticket_out(self):
        """`_cmd_ready`'s pending promotion: the status on disk and the status
        reported are the same claim, so a write that failed reports nothing
        ready. A promotion announced but not persisted would be handed to an
        executor whose own read finds it still pending."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_repo(tmp, {
                "T1": ("complete", "[]"),
                "T2": ("pending", "[T1]"),
                "T3": ("ready", "[]"),
            })
            with refusing_to_write(run_dir / "T2.md"):
                payload = run_cmd(tmp, "ready")
            self.assertEqual(["T3"], [item["id"] for item in payload["ready"]])
            self.assertIn(
                "status: pending", (run_dir / "T2.md").read_text(encoding="utf-8")
            )

    def test_a_ticket_that_stops_being_readable_mid_claim_is_a_named_error(self):
        """`_do_claim`'s re-read. `claim` reads the file twice before that
        re-read, each behind its own guard, so a read failing from the first
        call never reaches this one -- only a file that stops being readable
        partway through does."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_repo(tmp, {"T1": ("ready", "[]")})
            with refusing_to_read(run_dir / "T1.md", PermissionError, after=2):
                result = run_main(tmp, "claim", "testrun", "T1", "--by", "agent-a")
            self.assertEqual(1, result.returncode, result.stdout)
            self.assertIn("unreadable ticket", json.loads(result.stdout)["error"])
            self.assertIn(
                "status: ready", (run_dir / "T1.md").read_text(encoding="utf-8")
            )

    def test_a_ticket_that_stops_being_readable_mid_packet_is_a_named_error(self):
        """`_cmd_packet` reads the ticket a second time to section it, after
        `_load_ticket` has already read and guarded it."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_repo(tmp, {"T1": ("ready", "[]")})
            with refusing_to_read(run_dir / "T1.md", PermissionError, after=1):
                result = run_main(tmp, "packet", "testrun", "T1", "--reply-to", "main")
            self.assertEqual(1, result.returncode, result.stdout)
            self.assertIn("unreadable ticket", json.loads(result.stdout)["error"])

    def test_an_unreadable_ticket_refuses_the_result_rather_than_dropping_it(self):
        """`_cmd_result`'s read. Nothing is written when the read fails, so
        the executor's body is refused loudly instead of landing in a file
        rendered from text no one could see."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_repo(tmp, {"T1": ("claimed", "[]")})
            before = (run_dir / "T1.md").read_text(encoding="utf-8")
            with refusing_to_read(run_dir / "T1.md", PermissionError):
                result = run_main(
                    tmp, "result", "testrun", "T1", "--section", "Result", "--text", "x"
                )
            self.assertEqual(1, result.returncode, result.stdout)
            self.assertIn("unreadable ticket", json.loads(result.stdout)["error"])
            self.assertEqual(before, (run_dir / "T1.md").read_text(encoding="utf-8"))

    def test_a_ticket_that_cannot_be_written_says_so_by_name(self):
        """`_cmd_result`'s write: a different handler and a different word
        from the read's, because a caller retries the two differently."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_repo(tmp, {"T1": ("claimed", "[]")})
            with refusing_to_write(run_dir / "T1.md"):
                result = run_main(
                    tmp, "result", "testrun", "T1", "--section", "Result", "--text", "x"
                )
            self.assertEqual(1, result.returncode, result.stdout)
            self.assertIn("unwritable ticket", json.loads(result.stdout)["error"])

    def test_a_worklog_whose_close_cannot_be_read_still_takes_the_note(self):
        """`_worklog_terminal` is the one OSError here that is swallowed
        rather than reported: an unreadable worklog reads as an open one, so
        the note lands past a close nobody could see. Recorded as it
        behaves -- reporting the read failure instead would refuse a note the
        contract otherwise allows."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            run_cmd(
                worktree, "run-state", "testrun",
                "--terminal", "complete", "--text", "the deciding evidence",
            )
            log = worklog_of()
            self.assertIn("complete", log.read_text(encoding="utf-8"))
            with refusing_to_read(log, PermissionError):
                payload = run_cmd(worktree, "run-state", "testrun", "--note", "past the close")
            self.assertEqual("note", payload["run_state"]["mode"])
            self.assertIn("past the close", log.read_text(encoding="utf-8"))

    def test_an_unreadable_run_state_body_file_is_an_error_not_a_traceback(self):
        """`_cmd_run_state`'s body read: the `_cmd_result` handler's twin, on
        the other channel and reached by other flags."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            a_directory = worktree / "body-that-is-a-directory.md"
            a_directory.mkdir()
            present = worktree / "present-but-unreadable.md"
            present.write_text("bytes no reader reaches\n", encoding="utf-8")

            for label, path, raiser in (
                ("a directory where a file is expected", a_directory, None),
                ("a present file whose read raises", present, PermissionError),
            ):
                with self.subTest(label):
                    with refusing_to_read(path, raiser):
                        result = run_main(
                            worktree, "run-state", "testrun",
                            "--artifact", "evidence.md", "--file", str(path),
                        )
                    self.assertEqual(1, result.returncode, result.stdout)
                    error = json.loads(result.stdout)["error"]
                    self.assertIn("unreadable body file", error, error)

    def test_a_run_directory_that_cannot_be_made_is_a_named_error(self):
        """`_cmd_run_state`'s write. A plain file standing where the run's
        directory goes needs no seam at all: `mkdir(exist_ok=True)` excuses an
        existing directory, never an existing file, on every platform."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            runs = sink_root() / "runs"
            runs.mkdir(parents=True, exist_ok=True)
            (runs / "testrun").write_text("not a directory\n", encoding="utf-8")
            result = run_main(worktree, "run-state", "testrun", "--note", "nowhere to land")
            self.assertEqual(1, result.returncode, result.stdout)
            self.assertIn("unwritable run state", json.loads(result.stdout)["error"])


class TestMalformedFrontmatter(unittest.TestCase):
    def test_list_handles_ticket_with_no_frontmatter_delimiters(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / ".git").mkdir()
            run_dir = use_sink(tmp) / "tickets" / "testrun"
            run_dir.mkdir(parents=True)
            (run_dir / "T1.md").write_text(
                "# Not a ticket\n\nNo frontmatter delimiters at all.\n", encoding="utf-8"
            )
            result = run_main(tmp, "list", "--run", "testrun")
            self.assertEqual(0, result.returncode)
            payload = json.loads(result.stdout)
            self.assertEqual(1, len(payload["tickets"]))
            self.assertIsNone(payload["tickets"][0]["status"])

    def test_set_status_on_unterminated_frontmatter_returns_error_not_raise(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / ".git").mkdir()
            run_dir = use_sink(tmp) / "tickets" / "testrun"
            run_dir.mkdir(parents=True)
            (run_dir / "T1.md").write_text("---\nid: T1\nstatus: ready\n", encoding="utf-8")
            result = run_main(tmp, "set-status", "testrun", "T1", "complete")
            self.assertEqual(1, result.returncode)
            payload = json.loads(result.stdout)
            self.assertIn("error", payload)

    def test_claim_on_unterminated_frontmatter_returns_error_not_raise(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / ".git").mkdir()
            run_dir = use_sink(tmp) / "tickets" / "testrun"
            run_dir.mkdir(parents=True)
            (run_dir / "T1.md").write_text("---\nid: T1\nstatus: ready\n", encoding="utf-8")
            result = run_main(tmp, "claim", "testrun", "T1", "--by", "agent-a")
            self.assertEqual(1, result.returncode)
            payload = json.loads(result.stdout)
            self.assertIn("error", payload)


class TestRunFilter(unittest.TestCase):
    def test_run_filter_scopes_list_to_named_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, {"A1": ("ready", "[]")})
            other_dir = sink_root() / "tickets" / "otherrun"
            other_dir.mkdir(parents=True)
            (other_dir / "B1.md").write_text(
                "---\nid: B1\nrun: otherrun\nstatus: ready\ndepends_on: []\n"
                "write_scope: scratch/B1.txt\nbound: 30m\n---\n\n## Objective\n\nTest ticket.\n",
                encoding="utf-8",
            )

            payload_testrun = run_cmd(tmp, "list", "--run", "testrun")
            self.assertEqual(["A1"], [t["id"] for t in payload_testrun["tickets"]])

            payload_otherrun = run_cmd(tmp, "list", "--run", "otherrun")
            self.assertEqual(["B1"], [t["id"] for t in payload_otherrun["tickets"]])

            payload_all = run_cmd(tmp, "list")
            self.assertEqual(["A1", "B1"], sorted(t["id"] for t in payload_all["tickets"]))

    def test_run_filter_on_unknown_run_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, {"A1": ("ready", "[]")})
            payload = run_cmd(tmp, "list", "--run", "nonexistent-run")
            self.assertEqual([], payload["tickets"])


class TestEngineExecutorIsRejected(unittest.TestCase):
    """A ticket naming an engine as its executor is a call cycle.

    rules/composition.md §3: an engine dispatches a ticket's executor, so
    an engine cannot be one. Seventeen such tickets were cut in a real run
    and nothing caught them; these prove the reader now does.
    """

    def make(self, tmp: Path, executor: str) -> Path:
        run_dir = make_repo(tmp, {"T1": ("ready", "[]")})
        path = run_dir / "T1.md"
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "executor: orch-tdd", f"executor: {executor}"
            ),
            encoding="utf-8",
        )
        return run_dir

    def test_engine_list_matches_the_library(self):
        """The refused engines and the two lawful engine executors
        (orch-loop: a loop ticket; orch-frontier: a nested template)
        partition skills/engines/ — SPEC-ticket-set.md §3."""
        engines = {
            path.name
            for path in (ROOT / "skills" / "engines").iterdir()
            if path.is_dir()
        }
        refused = set(tickets_mod.ENGINE_EXECUTORS)
        lawful = set(tickets_mod.TICKET_EXECUTOR_ENGINES)
        self.assertEqual(set(), refused & lawful)
        self.assertEqual(engines, refused | lawful)

    def test_a_loop_or_frontier_executor_is_lawful(self):
        for engine in sorted(tickets_mod.TICKET_EXECUTOR_ENGINES):
            with tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)
                self.make(tmp, engine)
                summary = run_cmd(tmp, "list")["tickets"][0]
                self.assertNotIn("error", summary, engine)
                self.assertEqual(["T1"], [t["id"] for t in run_cmd(tmp, "ready")["ready"]])
                payload = run_cmd(tmp, "claim", "testrun", "T1", "--by", "agent-a")
                self.assertIn("claimed", payload, engine)

    def test_every_engine_is_refused(self):
        for engine in sorted(tickets_mod.ENGINE_EXECUTORS):
            with tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)
                self.make(tmp, engine)
                summary = run_cmd(tmp, "list")["tickets"][0]
                self.assertIn("error", summary, engine)
                self.assertIn("is an engine", summary["error"])

    def test_an_engine_executor_is_never_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp, "orch-task")
            self.assertEqual([], run_cmd(tmp, "ready")["ready"])

    def test_an_engine_executor_cannot_be_claimed(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = self.make(tmp, "orch-task")
            payload = run_cmd(tmp, "claim", "testrun", "T1", "--by", "agent-a")
            self.assertIn("is an engine", payload.get("error", ""))
            self.assertNotIn(
                "claimed_by", (run_dir / "T1.md").read_text(encoding="utf-8")
            )

    def test_backticks_and_spacing_do_not_evade_the_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp, "`orch-panel`")
            self.assertIn("error", run_cmd(tmp, "list")["tickets"][0])

    def test_a_lawful_executor_still_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp, "orch-verify")
            summary = run_cmd(tmp, "list")["tickets"][0]
            self.assertNotIn("error", summary)
            self.assertEqual(["T1"], [t["id"] for t in run_cmd(tmp, "ready")["ready"]])


class TestOutsideARepoTheSinkStillResolves(unittest.TestCase):
    """The sink is user-scope, so being outside a checkout is no longer an
    error: the tickets are found anyway, and only a genuinely absent one is
    reported missing."""

    def test_list_outside_a_repo_reads_the_sink(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            # deliberately no .git anywhere under this tempdir
            make_tickets(use_sink(tmp) / "tickets" / "testrun", {"T1": ("ready", "[]")})
            bare = tmp / "no-repo-here"
            bare.mkdir()
            result = run_full(bare, "list", "--run", "testrun")
            self.assertEqual(0, result.returncode)
            payload = json.loads(result.stdout)
            self.assertEqual(["T1"], [t["id"] for t in payload["tickets"]])

    def test_claim_outside_a_repo_claims_the_ticket_in_the_sink(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_tickets(
                use_sink(tmp) / "tickets" / "testrun", {"T1": ("ready", "[]")}
            )
            bare = tmp / "no-repo-here"
            bare.mkdir()
            result = run_full(bare, "claim", "testrun", "T1", "--by", "agent-a")
            self.assertEqual(0, result.returncode)
            self.assertNotIn("error", json.loads(result.stdout))
            self.assertIn(
                "status: claimed", (run_dir / "T1.md").read_text(encoding="utf-8")
            )

    def test_an_absent_ticket_is_still_reported_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            bare = tmp / "no-repo-here"
            bare.mkdir()
            payload = json.loads(
                run_full(bare, "claim", "testrun", "T1", "--by", "agent-a").stdout
            )
            self.assertIn("ticket not found", payload["error"])

    def test_a_sink_that_cannot_be_resolved_is_the_one_remaining_refusal(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            with mock.patch.object(
                tickets_mod.state_root, "tickets_root", side_effect=RuntimeError("no home")
            ):
                payload = tickets_mod._cmd_list([])
            self.assertEqual({"error": tickets_mod.NO_SINK_ERROR}, payload)


FULL_TICKET = """---
id: T1
run: testrun
status: ready
executor: orch-tdd
pack: orch-code-pack
depends_on: []
write_scope: scratch/t1.txt
bound: 30m
---

## Objective

Add `double(n)`.

## Fixed inputs

None.

## Completion test

1. `python -m unittest` exits 0. Oracle: that command. oracle_class: deterministic.

## Return fields

status, changed_artifacts, verification.
"""


class TestPacket(unittest.TestCase):
    """`packet` is the by-reference dispatch of contracts/delegation.md: the
    dispatcher gets a path and a refusal check, never the ticket body."""

    def make(self, tmp: Path, body: str = FULL_TICKET) -> Path:
        (tmp / ".git").mkdir()
        run_dir = use_sink(tmp) / "tickets" / "testrun"
        run_dir.mkdir(parents=True)
        path = run_dir / "T1.md"
        path.write_text(body, encoding="utf-8")
        return path

    def test_complete_ticket_yields_an_absolute_path_and_prompt(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            ticket_path = self.make(tmp)
            packet = run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main")["packet"]
            self.assertEqual(str(ticket_path.resolve()), packet["path"])
            self.assertTrue(Path(packet["path"]).is_absolute())
            self.assertEqual("orch-tdd", packet["executor"])
            self.assertEqual("orch-code-pack", packet["pack"])
            # contracts/work-item.md: absent `independence` reads `checker`.
            self.assertEqual("checker", packet["independence"])
            self.assertIn(packet["path"], packet["prompt"])
            self.assertIn("orch-tdd", packet["prompt"])
            self.assertIn("reply_to: main", packet["prompt"])

    def test_workspace_rides_the_prompt_only_when_supplied(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp)
            bare = run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main")["packet"]
            self.assertIsNone(bare["workspace"])
            self.assertNotIn("Workspace:", bare["prompt"])
            with_ws = run_cmd(
                tmp, "packet", "testrun", "T1", "--reply-to", "main", "--workspace", "/wt/a"
            )["packet"]
            self.assertEqual("/wt/a", with_ws["workspace"])
            self.assertIn("Workspace: /wt/a", with_ws["prompt"])

    def test_missing_body_section_is_refused_by_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            trimmed = FULL_TICKET.split("## Return fields")[0]
            self.make(tmp, trimmed)
            payload = run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main")
            self.assertIn("return_contract (## Return fields)", payload["error"])
            self.assertNotIn("packet", payload)

    def test_missing_frontmatter_part_is_refused_by_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp, FULL_TICKET.replace("bound: 30m\n", ""))
            payload = run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main")
            self.assertIn("bounds (bound)", payload["error"])

    def test_reply_to_is_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp)
            payload = run_cmd(tmp, "packet", "testrun", "T1")
            self.assertIn("reply_to (--reply-to)", payload["error"])

    def test_empty_write_scope_is_complete_authority(self):
        """A read-only lane's grant is exactly nothing outside its own
        ticket sections: `write_scope: []` is a complete packet, and only
        an absent key leaves authority missing."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp, FULL_TICKET.replace("write_scope: scratch/t1.txt\n", "write_scope: []\n"))
            payload = run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main")
            self.assertIn("packet", payload)
            self.assertNotIn("error", payload)
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp, FULL_TICKET.replace("write_scope: scratch/t1.txt\n", ""))
            payload = run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main")
            self.assertIn("authority (write_scope)", payload["error"])

    def test_criterion_without_oracle_class_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp, FULL_TICKET.replace(" oracle_class: deterministic.", ""))
            payload = run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main")
            self.assertIn("oracle_class", payload["error"])

    def test_engine_executor_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp, FULL_TICKET.replace("executor: orch-tdd", "executor: orch-task"))
            payload = run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main")
            self.assertIn("is an engine", payload["error"])

    def test_unknown_ticket_and_an_empty_sink_are_errors_not_crashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp)
            self.assertIn("ticket not found", run_cmd(tmp, "packet", "testrun", "T9", "--reply-to", "main")["error"])
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            result = run_full(tmp, "packet", "testrun", "T1", "--reply-to", "main")
            # an error payload, carried out to the caller's exit code
            self.assertEqual(1, result.returncode)
            self.assertIn("ticket not found", json.loads(result.stdout)["error"])


def make_worktree(tmp: Path, tickets: dict):
    """A main checkout plus a linked worktree whose ``.git`` is a pointer file.

    The shape `make_repo` cannot produce: `.git` as a file holding a
    `gitdir:` line, which is what an executor's isolated workspace has and
    what the result channel must dereference to the main checkout.
    """

    sink = use_sink(tmp)
    main = tmp / "main"
    main.mkdir()
    run_dir = make_repo(main, tickets, sink=sink)
    (main / ".git" / "worktrees" / "wt").mkdir(parents=True)
    worktree = tmp / "wt"
    worktree.mkdir()
    (worktree / ".git").write_text(
        f"gitdir: {main / '.git' / 'worktrees' / 'wt'}\n", encoding="utf-8"
    )
    return main, worktree, run_dir


class TestResultWorktreeCrossing(unittest.TestCase):
    """contracts/work-item.md: one run's tickets have one path, identical
    from every executor workspace. The executor files its result there from
    inside its own worktree, reading its body from that worktree."""

    def test_result_from_a_worktree_lands_in_the_main_checkout(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            body = worktree / "result-body.md"
            body.write_text("Landed at the main root.\n", encoding="utf-8")
            payload = run_cmd(
                worktree, "result", "testrun", "T1",
                "--section", "Result", "--file", str(body),
            )
            self.assertEqual("Result", payload["result"]["section"])
            self.assertEqual(
                str((run_dir / "T1.md").resolve()), payload["result"]["path"]
            )
            self.assertIn(
                "## Result\n\nLanded at the main root.\n",
                (run_dir / "T1.md").read_text(encoding="utf-8"),
            )
            # nothing was created in the worktree: the ticket tree is the
            # main checkout's alone
            self.assertFalse((worktree / ".orch").exists())

    def test_text_form_writes_the_same_body(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            payload = run_cmd(
                worktree, "result", "testrun", "T1",
                "--section", "verification", "--text", "1. PASS.",
            )
            self.assertEqual("Verification", payload["result"]["section"])
            self.assertIn(
                "## Verification\n\n1. PASS.\n",
                (run_dir / "T1.md").read_text(encoding="utf-8"),
            )


def frontmatter_of(path: Path) -> str:
    return path.read_text(encoding="utf-8").split("---\n", 2)[1]


class TestResultClosedSet(unittest.TestCase):
    """contracts/work-item.md:56-57 names exactly what an executor writes."""

    def test_the_writable_set_is_the_contracts_five(self):
        self.assertEqual(
            ("Result", "Verification", "Feedback", "Risks", "Handoff"),
            tickets_mod.EXECUTOR_SECTIONS,
        )

    def test_every_reserved_section_round_trips(self):
        for name in tickets_mod.EXECUTOR_SECTIONS:
            with tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)
                _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
                payload = run_cmd(
                    worktree, "result", "testrun", "T1",
                    "--section", name, "--text", f"body for {name}",
                )
                self.assertEqual(name, payload["result"]["section"], name)
                text = (run_dir / "T1.md").read_text(encoding="utf-8")
                self.assertEqual(f"body for {name}", tickets_mod._sections(text)[name])

    def test_a_cut_time_section_is_refused_and_the_set_is_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            before = (run_dir / "T1.md").read_text(encoding="utf-8")
            payload = run_cmd(
                worktree, "result", "testrun", "T1",
                "--section", "Objective", "--text", "hijacked",
            )
            self.assertIn("Objective", payload["error"])
            for name in tickets_mod.EXECUTOR_SECTIONS:
                self.assertIn(name, payload["error"])
            self.assertEqual(before, (run_dir / "T1.md").read_text(encoding="utf-8"))


class TestResultBodySource(unittest.TestCase):
    def test_both_file_and_text_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            body = worktree / "body.md"
            body.write_text("from a file\n", encoding="utf-8")
            before = (run_dir / "T1.md").read_text(encoding="utf-8")
            result = run_main(
                worktree, "result", "testrun", "T1", "--section", "Result",
                "--file", str(body), "--text", "from a string",
            )
            self.assertEqual(1, result.returncode)
            self.assertIn("error", json.loads(result.stdout))
            self.assertEqual(before, (run_dir / "T1.md").read_text(encoding="utf-8"))

    def test_neither_file_nor_text_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            before = (run_dir / "T1.md").read_text(encoding="utf-8")
            result = run_main(worktree, "result", "testrun", "T1", "--section", "Result")
            self.assertEqual(1, result.returncode)
            self.assertIn("error", json.loads(result.stdout))
            self.assertEqual(before, (run_dir / "T1.md").read_text(encoding="utf-8"))

    def test_an_unreadable_body_file_is_an_error_not_a_traceback(self):
        """A body path that exists and cannot be read, which is what this
        test's name claims and what an absent path is not.

        The absent path this carried until now takes the same handler, so
        the case that names the handler graded only ``FileNotFoundError``:
        a body file that is there and unreadable -- the reason the read is
        wrapped at all -- was never passed. Two shapes, both portable:
        a directory where a file is expected (``IsADirectoryError`` on
        POSIX, ``PermissionError`` on Windows -- ``chmod 000`` is neither,
        and does not bite as root), and a read that raises for that path
        alone. The absent path stays as a third case, now beside the two.
        """

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, _run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            a_directory = worktree / "body-that-is-a-directory.md"
            a_directory.mkdir()
            present = worktree / "present-but-unreadable.md"
            present.write_text("bytes no reader reaches\n", encoding="utf-8")

            for label, path, raiser in (
                ("a directory where a file is expected", a_directory, None),
                ("a present file whose read raises", present, PermissionError),
                ("an absent path", worktree / "absent.md", None),
            ):
                with self.subTest(label):
                    with refusing_to_read(path, raiser):
                        result = run_main(
                            worktree, "result", "testrun", "T1",
                            "--section", "Result", "--file", str(path),
                        )
                    self.assertEqual(1, result.returncode, result.stdout)
                    error = json.loads(result.stdout)["error"]
                    # the handler's own words, not a traceback rendered by
                    # `main`'s catch-all: with the handler gone this reads
                    # the bare OSError instead
                    self.assertIn("unreadable body file", error, error)


class TestResultRefusesTerminalStatus(unittest.TestCase):
    """Criterion 4's refusal half: terminal status is the join's alone
    (contracts/work-item.md:31-33), so `result` writes no frontmatter."""

    def test_a_status_flag_is_refused_and_names_set_status_and_the_join(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            before = (run_dir / "T1.md").read_text(encoding="utf-8")
            result = run_main(
                worktree, "result", "testrun", "T1", "--section", "Result",
                "--text", "done", "--status", "complete",
            )
            self.assertEqual(1, result.returncode)
            payload = json.loads(result.stdout)
            self.assertIn("--status", payload["error"])
            self.assertIn("set-status", payload["error"])
            self.assertIn("orch-integrate", payload["error"])
            self.assertEqual(before, (run_dir / "T1.md").read_text(encoding="utf-8"))

    def test_any_unrecognized_flag_is_refused_the_same_way(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, _run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            payload = run_cmd(
                worktree, "result", "testrun", "T1", "--section", "Result",
                "--text", "done", "--claimed-by", "someone",
            )
            self.assertIn("--claimed-by", payload["error"])
            self.assertIn("set-status", payload["error"])

    def test_frontmatter_is_byte_unchanged_after_writing_every_section(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            ticket = run_dir / "T1.md"
            before = frontmatter_of(ticket)
            for name in tickets_mod.EXECUTOR_SECTIONS:
                run_cmd(
                    worktree, "result", "testrun", "T1",
                    "--section", name, "--text", f"body for {name}",
                )
            self.assertEqual(before, frontmatter_of(ticket))
            self.assertIn("status: claimed", ticket.read_text(encoding="utf-8"))

    def test_a_heading_shaped_frontmatter_line_is_not_a_section_boundary(self):
        # A wrapped frontmatter value can begin a line with "## ". Treating it
        # as a heading would put the writer inside frontmatter the join owns.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            ticket = run_dir / "T1.md"
            ticket.write_text(
                ticket.read_text(encoding="utf-8").replace(
                    "bound: 30m\n", "bound: 30m\nnote:\n  - suspend through\n## Risks\n"
                ),
                encoding="utf-8",
            )
            before = frontmatter_of(ticket)
            run_cmd(
                worktree, "result", "testrun", "T1", "--section", "Risks", "--text", "[]",
            )
            self.assertEqual(before, frontmatter_of(ticket))
            self.assertEqual("[]", tickets_mod._sections(
                ticket.read_text(encoding="utf-8").split("---\n", 2)[2]
            )["Risks"])

    def test_a_fenced_heading_is_not_a_section_boundary(self):
        # Every deliverable in this repository is markdown with "## "
        # headings, and executors quote them at length. A heading inside a
        # fence is quoted content: ending the replaced span there deletes
        # the opening fence, orphans the closing one, and promotes the
        # quotation to a second heading that `_sections` then resolves
        # last-writer-wins -- silently reshaping sections the write never
        # named. Both fence characters, and an info string on the opener.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            ticket = run_dir / "T1.md"
            ticket.write_text(
                ticket.read_text(encoding="utf-8")
                + "\n## Result\n\nOLD BODY\n\n"
                + "```markdown\n## Objective\nquoted heading\n```\n\n"
                + "tail prose\n\n"
                + "## Feedback\n\n~~~\n## Handoff\nfenced handoff\n~~~\n\n"
                + "## Risks\n\n[]\n",
                encoding="utf-8",
            )
            run_cmd(
                worktree, "result", "testrun", "T1",
                "--section", "Result", "--text", "REPLACED", "--replace",
            )
            text = ticket.read_text(encoding="utf-8")
            sections = tickets_mod._sections(text.split("---\n", 2)[2])
            # The quotation stayed quoted: no second Objective, no orphan.
            self.assertEqual("Test ticket.", sections["Objective"])
            self.assertNotIn("quoted heading", text)
            self.assertNotIn("```", text)
            # The replaced span ran to the next real heading, and stopped.
            self.assertEqual("REPLACED", sections["Result"])
            self.assertIn("fenced handoff", sections["Feedback"])
            self.assertNotIn("Handoff", sections)
            self.assertEqual("[]", sections["Risks"])


class TestResultScriptContract(unittest.TestCase):
    def test_success_and_failure_each_print_one_json_document(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, _run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            ok = run_full(
                worktree, "result", "testrun", "T1", "--section", "Result", "--text", "ok",
            )
            self.assertEqual(0, ok.returncode)
            self.assertIn("result", json.loads(ok.stdout))
            self.assertEqual(1, len(ok.stdout.strip().splitlines()))
            bad = run_full(
                worktree, "result", "testrun", "T9", "--section", "Result", "--text", "ok",
            )
            self.assertEqual(1, bad.returncode)
            self.assertIn("ticket not found", json.loads(bad.stdout)["error"])
            self.assertEqual(1, len(bad.stdout.strip().splitlines()))

    def test_result_outside_a_repo_still_reaches_the_sink(self):
        """A result is user-scope state, so the cwd being outside a checkout
        no longer decides anything: the ticket is found and written."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_tickets(
                use_sink(tmp) / "tickets" / "testrun", {"T1": ("claimed", "[]")}
            )
            bare = tmp / "no-repo-here"
            bare.mkdir()
            result = run_full(
                bare, "result", "testrun", "T1", "--section", "Result", "--text", "x"
            )
            self.assertEqual(0, result.returncode)
            payload = json.loads(result.stdout)
            self.assertNotIn("error", payload)
            self.assertIn(
                "## Result\n\nx\n", (run_dir / "T1.md").read_text(encoding="utf-8")
            )


def headings_of(text: str) -> list:
    return [line[3:].strip() for line in text.splitlines() if line.startswith("## ")]


class TestResultSectionOrder(unittest.TestCase):
    """A created section takes its place in the order contracts/work-item.md
    states. The sparse `TICKET` fixture is the one that can tell the
    difference: on a fuller ticket, blind appending is right by accident."""

    def test_a_created_section_lands_in_contract_order_not_append_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            run_cmd(worktree, "result", "testrun", "T1", "--section", "Feedback", "--text", "[]")
            run_cmd(worktree, "result", "testrun", "T1", "--section", "Result", "--text", "did it")
            text = (run_dir / "T1.md").read_text(encoding="utf-8")
            self.assertEqual(["Objective", "Result", "Feedback"], headings_of(text))
            self.assertEqual("did it", tickets_mod._sections(text)["Result"])
            self.assertEqual("[]", tickets_mod._sections(text)["Feedback"])

    def test_handoff_lands_last_however_the_sections_arrive(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            for name in ("Handoff", "Risks", "Verification"):
                run_cmd(worktree, "result", "testrun", "T1", "--section", name, "--text", name)
            self.assertEqual(
                ["Objective", "Verification", "Risks", "Handoff"],
                headings_of((run_dir / "T1.md").read_text(encoding="utf-8")),
            )


class TestResultAppend(unittest.TestCase):
    """contracts/work-item.md:91-93: a rules/verification.md §10 checker
    appends its own pass and never rewrites the executor's."""

    def test_append_keeps_the_prior_body_and_adds_after_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            ticket = run_dir / "T1.md"
            run_cmd(worktree, "result", "testrun", "T1", "--section", "Result",
                    "--text", "executor pass")
            run_cmd(worktree, "result", "testrun", "T1", "--section", "Feedback", "--text", "[]")
            before = ticket.read_text(encoding="utf-8")
            payload = run_cmd(worktree, "result", "testrun", "T1", "--section", "Result",
                              "--text", "checker pass", "--append")
            self.assertEqual("append", payload["result"]["mode"])
            text = ticket.read_text(encoding="utf-8")
            self.assertEqual("executor pass\n\nchecker pass", tickets_mod._sections(text)["Result"])
            self.assertLess(text.index("executor pass"), text.index("checker pass"))
            # every other section is byte-unchanged
            self.assertEqual(headings_of(before), headings_of(text))
            for name in ("Objective", "Feedback"):
                self.assertEqual(
                    tickets_mod._sections(before)[name], tickets_mod._sections(text)[name]
                )
            self.assertEqual(frontmatter_of(ticket), frontmatter_of(ticket))

    def test_append_to_an_absent_section_creates_it_in_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            run_cmd(worktree, "result", "testrun", "T1", "--section", "Risks",
                    "--text", "[]", "--append")
            text = (run_dir / "T1.md").read_text(encoding="utf-8")
            self.assertEqual(["Objective", "Risks"], headings_of(text))
            self.assertEqual("[]", tickets_mod._sections(text)["Risks"])

    def test_replace_replaces_rather_than_appends(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            run_cmd(worktree, "result", "testrun", "T1", "--section", "Result", "--text", "first")
            payload = run_cmd(worktree, "result", "testrun", "T1", "--section", "Result",
                              "--text", "second", "--replace")
            self.assertEqual("replace", payload["result"]["mode"])
            text = (run_dir / "T1.md").read_text(encoding="utf-8")
            self.assertEqual("second", tickets_mod._sections(text)["Result"])
            self.assertNotIn("first", text)


class ResultOverwriteTest(unittest.TestCase):
    """A written section is not overwritten by default.

    contracts/worklog.md's closing law, read across to the ticket the same
    executor writes: clobbering is refused by default and the refusal names
    the path. The first write of a section, and a section standing empty at
    cut time, are not overwrites and stay free.
    """

    def written(self, tmp: Path):
        _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
        ticket = run_dir / "T1.md"
        run_cmd(worktree, "result", "testrun", "T1", "--section", "Result",
                "--text", "the executor's own pass")
        return worktree, ticket

    def test_a_written_section_is_refused_and_the_refusal_names_the_ticket(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            worktree, ticket = self.written(tmp)
            before = ticket.read_text(encoding="utf-8")
            result = run_main(worktree, "result", "testrun", "T1", "--section", "Result",
                              "--text", "a silent clobber")
            self.assertEqual(1, result.returncode, result.stdout)
            error = json.loads(result.stdout)["error"]
            self.assertIn(str(ticket.resolve()), error)
            self.assertIn("Result", error)
            self.assertIn("--replace", error)
            self.assertIn("--append", error)
            # the prior content is unchanged, byte for byte
            self.assertEqual(before, ticket.read_text(encoding="utf-8"))
            self.assertNotIn("a silent clobber", before)

    # The two flags that carry a write past this guard are graded by
    # TestResultAppend: `--replace` by test_replace_replaces_rather_than_appends
    # and `--append` by test_append_keeps_the_prior_body_and_adds_after_it,
    # each over a section already written and each asserting strictly more
    # than the pair that stood here (the append case also grades ordering and
    # that every other section is byte-unchanged).

    def test_a_first_write_and_an_empty_cut_time_section_are_not_overwrites(self):
        """A ticket is cut with its executor sections present and empty; the
        executor's first write into one is the write this subcommand exists
        for, and must not need a flag."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            ticket = run_dir / "T1.md"
            ticket.write_text(
                ticket.read_text(encoding="utf-8") + "\n## Result\n\n## Risks\n\n",
                encoding="utf-8",
            )
            for section, text in (("Result", "first pass"), ("Risks", "[]"),
                                  ("Feedback", "[]")):
                payload = run_cmd(worktree, "result", "testrun", "T1",
                                  "--section", section, "--text", text)
                self.assertEqual("write", payload["result"]["mode"], section)
            sections = tickets_mod._sections(ticket.read_text(encoding="utf-8"))
            self.assertEqual("first pass", sections["Result"])
            self.assertEqual("[]", sections["Risks"])
            self.assertEqual("[]", sections["Feedback"])

    def test_append_and_replace_together_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            worktree, ticket = self.written(tmp)
            before = ticket.read_text(encoding="utf-8")
            result = run_main(worktree, "result", "testrun", "T1", "--section", "Result",
                              "--text", "both", "--append", "--replace")
            self.assertEqual(1, result.returncode, result.stdout)
            error = json.loads(result.stdout)["error"]
            self.assertIn("--append", error)
            self.assertIn("--replace", error)
            self.assertEqual(before, ticket.read_text(encoding="utf-8"))

    def test_a_heading_shaped_frontmatter_line_does_not_trip_the_guard(self):
        """The guard skips the frontmatter exactly as the writer does. Reading
        a wrapped frontmatter value that begins `## ` as a written section
        refuses a first write into a section that does not exist yet."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            ticket = run_dir / "T1.md"
            ticket.write_text(
                ticket.read_text(encoding="utf-8").replace(
                    "bound: 30m\n", "bound: 30m\nnote:\n  - suspend through\n## Risks\n"
                ),
                encoding="utf-8",
            )
            payload = run_cmd(worktree, "result", "testrun", "T1",
                              "--section", "Risks", "--text", "[]")
            self.assertEqual("write", payload["result"]["mode"], payload)
            self.assertEqual("[]", tickets_mod._sections(
                ticket.read_text(encoding="utf-8").split("---\n", 2)[2]
            )["Risks"])

    def test_the_guard_reads_the_span_the_writer_writes(self):
        """A fenced `## Result` above the real one is quoted content to the
        writer; the guard must read it the same way, or it reports on a
        heading the write will never touch."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            ticket = run_dir / "T1.md"
            ticket.write_text(
                ticket.read_text(encoding="utf-8")
                + "\n## Verification\n\n```\n## Result\n\nquoted body\n```\n",
                encoding="utf-8",
            )
            payload = run_cmd(worktree, "result", "testrun", "T1",
                              "--section", "Result", "--text", "the real first write")
            self.assertEqual("write", payload["result"]["mode"], payload)
            text = ticket.read_text(encoding="utf-8")
            self.assertIn("quoted body", text)
            self.assertIn("the real first write", text)

    def test_every_executor_section_is_guarded_not_just_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            ticket = run_dir / "T1.md"
            for section in tickets_mod.EXECUTOR_SECTIONS:
                run_cmd(worktree, "result", "testrun", "T1", "--section", section,
                        "--text", f"{section} first")
                before = ticket.read_text(encoding="utf-8")
                result = run_main(worktree, "result", "testrun", "T1",
                                  "--section", section, "--text", f"{section} clobber")
                self.assertEqual(1, result.returncode, f"{section}: {result.stdout}")
                self.assertIn(section, json.loads(result.stdout)["error"])
                self.assertEqual(before, ticket.read_text(encoding="utf-8"), section)


# --- the run-state channel ---------------------------------------------------


def worklog_of(run: str = "testrun") -> Path:
    return sink_root() / "runs" / run / "worklog.md"


def run_dir_of(run: str = "testrun") -> Path:
    return sink_root() / "runs" / run


def tree_dir_of(tree: str, run: str = "testrun") -> Path:
    """One run's directory in a named run-state tree of the sink.

    ``runs`` is the default tree, so ``tree_dir_of("runs")`` and
    ``run_dir_of()`` are the same path by construction.
    """

    return sink_root() / tree / run


def run_state_lines(prompt: str) -> list:
    return [line for line in prompt.splitlines() if " run-state " in line]


def git_available() -> bool:
    try:
        return subprocess.run(
            ["git", "--version"], capture_output=True, text=True
        ).returncode == 0
    except OSError:
        return False


def make_real_worktree(tmp: Path):
    """A main checkout and a linked worktree that `git worktree add` made.

    `make_worktree` hand-writes the pointer file; this one lets git write it,
    so the resolver is proved against the shape git actually produces.
    """

    env = dict(
        os.environ,
        GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
        GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid",
    )

    def git(*args):
        completed = subprocess.run(
            ["git", "-c", "commit.gpgsign=false", *args],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", cwd=str(main), env=env,
        )
        if completed.returncode != 0:
            raise unittest.SkipTest(f"git {args[0]} failed: {completed.stderr.strip()}")

    use_sink(tmp)
    main = tmp / "main"
    main.mkdir()
    git("init", "--quiet")
    (main / "README.md").write_text("baseline\n", encoding="utf-8")
    git("add", "README.md")
    git("commit", "--quiet", "-m", "init")
    worktree = tmp / "wt"
    git("worktree", "add", "--quiet", "-b", "wt-branch", str(worktree))
    return main, worktree


class TestRunStateWorklog(unittest.TestCase):
    """rules/visibility.md §6: run state reaches the one user-scope sink
    from any workspace in any repository, or it fails loudly."""

    def test_a_note_from_a_worktree_appends_in_the_sink(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            payload = run_cmd(worktree, "run-state", "testrun", "--note", "slice one landed")
            self.assertEqual("note", payload["run_state"]["mode"])
            self.assertEqual(
                str(worklog_of().resolve()), payload["run_state"]["path"]
            )
            self.assertEqual(
                "slice one landed\n", worklog_of().read_text(encoding="utf-8")
            )
            # the run tree is the sink's alone
            self.assertFalse((worktree / ".orch").exists())
            self.assertFalse((main / ".orch").exists())

    def test_a_prior_line_and_an_outside_writer_both_survive(self):
        """Append mode, never read-modify-write: scripts/friction.py opens the
        shared log with ``"a"`` and an explicit ``newline`` for exactly this."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            run_cmd(worktree, "run-state", "testrun", "--note", "first from the channel")
            with open(worklog_of(), "a", encoding="utf-8", newline="\n") as handle:
                handle.write("second from another worktree\n")
            run_cmd(worktree, "run-state", "testrun", "--note", "third from the channel")
            self.assertEqual(
                [
                    "first from the channel",
                    "second from another worktree",
                    "third from the channel",
                ],
                worklog_of().read_text(encoding="utf-8").splitlines(),
            )

    def test_concurrent_notes_all_land_whole(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            notes = [f"writer-{i} " + "x" * 2000 for i in range(8)]
            # eight processes, never eight threads: the contention this grades
            # is between writers the platform serialises at the file, and
            # in-process callers would share one interpreter's own ordering
            with ThreadPoolExecutor(max_workers=8) as pool:
                payloads = list(
                    pool.map(
                        lambda note: run_json(worktree, "run-state", "testrun", "--note", note),
                        notes,
                    )
                )
            # A writer that reported an error and a writer whose line was lost
            # are two different defects, and the file check alone reports the
            # second for both -- the payloads are the only place the first is
            # visible, and this test used to throw them away.
            self.assertEqual([], [p["error"] for p in payloads if "error" in p])
            self.assertEqual(
                sorted(notes),
                sorted(worklog_of().read_text(encoding="utf-8").splitlines()),
            )


class TestRunStateArtifact(unittest.TestCase):
    """Anything not append-only is partitioned by run id, so two runs in two
    workspaces never write one file."""

    def test_a_named_artifact_lands_under_the_run_partition(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            payload = run_cmd(
                worktree, "run-state", "testrun", "--artifact", "evidence.md",
                "--text", "the bytes at the main root\n",
            )
            artifact = run_dir_of() / "evidence.md"
            self.assertEqual("artifact", payload["run_state"]["mode"])
            self.assertEqual(str(artifact.resolve()), payload["run_state"]["path"])
            self.assertEqual(
                "the bytes at the main root\n", artifact.read_text(encoding="utf-8")
            )
            self.assertFalse((worktree / ".orch").exists())

    def test_the_body_can_come_from_a_file_inside_the_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            body = worktree / "evidence-body.md"
            body.write_text("read inside, written outside\n", encoding="utf-8")
            run_cmd(
                worktree, "run-state", "testrun", "--artifact", "checks.md",
                "--file", str(body),
            )
            self.assertEqual(
                "read inside, written outside\n",
                (run_dir_of() / "checks.md").read_text(encoding="utf-8"),
            )


# Reading is the thing an append does not do. Any of these inside the writer
# says the write depends on what the file held at some earlier moment, which
# is the whole of the hazard whether the write itself appends or not.
READ_CALLS = frozenset({"read", "readline", "readlines", "read_text", "read_bytes"})


def _constant(node):
    """A literal argument's value, or ``None`` where it is not a literal."""

    return node.value if isinstance(node, ast.Constant) else None


def _open_mode(call, positional: int):
    """The mode an ``open`` call asks for, however the call spells it:
    positionally, by keyword, or by omission -- the default is a read.

    ``open(path, mode)`` and ``path.open(mode)`` carry it in different
    positions, so the caller says which one this call is.
    """

    for keyword in call.keywords:
        if keyword.arg == "mode":
            return _constant(keyword.value)
    if len(call.args) > positional:
        return _constant(call.args[positional])
    return "r"


def append_mechanism(source: str, name: str) -> dict:
    """How the function ``name`` in ``source`` opens its file, read off the
    AST rather than the text.

    A grep pins one spelling of the call: it said nothing once the call moved
    one function away, and it fails on ``open(path, 'a'``, on
    ``open(path, mode="a")`` and on ``path.open("a")`` -- false failures, no
    change in mechanism. What separates an append from a read-modify-write is
    how many opens there are, in what mode, and whether anything reads.
    """

    defined = [
        node
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.FunctionDef) and node.name == name
    ]
    if len(defined) != 1:
        raise AssertionError(f"{len(defined)} functions named {name!r} in this source")
    modes, reads = [], []
    for call in ast.walk(defined[0]):
        if not isinstance(call, ast.Call):
            continue
        if isinstance(call.func, ast.Attribute):
            called, position = call.func.attr, 0  # path.open(mode)
        elif isinstance(call.func, ast.Name):
            called, position = call.func.id, 1  # open(path, mode)
        else:
            continue
        if called == "open":
            modes.append(_open_mode(call, position))
        elif called in READ_CALLS:
            reads.append(called)
    return {"open_modes": modes, "reads": reads}


def assert_one_append_open_and_no_read(test, source: str, name: str) -> None:
    """Assert ``name`` appends: exactly one open, in append mode, nothing read.

    One check, both directions: the real function is graded by it and so is
    every wrong implementation built beside the tree, so what passes and what
    fails are decided by the same instrument.
    """

    mechanism = append_mechanism(source, name)
    test.assertEqual(["a"], mechanism["open_modes"], name)
    test.assertEqual([], mechanism["reads"], name)


# One mechanism, three spellings, and not one of them a string the grep
# could find. A check that fails on any of these reports a rewrite that
# never happened.
APPEND_SPELLINGS = {
    "single quotes": """
def _append_one_line(path, block):
    with open(path, 'a', encoding="utf-8", newline="\\n") as handle:
        handle.write(block)
""",
    "mode keyword": """
def _append_one_line(path, block):
    with open(path, mode="a", encoding="utf-8", newline="\\n") as handle:
        handle.write(block)
""",
    "Path.open": """
def _append_one_line(path, block):
    with path.open("a", encoding="utf-8", newline="\\n") as handle:
        handle.write(block)
""",
}

# The real function writes on two branches and flushes on one; a third branch
# would move that count again without moving anything the append depends on.
BRANCHED_APPEND = """
def _append_one_line(path, block):
    with open(path, "a", encoding="utf-8", newline="\\n") as handle:
        if msvcrt is None:
            handle.write(block)
            return
        handle.write(block)
        handle.flush()
        handle.write("")
"""

# Two implementations that are wrong and satisfy the behavioural test anyway.
# Each reproduces its expectation exactly, because the write that test
# interleaves lands between two complete invocations -- so nothing there can
# tell either of these from the real function. The first rewrites the whole
# file; the second appends, but only after deciding from a read that another
# writer can invalidate before the write lands.
WRONG_APPENDS = {
    "whole-file rewrite": """
def _append_one_line(path, block):
    existing = path.read_text(encoding="utf-8")
    with open(path, "w", encoding="utf-8", newline="\\n") as handle:
        handle.write(existing + block)
""",
    "append decided by a stale read": """
def _append_one_line(path, block):
    if block in path.read_text(encoding="utf-8"):
        return
    with open(path, "a", encoding="utf-8", newline="\\n") as handle:
        handle.write(block)
""",
}


def load_beside_the_tree(directory: Path, name: str, source: str):
    """Import ``source`` as a module of its own, beside the tree, never in it.

    A wrong implementation is evidence only if it is a real one, and
    rules/verification.md §8 rules out the other way of getting one: editing
    the tree under test and putting it back, where the harm is the window and
    not the commit.
    """

    path = directory / (name + ".py")
    path.write_text(source, encoding="utf-8")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TerminalNoteTest(unittest.TestCase):
    """contracts/worklog.md: "Notes append in occurrence order, and no note
    is written past a terminal section: a worklog carries no terminal
    placeholder until it closes."

    Both halves are one law. A placeholder written at creation would make
    every note a note past a terminal section; a terminal section written
    at the close makes the notes after it the error they are.
    """

    def test_creation_writes_no_terminal_placeholder(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            run_cmd(worktree, "run-state", "testrun", "--note", "the first line")
            text = worklog_of().read_text(encoding="utf-8")
            self.assertEqual("the first line\n", text)
            self.assertNotIn(tickets_mod.TERMINAL_HEADING, text)
            for state in tickets_mod.TERMINAL_STATES:
                self.assertNotIn(state, text, state)

    def test_note_note_terminal_note_refuses_the_fourth_in_occurrence_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            for line in ("note one", "note two"):
                self.assertIn(
                    "run_state", run_cmd(worktree, "run-state", "testrun", "--note", line)
                )
            closed = run_cmd(worktree, "run-state", "testrun", "--terminal", "complete",
                             "--text", "every criterion passed")
            self.assertEqual("terminal", closed["run_state"]["mode"])
            self.assertEqual("complete", closed["run_state"]["terminal"])

            result = run_main(worktree, "run-state", "testrun", "--note", "note four")
            self.assertEqual(1, result.returncode, result.stdout)
            error = json.loads(result.stdout)["error"]
            self.assertIn("terminal", error)
            self.assertIn("complete", error)
            self.assertIn(str(worklog_of().resolve()), error)

            lines = worklog_of().read_text(encoding="utf-8").splitlines()
            # the notes are in occurrence order, the close is after them, and
            # the fourth note is nowhere in the file
            self.assertEqual(["note one", "note two"], lines[:2])
            self.assertLess(lines.index("note two"), lines.index("## terminal: complete"))
            self.assertNotIn("note four", lines)
            self.assertIn("every criterion passed", lines)

    def test_a_second_close_is_refused_and_the_first_stands(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            run_cmd(worktree, "run-state", "testrun", "--terminal", "complete",
                    "--text", "the deciding evidence")
            before = worklog_of().read_text(encoding="utf-8")
            result = run_main(worktree, "run-state", "testrun", "--terminal", "failed",
                              "--text", "a second close")
            self.assertEqual(1, result.returncode, result.stdout)
            self.assertIn("complete", json.loads(result.stdout)["error"])
            self.assertEqual(before, worklog_of().read_text(encoding="utf-8"))

    # Both halves of what stood here are graded by TestRunStateWorklog, each
    # asserting more: the interleave by
    # test_a_prior_line_and_an_outside_writer_both_survive, and the eight
    # concurrent writers by test_concurrent_notes_all_land_whole, which also
    # grades the payloads (a writer that reported an error and a writer whose
    # line was lost are two defects, and the file check alone shows only the
    # second). The mechanism is graded below off the AST, which is the only
    # place it can be: the writes above land between complete invocations, so
    # a read-modify-write reproduces both expectations exactly.

    def test_the_append_is_one_open_in_append_mode_with_no_read(self):
        """The mechanism assertion, read off the AST: one open, append mode,
        nothing read.

        Replaces the source-text grep this class carried at 6c3b7aa:907,
        which fell to a spelling change and to the call moving one function
        away -- each a false failure, neither a change in mechanism."""

        assert_one_append_open_and_no_read(
            self, inspect.getsource(tickets_mod._append_one_line), "_append_one_line"
        )

    def test_the_assertion_survives_alternate_open_spellings(self):
        """The spellings the grep could not read. Each is the same mechanism
        written another way, so the assertion has to pass every one of them
        while the string the grep looked for appears in none."""

        for label, source in APPEND_SPELLINGS.items():
            with self.subTest(label):
                self.assertNotIn('open(path, "a"', source)
                assert_one_append_open_and_no_read(self, source, "_append_one_line")

    def test_a_read_modify_write_implementation_fails_the_assertion(self):
        """The can-fail direction, without which the assertion grades nothing.

        Each wrong implementation is imported beside the tree and run for
        real: first against the interleaved write, where it reproduces the
        behavioural expectation exactly and so goes uncaught, and then
        against the assertion, which is the one check here that can see it."""

        for label, source in WRONG_APPENDS.items():
            with self.subTest(label), tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)
                wrong = load_beside_the_tree(tmp, "wrong_append", source)
                path = tmp / "worklog.md"
                path.write_text("", encoding="utf-8")
                wrong._append_one_line(path, "from the channel\n")
                with open(path, "a", encoding="utf-8", newline="\n") as handle:
                    handle.write("from another worktree\n")
                wrong._append_one_line(path, "from the channel again\n")
                self.assertEqual(
                    ["from the channel", "from another worktree",
                     "from the channel again"],
                    path.read_text(encoding="utf-8").splitlines(),
                    "the behavioural test cannot tell this from the real one",
                )
                with self.assertRaises(AssertionError):
                    assert_one_append_open_and_no_read(
                        self,
                        inspect.getsource(wrong._append_one_line),
                        "_append_one_line",
                    )

    def test_the_write_call_count_is_not_asserted(self):
        """Bodies that differ only in how many times they write get one
        verdict. The real function is already on two writes and a flush, so a
        count here would fail the next branch added to it -- the grep's
        mistake in another instrument."""

        for label, source in (
            ("one write", APPEND_SPELLINGS["single quotes"]),
            ("a write on every branch", BRANCHED_APPEND),
        ):
            with self.subTest(label):
                assert_one_append_open_and_no_read(self, source, "_append_one_line")

    def test_the_close_requires_a_known_state_and_its_deciding_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            # a ticket-level status is not a run-level terminal state
            for bad in ("suspended", "ready", "done", ""):
                result = run_main(worktree, "run-state", "testrun", "--terminal", bad,
                                  "--text", "x")
                self.assertEqual(1, result.returncode, f"{bad!r}: {result.stdout}")
                error = json.loads(result.stdout)["error"]
                for state in tickets_mod.TERMINAL_STATES:
                    self.assertIn(state, error, f"{bad!r}: {state}")
            # the deciding evidence is not optional
            result = run_main(worktree, "run-state", "testrun", "--terminal", "complete")
            self.assertEqual(1, result.returncode, result.stdout)
            self.assertIn("--text", json.loads(result.stdout)["error"])
            self.assertFalse(worklog_of().exists())

    def test_every_run_level_terminal_state_closes_and_the_states_are_the_contract(self):
        for state in tickets_mod.TERMINAL_STATES:
            with tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)
                main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
                run_cmd(worktree, "run-state", "testrun", "--terminal", state,
                        "--text", "the deciding evidence")
                self.assertIn(
                    f"## terminal: {state}",
                    worklog_of().read_text(encoding="utf-8"),
                )
                result = run_main(worktree, "run-state", "testrun", "--note", "past it")
                self.assertEqual(1, result.returncode, f"{state}: {result.stdout}")
        self.assertEqual(
            ("complete", "blocked", "stalled", "limited", "failed"),
            tickets_mod.TERMINAL_STATES,
        )

    def test_a_note_may_not_forge_the_terminal_heading(self):
        """The marker is only trustworthy if a note cannot write one. A note
        that would read as a close is refused, so the guard can never be
        walked past by a line that merely looks like the close."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            for forged in ("## terminal: complete", "  ## terminal", "## Terminal: failed"):
                result = run_main(worktree, "run-state", "testrun", "--note", forged)
                self.assertEqual(1, result.returncode, f"{forged!r}: {result.stdout}")
                self.assertIn("--terminal", json.loads(result.stdout)["error"])
            self.assertFalse(worklog_of().exists())

    def test_the_close_is_per_run_and_per_tree(self):
        """A closed run does not close another run, and a closed research
        worklog does not close the run's own."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            run_cmd(worktree, "run-state", "testrun", "--terminal", "complete",
                    "--text", "closed")
            self.assertIn(
                "run_state", run_cmd(worktree, "run-state", "otherrun", "--note", "still open")
            )
            self.assertIn(
                "run_state",
                run_cmd(worktree, "run-state", "testrun", "--tree", "research",
                        "--note", "a research lane's own log"),
            )
            self.assertEqual(
                "a research lane's own log\n",
                (tree_dir_of("research") / "worklog.md").read_text(
                    encoding="utf-8"
                ),
            )

    def test_an_artifact_is_not_a_note_and_survives_the_close(self):
        """The law is about notes past a terminal section. Evidence written
        under a name is not a note and stays writable after the close."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            run_cmd(worktree, "run-state", "testrun", "--terminal", "complete",
                    "--text", "closed")
            payload = run_cmd(worktree, "run-state", "testrun", "--artifact",
                              "post-close.md", "--text", "the join's own record\n")
            self.assertEqual("artifact", payload["run_state"]["mode"])
            self.assertEqual(
                "the join's own record\n",
                (run_dir_of() / "post-close.md").read_text(encoding="utf-8"),
            )


class ArtifactOverwriteTest(unittest.TestCase):
    """contracts/worklog.md: "Writing an artifact that already exists is
    refused by default, the refusal naming the existing path."

    `--artifact` is the one whole-file write on this channel, and two
    workspaces write one repository's `.orch/` at once. Truncating an
    existing artifact is how a sibling lane's evidence leaves no trace of
    having existed.
    """

    def test_an_existing_artifact_is_refused_and_the_refusal_names_the_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            run_cmd(worktree, "run-state", "testrun", "--artifact", "evidence.md",
                    "--text", "the first lane's evidence\n")
            artifact = run_dir_of() / "evidence.md"
            result = run_main(worktree, "run-state", "testrun", "--artifact",
                              "evidence.md", "--text", "a silent truncation\n")
            self.assertEqual(1, result.returncode, result.stdout)
            error = json.loads(result.stdout)["error"]
            self.assertIn(str(artifact.resolve()), error)
            self.assertIn("--replace", error)
            # the first content stays intact
            self.assertEqual(
                "the first lane's evidence\n", artifact.read_text(encoding="utf-8")
            )

    def test_replace_is_what_carries_the_overwrite_through(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            run_cmd(worktree, "run-state", "testrun", "--artifact", "evidence.md",
                    "--text", "first\n")
            payload = run_cmd(worktree, "run-state", "testrun", "--artifact",
                              "evidence.md", "--text", "second\n", "--replace")
            self.assertEqual("artifact", payload["run_state"]["mode"])
            self.assertTrue(payload["run_state"]["replaced"])
            self.assertEqual(
                "second\n",
                (run_dir_of() / "evidence.md").read_text(encoding="utf-8"),
            )

    def test_a_first_write_needs_no_flag_and_reports_it_replaced_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            payload = run_cmd(worktree, "run-state", "testrun", "--artifact",
                              "evidence.md", "--text", "only\n")
            self.assertFalse(payload["run_state"]["replaced"])
            self.assertEqual(
                "only\n", (run_dir_of() / "evidence.md").read_text(encoding="utf-8")
            )

    def test_replace_on_an_absent_artifact_is_not_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            payload = run_cmd(worktree, "run-state", "testrun", "--artifact",
                              "fresh.md", "--text", "only\n", "--replace")
            self.assertEqual("artifact", payload["run_state"]["mode"])
            self.assertEqual(
                "only\n", (run_dir_of() / "fresh.md").read_text(encoding="utf-8")
            )

    def test_the_guard_is_the_run_partitioned_path_not_the_bare_name(self):
        """The same artifact name under two run ids is two paths, and neither
        refuses the other: the run id partitioning the path is what makes a
        whole-file write safe here at all."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            for run in ("testrun", "otherrun"):
                payload = run_cmd(worktree, "run-state", run, "--artifact",
                                  "evidence.md", "--text", f"{run}\n")
                self.assertIn("run_state", payload, run)
            for run in ("testrun", "otherrun"):
                self.assertEqual(
                    f"{run}\n",
                    (run_dir_of(run) / "evidence.md").read_text(encoding="utf-8"),
                )

    def test_a_note_is_an_append_and_never_trips_the_artifact_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            for line in ("one", "two", "three"):
                payload = run_cmd(worktree, "run-state", "testrun", "--note", line)
                self.assertIn("run_state", payload, line)
            self.assertEqual(
                ["one", "two", "three"],
                worklog_of().read_text(encoding="utf-8").splitlines(),
            )


class OrchTreesTest(unittest.TestCase):
    """`.orch/research/`, `.orch/improvement/` and `.orch/handoffs/` had no
    writer: named in the library, reachable by no subcommand, so anything
    meant for them was written by hand or not at all. `--tree` addresses
    them beside `runs/`, and the run id keeps partitioning the path."""

    OWNERLESS = ("research", "improvement", "handoffs")

    def test_one_file_is_written_and_read_back_in_each_ownerless_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            for tree in self.OWNERLESS:
                payload = run_cmd(worktree, "run-state", "testrun", "--tree", tree,
                                  "--artifact", "evidence.md", "--text", f"{tree} bytes\n")
                self.assertEqual(tree, payload["run_state"]["tree"], tree)
                landed = tree_dir_of(tree) / "evidence.md"
                self.assertEqual(str(landed.resolve()), payload["run_state"]["path"], tree)
                self.assertEqual(f"{tree} bytes\n", landed.read_text(encoding="utf-8"), tree)
            # written from the worktree, landed at the main root, every time
            self.assertFalse((worktree / ".orch").exists())

    def test_the_run_id_still_partitions_the_artifact_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            for run in ("testrun", "otherrun"):
                run_cmd(worktree, "run-state", run, "--tree", "research",
                        "--artifact", "evidence.md", "--text", f"{run}\n")
            for run in ("testrun", "otherrun"):
                self.assertEqual(
                    f"{run}\n",
                    (tree_dir_of("research", run) / "evidence.md").read_text(
                        encoding="utf-8"
                    ),
                )

    def test_runs_stays_the_default_and_nothing_is_retired(self):
        """Every pre-existing call site passes no `--tree` and must land
        exactly where it always did."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            note = run_cmd(worktree, "run-state", "testrun", "--note", "a line")
            self.assertEqual("runs", note["run_state"]["tree"])
            self.assertEqual(str(worklog_of().resolve()), note["run_state"]["path"])
            artifact = run_cmd(worktree, "run-state", "testrun", "--artifact",
                               "evidence.md", "--text", "bytes\n")
            self.assertEqual("runs", artifact["run_state"]["tree"])
            self.assertEqual(
                str((run_dir_of() / "evidence.md").resolve()),
                artifact["run_state"]["path"],
            )
            self.assertEqual("runs", tickets_mod.DEFAULT_RUN_STATE_TREE)
            self.assertIn("runs", tickets_mod.RUN_STATE_TREES)

    def test_an_explicit_runs_tree_is_the_same_path_as_the_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            explicit = run_cmd(worktree, "run-state", "testrun", "--tree", "runs",
                               "--artifact", "evidence.md", "--text", "bytes\n")
            self.assertEqual(
                str((run_dir_of() / "evidence.md").resolve()),
                explicit["run_state"]["path"],
            )

    def test_the_overwrite_guard_holds_in_every_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            for tree in self.OWNERLESS:
                run_cmd(worktree, "run-state", "testrun", "--tree", tree,
                        "--artifact", "evidence.md", "--text", "first\n")
                result = run_main(worktree, "run-state", "testrun", "--tree", tree,
                                  "--artifact", "evidence.md", "--text", "clobber\n")
                self.assertEqual(1, result.returncode, f"{tree}: {result.stdout}")
                landed = tree_dir_of(tree) / "evidence.md"
                self.assertIn(str(landed.resolve()), json.loads(result.stdout)["error"], tree)
                self.assertEqual("first\n", landed.read_text(encoding="utf-8"), tree)

    def test_an_unknown_tree_is_refused_and_the_closed_set_is_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            for bad in ("tickets", "friction", "../escape", "a/b", "", "canary"):
                result = run_main(worktree, "run-state", "testrun", "--tree", bad,
                                  "--artifact", "evidence.md", "--text", "x")
                self.assertEqual(1, result.returncode, f"{bad!r}: {result.stdout}")
                error = json.loads(result.stdout)["error"]
                for tree in tickets_mod.RUN_STATE_TREES:
                    self.assertIn(tree, error, f"{bad!r}: {tree}")
            # a refused tree creates nothing: the sink still holds only what
            # the fixture put there, and no run-state tree was opened
            self.assertEqual(
                ["tickets"], sorted(p.name for p in sink_root().iterdir())
            )
            self.assertFalse((main / ".orch").exists())

    def test_every_addressed_tree_is_gitignored_runtime_state(self):
        """`.gitignore` line 3 is `.orch/*`: every tree this subcommand
        writes is runtime state, never tracked content. A tree added to the
        closed set that escaped that line would commit run output."""

        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertIn(".orch/*", ignore)
        for tree in tickets_mod.RUN_STATE_TREES:
            self.assertNotIn(f"!.orch/{tree}/", ignore, tree)


class TestRunStateRootResolution(unittest.TestCase):
    def test_the_root_comes_from_the_one_resolver_with_no_subprocess(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            calls = []
            original = tickets_mod.state_root.runs_root

            def spy():
                calls.append(True)
                return original()

            cwd = os.getcwd()
            tickets_mod.state_root.runs_root = spy
            try:
                os.chdir(worktree)
                payload = tickets_mod._dispatch(
                    ["run-state", "testrun", "--note", "resolved in process"]
                )
            finally:
                os.chdir(cwd)
                tickets_mod.state_root.runs_root = original
            self.assertIn("run_state", payload)
            self.assertEqual(1, len(calls))
            self.assertEqual(
                "resolved in process\n", worklog_of().read_text(encoding="utf-8")
            )
            # nothing can shell out to git that never imports a way to:
            # the whole script's import set, not a word match on its prose
            imported = set()
            for node in ast.walk(ast.parse(TICKETS_PY.read_text(encoding="utf-8"))):
                if isinstance(node, ast.Import):
                    imported.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and not node.level:
                    imported.add((node.module or "").split(".")[0])
            self.assertNotIn("subprocess", imported)
            # `tempfile` is here for `run.json`: the identity document is
            # written beside itself and moved over, so a concurrent reader
            # never meets a half-written one. It opens no process either.
            self.assertNotIn("os", imported)
            # msvcrt is absent on POSIX and imported under try/except for the
            # one lock _append_one_line takes; it reaches no subprocess.
            # `time` is the retry budget `_replace_atomically` waits out a
            # Windows refusal against, and it too starts nothing.
            self.assertEqual(
                {"__future__", "datetime", "json", "msvcrt", "pathlib", "re",
                 "scripts", "state_root", "sys", "tempfile", "time"},
                imported,
            )

    @unittest.skipUnless(git_available(), "git is not on PATH")
    def test_inside_a_real_git_worktree_the_bytes_land_in_the_sink(self):
        with tempfile.TemporaryDirectory() as tmp:
            main, worktree = make_real_worktree(Path(tmp))
            payload = run_json(worktree, "run-state", "testrun", "--note", "from a real worktree")
            self.assertEqual(
                str(worklog_of().resolve()), payload["run_state"]["path"]
            )
            self.assertEqual(
                "from a real worktree\n", worklog_of().read_text(encoding="utf-8")
            )
            self.assertFalse((worktree / ".orch").exists())
            self.assertFalse((main / ".orch").exists())


class TestRunStateRefusesUnsafeNames(unittest.TestCase):
    """A run id or artifact name is one path segment. Anything that could
    climb out of the sink's `runs/` is refused by name, never sanitized
    silently."""

    def test_an_unsafe_run_id_is_refused_by_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            for bad in ("../escape", "a/b", "a\\b", ".."):
                payload = run_cmd(worktree, "run-state", bad, "--note", "x")
                self.assertIn(bad, payload.get("error", ""), bad)
                self.assertNotIn("run_state", payload)
            self.assertFalse((sink_root() / "runs").exists())

    def test_an_unsafe_artifact_name_is_refused_by_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            for bad in ("../escape.md", "a/b.md", "a\\b.md", ".."):
                payload = run_cmd(
                    worktree, "run-state", "testrun", "--artifact", bad, "--text", "x"
                )
                self.assertIn(bad, payload.get("error", ""), bad)
                self.assertNotIn("run_state", payload)
            self.assertFalse((sink_root() / "runs").exists())


class TestPacketCarriesTheRunStateCommand(unittest.TestCase):
    """Every dispatched child gets the channel in its own packet: no sibling
    reads another ticket to learn how to write run state."""

    def make(self, tmp: Path) -> Path:
        (tmp / ".git").mkdir()
        run_dir = use_sink(tmp) / "tickets" / "testrun"
        run_dir.mkdir(parents=True)
        path = run_dir / "T1.md"
        path.write_text(FULL_TICKET, encoding="utf-8")
        return path

    def test_every_packet_carries_it_workspace_or_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp)
            bare = run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main")["packet"]
            with_ws = run_cmd(
                tmp, "packet", "testrun", "T1", "--reply-to", "main", "--workspace", "/wt/a"
            )["packet"]
            for packet in (bare, with_ws):
                lines = run_state_lines(packet["prompt"])
                self.assertEqual(2, len(lines), packet["prompt"])
                for line in lines:
                    # `run` is interpolated from the ticket, not left a placeholder
                    self.assertIn(" run-state testrun ", line)

    def test_the_line_is_absolute_one_token_per_argument_and_shell_free(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp)
            packet = run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main")["packet"]
            note_line, artifact_line = run_state_lines(packet["prompt"])
            for line in (note_line, artifact_line):
                for forbidden in ("|", ">", "<", "&&", "$("):
                    self.assertNotIn(forbidden, line, line)
                tokens = line.split()
                self.assertEqual(sys.executable, tokens[0])
                self.assertTrue(Path(tokens[0]).is_absolute(), tokens[0])
                self.assertEqual(str(TICKETS_PY.resolve()), tokens[1])
                self.assertTrue(Path(tokens[1]).is_absolute(), tokens[1])
                self.assertEqual("tickets.py", Path(tokens[1]).name)
                self.assertEqual(["run-state", "testrun"], tokens[2:4])
            self.assertEqual(["--note", "TEXT"], note_line.split()[4:])
            self.assertEqual(
                ["--artifact", "NAME", "--text", "TEXT"], artifact_line.split()[4:]
            )

    def test_the_interpreter_and_script_path_are_derived_not_literal(self):
        """Run a copy of the script from somewhere else entirely: a literal
        `python3 scripts/tickets.py` would emit the same line from both."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp)
            elsewhere = tmp / "elsewhere"
            elsewhere.mkdir()
            copy = elsewhere / "tickets.py"
            copy.write_text(TICKETS_PY.read_text(encoding="utf-8"), encoding="utf-8")
            # the installed layout: the resolver sits flat beside it, and the
            # copy reaches it by the second arm of its two-arm import
            (elsewhere / "state_root.py").write_text(
                STATE_ROOT_PY.read_text(encoding="utf-8"), encoding="utf-8"
            )
            completed = subprocess.run(
                [sys.executable, str(copy), "packet", "testrun", "T1", "--reply-to", "main"],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", cwd=str(tmp),
            )
            packet = json.loads(completed.stdout)["packet"]
            lines = run_state_lines(packet["prompt"])
            self.assertEqual(2, len(lines))
            for line in lines:
                self.assertEqual(str(copy.resolve()), line.split()[1])
                self.assertNotIn(str(TICKETS_PY.resolve()), line)


class TestRelativeGitdirPointer(unittest.TestCase):
    """`make_worktree` writes an absolute pointer; git writes a relative one
    whenever the worktree was added with a relative path.

    The bodies moved to `scripts/state_root.py`; these two names survive
    here as re-exports, because `scripts/cutcheck.py` and `scripts/ui.py`
    still import them from this module. What is graded is that the
    re-export is the owner's function and not a second copy of it.
    """

    def test_a_relative_pointer_resolves_against_the_pointer_files_own_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main = tmp / "main"
            (main / ".git" / "worktrees" / "wt").mkdir(parents=True)
            worktree = tmp / "wt"
            worktree.mkdir()
            pointer = worktree / ".git"
            pointer.write_text("gitdir: ../main/.git/worktrees/wt\n", encoding="utf-8")
            self.assertEqual(main.resolve(), tickets_mod._main_checkout_root(pointer))
            self.assertEqual(main.resolve(), tickets_mod._find_repo_root(worktree))

    def test_the_two_names_are_the_resolvers_own_functions(self):
        self.assertIs(
            tickets_mod.state_root.main_checkout_root, tickets_mod._main_checkout_root
        )
        self.assertIs(
            tickets_mod.state_root.find_repo_root, tickets_mod._find_repo_root
        )


FENCE_TICKET_TAIL = (
    "\n## Result\n\nOLD BODY\n\n"
    "```markdown\n## Objective\nquoted heading\n```\n\n"
    "## Feedback\n\n[]\n"
)


def fence_broken(worktree_pair, tail: str) -> Path:
    """Append `tail` to the fixture ticket and hand back its path."""

    _main, _worktree, run_dir = worktree_pair
    ticket = run_dir / "T1.md"
    ticket.write_text(ticket.read_text(encoding="utf-8") + tail, encoding="utf-8")
    return ticket


class TestUnterminatedFenceIsReported(unittest.TestCase):
    """A fence that never closes hides every heading below it from
    `_heading_lines`, so the writer used to conclude the section was absent
    and create a second one -- leaving two `## Result` headings that
    `_sections` resolves to neither, since the fence swallows both. The file
    is corrupt input at that point: the only safe write is none, reported."""

    def test_an_unterminated_fence_in_an_earlier_section_is_reported_not_duplicated(self):
        with tempfile.TemporaryDirectory() as tmp:
            pair = make_worktree(Path(tmp), {"T1": ("claimed", "[]")})
            ticket = fence_broken(
                pair,
                "\n## Verification\n\n```text\nRan 1 test\nOK\n\n"  # never closed
                "## Result\n\nOLD BODY\n",
            )
            before = ticket.read_text(encoding="utf-8")
            payload = run_cmd(
                pair[1], "result", "testrun", "T1", "--section", "Result",
                "--text", "REPLACED",
            )
            self.assertIn("unterminated fence", payload.get("error", ""), payload)
            self.assertNotIn("result", payload)
            after = ticket.read_text(encoding="utf-8")
            self.assertEqual(before, after)
            self.assertEqual(1, after.count("\n## Result"), after)
            self.assertNotIn("REPLACED", after)

    def test_the_refusal_covers_append_a_tilde_fence_and_a_fence_below_the_target(self):
        tails = {
            "tilde opener": "\n## Verification\n\n~~~\nRan 1 test\n\n## Result\n\nOLD\n",
            "opened below the target": "\n## Result\n\nOLD\n\n## Feedback\n\n```\nopen\n",
        }
        for name, tail in tails.items():
            for mode in ([], ["--append"]):
                with self.subTest(tail=name, mode=mode or ["replace"]):
                    with tempfile.TemporaryDirectory() as tmp:
                        pair = make_worktree(Path(tmp), {"T1": ("claimed", "[]")})
                        ticket = fence_broken(pair, tail)
                        before = ticket.read_text(encoding="utf-8")
                        payload = run_cmd(
                            pair[1], "result", "testrun", "T1", "--section", "Result",
                            "--text", "REPLACED", *mode,
                        )
                        self.assertIn("unterminated fence", payload.get("error", ""), payload)
                        self.assertEqual(before, ticket.read_text(encoding="utf-8"))


class TestIndentedFenceIsNotAFence(unittest.TestCase):
    """CommonMark 4.4-4.5: at four columns of indentation a ``` line is
    indented-code content, not a fence. Opening a block there is how a
    ticket that merely quotes an indented snippet became unwritable."""

    def test_a_four_space_indented_fence_is_not_a_fence(self):
        self.assertEqual(
            [0, 5],
            tickets_mod._heading_lines([
                "## Objective",
                "",
                "    ```",
                "    ## quoted inside an indented block",
                "",
                "## Result",
            ]),
        )
        # up to three columns it is still a fence, and so is an unindented one
        self.assertEqual([0], tickets_mod._heading_lines(["## A", "   ```", "## B", "```"]))
        self.assertEqual([0], tickets_mod._heading_lines(["## A", "```", "## B", "```"]))

    def test_a_section_below_an_indented_fence_is_replaced_not_duplicated(self):
        with tempfile.TemporaryDirectory() as tmp:
            pair = make_worktree(Path(tmp), {"T1": ("claimed", "[]")})
            ticket = fence_broken(
                pair,
                "\n## Verification\n\n    ```\n    ## quoted\n\n## Result\n\nOLD BODY\n",
            )
            payload = run_cmd(
                pair[1], "result", "testrun", "T1", "--section", "Result",
                "--text", "REPLACED", "--replace",
            )
            self.assertIn("result", payload)
            text = ticket.read_text(encoding="utf-8")
            self.assertEqual(1, text.count("\n## Result"), text)
            sections = tickets_mod._sections(text)
            self.assertEqual("REPLACED", sections["Result"])
            self.assertIn("## quoted", sections["Verification"])


class TestFenceRepairHoldsBothDirections(unittest.TestCase):
    """The repair `d8af1c4` made -- a balanced fenced heading is quoted
    content, not a boundary -- and the refusal this item adds are one
    behavior read two ways. Pinning them in one case is what keeps a later
    change from buying either direction with the other."""

    def test_the_repair_holds_in_both_directions(self):
        # balanced: the quotation stays quoted and the span is replaced
        with tempfile.TemporaryDirectory() as tmp:
            pair = make_worktree(Path(tmp), {"T1": ("claimed", "[]")})
            ticket = fence_broken(pair, FENCE_TICKET_TAIL)
            payload = run_cmd(
                pair[1], "result", "testrun", "T1", "--section", "Result",
                "--text", "REPLACED", "--replace",
            )
            self.assertIn("result", payload)
            text = ticket.read_text(encoding="utf-8")
            sections = tickets_mod._sections(text)
            self.assertEqual("REPLACED", sections["Result"])
            self.assertEqual("Test ticket.", sections["Objective"])
            self.assertEqual("[]", sections["Feedback"])
            self.assertNotIn("quoted heading", text)

        # the same ticket with the closing fence gone: refused, bytes intact
        with tempfile.TemporaryDirectory() as tmp:
            pair = make_worktree(Path(tmp), {"T1": ("claimed", "[]")})
            ticket = fence_broken(
                pair, FENCE_TICKET_TAIL.replace("quoted heading\n```\n", "quoted heading\n")
            )
            before = ticket.read_text(encoding="utf-8")
            payload = run_cmd(
                pair[1], "result", "testrun", "T1", "--section", "Result",
                "--text", "REPLACED",
            )
            self.assertIn("unterminated fence", payload.get("error", ""), payload)
            self.assertEqual(before, ticket.read_text(encoding="utf-8"))


ISOLATED_TICKET = FULL_TICKET.replace(
    "write_scope:", "isolation: required\nwrite_scope:"
)
UNISOLATED_TICKET = FULL_TICKET.replace(
    "write_scope:", "isolation: none\nwrite_scope:"
)

GIT_ENV = dict(
    os.environ,
    GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
    GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid",
)


def git_run(cwd: Path, *args) -> str:
    completed = subprocess.run(
        ["git", "-c", "commit.gpgsign=false", *args],
        capture_output=True, text=True, encoding="utf-8",
        errors="replace", cwd=str(cwd), env=GIT_ENV,
    )
    if completed.returncode != 0:
        raise unittest.SkipTest(f"git {args[0]} failed: {completed.stderr.strip()}")
    return completed.stdout.strip()


def establishment_lines(prompt: str) -> list:
    """Every emitted establishment line, found the way a child finds it: by
    the tokens themselves, never by position and never by a literal path."""

    found = []
    for line in prompt.splitlines():
        tokens = line.split()
        if (
            len(tokens) > 2
            and Path(tokens[1]).name == "workspace.py"
            and tokens[2] == "start"
        ):
            found.append(line)
    return found


def make_packet_repo(tmp: Path, body: str, run: str = "testrun", tid: str = "T1") -> Path:
    (tmp / ".git").mkdir()
    run_dir = use_sink(tmp) / "tickets" / run
    run_dir.mkdir(parents=True)
    path = run_dir / f"{tid}.md"
    path.write_text(body, encoding="utf-8")
    return path


def make_isolated_fixture(tmp: Path, body: str = None):
    """A real `git init` main checkout, a ticket at its root, and a linked
    `git worktree add` tree on its own branch — the shape the emitted line is
    meant to be run in."""

    use_sink(tmp)
    main = tmp / "main"
    main.mkdir()
    git_run(main, "init", "--quiet")
    (main / "README.md").write_text("baseline\n", encoding="utf-8")
    git_run(main, "add", "README.md")
    git_run(main, "commit", "--quiet", "-m", "init")
    base = git_run(main, "rev-parse", "HEAD")
    run_dir = sink_root() / "tickets" / "testrun"
    run_dir.mkdir(parents=True)
    ticket = run_dir / "T1.md"
    ticket.write_text(ISOLATED_TICKET if body is None else body, encoding="utf-8")
    worktree = tmp / "wt"
    git_run(main, "worktree", "add", "--quiet", "-b", "item-branch", str(worktree))
    return main, worktree, ticket, base


def run_argv(argv: list, cwd: Path):
    return subprocess.run(
        argv, capture_output=True, text=True, encoding="utf-8",
        errors="replace", cwd=str(cwd),
    )


class TestPacketEmitsTheEstablishmentCommand(unittest.TestCase):
    """contracts/work-item.md's `isolation` is what `packet` conditions on:
    an isolated item is told how to establish its workspace, and a read-only
    lane is told nothing it must not run."""

    def packet_for(self, tmp: Path, body: str, run: str = "testrun", tid: str = "T1"):
        make_packet_repo(tmp, body, run, tid)
        return run_cmd(tmp, "packet", run, tid, "--reply-to", "main")["packet"]

    def test_required_emits_the_line_and_none_or_absent_omit_it(self):
        for body, expected in (
            (ISOLATED_TICKET, 1), (UNISOLATED_TICKET, 0), (FULL_TICKET, 0)
        ):
            with tempfile.TemporaryDirectory() as tmp:
                packet = self.packet_for(Path(tmp), body)
                prompt = packet["prompt"]
                self.assertEqual(expected, len(establishment_lines(prompt)), prompt)
                if not expected:
                    # omitted entirely: not the command, not a mention of it
                    self.assertNotIn("workspace.py", prompt)

    def test_run_and_id_are_interpolated_from_the_ticket(self):
        for run, tid in (("testrun", "T1"), ("otherrun", "Z9")):
            body = ISOLATED_TICKET.replace("id: T1", f"id: {tid}").replace(
                "run: testrun", f"run: {run}"
            )
            with tempfile.TemporaryDirectory() as tmp:
                packet = self.packet_for(Path(tmp), body, run, tid)
                (line,) = establishment_lines(packet["prompt"])
                self.assertEqual([run, tid], line.split()[3:5], line)

    def test_isolation_rides_the_packet_dict_beside_pack_and_independence(self):
        for body, expected in (
            (ISOLATED_TICKET, "required"),
            (UNISOLATED_TICKET, "none"),
            (FULL_TICKET, "none"),  # contracts/work-item.md: absent reads `none`
        ):
            with tempfile.TemporaryDirectory() as tmp:
                packet = self.packet_for(Path(tmp), body)
                self.assertLessEqual(
                    {"pack", "independence", "isolation"}, set(packet), sorted(packet)
                )
                self.assertEqual(expected, packet["isolation"])
                self.assertEqual("orch-code-pack", packet["pack"])

    def test_the_line_is_absolute_one_token_per_argument_and_shell_free(self):
        with tempfile.TemporaryDirectory() as tmp:
            packet = self.packet_for(Path(tmp), ISOLATED_TICKET)
            (line,) = establishment_lines(packet["prompt"])
            for forbidden in ("|", ">", "<", "&&", "$(", '"', "'"):
                self.assertNotIn(forbidden, line, line)
            tokens = line.split()
            self.assertEqual(5, len(tokens), line)
            self.assertEqual(sys.executable, tokens[0])
            self.assertTrue(Path(tokens[0]).is_absolute(), tokens[0])
            self.assertEqual(str((TICKETS_PY.parent / "workspace.py").resolve()), tokens[1])
            self.assertTrue(Path(tokens[1]).is_absolute(), tokens[1])
            self.assertEqual(["start", "testrun", "T1"], tokens[2:])

    def test_the_interpreter_and_script_path_are_derived_not_literal(self):
        """Run a copy of both scripts from somewhere else entirely: a
        hardcoded interpreter or a literal script path emits the same line
        from either layout, and installed scripts do not sit in `scripts/`."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_packet_repo(tmp, ISOLATED_TICKET)
            elsewhere = tmp / "elsewhere"
            elsewhere.mkdir()
            for name in ("state_root.py", "tickets.py", "workspace.py"):
                (elsewhere / name).write_text(
                    (TICKETS_PY.parent / name).read_text(encoding="utf-8"),
                    encoding="utf-8",
                )
            completed = run_argv(
                [sys.executable, str(elsewhere / "tickets.py"), "packet",
                 "testrun", "T1", "--reply-to", "main"],
                tmp,
            )
            packet = json.loads(completed.stdout)["packet"]
            (line,) = establishment_lines(packet["prompt"])
            self.assertEqual(str((elsewhere / "workspace.py").resolve()), line.split()[1])
            self.assertNotIn(str(TICKETS_PY.parent.resolve()), line)

    def test_the_emitting_code_holds_no_literal_interpreter_or_script_path(self):
        source = " ".join(inspect.getsource(tickets_mod._cmd_packet).split())
        self.assertNotIn("python3", source)
        self.assertNotIn("scripts/workspace.py", source)
        self.assertIn("sys.executable", source)
        self.assertIn("with_name", source)


def repacked(pack: str, body: str = ISOLATED_TICKET) -> str:
    """`body` restamped onto another pack. Every fixture below differs from
    the next in that one field, so nothing else can be what moved."""

    restamped = body.replace("pack: orch-code-pack", f"pack: {pack}")
    assert restamped != body or pack == "orch-code-pack", pack
    return restamped


class PackWorkspaceTest(unittest.TestCase):
    """`isolation: required` says this item works alone; the pack's
    `workspace` cell says what working alone is made of. Only a git mechanism
    has a workspace `scripts/workspace.py start` can establish — it branches
    and adds a worktree — so under a document-tree or evidence-store pack the
    emitted command is an instruction to do something the run's mechanism has
    no meaning for. `packet` conditions on both, never on `isolation` alone."""

    def lines_for(self, body: str) -> list:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_packet_repo(tmp, body)
            packet = run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main")
            self.assertIn("packet", packet, packet)
            return establishment_lines(packet["packet"]["prompt"])

    def prompt_for(self, body: str) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_packet_repo(tmp, body)
            return run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main")[
                "packet"
            ]["prompt"]

    def test_a_git_cell_pack_that_is_required_carries_the_invocation(self):
        for pack in ("orch-code-pack", "orch-design-pack"):
            lines = self.lines_for(repacked(pack))
            self.assertEqual(1, len(lines), (pack, lines))
            self.assertEqual(["start", "testrun", "T1"], lines[0].split()[2:], pack)

    def test_a_non_git_cell_pack_that_is_required_carries_none(self):
        for pack in ("orch-content-pack", "orch-research-pack"):
            prompt = self.prompt_for(repacked(pack))
            self.assertEqual([], establishment_lines(prompt), (pack, prompt))
            # omitted entirely: not the command, not a mention of it
            self.assertNotIn("workspace.py", prompt, pack)

    def test_the_declaration_is_still_reported_faithfully(self):
        """Suppressing the step never rewrites what the item declared: the
        packet still reads `required`, so a join grading isolation sees the
        item's own value and not this script's opinion of it."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_packet_repo(tmp, repacked("orch-content-pack"))
            packet = run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main")[
                "packet"
            ]
            self.assertEqual("required", packet["isolation"])
            self.assertEqual("orch-content-pack", packet["pack"])

    def test_a_content_pack_with_the_field_absent_carries_none(self):
        """Coverage of the item shape a decomposer emits for a content lane —
        no `isolation` at all — not discrimination: `packet` omitted the
        command for an absent field before this table existed."""

        prompt = self.prompt_for(repacked("orch-content-pack", FULL_TICKET))
        self.assertNotIn("isolation:", prompt)
        self.assertEqual([], establishment_lines(prompt), prompt)
        self.assertNotIn("workspace.py", prompt)

    def test_the_git_half_needs_the_declaration_too(self):
        """The pack is a second condition, never a replacement for the first:
        a git-cell pack that never declared isolation is still told nothing."""

        prompt = self.prompt_for(FULL_TICKET)
        self.assertEqual([], establishment_lines(prompt), prompt)
        self.assertNotIn("workspace.py", prompt)

    def test_a_pack_absent_from_the_table_still_gets_the_command(self):
        """The table can only be as current as the last sync. An unknown pack
        resolves toward emitting: a child handed a step its mechanism cannot
        use fails at its first act, in the open, while an omitted step leaves
        an isolated item working in the shared tree and losing it at the
        join, with nothing to see."""

        for pack in ("orch-widget-pack", ""):
            prompt = self.prompt_for(repacked(pack))
            self.assertEqual(1, len(establishment_lines(prompt)), (pack, prompt))

    def test_the_table_is_hardcoded_beside_the_engine_list(self):
        """The shape `ENGINE_EXECUTORS` set: a module-level literal, not a
        tree read, because an installed copy of this script runs against a
        target repository that carries no `packs/` at all."""

        table = tickets_mod.PACK_WORKSPACE_MECHANISMS
        self.assertIsInstance(table, dict)
        self.assertTrue(all(isinstance(v, str) and v for v in table.values()), table)
        lines = TICKETS_PY.read_text(encoding="utf-8").splitlines()
        index = next(
            i for i, line in enumerate(lines)
            if line.startswith("PACK_WORKSPACE_MECHANISMS = ")
        )
        comment = []
        while index and lines[index - 1].lstrip().startswith("#"):
            index -= 1
            comment.insert(0, lines[index])
        comment = "\n".join(comment)
        for token in ("packs/", "tests/test_sync.py", "workspace"):
            self.assertIn(token, comment, comment)


SCRIPTS = ROOT / "scripts"
PACKS_SEGMENT = "packs"
# scripts/cutcheck.py reads `<worktree_root>/packs/<pack>/SKILL.md`, where the
# root is the cut's own tree, handed in by the caller. That is a read of the
# repository under grading, not of the tree the script was installed from, and
# it already tolerates the tree's absence. It is the one module allowed a
# string naming the tree, named here so a second one cannot arrive unnoticed.
TREE_READING_SCRIPTS = {"cutcheck.py"}


def code_strings(source: str) -> list:
    """Every string constant in `source` that is not a docstring.

    Comments never enter the AST at all, and a docstring is skipped by
    identity here, so naming the tree in prose is outside this set by
    construction -- which is the distinction a grep cannot draw.
    """

    tree = ast.parse(source)
    docstrings = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ) or not body:
            continue
        first = body[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
            if isinstance(first.value.value, str):
                docstrings.add(id(first.value))
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in docstrings
    ]


def names_the_tree(source: str) -> list:
    """The code strings in `source` carrying `packs` as a whole path segment.
    `orch-code-pack` is not one; `packs`, `packs/x` and `a/packs` are."""

    return [
        value
        for value in code_strings(source)
        if PACKS_SEGMENT in value.replace("\\", "/").split("/")
    ]


class NoLibraryTreeReadTest(unittest.TestCase):
    """The installed script has no library beside it: it runs from wherever
    the installer put it, against a target repository that carries no
    `packs/`. So the pack-to-mechanism table is a literal and nothing here
    resolves a pack by reading the tree.

    Asserted in a class rather than by a recursive grep, which exits 1 on the
    no-match result that means success and so reads backwards as an oracle --
    and which cannot tell a comment naming the tree from a read of it.

    Note: the ticket's premise that `scripts/` carries no such string at the
    baseline holds only for the literal `packs/`; `scripts/cutcheck.py` has
    carried `PACKS_DIR = "packs"` and a read through it all along, of the cut's
    own tree. That module is allowlisted by name above rather than asserted
    away, so this stays a true statement about a tree that already has one.
    """

    def test_the_ticket_script_names_no_library_tree_path(self):
        found = names_the_tree(TICKETS_PY.read_text(encoding="utf-8"))
        self.assertEqual([], found, f"scripts/tickets.py names the tree: {found}")

    def test_no_module_outside_the_named_one_names_it(self):
        naming = {
            path.name: names_the_tree(path.read_text(encoding="utf-8"))
            for path in sorted(SCRIPTS.glob("*.py"))
        }
        offenders = {name: hits for name, hits in naming.items() if hits}
        self.assertLessEqual(set(offenders), TREE_READING_SCRIPTS, offenders)

    def test_prose_naming_the_tree_is_not_a_read(self):
        """The oracle's own discrimination: it must ignore a comment and a
        docstring and still catch a path built in code, or the two assertions
        above pass for the wrong reason."""

        prose = '"""A docstring naming packs/x."""\n# a comment naming packs/x\n'
        self.assertEqual([], names_the_tree(prose))
        self.assertEqual([], names_the_tree(prose + 'PACK = "orch-code-pack"\n'))
        self.assertEqual(
            ["packs"], names_the_tree(prose + 'P = root / "packs" / pack\n')
        )
        self.assertEqual(
            ["packs/orch-code-pack"],
            names_the_tree(prose + 'P = root / "packs/orch-code-pack"\n'),
        )

    def test_a_packet_renders_where_no_library_tree_exists(self):
        """The behavioural half: a copy of the script somewhere with no
        `packs/` above it or beside it still decides every pack in the table,
        exit 0. A tree read would answer differently, or not at all."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            elsewhere = tmp / "elsewhere"
            elsewhere.mkdir()
            # state_root.py travels with it: the script imports its sibling
            # resolver, and the installer copies `scripts/` as one unit. What
            # this case removes is the *library* tree, not the sibling.
            for name in ("tickets.py", "workspace.py", "state_root.py"):
                (elsewhere / name).write_text(
                    (SCRIPTS / name).read_text(encoding="utf-8"), encoding="utf-8"
                )
            self.assertFalse((elsewhere / "packs").exists())
            self.assertFalse((tmp / "packs").exists())
            for pack, mechanism in sorted(
                tickets_mod.PACK_WORKSPACE_MECHANISMS.items()
            ):
                repo = tmp / pack
                repo.mkdir()
                make_packet_repo(repo, repacked(pack))
                completed = run_argv(
                    [sys.executable, str(elsewhere / "tickets.py"), "packet",
                     "testrun", "T1", "--reply-to", "main"],
                    repo,
                )
                self.assertEqual(0, completed.returncode, completed.stderr)
                prompt = json.loads(completed.stdout)["packet"]["prompt"]
                expected = int(mechanism in tickets_mod.GIT_WORKSPACE_MECHANISMS)
                self.assertEqual(
                    expected, len(establishment_lines(prompt)), (pack, prompt)
                )


@unittest.skipUnless(git_available(), "git is not on PATH")
class TestExecutedPacketSeam(unittest.TestCase):
    """The establishment line is not read, it is run: lifted verbatim out of
    the rendered packet, split to argv, executed against the shipped scripts
    in a real linked worktree, and graded by what it did to the repository."""

    def test_the_emitted_line_runs_from_inside_and_check_grades_the_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            main, worktree, ticket, base = make_isolated_fixture(Path(tmp))
            packet = run_json(worktree, "packet", "testrun", "T1", "--reply-to", "main")["packet"]
            (line,) = establishment_lines(packet["prompt"])
            argv = line.split()

            started = run_argv(argv, worktree)
            self.assertEqual(0, started.returncode, started.stderr)
            recorded = json.loads(started.stdout)["start"]
            self.assertEqual(str(main.resolve()), str(Path(recorded["main_root"]).resolve()))
            self.assertTrue(recorded["isolated"])

            front = tickets_mod._parse_frontmatter(ticket.read_text(encoding="utf-8"))
            self.assertEqual("item-branch", front.get("workspace_branch"))
            self.assertEqual(f"{base} clean", front.get("workspace_baseline"))
            # the run tree is the sink's alone
            self.assertFalse((worktree / ".orch").exists())
            self.assertFalse((main / ".orch").exists())

            # `check` reuses every token the packet supplied but the subcommand
            check_argv = [*argv[:2], "check", *argv[3:], "--base", base]
            (worktree / "scratch").mkdir()
            (worktree / "scratch" / "t1.txt").write_text("in scope\n", encoding="utf-8")
            git_run(worktree, "add", "scratch/t1.txt")
            git_run(worktree, "commit", "--quiet", "-m", "in scope")
            clean = run_argv(check_argv, main)
            self.assertEqual(0, clean.returncode, clean.stdout + clean.stderr)
            graded = json.loads(clean.stdout)["check"]
            self.assertEqual("pass", graded["verdict"])
            self.assertEqual("item-branch", graded["workspace_branch"])

            # a deliberate scope breach, committed in the fixture
            (worktree / "secrets.txt").write_text("out of scope\n", encoding="utf-8")
            git_run(worktree, "add", "secrets.txt")
            git_run(worktree, "commit", "--quiet", "-m", "breach")
            breached = run_argv(check_argv, main)
            self.assertEqual(4, breached.returncode, breached.stdout + breached.stderr)
            payload = json.loads(breached.stdout)
            self.assertEqual("scope-breach", payload["verdict"])
            self.assertEqual(["secrets.txt"], payload["breaches"])


@unittest.skipUnless(git_available(), "git is not on PATH")
class TestExecutedRunStateSeam(unittest.TestCase):
    """The same execution against the run-state line every packet carries:
    run from inside the linked tree, the bytes land at the main root."""

    def test_the_emitted_run_state_lines_run_from_inside_the_linked_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            main, worktree, _, _ = make_isolated_fixture(Path(tmp))
            packet = run_json(worktree, "packet", "testrun", "T1", "--reply-to", "main")["packet"]
            note_line, artifact_line = run_state_lines(packet["prompt"])

            note_argv = note_line.split()
            self.assertEqual("TEXT", note_argv[-1])  # the one placeholder
            note_argv[-1] = "seam-note-from-the-linked-tree"
            noted = run_argv(note_argv, worktree)
            self.assertEqual(0, noted.returncode, noted.stderr)
            payload = json.loads(noted.stdout)
            # exit 0 and an error-free payload are one fact, asserted as two
            self.assertNotIn("error", payload)
            self.assertEqual(str(worklog_of().resolve()), payload["run_state"]["path"])
            self.assertEqual(
                "seam-note-from-the-linked-tree\n",
                worklog_of().read_text(encoding="utf-8"),
            )

            artifact_argv = artifact_line.split()
            self.assertEqual(["NAME", "--text", "TEXT"], artifact_argv[-3:])
            artifact_argv[-3] = "seam-evidence.md"
            artifact_argv[-1] = "seam-bytes-at-the-main-root"
            wrote = run_argv(artifact_argv, worktree)
            self.assertEqual(0, wrote.returncode, wrote.stderr)
            artifact = json.loads(wrote.stdout)
            self.assertNotIn("error", artifact)
            landed = run_dir_of() / "seam-evidence.md"
            self.assertEqual(str(landed.resolve()), artifact["run_state"]["path"])
            self.assertEqual("seam-bytes-at-the-main-root", landed.read_text(encoding="utf-8"))
            self.assertFalse((worktree / ".orch").exists())


# --- run identity -----------------------------------------------------------

GIT_CONFIG = (
    "[core]\n\trepositoryformatversion = 0\n"
    '[remote "{remote}"]\n\turl = {url}\n'
    "\tfetch = +refs/heads/*:refs/remotes/{remote}/*\n"
)
ALPHA = "https://example.invalid/acme/alpha.git"
BETA = "https://example.invalid/other/beta.git"
STAMP_RE = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"


def identity_of(run: str = "testrun") -> Path:
    return run_dir_of(run) / "run.json"


def identity_doc(run: str = "testrun") -> dict:
    """The run's identity document, or an assertion that none was written.

    Absence is the wrong *behavior*, not broken plumbing: a can-fail run
    against a revision that stamps no identity must read here as a failure,
    never as a `FileNotFoundError` from the fixture.
    """

    path = identity_of(run)
    if not path.is_file():
        raise AssertionError(f"no run identity was written at {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def identity_bytes(run: str = "testrun") -> bytes:
    identity_doc(run)  # the same assertion, for the same reason
    return identity_of(run).read_bytes()


def workspaces_of(run: str = "testrun") -> list:
    return [entry["path"] for entry in identity_doc(run)["workspaces"]]


def make_clone(root: Path, url=None, *, remote: str = "origin") -> Path:
    """A checkout at ``root`` whose ``.git/config`` names ``url``.

    ``url=None`` leaves it rootless — no remote at all — which is the other
    half of the identity rule and the shape `make_repo` already produces.
    """

    (root / ".git").mkdir(parents=True)
    if url is not None:
        (root / ".git" / "config").write_text(
            GIT_CONFIG.format(remote=remote, url=url), encoding="utf-8"
        )
    return root


class TestRunIdentity(unittest.TestCase):
    """One sink holds every project's runs, so each run says whose it is:
    which project opened it, when, and which workspaces of that project have
    written to it since."""

    def test_a_first_note_stamps_the_identity_document(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            repo = make_clone(tmp / "repo", ALPHA)
            payload = run_cmd(repo, "run-state", "testrun", "--note", "one")
            self.assertNotIn("error", payload)
            doc = identity_doc()
            self.assertEqual("testrun", doc["run"])
            self.assertEqual(2, doc["sink_convention"])
            self.assertEqual(
                {"root": str(repo.resolve()), "origin": ALPHA, "name": "repo"},
                doc["project"],
            )
            self.assertRegex(doc["opened_at"], STAMP_RE)
            self.assertEqual([str(repo.resolve())], workspaces_of())
            self.assertEqual(doc["opened_at"], doc["workspaces"][0]["first_seen"])
            self.assertEqual("one\n", worklog_of().read_text(encoding="utf-8"))

    def test_the_timestamp_shape_has_one_owner_in_this_script(self):
        """A second literal is how `claimed_at` and `opened_at` come to
        disagree. The count is what catches one being pasted back in; a
        `UTC_STAMP` that merely exists beside two literals would not."""

        source = TICKETS_PY.read_text(encoding="utf-8")
        # graded before the constant is named, so a revision that has no
        # `UTC_STAMP` reads as the wrong shape rather than a missing attribute
        self.assertEqual(1, source.count('"%Y-%m-%dT%H:%M:%SZ"'), "shape restated")
        self.assertEqual(2, source.count("strftime(UTC_STAMP)"), "stamped elsewhere")
        self.assertEqual("%Y-%m-%dT%H:%M:%SZ", tickets_mod.UTC_STAMP)

    def test_an_existing_run_directory_without_an_identity_gains_one(self):
        """The shape this repository's own live run is in: a worklog written
        before `run.json` existed. A missing identity is the ordinary first
        write, never an error, or a run in flight cannot record its own
        progress."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            repo = make_clone(tmp / "repo", None)
            run_dir_of().mkdir(parents=True)
            worklog_of().write_text("a line from before\n", encoding="utf-8")
            self.assertNotIn(
                "error", run_cmd(repo, "run-state", "testrun", "--note", "after")
            )
            self.assertEqual(
                ["a line from before", "after"],
                worklog_of().read_text(encoding="utf-8").splitlines(),
            )
            doc = identity_doc()
            self.assertEqual(str(repo.resolve()), doc["project"]["root"])
            self.assertIsNone(doc["project"]["origin"])

    def test_a_second_clone_of_one_origin_appends_and_never_rewrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            first = make_clone(tmp / "first", ALPHA)
            second = make_clone(tmp / "second", ALPHA)
            run_cmd(first, "run-state", "testrun", "--note", "from the first clone")
            opened = identity_doc()
            payload = run_cmd(second, "run-state", "testrun", "--note", "from the second")
            self.assertNotIn("error", payload)
            doc = identity_doc()
            self.assertEqual(opened["project"], doc["project"])
            self.assertEqual(opened["opened_at"], doc["opened_at"])
            self.assertEqual(
                [str(first.resolve()), str(second.resolve())], workspaces_of()
            )
            self.assertEqual(
                ["from the first clone", "from the second"],
                worklog_of().read_text(encoding="utf-8").splitlines(),
            )

    def test_one_url_spelled_two_ways_by_one_transport_is_one_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            first = make_clone(tmp / "first", "https://example.invalid/acme/alpha.git")
            second = make_clone(tmp / "second", "https://example.invalid/acme/alpha/")
            run_cmd(first, "run-state", "testrun", "--note", "one")
            self.assertNotIn(
                "error", run_cmd(second, "run-state", "testrun", "--note", "two")
            )
            self.assertEqual(2, len(workspaces_of()))

    def test_a_linked_worktree_appends_as_its_own_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            run_cmd(main, "run-state", "testrun", "--note", "from the main checkout")
            run_cmd(worktree, "run-state", "testrun", "--note", "from the linked tree")
            doc = identity_doc()
            # one project: the pointer file is dereferenced to the main root,
            # while the workspace recorded is the tree the write came from
            self.assertEqual(str(main.resolve()), doc["project"]["root"])
            self.assertEqual(
                [str(main.resolve()), str(worktree.resolve())], workspaces_of()
            )

    def test_a_repeat_write_from_a_recorded_workspace_changes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            repo = make_clone(tmp / "repo", ALPHA)
            run_cmd(repo, "run-state", "testrun", "--note", "one")
            opened = identity_bytes()
            for note in ("two", "three"):
                run_cmd(repo, "run-state", "testrun", "--note", note)
            self.assertEqual(1, len(workspaces_of()))
            # not merely deduplicated: no write is owed, so the file is
            # byte-untouched rather than rewritten identically each note
            self.assertEqual(opened, identity_of().read_bytes())
            self.assertEqual(
                ["one", "two", "three"],
                worklog_of().read_text(encoding="utf-8").splitlines(),
            )

    def test_the_origin_is_read_from_the_main_checkouts_config(self):
        """The write comes from a linked worktree, whose own `.git` is a
        pointer file with no config in it at all: the pointer is dereferenced
        first and the main checkout's config is what is read."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            (main / ".git" / "config").write_text(
                GIT_CONFIG.format(remote="origin", url=ALPHA), encoding="utf-8"
            )
            self.assertTrue((worktree / ".git").is_file())
            run_cmd(worktree, "run-state", "testrun", "--note", "from the linked tree")
            doc = identity_doc()
            self.assertEqual(ALPHA, doc["project"]["origin"])
            self.assertEqual(str(main.resolve()), doc["project"]["root"])

    @staticmethod
    def origin_reader():
        """The script's config reader, fetched by name rather than dotted.

        A revision that has none must read here as *cannot read a remote at
        all* — a failure about behavior — rather than as an AttributeError
        raised while collecting the case.
        """

        reader = getattr(tickets_mod, "_origin_url", None)
        if reader is None:
            raise AssertionError("this script cannot read a remote's url at all")
        return reader

    def test_the_config_reader_finds_origin_and_only_origin(self):
        reader = self.origin_reader()
        cases = (
            ("quoted", '[remote "origin"]\n\turl = ' + ALPHA + "\n", ALPHA),
            ("dotted", "[remote.origin]\n\turl = " + ALPHA + "\n", ALPHA),
            ("no-space", '[remote "origin"]\n\turl=' + ALPHA + "\n", ALPHA),
            ("upstream-only", '[remote "upstream"]\n\turl = ' + BETA + "\n", None),
            ("origin-without-url", '[remote "origin"]\n\tfetch = +refs/*\n', None),
            ("commented-out", '#[remote "origin"]\n\turl = ' + ALPHA + "\n", None),
            ("later-section-closes-it",
             '[remote "origin"]\n[user]\n\turl = ' + BETA + "\n", None),
        )
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            for name, text, expected in cases:
                with self.subTest(name):
                    root = tmp / name
                    (root / ".git").mkdir(parents=True)
                    (root / ".git" / "config").write_text(text, encoding="utf-8")
                    self.assertEqual(expected, reader(root))

    def test_a_repository_with_no_config_at_all_has_no_origin(self):
        reader = self.origin_reader()
        with tempfile.TemporaryDirectory() as tmp:
            root = make_clone(Path(tmp) / "bare", None)
            self.assertIsNone(reader(root))

    def test_two_concurrent_openings_leave_one_well_formed_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            repo = make_clone(tmp / "repo", ALPHA)
            notes = [f"opener-{i}" for i in range(8)]
            with ThreadPoolExecutor(max_workers=8) as pool:
                payloads = list(
                    pool.map(
                        lambda note: run_cmd(repo, "run-state", "testrun", "--note", note),
                        notes,
                    )
                )
            for payload in payloads:
                self.assertNotIn("error", payload)
            # exactly two files: one identity, one worklog, no `.tmp` left behind
            self.assertEqual(
                ["run.json", "worklog.md"],
                sorted(path.name for path in run_dir_of().iterdir()),
            )
            doc = identity_doc()  # parses, so no writer saw a torn file
            self.assertEqual("testrun", doc["run"])
            self.assertEqual([str(repo.resolve())], workspaces_of())
            self.assertEqual(
                sorted(notes),
                sorted(worklog_of().read_text(encoding="utf-8").splitlines()),
            )

    def test_the_identity_is_moved_into_place_never_written_over(self):
        """Atomicity is the claim `_write_identity` makes, and a plain write
        would pass the concurrency case above most days it ran. What is
        graded is the mechanism: the target is only ever reached by a move,
        so a reader cannot meet a half-written identity, and the move is the
        one `_replace_atomically` owns."""

        source = inspect.getsource(tickets_mod._write_identity)
        self.assertIn("_replace_atomically(temporary, run_dir / RUN_IDENTITY_NAME)", source)
        self.assertNotIn("write_text", source)
        mover = inspect.getsource(tickets_mod._replace_atomically)
        self.assertIn("temporary.replace(target)", mover)
        self.assertNotIn("write_text", mover)

    @unittest.skipUnless(git_available(), "git is not on PATH")
    def test_a_real_git_worktree_appends_to_the_same_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            main, worktree = make_real_worktree(Path(tmp))
            run_cmd(main, "run-state", "testrun", "--note", "from main")
            run_cmd(worktree, "run-state", "testrun", "--note", "from the worktree")
            doc = identity_doc()
            self.assertEqual(str(main.resolve()), doc["project"]["root"])
            self.assertEqual(
                [str(main.resolve()), str(worktree.resolve())], workspaces_of()
            )


class TestAtomicReplace(unittest.TestCase):
    """Both sides of the identity document's move, on both platforms.

    The branch that matters runs on Windows only, where a move and an open
    of one name refuse each other for the instant the move takes, so on
    every other host it is unreachable code that three cells of the matrix
    are the first to run. `msvcrt` is the discriminator the module already
    uses, so setting it is how this host asks the Windows question.
    """

    def refusals(self, count: int):
        """A `Path.replace` that refuses `count` times, then moves."""

        real = Path.replace
        state = {"left": count, "calls": 0}

        def replace(self, target):
            state["calls"] += 1
            if state["left"] > 0:
                state["left"] -= 1
                raise PermissionError(5, "Access is denied")
            return real(self, target)

        return replace, state

    def move(self, tmp: Path):
        source = tmp / "source"
        source.write_text("moved\n", encoding="utf-8")
        return source, tmp / "target"

    def test_windows_waits_out_a_transient_refusal(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            source, target = self.move(tmp)
            replace, state = self.refusals(3)
            with mock.patch.object(tickets_mod, "msvcrt", object()), mock.patch.object(
                Path, "replace", replace
            ):
                tickets_mod._replace_atomically(source, target)
            self.assertEqual(4, state["calls"])
            self.assertEqual("moved\n", target.read_text(encoding="utf-8"))

    def test_a_refusal_that_never_ends_is_reported_when_the_budget_runs_out(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            source, target = self.move(tmp)
            replace, _ = self.refusals(10**6)
            with mock.patch.object(tickets_mod, "msvcrt", object()), mock.patch.object(
                tickets_mod, "REPLACE_BUDGET_SECONDS", 0.05
            ), mock.patch.object(Path, "replace", replace):
                with self.assertRaises(PermissionError):
                    tickets_mod._replace_atomically(source, target)
            self.assertFalse(target.exists())

    def test_posix_takes_the_first_answer(self):
        """No retry where the platform has no transient refusal: a refusal
        there is real, and waiting on it would only delay the report."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            source, target = self.move(tmp)
            replace, state = self.refusals(1)
            with mock.patch.object(tickets_mod, "msvcrt", None), mock.patch.object(
                Path, "replace", replace
            ):
                with self.assertRaises(PermissionError):
                    tickets_mod._replace_atomically(source, target)
            self.assertEqual(1, state["calls"])

    def test_an_unobstructed_move_costs_one_attempt_on_either_platform(self):
        for label, sentinel in (("windows", object()), ("posix", None)):
            with self.subTest(label), tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)
                source, target = self.move(tmp)
                replace, state = self.refusals(0)
                with mock.patch.object(tickets_mod, "msvcrt", sentinel), mock.patch.object(
                    Path, "replace", replace
                ):
                    tickets_mod._replace_atomically(source, target)
                self.assertEqual(1, state["calls"])
                self.assertFalse(source.exists())
                self.assertEqual("moved\n", target.read_text(encoding="utf-8"))

    def test_an_absent_file_is_an_answer_and_is_never_waited_on(self):
        """The refusal is waited out; every other `OSError` is a fact. Most
        run-state writes open a run that has no identity yet, and a budget
        spent on that would be paid by the ordinary path to spare the rare
        one."""

        calls = []

        def missing():
            calls.append(1)
            raise FileNotFoundError(2, "No such file or directory")

        with mock.patch.object(tickets_mod, "msvcrt", object()):
            with self.assertRaises(FileNotFoundError):
                tickets_mod._waiting_out_windows(missing)
        self.assertEqual(1, len(calls))

    def test_the_reader_waits_out_a_writers_move_and_returns_the_document(self):
        """The other side of the same instant: an `open` of the name a move
        is landing on is refused too, and a run-state write that reported it
        would fail for someone else's write."""

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "run.json"
            path.write_text('{"run": "testrun"}\n', encoding="utf-8")
            real = Path.read_text
            state = {"left": 3}

            def read_text(self, *args, **kwargs):
                if state["left"] > 0:
                    state["left"] -= 1
                    raise PermissionError(13, "Permission denied")
                return real(self, *args, **kwargs)

            with mock.patch.object(tickets_mod, "msvcrt", object()), mock.patch.object(
                Path, "read_text", read_text
            ):
                document, error = tickets_mod._read_identity(path)
            self.assertIsNone(error)
            self.assertEqual({"run": "testrun"}, document)
            self.assertEqual(0, state["left"])

    def test_a_reader_refused_past_the_budget_is_still_refused_by_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "run.json"
            path.write_text('{"run": "testrun"}\n', encoding="utf-8")

            def read_text(self, *args, **kwargs):
                raise PermissionError(13, "Permission denied")

            with mock.patch.object(tickets_mod, "msvcrt", object()), mock.patch.object(
                tickets_mod, "REPLACE_BUDGET_SECONDS", 0.05
            ), mock.patch.object(Path, "read_text", read_text):
                document, error = tickets_mod._read_identity(path)
            self.assertIsNone(document)
            self.assertIn("unreadable run identity", error["error"])


class TestRunIdentityCollision(unittest.TestCase):
    """A run id is one project's. Two projects that pick the same one
    interleave into one worklog and neither can tell which line is whose, so
    the second is refused by name and nothing at all lands."""

    def opened_by_alpha(self, tmp: Path):
        use_sink(tmp)
        alpha = make_clone(tmp / "a", ALPHA)
        beta = make_clone(tmp / "b", BETA)
        run_cmd(alpha, "run-state", "testrun", "--note", "alpha opened it")
        return alpha, beta

    def assert_nothing_moved(self, identity: bytes, worklog: bytes):
        self.assertEqual(identity, identity_of().read_bytes())
        self.assertEqual(worklog, worklog_of().read_bytes())
        self.assertEqual(
            ["run.json", "worklog.md"],
            sorted(path.name for path in run_dir_of().iterdir()),
        )
        self.assertFalse((sink_root() / "tickets").exists())

    def test_a_different_origin_is_refused_by_name_and_nothing_lands(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _alpha, beta = self.opened_by_alpha(tmp)
            identity, worklog = identity_bytes(), worklog_of().read_bytes()
            payload = run_cmd(beta, "run-state", "testrun", "--note", "beta tried")
            self.assertNotIn("run_state", payload)
            self.assertIn("acme/alpha", payload["error"])
            self.assertIn("other/beta", payload["error"])
            self.assert_nothing_moved(identity, worklog)

    def test_the_refusal_blocks_an_artifact_too(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _alpha, beta = self.opened_by_alpha(tmp)
            identity, worklog = identity_bytes(), worklog_of().read_bytes()
            payload = run_cmd(
                beta, "run-state", "testrun", "--artifact", "beta.md", "--text", "x"
            )
            self.assertNotIn("run_state", payload)
            self.assertIn("acme/alpha", payload["error"])
            self.assert_nothing_moved(identity, worklog)

    def test_two_rootless_projects_still_collide(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            first = make_clone(tmp / "a", None)
            second = make_clone(tmp / "b", None)
            run_cmd(first, "run-state", "testrun", "--note", "a opened it")
            payload = run_cmd(second, "run-state", "testrun", "--note", "b tried")
            self.assertNotIn("run_state", payload)
            self.assertIn(str(first.resolve()), payload["error"])
            self.assertIn(str(second.resolve()), payload["error"])
            self.assertEqual([str(first.resolve())], workspaces_of())

    def test_one_rootless_project_still_appends(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            run_cmd(main, "run-state", "testrun", "--note", "from main")
            payload = run_cmd(worktree, "run-state", "testrun", "--note", "from the tree")
            self.assertNotIn("error", payload)
            self.assertEqual(2, len(workspaces_of()))

    def test_a_checkout_that_gained_a_remote_is_still_itself(self):
        """Identity falls back to the root whenever either side has no
        origin, so `git remote add` mid-run does not lock a project out of
        the run it opened."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            repo = make_clone(tmp / "repo", None)
            run_cmd(repo, "run-state", "testrun", "--note", "before the remote")
            (repo / ".git" / "config").write_text(
                GIT_CONFIG.format(remote="origin", url=ALPHA), encoding="utf-8"
            )
            payload = run_cmd(repo, "run-state", "testrun", "--note", "after the remote")
            self.assertNotIn("error", payload)
            # `project` is the first writer's and is never rewritten
            self.assertIsNone(identity_doc()["project"]["origin"])

    def test_an_unreadable_identity_is_refused_by_name_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            repo = make_clone(tmp / "repo", ALPHA)
            run_cmd(repo, "run-state", "testrun", "--note", "one")
            worklog = worklog_of().read_bytes()
            for corrupt in ("{ not json", '"a string, not an object"'):
                with self.subTest(corrupt):
                    identity_of().write_text(corrupt, encoding="utf-8")
                    payload = run_cmd(repo, "run-state", "testrun", "--note", "two")
                    self.assertNotIn("run_state", payload)
                    self.assertIn(str(identity_of()), payload["error"])
                    self.assertEqual(corrupt, identity_of().read_text(encoding="utf-8"))
                    self.assertEqual(worklog, worklog_of().read_bytes())


class TestNoFallback(unittest.TestCase):
    """rules/visibility.md §6: a write that cannot reach the resolved root
    fails loudly and lands nowhere — in particular not in the caller's own
    tree, which is the silent loss this channel exists to end."""

    @staticmethod
    def block_the_sink(tmp: Path) -> Path:
        """A sink root that cannot be created, on every platform.

        Its parent is a regular file, so `mkdir` raises `NotADirectoryError`
        rather than depending on a permission bit Windows does not have.
        """

        blocker = tmp / "not-a-directory"
        blocker.write_text("this is a file\n", encoding="utf-8")
        os.environ[STATE_HOME_ENV_VAR] = str(blocker / "state")
        return blocker

    @staticmethod
    def listing(root: Path) -> list:
        return sorted(str(path.relative_to(root)) for path in root.rglob("*"))

    def test_run_state_reports_and_lands_nowhere(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            repo = make_clone(tmp / "repo", ALPHA)
            (repo / "work.txt").write_text("payload\n", encoding="utf-8")
            blocker = self.block_the_sink(tmp)
            before = self.listing(repo)
            for args in (
                ("run-state", "testrun", "--note", "a line"),
                ("run-state", "testrun", "--artifact", "e.md", "--text", "bytes"),
            ):
                with self.subTest(args[2]):
                    completed = run_full(repo, *args)
                    # the script's convention: an error payload, and a
                    # nonzero exit carrying it out to the caller
                    self.assertEqual(1, completed.returncode, completed.stderr)
                    payload = json.loads(completed.stdout)
                    self.assertIn("error", payload)
                    self.assertNotIn("run_state", payload)
            self.assertEqual(before, self.listing(repo))
            self.assertFalse((repo / ".orch").exists())
            self.assertTrue(blocker.is_file())

    def test_every_ticket_writing_subcommand_reports_and_lands_nowhere(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            repo = make_clone(tmp / "repo", ALPHA)
            body = repo / "body.md"
            body.write_text("a result body\n", encoding="utf-8")
            self.block_the_sink(tmp)
            before = self.listing(repo)
            for args in (
                ("claim", "testrun", "T1", "--by", "agent-a"),
                ("set-status", "testrun", "T1", "complete"),
                ("result", "testrun", "T1", "--section", "Result", "--file", str(body)),
            ):
                with self.subTest(args[0]):
                    completed = run_full(repo, *args)
                    self.assertEqual(1, completed.returncode, completed.stderr)
                    self.assertIn("error", json.loads(completed.stdout))
            self.assertEqual(before, self.listing(repo))
            self.assertFalse((repo / ".orch").exists())


def improvement_of() -> Path:
    """The sink's improvement tree, wherever ``use_sink`` last pointed."""

    return sink_root() / "improvement"


def coverage_of() -> Path:
    return improvement_of() / "covered.jsonl"


def function_def(name: str):
    """One top-level function of ``scripts/tickets.py``, as its AST."""

    tree = ast.parse(TICKETS_PY.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"scripts/tickets.py declares no {name}")


def open_modes(node) -> list:
    """The mode every ``open(...)`` under ``node`` is called with."""

    modes = []
    for child in ast.walk(node):
        if not (isinstance(child, ast.Call) and isinstance(child.func, ast.Name)):
            continue
        if child.func.id != "open":
            continue
        mode = None
        if len(child.args) > 1 and isinstance(child.args[1], ast.Constant):
            mode = child.args[1].value
        for keyword in child.keywords:
            if keyword.arg == "mode" and isinstance(keyword.value, ast.Constant):
                mode = keyword.value.value
        modes.append(mode)
    return modes


def coverage_branch():
    """The statements of ``_cmd_improvement`` that write the coverage record.

    Found by the constant that names the record, never by position, so
    rearranging the function cannot quietly move what the case below reads.
    """

    smallest = None
    for node in ast.walk(function_def("_cmd_improvement")):
        if not isinstance(node, ast.If):
            continue
        for branch in (node.body, node.orelse):
            names_it = any(
                isinstance(sub, ast.Name) and sub.id == "COVERAGE_RECORD_NAME"
                for stmt in branch
                for sub in ast.walk(stmt)
            )
            if names_it and (smallest is None or len(branch) < len(smallest)):
                smallest = branch
    return smallest


class TestImprovementWriter(unittest.TestCase):
    """The improvement streams reach the sink through the installed script,
    the way run state does: `rules/visibility.md` §6 covers the coverage
    record and every proposal, and neither has any other channel."""

    def test_a_proposal_lands_whole_under_the_sink(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            body = "# proposal\n\nthe amendment, verbatim\n"
            self.assertFalse(improvement_of().exists())
            payload = run_cmd(tmp, "improvement", "--proposal", "amend-x.md", "--text", body)
            landed = improvement_of() / "proposals" / "amend-x.md"
            # assert the marker, then read past it: a script without the
            # subcommand reads as a failure here, never as a KeyError
            self.assertIn("improvement", payload, payload.get("error"))
            self.assertEqual("proposal", payload["improvement"]["mode"])
            self.assertEqual("amend-x.md", payload["improvement"]["name"])
            self.assertEqual(str(landed), payload["improvement"]["path"])
            self.assertTrue(Path(payload["improvement"]["path"]).is_absolute())
            # the parents did not exist a moment ago
            self.assertEqual(body, landed.read_text(encoding="utf-8"))
            self.assertEqual(body.encode("utf-8"), landed.read_bytes())

    def test_the_proposal_body_can_come_from_a_file_in_the_callers_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            workspace = tmp / "workspace"
            workspace.mkdir()
            source = workspace / "draft.md"
            source.write_text("read inside, written outside\n", encoding="utf-8")
            payload = run_cmd(
                workspace, "improvement", "--proposal", "draft.md", "--file", str(source)
            )
            self.assertIn("improvement", payload, payload.get("error"))
            self.assertEqual(
                "read inside, written outside\n",
                (improvement_of() / "proposals" / "draft.md").read_text(encoding="utf-8"),
            )
            # the workspace holds its own draft and nothing else
            self.assertEqual([source], sorted(workspace.rglob("*")))

    def test_a_covered_line_is_appended_and_every_earlier_line_survives(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            payload = run_cmd(tmp, "improvement", "--covered", '{"id": "f-1"}')
            self.assertIn("improvement", payload, payload.get("error"))
            self.assertEqual("covered", payload["improvement"]["mode"])
            self.assertIsNone(payload["improvement"]["name"])
            self.assertEqual(str(coverage_of()), payload["improvement"]["path"])
            before = coverage_of().read_bytes()
            with open(coverage_of(), "a", encoding="utf-8", newline="\n") as handle:
                handle.write('{"id": "f-2"}\n')
            run_cmd(tmp, "improvement", "--covered", '{"id": "f-3"}')
            self.assertEqual(
                ['{"id": "f-1"}', '{"id": "f-2"}', '{"id": "f-3"}'],
                coverage_of().read_text(encoding="utf-8").splitlines(),
            )
            self.assertEqual(before, coverage_of().read_bytes()[: len(before)])

    def test_ten_concurrent_writers_each_land_one_whole_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            lines = [f'{{"writer": {i}, "pad": "' + "x" * 2000 + '"}' for i in range(10)]
            with ThreadPoolExecutor(max_workers=10) as pool:
                payloads = list(
                    pool.map(
                        lambda line: run_cmd(tmp, "improvement", "--covered", line), lines
                    )
                )
            # A writer that reported an error and a writer whose line was lost
            # are two different defects, and the file check below reports the
            # second for both -- the payloads are the only place the first is
            # visible.
            self.assertEqual([], [p["error"] for p in payloads if "error" in p])
            self.assertTrue(coverage_of().is_file(), "no coverage record was written")
            self.assertEqual(
                sorted(lines), sorted(coverage_of().read_text(encoding="utf-8").splitlines())
            )

    def test_the_coverage_record_is_written_through_the_serialised_appender(self):
        """The guard against a lost line and against a later
        read-modify-write, read off the module itself.

        The branch opens nothing of its own. Every workspace on the machine
        appends to this one record, and a bare ``open(..., "a")`` is a seek
        and a write on Windows -- two writers take one offset and a whole
        line vanishes, which reads like a writer that never ran. So the
        branch calls ``_append_one_line``, the one place that append is
        serialised, and the mechanism is graded there by the instrument that
        grades the worklog's."""

        branch = coverage_branch()
        self.assertIsNotNone(
            branch, "no branch of _cmd_improvement names COVERAGE_RECORD_NAME"
        )
        self.assertEqual([], [mode for stmt in branch for mode in open_modes(stmt)])
        self.assertEqual(
            ["_append_one_line"],
            [
                sub.func.id
                for stmt in branch
                for sub in ast.walk(stmt)
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name)
            ],
            "the coverage record is appended through the serialised writer",
        )
        assert_one_append_open_and_no_read(
            self, inspect.getsource(tickets_mod._append_one_line), "_append_one_line"
        )
        # and that branch is the only place the record's path is composed
        loads = [
            node
            for node in ast.walk(ast.parse(TICKETS_PY.read_text(encoding="utf-8")))
            if isinstance(node, ast.Name)
            and node.id == "COVERAGE_RECORD_NAME"
            and isinstance(node.ctx, ast.Load)
        ]
        self.assertEqual(1, len(loads))

    def test_an_unsafe_proposal_name_is_refused_by_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            for bad in ("../escape.md", "a/b.md", "a\\b.md", "..", "."):
                with self.subTest(bad):
                    payload = run_cmd(tmp, "improvement", "--proposal", bad, "--text", "x")
                    self.assertIn("unsafe proposal name", payload.get("error", ""))
                    self.assertIn(f"'{bad}'", payload.get("error", ""))
                    self.assertNotIn("improvement", payload)
            self.assertFalse(improvement_of().exists())

    def test_a_malformed_invocation_is_refused_by_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            cases = {
                "both modes": (
                    ("improvement", "--proposal", "p.md", "--covered", "line"),
                    "one of --proposal",
                ),
                "neither mode": (("improvement",), "one of --proposal"),
                "no body": (("improvement", "--proposal", "p.md"), "one of --file"),
                "both bodies": (
                    ("improvement", "--proposal", "p.md", "--text", "x", "--file", "f"),
                    "one of --file",
                ),
                "a body for a covered line": (
                    ("improvement", "--covered", "line", "--text", "x"),
                    "--covered carries its own line",
                ),
                "an unreadable body file": (
                    ("improvement", "--proposal", "p.md", "--file", str(tmp / "absent.md")),
                    "unreadable body file",
                ),
                "a positional argument": (
                    ("improvement", "stray", "--covered", "line"),
                    "no positional argument",
                ),
                "an unknown flag": (
                    ("improvement", "--covered", "line", "--force"),
                    "does not accept --force",
                ),
            }
            for label, (args, expected) in cases.items():
                with self.subTest(label):
                    completed = run_full(tmp, *args)
                    self.assertEqual(1, completed.returncode, completed.stderr)
                    payload = json.loads(completed.stdout)
                    self.assertIn(expected, payload.get("error", ""))
                    self.assertNotIn("improvement", payload)
            self.assertFalse(improvement_of().exists())

    def test_neither_mode_falls_back_into_the_callers_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            workspace = tmp / "workspace"
            workspace.mkdir()
            (workspace / "work.txt").write_text("payload\n", encoding="utf-8")
            blocker = TestNoFallback.block_the_sink(tmp)
            before = TestNoFallback.listing(workspace)
            for args in (
                ("improvement", "--proposal", "p.md", "--text", "a body"),
                ("improvement", "--covered", '{"id": "f-1"}'),
            ):
                with self.subTest(args[1]):
                    completed = run_full(workspace, *args)
                    # the script's convention: an error payload, and a
                    # nonzero exit carrying it out to the caller
                    self.assertEqual(1, completed.returncode, completed.stderr)
                    payload = json.loads(completed.stdout)
                    # the refusal is about the sink it could not reach, so a
                    # script that simply has no such subcommand fails here
                    self.assertIn("unwritable improvement record", payload.get("error", ""))
                    self.assertNotIn("improvement", payload)
            self.assertEqual(before, TestNoFallback.listing(workspace))
            self.assertFalse((workspace / ".orch").exists())
            self.assertTrue(blocker.is_file())

    def test_the_subcommand_is_named_where_a_caller_looks(self):
        with tempfile.TemporaryDirectory() as tmp:
            use_sink(Path(tmp))
            payload = run_cmd(Path(tmp))
            self.assertIn("improvement", payload["error"])
        self.assertIn("Subcommands:", tickets_mod.__doc__)
        listed = tickets_mod.__doc__.partition("Subcommands:")[2]
        self.assertIn("improvement --proposal <name> (--file <path> | --text <string>)", listed)
        self.assertIn("improvement --covered <line>", listed)
class ExitConventionTest(unittest.TestCase):
    """Pin the exit convention: exit 1 when JSON has 'error', exit 0 otherwise."""

    def test_error_exits_1(self):
        """An error path exits with code 1."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, {})
            result = run_full(tmp, "result", "no-run", "no-id", "--section", "Result", "--text", "x")
            self.assertIn("error", result.stdout)
            self.assertEqual(1, result.returncode)

    def test_success_exits_0_list(self):
        """A success path exits with code 0: list subcommand."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, {"T1": ("ready", "[]")})
            result = run_full(tmp, "list")
            payload = json.loads(result.stdout)
            self.assertNotIn("error", payload)
            self.assertEqual(0, result.returncode)

    def test_success_exits_0_ready(self):
        """A success path exits with code 0: ready subcommand."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, {"T1": ("ready", "[]")})
            result = run_full(tmp, "ready")
            payload = json.loads(result.stdout)
            self.assertNotIn("error", payload)
            self.assertEqual(0, result.returncode)

    def test_error_exits_1_claim(self):
        """An error path exits with code 1: claim on non-ready ticket."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, {"T1": ("complete", "[]")})
            result = run_full(tmp, "claim", "testrun", "T1", "--by", "test")
            payload = json.loads(result.stdout)
            self.assertIn("error", payload)
            self.assertEqual(1, result.returncode)

    def test_error_exits_1_set_status_invalid(self):
        """An error path exits with code 1: invalid status."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, {"T1": ("ready", "[]")})
            result = run_full(tmp, "set-status", "testrun", "T1", "invalid-status")
            payload = json.loads(result.stdout)
            self.assertIn("error", payload)
            self.assertEqual(1, result.returncode)

    def test_error_exits_1_missing_subcommand(self):
        """An error path exits with code 1: missing subcommand."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, {})
            result = run_full(tmp)
            payload = json.loads(result.stdout)
            self.assertIn("error", payload)
            self.assertEqual(1, result.returncode)


class DocstringHonestyTest(unittest.TestCase):
    """Assert the module docstring does not claim exit 0 on failure."""

    def test_docstring_does_not_claim_exit_0_on_failure(self):
        """The docstring should not claim 'never as a non-zero exit'."""
        docstring = tickets_mod.__doc__ or ""
        self.assertNotIn("never as a non-zero exit", docstring)


def dispatch_subcommands() -> list:
    """Every name ``_dispatch`` accepts, read off its own comparisons.

    The loop below has to be total over the subcommands that exist, not
    over a list a reader kept in step by hand: a subcommand added to the
    dispatcher and forgotten here would be exactly the one whose ``--help``
    still errors.
    """

    found = []
    for node in ast.walk(ast.parse(inspect.getsource(tickets_mod._dispatch))):
        if not isinstance(node, ast.Compare):
            continue
        if not (isinstance(node.left, ast.Name) and node.left.id == "command"):
            continue
        for comparator in node.comparators:
            if isinstance(comparator, ast.Constant) and isinstance(comparator.value, str):
                found.append(comparator.value)
            elif isinstance(comparator, (ast.Tuple, ast.List, ast.Set)):
                found.extend(
                    element.value
                    for element in comparator.elts
                    if isinstance(element, ast.Constant)
                    and isinstance(element.value, str)
                )
    return found


class HelpTest(unittest.TestCase):
    """`--help` is a request this script answers, never an unhandled case it
    renders as the ordinary error path: exit 0 and usage on stdout, at the
    top level and for every subcommand the dispatcher accepts."""

    def test_the_subcommand_list_is_not_empty_and_excludes_help_flags(self):
        subcommands = dispatch_subcommands()
        self.assertGreaterEqual(len(subcommands), 7, subcommands)
        for flag in ("--help", "-h"):
            self.assertNotIn(flag, subcommands)

    def test_bare_help_exits_0_with_usage_on_stdout(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, {})
            for flag in ("--help", "-h", "help"):
                result = run_full(tmp, flag)
                self.assertEqual(0, result.returncode, f"{flag}: {result.stdout}")
                self.assertTrue(result.stdout.strip(), flag)
                payload = json.loads(result.stdout)
                self.assertNotIn("error", payload)
                # the top-level answer names every subcommand it dispatches
                for subcommand in dispatch_subcommands():
                    self.assertIn(subcommand, result.stdout, f"{flag}: {subcommand}")

    def test_every_subcommand_help_exits_0_with_non_empty_stdout(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, {})
            for subcommand in dispatch_subcommands():
                for flag in ("--help", "-h"):
                    result = run_full(tmp, subcommand, flag)
                    self.assertEqual(
                        0, result.returncode, f"{subcommand} {flag}: {result.stdout}"
                    )
                    self.assertTrue(result.stdout.strip(), f"{subcommand} {flag}")
                    payload = json.loads(result.stdout)
                    self.assertNotIn("error", payload, f"{subcommand} {flag}")
                    self.assertIn(subcommand, result.stdout, f"{subcommand} {flag}")

    def test_help_never_touches_the_repository(self):
        """Usage is answered before any argument is resolved: `--help` on a
        subcommand whose required arguments are absent still answers, and
        outside a repository entirely it answers the same way."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)  # deliberately no .git anywhere under this tempdir
            for argv in (["--help"], ["claim", "--help"], ["run-state", "--help"]):
                result = run_full(tmp, *argv)
                self.assertEqual(0, result.returncode, f"{argv}: {result.stdout}")
                self.assertNotIn("error", json.loads(result.stdout), argv)

    def test_a_help_flag_taken_as_a_flag_value_is_not_a_help_request(self):
        """`--note --help` writes the note `--help`; only a help flag standing
        as its own token asks for usage. A run-state note whose text happens to
        be a help flag must not be silently swallowed into a usage answer."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            result = run_main(worktree, "run-state", "testrun", "--note", "--help")
            self.assertEqual(0, result.returncode, result.stdout)
            payload = json.loads(result.stdout)
            self.assertNotIn("help", payload)
            self.assertEqual("note", payload["run_state"]["mode"])
            self.assertEqual("--help\n", worklog_of().read_text(encoding="utf-8"))

    def test_the_usage_table_covers_exactly_the_dispatched_subcommands(self):
        self.assertEqual(
            sorted(dispatch_subcommands()),
            sorted(tickets_mod.SUBCOMMAND_USAGE),
        )


if __name__ == "__main__":
    unittest.main()
