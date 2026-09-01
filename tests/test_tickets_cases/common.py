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

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.state_root as state_root  # noqa: E402
import scripts.tickets as tickets_mod  # noqa: E402

TICKETS_PY = ROOT / "scripts" / "tickets.py"


def support_names() -> tuple:
    """The flat ticket family, named the way `install.py` names it.

    `discover_script_names` copies every `scripts/*.py` whose stem starts
    with a `SCRIPT_SUPPORT_PREFIXES` entry and an underscore, sorted, minus
    the entrypoints; for this family that is exactly `tickets_*.py`, and the
    `tickets.py` facade is an entrypoint the pattern cannot match. Read at
    call time, so a module added beside the facade joins the installed-copy
    fixtures without an edit here.
    """

    return tuple(
        sorted(path.name for path in TICKETS_PY.parent.glob("tickets_*.py"))
    )


TICKETS_SUPPORT_NAMES = support_names()
TICKETS_MODULES = (TICKETS_PY,) + tuple(
    TICKETS_PY.with_name(name) for name in TICKETS_SUPPORT_NAMES
)
TICKETS_DISPATCH_PY = TICKETS_PY.with_name("tickets_dispatch.py")
STATE_HOME_ENV_VAR = state_root.ENV_VAR

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
    """Point the sink env var at a sink under this test's tempdir.

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


def git_available() -> bool:
    try:
        return subprocess.run(
            ["git", "--version"], capture_output=True, text=True
        ).returncode == 0
    except OSError:
        return False


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


def backdate(path: Path, minutes: int) -> None:
    """Move one file's mtime ``minutes`` into the past.

    A fixture that writes a ticket has just written it, so on disk that
    ticket is moving now. Every case that means "nothing has moved" has to
    say so, which is what this says.
    """

    when = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).timestamp()
    os.utime(path, (when, when))


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


def run_dir_of(run: str = "testrun") -> Path:
    return sink_root() / "runs" / run


def tree_dir_of(tree: str, run: str = "testrun") -> Path:
    """One run's directory in a named run-state tree of the sink.

    ``runs`` is the default tree, so ``tree_dir_of("runs")`` and
    ``run_dir_of()`` are the same path by construction.
    """

    return sink_root() / tree / run


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


# --- run identity fixtures ---------------------------------------------

GIT_CONFIG = (
    "[core]\n\trepositoryformatversion = 0\n"
    '[remote "{remote}"]\n\turl = {url}\n'
    "\tfetch = +refs/heads/*:refs/remotes/{remote}/*\n"
)
ALPHA = "https://example.invalid/acme/alpha.git"
BETA = "https://example.invalid/other/beta.git"
STAMP_RE = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"


def notes_of(run: str = "testrun") -> Path:
    """`run-state --note`'s target: the run's free notes, beside the
    rendered view and never it (contracts/worklog.md)."""
    return sink_root() / "runs" / run / tickets_mod.RUN_NOTES_NAME
