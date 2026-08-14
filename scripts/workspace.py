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

Subcommands:
    start <run> <id>
    check <run> <id> --base <rev>
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

import tickets  # noqa: E402  the root resolver, imported and never copied

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

REQUIRED = "required"
EXIT_OK = 0
EXIT_ERROR = 1
EXIT_ISOLATION_MISSING = 2
EXIT_WRONG_BRANCH_POINT = 3
EXIT_SCOPE_BREACH = 4
EXIT_NO_RECORD = 5
VERDICTS = {
    EXIT_OK: "pass",
    EXIT_ERROR: "error",
    EXIT_ISOLATION_MISSING: "isolation-missing",
    EXIT_WRONG_BRANCH_POINT: "wrong-branch-point",
    EXIT_SCOPE_BREACH: "scope-breach",
    EXIT_NO_RECORD: "no-record",
}
# A frontmatter scalar carries the dirty set as one comma-joined line, so a
# path holding either character cannot be written unambiguously.
AMBIGUOUS = (",", '"', "'")
USAGE = (
    "usage: workspace.py start <run> <id>\n"
    "       workspace.py check <run> <id> --base <rev>"
)


class Refused(Exception):
    """What the script will not do, carrying the exit code that names why."""

    def __init__(self, message: str, code: int = EXIT_ERROR):
        super().__init__(message)
        self.code = code


# --- git, always the caller's own -------------------------------------------


def _git(*args: str):
    """Run git in the caller's own tree: never ``-C``, never a redirect."""

    completed = subprocess.run(
        ["git", *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    return (
        completed.returncode,
        completed.stdout.decode("utf-8", "replace"),
        completed.stderr.decode("utf-8", "replace"),
    )


def _git_out(*args: str) -> str:
    code, out, err = _git(*args)
    if code != 0:
        raise Refused("git {}: {}".format(" ".join(args), err.strip()))
    return out.strip()


def _dirty_paths() -> list:
    """Every path ``git status`` reports, both ends of a rename included."""

    code, out, err = _git("status", "--porcelain", "-z")
    if code != 0:
        raise Refused("git status: {}".format(err.strip()))
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
        raise Refused("{}: tickets.py returned no payload".format(what))
    if "error" in payload:
        raise Refused("{}: {}".format(what, payload["error"]))
    return payload


def _locate(run: str, ticket_id: str):
    """The main repository root and the one ticket path every workspace shares."""

    root = tickets._find_repo_root(Path.cwd())
    if root is None:
        raise Refused("not inside a git repository")
    path = root / ".orch" / "tickets" / run / "{}.md".format(ticket_id)
    if not path.is_file():
        raise Refused("ticket not found: {}/{}".format(run, ticket_id))
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
        return {"error": "unreadable ticket: {}".format(error)}
    if current_text != prior_text:
        return {"error": "ticket changed since read; lost the frontmatter write race, retry"}
    try:
        updated = tickets._set_frontmatter_field(prior_text, BRANCH_KEY, branch)
        updated = tickets._set_frontmatter_field(updated, BASELINE_KEY, baseline)
        ticket_path.write_text(updated, encoding="utf-8")
    except (OSError, ValueError) as error:
        return {"error": "unwritable ticket: {}".format(error)}
    return {"recorded": {BRANCH_KEY: branch, BASELINE_KEY: baseline}}


# --- subcommands ------------------------------------------------------------


def _positional(rest, count: int, command: str) -> list:
    args = list(rest)
    stray = next((arg for arg in args if arg.startswith("-")), None)
    if stray is not None or len(args) != count:
        raise Refused("{} takes <run> <id>. {}".format(command, USAGE))
    return args


def _cmd_start(rest):
    """Record what this workspace is, from inside it. It does not claim."""

    run, ticket_id = _positional(rest, 2, "start")
    root, path = _locate(run, ticket_id)
    _graded(tickets._load_ticket(path), "read {}/{}".format(run, ticket_id))
    top = Path(_git_out("rev-parse", "--show-toplevel")).resolve()
    branch = _git_out("rev-parse", "--abbrev-ref", "HEAD")
    head = _git_out("rev-parse", "HEAD")
    dirty = sorted(set(_dirty_paths()))
    for entry in dirty:
        for character in AMBIGUOUS:
            if character in entry:
                raise Refused(
                    "dirty path {!r} contains {!r}, which a comma-joined "
                    "frontmatter value cannot carry unambiguously: commit, "
                    "remove or rename it, then run start again".format(
                        entry, character
                    )
                )
    # the revision this workspace derives from, plus what was dirty at start:
    # orch-workspace forbids proceeding without recording, not proceeding
    baseline = (
        "{} clean".format(head)
        if not dirty
        else "{} dirty: {}".format(head, ", ".join(dirty))
    )
    outcome = _record(path, path.read_text(encoding="utf-8"), branch, baseline)
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


def main(argv=None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    handlers = {"start": _cmd_start}
    command = arguments[0] if arguments else None
    handler = handlers.get(command)
    if handler is None:
        detail = "missing subcommand" if command is None else "unknown subcommand: {}".format(command)
        print(json.dumps({"error": detail, "code": EXIT_ERROR}, ensure_ascii=False))
        print("workspace: {}\n{}".format(detail, USAGE), file=sys.stderr)
        return EXIT_ERROR
    try:
        payload, code = handler(arguments[1:])
    except Refused as refusal:
        print(
            json.dumps(
                {
                    "error": str(refusal),
                    "code": refusal.code,
                    "verdict": VERDICTS.get(refusal.code, "error"),
                },
                ensure_ascii=False,
            )
        )
        print("workspace: {}".format(refusal), file=sys.stderr)
        return refusal.code
    except Exception as error:  # an internal error is exit 1, never a traceback
        print(json.dumps({"error": str(error), "code": EXIT_ERROR}, ensure_ascii=False))
        print("workspace: {}".format(error), file=sys.stderr)
        return EXIT_ERROR
    print(json.dumps(payload, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
