#!/usr/bin/env python3
"""Friction logger. Stdlib-only, cross-platform (Windows + POSIX).

Reliability bar: this script must NEVER block, prompt, raise, or exit
non-zero, no matter what. Every code path funnels through ``main``'s
broad ``except Exception`` so an internal failure is silent and the
process still exits 0. Prints exactly one line, ``friction logged``, on
success; nothing on failure.

The one wait it ever takes is the append lock's retry budget: nothing at
all on POSIX, and on a contended Windows append a bounded half second
that ends in the write either way. See ``_acquire_append_lock``.

Usage:
    python friction.py "<observed>" "<expected>" [--category C]
        [--skill S] [--ticket T] [--run R]

Log location: ``<sink>/friction/<YYYY-MM>.jsonl``, where the sink is the
one user-scope root ``scripts/state_root.py`` resolves —
``$ORCHFLOWS_STATE_HOME`` or ``~/.orchflows/state``. One stream for
every repository; the project an entry arose in is a field on the entry,
never its location. There is no fallback: a write that cannot reach that
root lands nowhere, silently, per the bar above.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:  # Windows only; POSIX append needs no lock. See _acquire_append_lock.
    import msvcrt
except ImportError:
    msvcrt = None

FLAG_MAP = {
    "--category": "category",
    "--skill": "skill",
    "--ticket": "ticket",
    "--run": "run",
}
SESSION_ENV_VARS = (
    "CLAUDE_SESSION_ID",
    "CLAUDE_CODE_SESSION_ID",
    "CODEX_SESSION_ID",
    "SESSION_ID",
)
GIT_REV_TIMEOUT_SECONDS = 2
# Half the one-second ceiling this logger is held to, so the ceiling still
# holds on a loaded machine once the last retry's sleep is counted in.
APPEND_LOCK_BUDGET_SECONDS = 0.5
APPEND_LOCK_RETRY_SECONDS = 0.01
# What `project_source` may say: which of the three questions below
# actually answered "which project". Named so a reader of the stream and
# `_provenance` cannot drift on the vocabulary.
SOURCE_RUN = "run"
SOURCE_CWD = "cwd"
SOURCE_NONE = "none"


def _parse_args(argv):
    """Return (observed, expected, options) or None when argv is malformed."""

    positional = []
    options = {"category": None, "skill": None, "ticket": None, "run": None}
    i = 0
    while i < len(argv):
        token = argv[i]
        if token in FLAG_MAP:
            i += 1
            if i >= len(argv):
                return None
            options[FLAG_MAP[token]] = argv[i]
        elif "=" in token and token.split("=", 1)[0] in FLAG_MAP:
            key, _, value = token.partition("=")
            options[FLAG_MAP[key]] = value
        else:
            positional.append(token)
        i += 1
    if len(positional) != 2:
        return None
    return positional[0], positional[1], options


def _state_root():
    """Import the one resolver, here rather than at module scope.

    rules/visibility.md §3: ``scripts/state_root.py`` owns the sink root,
    and this script holds no second copy of it. The import sits inside a
    function because the reliability bar above is absolute — a module-level
    import that failed (a partial install with no ``state_root.py`` beside
    this file) would traceback before ``main`` existed to swallow it, and
    the logger would exit non-zero. From here, ``main``'s broad ``except``
    still catches it.
    """

    try:  # in-repo; the installed copy sits flat beside state_root.py
        from scripts import state_root
    except ImportError:  # pragma: no cover - the installed copy's path
        import state_root
    return state_root


def _identity_module():
    """Import the owner of project identity, guarded and here, not at module scope.

    ``scripts/tickets.py`` owns what a project *is* and which sink layout a
    record is written under. This script holds no second copy of either
    rule; it calls them. The import is deferred and guarded for the same
    reason ``_state_root``'s is: a partial install with no sibling beside
    this file must cost the fields that sibling feeds, never the entry.
    """

    try:  # in-repo; the installed copy sits flat beside tickets.py
        from scripts import tickets
    except ImportError:  # pragma: no cover - the installed copy's path
        import tickets
    return tickets


def _unattributed():
    """The provenance fields when nothing about the caller resolved.

    Not an error. The entry still lands, and ``project_source: "none"``
    is the entry saying so, so a reader grouping by project sees its own
    group rather than mistaking it for someone else's.
    """

    return {
        "project": None,
        "project_source": SOURCE_NONE,
        "workspace": None,
        "sink_convention": None,
    }


def _recorded_project(run, identity):
    """The project ``run`` already belongs to, read from the sink, or ``None``.

    A run's identity document is the only place that answer can come from,
    so an entry filed against a run from anywhere reads as that run's
    project. A run the sink does not hold, a document that does not parse,
    and a document carrying no project all answer ``None`` — each falls
    through to the caller's own repository, which is a weaker answer to
    the same question, never a different one.
    """

    if not run:
        return None
    path = _state_root().runs_root() / run / identity.RUN_IDENTITY_NAME
    document, error = identity._read_identity(path)
    if error is not None or not isinstance(document, dict):
        return None
    project = document.get("project")
    return project if isinstance(project, dict) else None


def _in_a_repository():
    """Whether the caller is standing in a checkout at all."""

    try:
        return _state_root().find_repo_root(Path.cwd().resolve()) is not None
    except Exception:
        return False


def _provenance(options):
    """Which project this entry arose in, from where, and under which layout.

    Precedence, and what each guard costs when it trips:

    1. ``--run`` naming a run the sink already holds -> that run's own
       recorded project, ``project_source: "run"``.
    2. Otherwise the repository the caller stands in ->
       ``project_source: "cwd"``.
    3. Otherwise ``project: null``, ``project_source: "none"``.

    Every resolution sits in its own guard, so an unreachable sibling, a
    corrupt identity document or an unreadable ``.git/config`` costs the
    field it feeds and never the entry.
    """

    fields = _unattributed()
    try:
        identity = _identity_module()
    except Exception:
        return fields
    fields["sink_convention"] = getattr(identity, "SINK_CONVENTION", None)

    try:
        # One call for both halves: the project the caller belongs to, and
        # the workspace it is standing in. They differ in a linked worktree,
        # which is exactly what `workspace` is here to record.
        standing_in, workspace = identity._writer_identity()
        fields["workspace"] = workspace
    except Exception:
        standing_in = None

    try:
        recorded = _recorded_project(options.get("run"), identity)
    except Exception:
        recorded = None
    if recorded is not None:
        fields["project"] = recorded
        fields["project_source"] = SOURCE_RUN
        return fields

    # Outside any repository `_writer_identity` still names a project, so
    # that a run written from nowhere has an owner to collide on. An entry
    # has nothing to collide on and genuinely arose in no project, so that
    # answer is dropped here rather than recorded. The rule for what a
    # project *is* stays item 03's, untouched.
    if standing_in is not None and _in_a_repository():
        fields["project"] = standing_in
        fields["project_source"] = SOURCE_CWD
    return fields


def _git_rev(cwd: Path):
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(cwd),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=GIT_REV_TIMEOUT_SECONDS,
        )
        if result.returncode == 0:
            rev = result.stdout.decode("utf-8", errors="replace").strip()
            return rev or None
    except Exception:
        pass
    return None


def _detect_host():
    env = os.environ
    if env.get("CLAUDECODE") or any(key.startswith("CLAUDE_") for key in env):
        return "claude-code"
    if any(key.startswith("CODEX_") for key in env):
        return "codex"
    return "unknown"


def _detect_session():
    for var in SESSION_ENV_VARS:
        value = os.environ.get(var)
        if value:
            return value
    return None


def _target_path(now: datetime):
    stamp = now.strftime("%Y-%m")
    return _state_root().friction_root() / f"{stamp}.jsonl"


def _build_entry(observed, expected, options, now: datetime):
    """One entry. Key order is the order a reader should meet the fields in.

    ``sink_convention`` first because it says how to read the rest; then
    the four that answer *where this came from*, cwd being the literal
    directory and the other three the identity of it; then the fields the
    caller supplied.
    """

    try:
        provenance = _provenance(options)
    except Exception:
        # `_provenance` guards every resolution it makes, so reaching here
        # means the guards themselves broke. Even that costs four fields
        # and not the entry.
        provenance = _unattributed()
    return {
        "sink_convention": provenance.get("sink_convention"),
        "ts": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cwd": str(Path.cwd()),
        "workspace": provenance.get("workspace"),
        "project": provenance.get("project"),
        "project_source": provenance.get("project_source", SOURCE_NONE),
        "git_rev": _git_rev(Path.cwd()),
        "host": _detect_host(),
        "session": _detect_session(),
        "category": options.get("category") or "uncategorized",
        "skill": options.get("skill"),
        "ticket": options.get("ticket"),
        "run": options.get("run"),
        "observed": observed,
        "expected": expected,
    }


def _acquire_append_lock(handle):
    """Try for the byte-zero append lock. Never blocks on it, never fails for
    want of it; returns whether it was taken.

    Windows has no atomic append. The CRT emulates it with a seek and then a
    write, so two appenders take the same offset and one whole line vanishes --
    the same defect ``scripts/tickets.py:_append_one_line`` documents, and this
    file was the source of the unlocked idiom it fixed. POSIX ``O_APPEND``
    places the write at end-of-file in one step, so there is nothing to lock
    there and this is a no-op.

    ``LK_NBLCK``, not the ``LK_LOCK`` tickets.py takes: ``LK_LOCK`` blocks for
    about ten seconds and *then* raises, and ``rules/improvement.md`` §1 says
    this logger never blocks and never fails. ``LK_NBLCK`` returns at once, so
    the wait is this budget and nothing longer -- under a second, below a plain
    ``open()`` on a slow filesystem. A budget that runs out returns False and
    the caller writes anyway: that degrades to the unlocked append this
    replaced, never to a lost log line.
    """

    if msvcrt is None:
        return False
    deadline = time.monotonic() + APPEND_LOCK_BUDGET_SECONDS
    while True:
        try:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            return True
        except Exception:
            if time.monotonic() + APPEND_LOCK_RETRY_SECONDS >= deadline:
                return False
            time.sleep(APPEND_LOCK_RETRY_SECONDS)


def _append_line(path: Path, line: str) -> None:
    """Append one whole line, serialised where the platform does not do it."""

    with open(path, "a", encoding="utf-8", newline="\n") as handle:
        acquired = _acquire_append_lock(handle)
        try:
            handle.write(line)
            handle.flush()
        finally:
            if acquired:
                try:
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                except Exception:
                    pass


def _run(argv):
    parsed = _parse_args(argv)
    if parsed is None:
        return False
    observed, expected, options = parsed
    now = datetime.now(timezone.utc)
    entry = _build_entry(observed, expected, options, now)
    path = _target_path(now)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(entry, ensure_ascii=False) + "\n"
    _append_line(path, line)
    return True


def main(argv=None):
    try:
        if _run(sys.argv[1:] if argv is None else argv):
            print("friction logged")
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
