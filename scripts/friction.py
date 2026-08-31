#!/usr/bin/env python3
"""Friction logger. Stdlib-only, cross-platform (Windows + POSIX).

Reliability bar: this script must NEVER block, prompt, or raise. It exits
non-zero for malformed argv, refused at parse before anything is written;
an internal failure still exits 0 but names itself on stderr. Prints exactly
one line, ``friction logged``, on success, and one line on stderr otherwise.

Refusing malformed argv gives ``templates/host-block.md``'s manual append
remedy a readable trigger. A removed or unknown option is ordinary malformed
argv and is refused without writing.

The one wait it ever takes is the append lock's retry budget: nothing at
all on POSIX, and on a contended Windows append a bounded half second
that ends in the write either way. See ``_acquire_append_lock``.

Usage:
    python friction.py "<observed>" "<expected>"
        [--skill S] [--ticket T] [--run R]

``--run`` is an override, not the only route to the field: absent, the run
is resolved mechanically -- ``$ORCHFLOWS_RUN``, else the candidate
workspace the caller is standing in. See ``_resolved_run``.

Log location: ``<sink>/friction/<YYYY-MM>.jsonl``, where the sink is the
one user-scope root ``scripts/state_root.py`` resolves —
``$ORCHFLOWS_STATE_HOME`` or ``~/.orchflows/state``. One stream for
every repository; the project an entry arose in is a field on the entry,
never its location. There is no fallback: a write that cannot reach that
root lands nowhere, and says so on stderr, per the bar above.
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
    "--skill": "skill",
    "--ticket": "ticket",
    "--run": "run",
}
# The one non-zero exit, kept off 0 and off 1: 2 is the usage-error code
# argparse itself uses, so a caller reading exit codes rather than stderr
# still reads "you called it wrong" and not "the log failed".
USAGE_EXIT = 2
# The run a host declares for the process it launched. Read only when the
# caller named none, so an explicit --run always wins.
RUN_ENV_VAR = "ORCHFLOWS_RUN"
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


class _UsageError(Exception):
    """A call this logger refuses. Raised before any write, and the only
    exception ``main`` lets past its broad swallow."""


def _parse_args(argv):
    """Return (observed, expected, options), or raise ``_UsageError``."""

    positional = []
    options = {"skill": None, "ticket": None, "run": None}
    i = 0
    while i < len(argv):
        token = argv[i]
        if token in FLAG_MAP:
            i += 1
            if i >= len(argv):
                raise _UsageError(
                    "friction.py: {0} needs a value; nothing followed it".format(token)
                )
            if argv[i].startswith('-'):
                raise _UsageError(
                    "friction.py: {0} needs a value; got option-shaped token {1}".format(token, argv[i])
                )
            options[FLAG_MAP[token]] = argv[i]
        elif "=" in token and token.split("=", 1)[0] in FLAG_MAP:
            key, _, value = token.partition("=")
            if not value or value.startswith('-'):
                raise _UsageError("friction.py: {0} needs a non-option value".format(key))
            options[FLAG_MAP[key]] = value
        elif token.startswith('-'):
            raise _UsageError(
                "friction.py: expected two positional arguments; unknown option {0}; known flags: {1}".format(
                    token, ", ".join(sorted(FLAG_MAP))
                )
            )
        else:
            positional.append(token)
        i += 1
    if len(positional) != 2:
        raise _UsageError(
            'friction.py: expected two positional arguments, "<observed>" '
            '"<expected>"; read {0} (an unknown flag counts as one). Known '
            "flags: {1}".format(len(positional), ", ".join(sorted(FLAG_MAP)))
        )
    return positional[0], positional[1], options


def _console():
    """Import the console discipline, here rather than at module scope.

    The same bar ``_state_root`` records, and for the same reason: nothing
    outside the standard library may run while this module is imported, so
    a partial install with no ``console.py`` beside this file costs the
    UTF-8 console and never the line this logger exists to append.
    """

    try:  # in-repo; the installed copy sits flat beside console.py
        from scripts import console
    except ImportError:  # pragma: no cover - the installed copy's path
        import console
    return console


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


def _resolved_run(options):
    """Which run this entry belongs to. Never raises, never blocks.

    Every entry of 2026-08-30 carried ``run: null`` because the flag was
    the only route to the field and no caller passed it, which left a
    whole day of friction unqueryable by the run that produced it. So the
    flag becomes an override over a mechanical answer, in this order:

    1. ``--run`` -- the caller said so, and nothing outranks that.
    2. ``$ORCHFLOWS_RUN`` -- the host declared it for this process.
    3. The candidate workspace the caller is standing in. Which run's
       tree a path is comes from ``state_root.candidate_identity``, the
       inverse of the one derivation that placed it; the answer counts
       only when the sink still holds that item's ticket, so a stale or
       hand-made directory under the worktrees root names no run.

    Nothing else resolves to a run. An unresolved run is ``null``, as it
    has always been: this widens the field's coverage and never guesses.
    """

    named = options.get("run")
    if named:
        return named
    declared = os.environ.get(RUN_ENV_VAR, "").strip()
    if declared:
        return declared
    try:
        root = _state_root()
        identity = root.candidate_identity(Path.cwd())
        if not identity:
            return None
        ticket = root.tickets_root() / identity["run"] / "{0}.md".format(identity["id"])
        return identity["run"] if ticket.is_file() else None
    except Exception:
        return None


def _in_a_repository():
    """Whether the caller is standing in a checkout at all."""

    try:
        return _state_root().find_repo_root(Path.cwd().resolve()) is not None
    except Exception:
        return False


def _provenance(options):
    """Which project this entry arose in, from where, and under which layout.

    Precedence, and what each guard costs when it trips:

    1. The resolved run (``_resolved_run``) naming a run the sink already
       holds -> that run's own recorded project, ``project_source: "run"``.
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
    observed, expected, options = _parse_args(argv)
    # Before `_build_entry`, so the provenance lookup and the recorded
    # field read the same run. Guarded here as well as inside, on the bar
    # this file is held to: resolving a run may cost the field, never the
    # entry.
    try:
        options["run"] = _resolved_run(options)
    except Exception:
        pass
    now = datetime.now(timezone.utc)
    entry = _build_entry(observed, expected, options, now)
    path = _target_path(now)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(entry, ensure_ascii=False) + "\n"
    _append_line(path, line)


def main(argv=None):
    try:
        _console().harden()
    except Exception:  # pragma: no cover - the console is not the log
        pass
    try:
        _run(sys.argv[1:] if argv is None else argv)
        print("friction logged")
    except _UsageError as exc:
        print(str(exc), file=sys.stderr)
        return USAGE_EXIT
    except Exception as exc:
        # Still exit 0 -- the bar -- but not silently: the host block's
        # "append the line by hand whenever the logger cannot run" needs
        # something to trigger on, and the absence of `friction logged` is
        # not it. One line, the cause named, never a traceback.
        print("friction.py: not logged: {0}".format(exc), file=sys.stderr)
    return 0


def _guarded(argv):
    """``main`` under the console's discipline wherever there is one."""

    try:
        console = _console()
    except ImportError:  # pragma: no cover - a partial install
        return main(argv)
    return console.run(main, argv)


if __name__ == "__main__":
    raise SystemExit(_guarded(sys.argv[1:]))
