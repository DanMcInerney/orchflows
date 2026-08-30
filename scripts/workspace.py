#!/usr/bin/env python3
"""Establish, observe and grade one work item's isolated workspace.

Stdlib-only, cross-platform, Python 3.9 and up, no network at run time.
The ticket is the work item of ``contracts/work-item.md``.

``establish`` is the owner of an isolated candidate: for an item declaring
``isolation: required`` it creates the worktree its identity derives --
``state_root.candidate_paths`` names both the path and the branch -- and
records what it created. Nothing improvises that tree, and nothing falls
back to the tree the caller happened to be standing in. ``retire`` removes
it again, leaving every stamp that names it in place for the join.

``prepare`` installs what the recorded workspace's tree declares, against
the ``workspace_path`` establishment already stamped. It is a verb of its
own because it is the one act here that costs a package manager's minutes
and writes no ticket: run inside a caller's critical section it made every
sibling of the run wait for a tree that was not theirs, so it takes no lock
and is called once the establishment's lock is let go.

``start`` is the observation that predates it and still answers for
everything else: it records the durable ``workspace_path`` for every
supported adapter, adds ``workspace_branch`` and ``workspace_baseline`` for
a Git tree the caller already stands in, and creates the canonical
run-scoped store for an evidence-store lane. ``check`` grades the item's
``isolation`` declaration at the join from the integrating checkout's git --
the caller's own, or the one ``--repo`` names. ``check`` never creates,
enters, or removes a Git candidate; no subcommand here claims.

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
    establish <run> <id> [--repo <source-tree>]
    prepare <run> <id>
    retire <run> <id> [--force]
    start <run> <id>  # from a Git candidate, or anywhere for evidence-store
    check <run> <id> --base <rev> [--repo <path>]

``--repo <path>`` aims ``establish`` and ``check`` at another checkout:
every git call and the repository root both come from there, so the caller
need not stand where the answer lives. ``retire`` takes none -- it finds the
repository from the derived worktree's own pointer.

``--help``, on the script or on any subcommand, prints usage on stdout
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

import console  # noqa: E402  the console discipline every entrypoint takes first
import state_root  # noqa: E402  the sink resolver, imported and never copied
import tickets  # noqa: E402  frontmatter and isolation, imported and never copied

# Literal sibling imports work in the source tree and in the flat installed
# ``bin`` layout after the directory above has joined ``sys.path``.
workspace_git = __import__("workspace_git")
workspace_candidate = __import__("workspace_candidate")
# Re-exported, never respelled: the names are declared beside the writes and
# the refusals that use them, and this facade is where a reader looks them up.
ISOLATION_KEY = workspace_git.ISOLATION_KEY
BRANCH_KEY = workspace_git.BRANCH_KEY
BASELINE_KEY = workspace_git.BASELINE_KEY
PATH_KEY = workspace_git.PATH_KEY
# Every frontmatter key name this script writes or reads, and where. The
# spellings belong to ``contracts/work-item.md``; ``tests/test_workspace.py``
# reads this mapping and the contract's own bytes and asserts the two agree
# in both directions, so a key cannot be spelled one way here and another
# way there behind a green suite.
FRONTMATTER_KEYS = {
    ISOLATION_KEY: "read by check",
    BRANCH_KEY: "written by start, read by check",
    BASELINE_KEY: "written by start",
    PATH_KEY: "written by start",
}

# The value and its normalization both come from ``tickets.py``, never a
# second spelling here: packet projection gates the host establishment off
# this same declaration, and a grader reading it differently skips the grade
# at exit 0 while the join reads success.
REQUIRED = tickets.REQUIRED_ISOLATION
EXIT_OK = workspace_git.EXIT_OK
EXIT_ERROR = workspace_git.EXIT_ERROR
EXIT_ISOLATION_MISSING = workspace_git.EXIT_ISOLATION_MISSING
EXIT_WRONG_BRANCH_POINT = workspace_git.EXIT_WRONG_BRANCH_POINT
EXIT_SCOPE_BREACH = workspace_git.EXIT_SCOPE_BREACH
EXIT_NO_RECORD = workspace_git.EXIT_NO_RECORD
EXIT_WRONG_VANTAGE = workspace_git.EXIT_WRONG_VANTAGE
EXIT_SHARED_WORKSPACE = workspace_git.EXIT_SHARED_WORKSPACE
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
# Candidate diffs are reported in full. Suggested files are not read here.
# One spelling of each subcommand's arguments, joined into ``USAGE`` for the
# refusals and printed alone for ``<sub> --help``. Two spellings would drift.
COMMAND_USAGE = {
    "establish": "workspace.py establish <run> <id> [--repo <source-tree>]",
    "prepare": "workspace.py prepare <run> <id>",
    "retire": "workspace.py retire <run> <id> [--force]",
    "start": "workspace.py start <run> <id>",
    "check": "workspace.py check <run> <id> --base <rev> [--repo <path>]",
}
COMMAND_HELP = {
    "establish": "create and record the candidate worktree this item's identity derives",
    "prepare": "install what the recorded workspace declares; takes no run lock",
    "retire": "remove that derived worktree, leaving every stamp that names it",
    "start": "record the pack workspace the caller already stands in; never creates one",
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
    """``workspace_git.dirty_paths``, in the tree under grade."""
    return workspace_git.dirty_paths(_GIT_CWD, lambda cwd, *args: _git(*args))

# --- the ticket, always at the main repository root -------------------------

# Reading git's own output is `workspace_git`'s, beside the porcelain and
# worktree walks: this facade routes and grades, it never parses.
_actual_mutations = workspace_git.actual_mutations
_graded = workspace_git._graded
_locate = workspace_git._locate
_record = workspace_git._record
_sharers = workspace_git._sharers

# --- subcommands ------------------------------------------------------------

def _positional(rest, count: int, command: str) -> list:
    args = list(rest)
    stray = next((arg for arg in args if arg.startswith("-")), None)
    if stray is not None or len(args) != count:
        raise Refused(f"{command} takes <run> <id>. {USAGE}")
    return args

def _seams() -> dict:
    """The calls the establishment lanes make back through this module.

    Resolved on every call and never captured at import: a test that
    re-points ``_git``, ``_dirty_paths`` or ``_record`` on this module is
    re-pointing the call the lane actually makes, which is the only way a
    seam is worth having. ``_git_out`` and ``_dirty_paths`` read ``_git``
    through the module globals in turn, so aiming ``_GIT_CWD`` aims them
    both.
    """

    return {
        "git_out": _git_out,
        "dirty_paths": _dirty_paths,
        "record": _record,
        "is_ancestor": _is_ancestor,
    }

def _cmd_start(rest):
    """Record the workspace the caller already stands in. It does not claim."""

    held = workspace_git.LOCK_HELD in rest
    run, ticket_id = _positional([a for a in rest if a != workspace_git.LOCK_HELD], 2, "start")
    return workspace_candidate.observe(run, ticket_id, held=held, seams=_seams())

def _cmd_establish(rest):
    """Create and record the candidate worktree this item's identity derives.

    ``--repo`` names the tree the candidate is cut from; absent, the caller's
    own. Every git call runs there, so ``_GIT_CWD`` is aimed before the first
    one -- an item whose isolation is not ``required`` falls through to the
    same observation ``start`` makes, and it must observe the named tree
    rather than whichever directory this process happens to have started in.
    """

    global _GIT_CWD
    held = workspace_git.LOCK_HELD in rest
    args = [argument for argument in rest if argument != workspace_git.LOCK_HELD]
    aimed = "--repo" in args
    repo = _extract_flag(args, "--repo")
    run, ticket_id = _positional(args, 2, "establish")
    if aimed and repo is None:
        raise Refused(f"--repo takes <path>. {USAGE}")
    named = Path(repo).expanduser() if repo is not None else Path.cwd()
    if not named.is_dir():
        raise Refused(f"--repo '{repo}' is not a directory")
    _GIT_CWD = str(named.resolve())
    return workspace_candidate.establish(
        run, ticket_id, source=_GIT_CWD, held=held, seams=_seams()
    )

def _cmd_prepare(rest):
    """Install what the recorded workspace declares. It writes no ticket.

    Kept out of ``establish`` because it is the one act in this script that
    costs a package manager's minutes: run inside the dispatch facade's
    critical section it made every sibling of the run wait for a tree that
    was not theirs. Nothing here is written under a lock, so it takes none.
    """

    run, ticket_id = _positional(rest, 2, "prepare")
    return workspace_candidate.prepare(run, ticket_id)

def _cmd_retire(rest):
    """Remove the derived worktree. It reads and writes no ticket."""

    force = "--force" in rest
    run, ticket_id = _positional(
        [argument for argument in rest if argument != "--force"], 2, "retire"
    )
    return workspace_candidate.retire(run, ticket_id, force=force)

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
        recorded_workspace = str(data.get(PATH_KEY) or "").strip()
        if recorded_workspace and Path(recorded_workspace).resolve() != ticket_worktree.resolve():
            raise Refused(
                f"branch {branch!r} now stands in {ticket_worktree.resolve()}, not its "
                f"recorded workspace_path {Path(recorded_workspace).resolve()}",
                EXIT_ISOLATION_MISSING,
            )
        dirty = workspace_git.dirty_paths(str(ticket_worktree))
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
    # while printing its verdict reports none. One owner for that treatment,
    # `scripts/console.py`, which every entrypoint here calls first.
    console.harden()
    # this process's git aim, held only for the call below: ``main`` is called
    # more than once in one process by the tests, and an aim left set would
    # grade the next call's item against the last call's checkout
    global _GIT_CWD
    _GIT_CWD = None
    arguments = list(sys.argv[1:] if argv is None else argv)
    handlers = {
        "establish": _cmd_establish, "prepare": _cmd_prepare,
        "retire": _cmd_retire, "start": _cmd_start, "check": _cmd_check,
    }
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
    # Serialization inside the guard, not after it: a payload carrying a value
    # ``json.dumps`` will not encode used to raise past every handler here and
    # print nothing at all, and a caller that parses this stdout read the
    # silence as a workspace it never got. One document leaves this function
    # on every path.
    try:
        payload, code = handler(arguments[1:])
        document = json.dumps(payload, ensure_ascii=False)
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
    print(document)
    return code

if __name__ == "__main__":
    raise SystemExit(console.run(main))
