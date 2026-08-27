#!/usr/bin/env python3
"""Observe and grade one work item's isolated workspace.

Stdlib-only, cross-platform, Python 3.9 and up, no network at run time.
The ticket is the work item of ``contracts/work-item.md``: ``start``,
run from inside a workspace, records the lifecycle stamps
``workspace_branch`` and ``workspace_baseline`` into the main-root
ticket's frontmatter; ``check`` grades the item's ``isolation``
declaration at the join from the integrating checkout's git -- the
caller's own, or the one ``--repo`` names. A script observes and
grades — it never creates, enters or removes a workspace, and ``start``
never claims.

Deviation from ``scripts/tickets.py``, stated because a caller reads
these exit codes: this script does not inherit that script's exit-0
convention. ``tickets.py`` exits 0 for every outcome and reports failure
inside its JSON payload; ``workspace.py`` returns a real exit code per
failure mode, and every ``tickets.py`` call it makes is graded by parsing
the returned payload, never by exit status.

Exit codes:
    0  success, including ``isolation: none`` or absent
    1  usage or internal error
    2  isolation-missing
    3  wrong-branch-point
    4  dirty-candidate
    5  no-record
    6  wrong-vantage: the caller stood in the workspace it asked about, so
       nothing about the item was graded. Distinct from 2 on purpose -- 2
       says the item failed, 6 says the question was asked from the wrong
       place, and an integrator that reads one as the other rejects intact
       work.
    7  shared-workspace: another claimed item of the run recorded this same
       tree, so it is not this item's alone. ``start`` records before it
       flags: the join must still read what the item was executed in.

Subcommands:
    start <run> <id>
    check <run> <id> --base <rev> [--repo <path>]

``--repo <path>`` aims ``check`` at another checkout: every git call and the
repository root both come from there, so the caller need not stand where the
answer lives.

``--help``, on the script or on either subcommand, prints usage on stdout
and exits 0. It is the one call whose stdout is not a JSON payload: the
caller asking what the arguments are is a reader, and answering a reader
with an error payload is how this script used to answer.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# ``workspace.py`` and ``tickets.py`` are siblings in ``scripts/`` and again
# in ``bin_dir`` after ``install.py`` copies them, so a plain sibling import
# is the only shape that works in both layouts. Appended, never prepended,
# for the reason ``scripts/ui.py`` records: this directory also holds
# ``trace.py``, which at sys.path[0] would shadow the stdlib ``trace``
# module for the whole process.
_SIBLING_DIR = str(Path(__file__).resolve().parent)
if _SIBLING_DIR not in sys.path:
    sys.path.append(_SIBLING_DIR)

import state_root  # noqa: E402  the sink resolver, imported and never copied
import tickets  # noqa: E402  frontmatter and isolation, imported and never copied

# Literal sibling imports work in the source tree and in the flat installed
# ``bin`` layout after the directory above has joined ``sys.path``.
workspace_git = __import__("workspace_git")
workspace_prepare = __import__("workspace_prepare")
ISOLATION_KEY = "isolation"
BRANCH_KEY = "workspace_branch"
BASELINE_KEY = "workspace_baseline"
# Every frontmatter key name this script writes or reads, and where. The
# spellings belong to ``contracts/work-item.md``; ``tests/test_workspace.py``
# reads this mapping and the contract's own bytes and asserts the two agree
# in both directions, so a key cannot be spelled one way here and another
# way there behind a green suite.
FRONTMATTER_KEYS = {
    ISOLATION_KEY: "read by check",
    BRANCH_KEY: "written by start, read by check",
    BASELINE_KEY: "written by start",
}

# The value and its normalization both come from ``tickets.py``, never a
# second spelling here: that script emits the establishment step off this
# same declaration, and a grader reading it differently skips the grade at
# exit 0 while the join reads success.
REQUIRED = tickets.REQUIRED_ISOLATION
EXIT_OK = 0
EXIT_ERROR = 1
EXIT_ISOLATION_MISSING = 2
EXIT_WRONG_BRANCH_POINT = 3
EXIT_SCOPE_BREACH = 4
EXIT_NO_RECORD = 5
EXIT_WRONG_VANTAGE = 6
EXIT_SHARED_WORKSPACE = 7
VERDICTS = {
    EXIT_OK: "pass",
    EXIT_ERROR: "error",
    EXIT_ISOLATION_MISSING: "isolation-missing",
    EXIT_WRONG_BRANCH_POINT: "wrong-branch-point",
    EXIT_SCOPE_BREACH: "dirty-candidate",
    EXIT_NO_RECORD: "no-record",
    EXIT_WRONG_VANTAGE: "wrong-vantage",
    EXIT_SHARED_WORKSPACE: "shared-workspace",
}
AMBIGUOUS = workspace_git.AMBIGUOUS
# Candidate diffs are reported in full. Suggested files are not read here.
# One spelling of each subcommand's arguments, joined into ``USAGE`` for the
# refusals and printed alone for ``<sub> --help``. Two spellings would drift.
COMMAND_USAGE = {
    "start": "workspace.py start <run> <id>",
    "check": "workspace.py check <run> <id> --base <rev> [--repo <path>]",
}
COMMAND_HELP = {
    "start": "from inside the workspace: record its branch and baseline into the ticket",
    "check": "from the integrating checkout: grade isolation and report the actual diff",
}
USAGE = "usage: " + "\n       ".join(COMMAND_USAGE.values())
HELP_FLAGS = ("--help", "-h")
Refused = workspace_git.Refused


# --- git, in the tree under grade -------------------------------------------


# The checkout every ``_git`` call runs in. ``None`` -- the caller's own tree,
# and subprocess's own default, so an unaimed call is what it always was. Set
# once by ``check --repo`` before its first git call and never after: a grade
# whose facts came from two checkouts is not a grade.
_GIT_CWD = None


def _git(*args: str):
    """Run git in the tree under grade: the caller's own, or ``--repo``'s."""

    return workspace_git._git(_GIT_CWD, *args)


def _git_out(*args: str) -> str:
    code, out, err = _git(*args)
    if code != 0:
        raise Refused(f"git {' '.join(args)}: {err.strip()}")
    return out.strip()


def _dirty_paths() -> list:
    """``workspace_git._dirty_paths``, in the tree under grade."""
    return workspace_git._dirty_paths(_GIT_CWD, lambda cwd, *args: _git(*args))


# --- the ticket, always at the main repository root -------------------------


_graded = workspace_git._graded
_locate = workspace_git._locate
_record = workspace_git._record
_sharers = workspace_git._sharers


def _actual_mutations(name_status: str) -> list:
    """Normalize ``git diff --name-status --no-renames -z`` rows."""
    tokens = name_status.split("\0")
    rows = []
    index = 0
    operations = {"A": "create", "D": "delete", "M": "change", "T": "change"}
    while index < len(tokens) and tokens[index]:
        status = tokens[index]
        if "\t" in status:
            status, path = status.split("\t", 1)
            index += 1
        elif index + 1 < len(tokens):
            path = tokens[index + 1]
            index += 2
        else:
            raise Refused("git name-status output ended before its path")
        operation = operations.get(status[:1])
        if operation is None:
            raise Refused(f"git name-status returned unsupported status {status!r}")
        rows.append((operation, path))
    return sorted(set(rows))


# --- subcommands ------------------------------------------------------------


def _positional(rest, count: int, command: str) -> list:
    args = list(rest)
    stray = next((arg for arg in args if arg.startswith("-")), None)
    if stray is not None or len(args) != count:
        raise Refused(f"{command} takes <run> <id>. {USAGE}")
    return args


def _cmd_start(rest):
    """Record what this workspace is, from inside it. It does not claim."""

    run, ticket_id = _positional(rest, 2, "start")
    root, path = _locate(run, ticket_id)
    data = _graded(tickets._load_ticket(path), f"read {run}/{ticket_id}")
    # the snapshot the stamps are written against, taken before the git calls
    # below and not after them: those calls are the seconds a concurrent
    # `set-status` lands in, and a snapshot taken past them absorbs the write
    # this guard exists to report
    prior_text = path.read_text(encoding="utf-8")
    top = Path(_git_out("rev-parse", "--show-toplevel")).resolve()
    branch, head = workspace_git._head_and_branch(_git_out)
    dirty = sorted(set(_dirty_paths()))
    # Write-once: ``tickets_packet.py`` feeds this stamp to ``cutcheck.py
    # --baseline``, so it goes on naming the revision the item was cut from,
    # never the moved tree a re-establishment stands in -- a second executor
    # turn, or the step a read-only verifier is itself required to run. The
    # observation is reported under its own key instead of recorded: a second
    # stamp would have to be a key ``contracts/work-item.md`` declares.
    # Computed either way: this call also refuses a dirty path no
    # comma-joined frontmatter scalar could carry unambiguously.
    observed = workspace_git._baseline(head, dirty)
    stamped = str(data.get(BASELINE_KEY) or "").strip()
    baseline = stamped or observed
    outcome = _record(path, prior_text, branch, baseline)
    if "error" in outcome:
        raise Refused(outcome["error"])
    # after recording, never before: a tree that cannot be prepared is still
    # a workspace whose branch and baseline the join has to be able to read,
    # and the preparation's own verdict is reported rather than raised
    prepared = workspace_prepare.prepare(top)
    # after recording: this item's own stamp is in the sink, and skipped
    sharing = _sharers(path, _git_out, _is_ancestor, branch)
    return {
        "start": {
            "run": run,
            "id": ticket_id,
            "ticket": str(path),
            BRANCH_KEY: branch,
            BASELINE_KEY: baseline,
            # present only on a re-establishment, which its presence declares
            **({"reestablished": observed} if stamped else {}),
            "workspace_root": str(top),
            "main_root": str(root),
            # a linked tree is necessary, and no longer sufficient
            "isolated": top != root and not sharing,
            "shared_with": sharing,
            "dirty": dirty,
            **prepared,
        }
    }, EXIT_SHARED_WORKSPACE if sharing else EXIT_OK


def _extract_flag(args: list, flag: str):
    if flag in args:
        index = args.index(flag)
        if index + 1 < len(args):
            value = args[index + 1]
            del args[index : index + 2]
            return value
        del args[index : index + 1]
    return None


def _is_ancestor(ancestor: str, descendant: str) -> bool:
    return workspace_git._is_ancestor(_git, ancestor, descendant)


def _cmd_check(rest):
    """Grade the item at the join, every fact re-derived from the integrating
    checkout's git -- the caller's own, or ``--repo``'s. Nothing a child wrote
    in prose is read, and the branch facts — not the presence of a linked tree
    the host may already have removed — are the verdict."""

    global _GIT_CWD
    args = list(rest)
    # read off the untouched argv: ``_extract_flag`` drops a valueless flag
    # and returns the same ``None`` an absent one does, and the two must not
    # read alike here -- an ignored ``--repo`` grades the caller's own
    # checkout and reports pass for a checkout nobody named
    aimed = "--repo" in rest
    base = _extract_flag(args, "--base")
    repo = _extract_flag(args, "--repo")
    run, ticket_id = _positional(args, 2, "check")
    if base is None:
        raise Refused(f"check requires --base <rev>. {USAGE}")
    if aimed and repo is None:
        raise Refused(f"--repo takes <path>. {USAGE}")
    if repo is not None:
        named = Path(repo).expanduser()
        if not named.is_dir():
            raise Refused(f"--repo '{repo}' is not a directory")
        # before the first git call, and before ``_locate``, so every fact
        # below is the named checkout's
        _GIT_CWD = str(named.resolve())
    root, path = _locate(run, ticket_id, _GIT_CWD)
    data = _graded(tickets._load_ticket(path), f"read {run}/{ticket_id}")
    reported = {"run": run, "id": ticket_id, "ticket": str(path)}

    isolation = tickets.normalized_isolation(data.get(ISOLATION_KEY))
    if isolation != REQUIRED:
        # read-only lanes and unisolated-by-design items never reach git
        reported.update({ISOLATION_KEY: isolation, "verdict": "not required"})
        return {"check": reported}, EXIT_OK
    reported[ISOLATION_KEY] = isolation

    branch = str(data.get(BRANCH_KEY) or "").strip()
    if not branch:
        raise Refused(
            f"{ticket_id} declares {ISOLATION_KEY}: {REQUIRED} and carries no {BRANCH_KEY}: nothing recorded what it "
            "was executed in",
            EXIT_NO_RECORD,
        )
    ref = workspace_git._tip_ref(branch)
    code, tip, _ = _git("rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    unresolved = f"branch {branch!r} does not resolve in this repository"
    if code == 0 and ref != branch:
        # a resolving revision is not yet a gradable workspace: only the
        # worktree standing past it carries the item's commits
        moved = workspace_git._detached_tip(_git_out, _is_ancestor, tip.strip())
        code, tip = (0, moved) if moved else (1, tip)
        unresolved = workspace_git._no_workspace(branch)
    if code != 0:
        raise Refused(unresolved, EXIT_ISOLATION_MISSING)
    tip = tip.strip()
    own = workspace_git._current_branch(_git_out)
    if branch == own:
        # Git checks a branch out in at most one tree, so standing on this
        # item's branch inside a linked worktree is standing inside the item's
        # own workspace: a fact about the caller's position, not about the
        # item. In the main checkout the same equality means the item was
        # executed on the caller's own branch, which is the isolation breach
        # it has always been. The two are told apart the way ``start`` tells
        # them apart -- this checkout's top against the main root.
        top = Path(_git_out("rev-parse", "--show-toplevel")).resolve()
        if top != root:
            raise Refused(
                f"this checkout is the workspace under check: a linked worktree of "
                f"{root} holding branch {branch!r}, which cannot grade itself. Run "
                "check from the integrating checkout, or name that checkout with "
                "--repo <path>",
                EXIT_WRONG_VANTAGE,
            )
        raise Refused(
            f"branch {branch!r} is the caller's own branch: no distinct branch carries the work",
            EXIT_ISOLATION_MISSING,
        )
    if _is_ancestor(tip, "HEAD"):
        # the caller's own branch lands here too: HEAD is its own ancestor
        raise Refused(
            f"branch {branch!r} is already an ancestor of the caller's HEAD: no "
            "distinct branch carries the work",
            EXIT_ISOLATION_MISSING,
        )

    code, base_commit, err = _git("rev-parse", "--verify", "--quiet", f"{base}^{{commit}}")
    if code != 0:
        raise Refused(f"base {base!r} does not resolve in this repository")
    base_commit = base_commit.strip()
    if not _is_ancestor(base_commit, tip):
        raise Refused(
            f"branch {branch!r} is not cut from {base}: the base is not an ancestor of "
            "the branch",
            EXIT_WRONG_BRANCH_POINT,
        )

    ticket_worktree = workspace_git._ticket_worktree(_git_out, branch, tip)
    if ticket_worktree is not None:
        dirty = workspace_git._dirty_paths(str(ticket_worktree))
        # Emission, not the item's change: an acceptance oracle imports the
        # tree it grades and CPython writes bytecode beside it, so counting
        # those bytes fails the item for having been verified. By path shape,
        # never by tracked status -- the verdict this replaced fired on
        # bytecode a frozen baseline tracked. Reported, never dropped.
        emitted = sorted(name for name in dirty
                         if name.endswith((".pyc", ".pyo")) or "__pycache__" in name.split("/"))
        dirty = sorted(set(dirty) - set(emitted))
        if emitted:
            reported["emission"] = emitted
        if dirty:
            raise Refused(
                f"branch {branch!r} still has uncommitted bytes in its isolated worktree: "
                + ", ".join(dirty),
                EXIT_SCOPE_BREACH,
                dirty=dirty,
            )

    actual = _actual_mutations(_git_out(
        "diff", "--name-status", "--no-renames", "-z", f"{base_commit}...{tip}", "--"))
    changed = sorted({path for _, path in actual})
    reported.update({
        BRANCH_KEY: branch, "tip": tip, "base": base_commit, "changed": changed,
        "mutations": [f"{operation}:{path}" for operation, path in actual],
    })
    reported["commits"] = int(
        _git_out("rev-list", "--count", f"{base_commit}..{tip}", "--") or 0
    )
    reported["verdict"] = "pass"
    return {"check": reported}, EXIT_OK


def _help_text(command=None) -> str:
    """Usage for the whole script, or for one subcommand.

    The exit codes are part of the answer, not decoration: this script's
    codes are its verdicts, and a caller who reads only the usage line
    would still have to read the source to learn what a 4 meant.
    """

    if command is not None:
        return f"usage: {COMMAND_USAGE[command]}\n\n  {COMMAND_HELP[command]}"
    lines = [USAGE, ""]
    lines += [f"  {name}  {COMMAND_HELP[name]}" for name in COMMAND_USAGE]
    lines += ["", "exit codes:"]
    lines += [f"  {code}  {verdict}" for code, verdict in sorted(VERDICTS.items())]
    return "\n".join(lines)


def main(argv=None) -> int:
    # A refusal quotes a path and a ticket's own words, either of which can
    # carry a character a cp1252 console cannot encode; a script that crashes
    # while printing its verdict reports none. The same treatment
    # `scripts/tickets.py` and `tools/validate.py` give their one print.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):  # pragma: no cover - not a TextIOWrapper
            pass
    # this process's git aim, held only for the call below: ``main`` is called
    # more than once in one process by the tests, and an aim left set would
    # grade the next call's item against the last call's checkout
    global _GIT_CWD
    _GIT_CWD = None
    arguments = list(sys.argv[1:] if argv is None else argv)
    handlers = {"start": _cmd_start, "check": _cmd_check}
    command = arguments[0] if arguments else None
    if command in HELP_FLAGS:
        print(_help_text())
        return EXIT_OK
    handler = handlers.get(command)
    if handler is None:
        detail = "missing subcommand" if command is None else f"unknown subcommand: {command}"
        print(json.dumps({"error": detail, "code": EXIT_ERROR}, ensure_ascii=False))
        print(f"workspace: {detail}\n{USAGE}", file=sys.stderr)
        return EXIT_ERROR
    # after the subcommand is known, so `<sub> --help` answers about that
    # subcommand, and before the handler, which would read the flag as a stray
    if any(argument in HELP_FLAGS for argument in arguments[1:]):
        print(_help_text(command))
        return EXIT_OK
    try:
        payload, code = handler(arguments[1:])
    except Refused as refusal:
        reported = {"error": str(refusal), "code": refusal.code,
                    "verdict": VERDICTS.get(refusal.code, "error")}
        reported.update(refusal.detail)
        print(json.dumps(reported, ensure_ascii=False))
        print(f"workspace: {refusal}", file=sys.stderr)
        return refusal.code
    except Exception as error:  # an internal error is exit 1, never a traceback
        print(json.dumps({"error": str(error), "code": EXIT_ERROR}, ensure_ascii=False))
        print(f"workspace: {error}", file=sys.stderr)
        return EXIT_ERROR
    print(json.dumps(payload, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
