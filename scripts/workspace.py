#!/usr/bin/env python3
"""Observe and grade one work item's isolated workspace.

Stdlib-only, cross-platform, Python 3.9 and up, no network at run time.
The ticket is the work item of ``contracts/work-item.md``: ``start``,
run from inside a workspace, records the lifecycle stamps
``workspace_branch`` and ``workspace_baseline`` into the main-root
ticket's frontmatter; ``check`` grades the item's ``isolation``
declaration at the join from the caller's own git. A script observes and
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
    4  scope-breach
    5  no-record
    6  wrong-vantage: the caller stood in the workspace it asked about, so
       nothing about the item was graded. Distinct from 2 on purpose -- 2
       says the item failed, 6 says the question was asked from the wrong
       place, and an integrator that reads one as the other rejects intact
       work.

Subcommands:
    start <run> <id>
    check <run> <id> --base <rev> [--repo <path>]

``check`` grades from the integrating checkout, and refuses at code 6 when
run from inside the workspace it was asked about. ``--repo <path>`` aims it
at another checkout instead: every git call and the repository root both
come from there, so the caller need not stand where the answer lives.

``--help``, on the script or on either subcommand, prints usage on stdout
and exits 0. It is the one call whose stdout is not a JSON payload: the
caller asking what the arguments are is a reader, and answering a reader
with an error payload is how this script used to answer.
"""

from __future__ import annotations

import json
import subprocess
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

ISOLATION_KEY = "isolation"
BRANCH_KEY = "workspace_branch"
BASELINE_KEY = "workspace_baseline"
WRITE_SCOPE_KEY = "write_scope"
# Every frontmatter key name this script writes or reads, and where. The
# spellings belong to ``contracts/work-item.md``; ``tests/test_workspace.py``
# reads this mapping and the contract's own bytes and asserts the two agree
# in both directions, so a key cannot be spelled one way here and another
# way there behind a green suite.
FRONTMATTER_KEYS = {
    ISOLATION_KEY: "read by check",
    BRANCH_KEY: "written by start, read by check",
    BASELINE_KEY: "written by start",
    WRITE_SCOPE_KEY: "read by check",
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
VERDICTS = {
    EXIT_OK: "pass",
    EXIT_ERROR: "error",
    EXIT_ISOLATION_MISSING: "isolation-missing",
    EXIT_WRONG_BRANCH_POINT: "wrong-branch-point",
    EXIT_SCOPE_BREACH: "scope-breach",
    EXIT_NO_RECORD: "no-record",
    EXIT_WRONG_VANTAGE: "wrong-vantage",
}
# A frontmatter scalar carries the dirty set as one comma-joined line, so a
# path holding either character cannot be written unambiguously.
AMBIGUOUS = (",", '"', "'")
# ``contracts/work-item.md``: ``write_scope`` is exactly what the item may
# change -- paths, and this script compares them against the paths a diff
# names. A space or a parenthesis makes an entry prose ("scripts/ and tests/",
# "docs/ (tests only)"), which matches no path, so either every change reads
# as a breach or the grant covers nothing and none does. Refused at ``start``,
# where the cut can still fix it, rather than graded at the join.
UNGRADABLE_IN_SCOPE = (" ", "\t", "(", ")")
# The two of them a real path can carry, which ``_refuse_ungradable_scope``
# therefore decides by resolving the entry rather than by the character.
SPACING = (" ", "\t")
CONTRACT = "contracts/work-item.md"
# One spelling of each subcommand's arguments, joined into ``USAGE`` for the
# refusals and printed alone for ``<sub> --help``. Two spellings would drift.
COMMAND_USAGE = {
    "start": "workspace.py start <run> <id>",
    "check": "workspace.py check <run> <id> --base <rev> [--repo <path>]",
}
COMMAND_HELP = {
    "start": "from inside the workspace: record its branch and baseline into the ticket",
    "check": "from the integrating checkout: grade the item's isolation and write scope",
}
USAGE = "usage: " + "\n       ".join(COMMAND_USAGE.values())
HELP_FLAGS = ("--help", "-h")


class Refused(Exception):
    """What the script will not do, carrying the exit code that names why."""

    def __init__(self, message: str, code: int = EXIT_ERROR, **detail):
        super().__init__(message)
        self.code = code
        # what the caller needs to act on the refusal, carried in the payload
        # beside the exit code that names it
        self.detail = detail


# --- git, always the caller's own -------------------------------------------


# The checkout every ``_git`` call runs in. ``None`` -- the caller's own tree,
# and subprocess's own default, so an unaimed call is what it always was. Set
# once by ``check --repo`` before its first git call and never after: a grade
# whose facts came from two checkouts is not a grade.
_GIT_CWD = None


def _git(*args: str):
    """Run git in the tree under grade: the caller's own, or ``--repo``'s."""

    completed = subprocess.run(
        ["git", *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=_GIT_CWD
    )
    return (
        completed.returncode,
        completed.stdout.decode("utf-8", "replace"),
        completed.stderr.decode("utf-8", "replace"),
    )


def _git_out(*args: str) -> str:
    code, out, err = _git(*args)
    if code != 0:
        raise Refused(f"git {' '.join(args)}: {err.strip()}")
    return out.strip()


def _dirty_paths() -> list:
    """Every path ``git status`` reports, both ends of a rename included."""

    code, out, err = _git("status", "--porcelain", "-z")
    if code != 0:
        raise Refused(f"git status: {err.strip()}")
    fields = out.split("\0")
    found, index = [], 0
    while index < len(fields):
        entry = fields[index]
        index += 1
        if not entry:
            continue
        status, path = entry[:2], entry[3:]
        found.append(path)
        if "R" in status or "C" in status:
            if index < len(fields):
                found.append(fields[index])
                index += 1
    return found


# --- the ticket, always at the main repository root -------------------------


def _graded(payload, what: str) -> dict:
    """Grade a ``tickets.py`` result by its payload, never by exit status."""

    if not isinstance(payload, dict):
        raise Refused(f"{what}: tickets.py returned no payload")
    if "error" in payload:
        raise Refused(f"{what}: {payload['error']}")
    return payload


def _locate(run: str, ticket_id: str, where=None):
    """This workspace's repository root, and the ticket's one path in the sink.

    Two questions with two answers. The root says *which project this
    workspace is*, which is what grades isolation and write scope. The
    ticket lives in the user-scope sink ``scripts/state_root.py`` resolves,
    identical from every workspace in every repository.

    ``where`` is the checkout to answer the first question about, defaulting
    to the caller's own. ``check --repo`` passes the checkout it was aimed
    at, so the root and the git calls come from the same tree.
    """

    start = Path(where) if where is not None else Path.cwd()
    root = state_root.find_repo_root(start)
    if root is None:
        raise Refused(f"not inside a git repository: {start}")
    path = state_root.tickets_root() / run / f"{ticket_id}.md"
    if not path.is_file():
        raise Refused(f"ticket not found: {run}/{ticket_id}")
    return root, path


def _record(ticket_path: Path, prior_text: str, branch: str, baseline: str) -> dict:
    """Write both stamps against the snapshot the caller read.

    Re-reads and compares before writing, the guard ``tickets.py``'s
    ``_do_claim`` uses: a concurrent ``set-status`` has no guard of its own,
    and ``_set_frontmatter_field`` is a read-modify-write, so an unguarded
    stamp would silently clobber whatever landed in between.
    """

    try:
        current_text = ticket_path.read_text(encoding="utf-8")
    except OSError as error:
        return {"error": f"unreadable ticket: {error}"}
    if current_text != prior_text:
        return {"error": "ticket changed since read; lost the frontmatter write race, retry"}
    try:
        updated = tickets._set_frontmatter_field(prior_text, BRANCH_KEY, branch)
        updated = tickets._set_frontmatter_field(updated, BASELINE_KEY, baseline)
        ticket_path.write_text(updated, encoding="utf-8")
    except (OSError, ValueError) as error:
        return {"error": f"unwritable ticket: {error}"}
    return {"recorded": {BRANCH_KEY: branch, BASELINE_KEY: baseline}}


# --- subcommands ------------------------------------------------------------


def _positional(rest, count: int, command: str) -> list:
    args = list(rest)
    stray = next((arg for arg in args if arg.startswith("-")), None)
    if stray is not None or len(args) != count:
        raise Refused(f"{command} takes <run> <id>. {USAGE}")
    return args


def _exists_as_path(entry: str, root) -> bool:
    """Whether ``entry`` names something that is actually there.

    Absolute as it stands, or relative to the workspace root -- the same two
    readings ``check`` gives a scope entry when it splits a diff against it.
    """

    try:
        candidate = Path(entry)
        if candidate.is_absolute():
            return candidate.exists()
        return root is not None and (Path(root) / entry).exists()
    except OSError:  # pragma: no cover - a name the filesystem rejects
        return False


def _refuse_ungradable_scope(declared, root=None) -> None:
    """Refuse a ``write_scope`` entry no path comparison can read.

    The grant is what ``check`` grades a branch's diff against, so an entry
    that is prose rather than a path grades nothing and says so nowhere: the
    scope silently covers no path the branch touched, and the breach it was
    written to prevent passes. Raised at ``start`` -- the first thing an
    isolated item runs -- so the answer arrives while the cut can still be
    repaired, rather than at the join with the work already done.

    A space is evidence of prose, never proof of it: a home directory with a
    space in its name makes an ordinary path carry one, and refusing that
    refuses the host rather than the cut. So a spaced entry that resolves to
    something on disk is a path and is kept; one that resolves to nothing is
    the phrase this guard was written for. A parenthesis needs no such test
    -- it is the annotation shape itself ("docs/ (tests only)"), and a path
    carrying one still reads as one entry only by accident.
    """

    entries = [declared] if isinstance(declared, str) else list(declared or [])
    for raw in entries:
        entry = str(raw).strip().strip("`").strip()
        for character in UNGRADABLE_IN_SCOPE:
            if character not in entry:
                continue
            if character in SPACING and _exists_as_path(entry, root):
                break
            raise Refused(
                f"{WRITE_SCOPE_KEY} entry '{entry}' contains {character!r} and "
                f"names no path here: per {CONTRACT} an entry is exactly a "
                "path this item may change, and a phrase matches none, so "
                "nothing here can grade it. Cut the scope as one bare path "
                "per entry"
            )


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
    # after `top`, which is the root a relative scope entry resolves against
    _refuse_ungradable_scope(data.get(WRITE_SCOPE_KEY), top)
    branch = _git_out("rev-parse", "--abbrev-ref", "HEAD")
    head = _git_out("rev-parse", "HEAD")
    dirty = sorted(set(_dirty_paths()))
    for entry in dirty:
        for character in AMBIGUOUS:
            if character in entry:
                raise Refused(
                    f"dirty path {entry!r} contains {character!r}, which a comma-joined "
                    "frontmatter value cannot carry unambiguously: commit, "
                    "remove or rename it, then run start again"
                )
    # the revision this workspace derives from, plus what was dirty at start:
    # orch-workspace forbids proceeding without recording, not proceeding
    baseline = (
        f"{head} clean"
        if not dirty
        else f"{head} dirty: {', '.join(dirty)}"
    )
    outcome = _record(path, prior_text, branch, baseline)
    if "error" in outcome:
        raise Refused(outcome["error"])
    return {
        "start": {
            "run": run,
            "id": ticket_id,
            "ticket": str(path),
            BRANCH_KEY: branch,
            BASELINE_KEY: baseline,
            "workspace_root": str(top),
            "main_root": str(root),
            "isolated": top != root,
            "dirty": dirty,
        }
    }, EXIT_OK


def _extract_flag(args: list, flag: str):
    if flag in args:
        index = args.index(flag)
        if index + 1 < len(args):
            value = args[index + 1]
            del args[index : index + 2]
            return value
        del args[index : index + 1]
    return None


def _normalized_scope(declared, root: Path) -> tuple:
    """``write_scope`` as repository-relative POSIX paths.

    An absolute entry inside the main repository root is normalized to
    relative; one outside it is refused by name, because a scope naming
    something this repository cannot contain grades nothing.
    """

    if isinstance(declared, str):
        declared = [declared]
    entries = []
    for raw in declared or []:
        entry = raw.strip().strip("`").strip()
        if not entry:
            continue
        candidate = Path(entry)
        if candidate.is_absolute() or (len(entry) > 1 and entry[1] == ":"):
            try:
                entry = candidate.resolve().relative_to(root).as_posix()
            except ValueError:
                raise Refused(
                    # quoted plainly, never {!r}: a Windows entry carries
                    # backslashes, and repr doubles every one of them, so the
                    # refusal named a path the caller never wrote and could
                    # not grep its own ticket for
                    f"{WRITE_SCOPE_KEY} entry '{entry}' is an absolute path outside the main "
                    f"repository root {root}: nothing in this repository can match "
                    "it"
                )
        parts = [part for part in entry.replace("\\", "/").split("/") if part not in ("", ".")]
        if ".." in parts:
            raise Refused(
                f"{WRITE_SCOPE_KEY} entry '{entry}' escapes the repository"
            )
        if parts:
            entries.append("/".join(parts))
    return tuple(entries)


def _in_scope(name: str, scope) -> bool:
    """A path prefix compared on whole segments: `docs` never takes `docsmith`."""

    return any(name == prefix or name.startswith(prefix + "/") for prefix in scope)


def _is_ancestor(ancestor: str, descendant: str) -> bool:
    code, _, err = _git("merge-base", "--is-ancestor", ancestor, descendant)
    if code in (0, 1):
        return code == 0
    raise Refused(
        f"git merge-base --is-ancestor {ancestor} {descendant}: {err.strip()}"
    )


def _cmd_check(rest):
    """Grade the item at the join, every fact re-derived from the caller's
    own git. Nothing a child wrote in prose is read, and the branch facts —
    not the presence of a linked tree the host may already have removed —
    are the verdict."""

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
    scope = _normalized_scope(data.get(WRITE_SCOPE_KEY), root)

    code, tip, _ = _git("rev-parse", "--verify", "--quiet", f"{branch}^{{commit}}")
    if code != 0:
        raise Refused(
            f"branch {branch!r} does not resolve in this repository",
            EXIT_ISOLATION_MISSING,
        )
    tip = tip.strip()
    own = _git_out("rev-parse", "--abbrev-ref", "HEAD")
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
            f"branch {branch!r} is the caller's own branch: no distinct branch "
            "carries the work",
            EXIT_ISOLATION_MISSING,
        )
    if _is_ancestor(tip, "HEAD"):
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

    # three-dot, from the merge base: a breach that arrives inside a merge
    # commit is invisible to `git log --name-only` and visible here.
    # `--` terminates the revisions: without it git stats the range as a
    # filename first, and a long absolute revision came back "Filename too
    # long" -- a grade lost to a name nobody meant as a path.
    changed = [
        line
        for line in _git_out(
            "diff", "--name-only", "--no-renames", f"{base_commit}...{tip}", "--"
        ).splitlines()
        if line
    ]
    breaches = [name for name in changed if not _in_scope(name, scope)]
    reported.update(
        {
            BRANCH_KEY: branch,
            "tip": tip,
            "base": base_commit,
            "changed": changed,
            WRITE_SCOPE_KEY: list(scope),
        }
    )
    if breaches:
        raise Refused(
            f"branch {branch!r} changed {len(breaches)} path(s) outside {WRITE_SCOPE_KEY}: {', '.join(breaches)}",
            EXIT_SCOPE_BREACH,
            breaches=breaches,
            changed=changed,
        )
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
        reported = {
            "error": str(refusal),
            "code": refusal.code,
            "verdict": VERDICTS.get(refusal.code, "error"),
        }
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
