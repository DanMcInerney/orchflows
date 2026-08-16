#!/usr/bin/env python3
"""Mechanical ticket queries over ``<sink>/tickets/<run>/*.md``.

Stdlib-only, cross-platform. Tickets are markdown work items per
``contracts/work-item.md``; frontmatter is parsed manually (no third-party
YAML dependency). The root is the one user-scope state sink
``scripts/state_root.py`` resolves — ``$ORCHFLOWS_STATE_HOME`` or
``~/.orchflows/state`` — so every workspace in every repository reads and
writes one run's tickets at one path, and a run outlives the checkout it
started in. Every subcommand prints exactly one JSON document to stdout.
Failures are reported as ``{"error": "..."}`` in the JSON payload and
exit 1; success exits 0. No outcome raises a traceback.

``--help``, ``-h`` or ``help`` answers usage at the top level, and
``<subcommand> --help`` for one subcommand: a request for usage is served,
never rendered as an unknown-subcommand error.

Subcommands:
    list [--run R]
    ready [--run R]
    claim <run> <id> --by <name>
    set-status <run> <id> <status>
    packet <run> <id> --reply-to <name> [--workspace <path>]
    result <run> <id> --section <name> (--file <path> | --text <string>)
           [--append | --replace]
    run-state <run> [--tree <name>] (--note <line> |
             (--artifact <name> [--replace] | --terminal <state>)
             (--file <path> | --text <string>))
    improvement --proposal <name> (--file <path> | --text <string>)
    improvement --covered <line>
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:  # in-repo; the installed copy sits flat beside state_root.py
    from scripts import state_root
except ImportError:  # pragma: no cover - the installed copy's path
    import state_root

try:  # Windows only; POSIX append needs no lock. See _append_one_line.
    import msvcrt
except ImportError:
    msvcrt = None

VALID_STATUSES = {
    "pending",
    "ready",
    "claimed",
    "suspended",
    "complete",
    "blocked",
    "failed",
    "limited",
}
# contracts/work-item.md: `executor` is the named skill bound to do the
# work. An engine is what dispatches a ticket's executor, so naming one
# here is the call cycle rules/composition.md §3 forbids — orch-task
# would spawn orch-task. Mirrors skills/engines/; tests/test_tickets.py
# holds the two in sync, because an installed copy of this script has no
# library tree to read the list from.
ENGINE_EXECUTORS = frozenset(
    {"orch-compose", "orch-frontier", "orch-loop", "orch-panel", "orch-task"}
)
# contracts/verdict.md's `oracle_class`, and contracts/work-item.md's
# optional oracle provenance. Both are closed sets, and this script is the
# one place a criterion is graded against them.
ORACLE_CLASSES = ("deterministic", "judged", "evidence")
ORACLE_PROVENANCES = ("pre-existing", "authored-here")
# contracts/work-item.md's compatibility floor, split by what a stub is
# missing: a stub is a ticket without `run`, `status` and `claimed_*`, so
# only the first group is required of one. `claimed_by` and `claimed_at`
# are lifecycle, written on claim, and absent from both groups.
REQUIRED_TICKET_KEYS = ("id", "executor", "depends_on", "write_scope", "bound")
REQUIRED_LIFECYCLE_KEYS = ("run", "status")
# One criterion is one bullet: `- text`, `* text`, or an enumerated
# `1. text`. Up to three columns of indentation, because four is
# indented-code content (CommonMark 4.4) and `_fence_run` reads it as such.
CRITERION_BULLET_RE = re.compile(r"^ {0,3}(?:[-*+]|\d+[.)])\s+")
# `oracle:` and `oracle_class:` are two keys, not one with a suffix: the
# literal `oracle:` does not occur inside `oracle_class:`, so a plain search
# for each answers independently. Case-insensitive because the library's own
# tickets write `Oracle:` at the head of a sentence. An oracle's value runs
# to the next `|` or end of line; a class or provenance is one word, so
# ordinary sentence punctuation around it is not part of it.
ORACLE_RE = re.compile(r"oracle:\s*([^|\n]*)", re.IGNORECASE)
ORACLE_CLASS_RE = re.compile(r"oracle_class:\s*([A-Za-z_-]*)", re.IGNORECASE)
PROVENANCE_RE = re.compile(r"provenance:\s*([A-Za-z_-]*)", re.IGNORECASE)
DURATION_RE = re.compile(r"^(\d+)(m|h)$")
DEFAULT_BOUND_MINUTES = 60
# The shape of every UTC instant this script writes, stated once and read
# wherever one is stamped: a claim's `claimed_at` and a run's `opened_at`
# cannot drift into two shapes. It is the shape `scripts/friction.py`
# already produces for its own stream.
UTC_STAMP = "%Y-%m-%dT%H:%M:%SZ"
# The run's identity document, beside its worklog under the same run
# partition. `sink_convention` says which layout wrote it; item 06 states
# the field list in the contract.
RUN_IDENTITY_NAME = "run.json"
SINK_CONVENTION = 2
NO_SINK_ERROR = (
    "cannot resolve the state sink: no $ORCHFLOWS_STATE_HOME and no home directory"
)
# contracts/delegation.md: a work-item dispatch may supply the six packet
# parts by reference to the ticket path. These are the parts that live in
# a body section; authority and bounds live in frontmatter, and reply_to
# is the dispatcher's own, never the item's.
PACKET_SECTIONS = (
    ("objective", "Objective"),
    ("inputs", "Fixed inputs"),
    ("return_contract", "Return fields"),
)
# contracts/work-item.md: the closed set of sections an executor writes.
# Every other heading is cut-time content, and terminal `status` is the
# join's alone — which is why `result` writes no frontmatter at all.
EXECUTOR_SECTIONS = ("Result", "Verification", "Feedback", "Risks", "Handoff")
EXECUTOR_SECTIONS_BY_KEY = {name.lower(): name for name in EXECUTOR_SECTIONS}
# contracts/work-item.md states the sections in this order; a created section
# takes its place in it, never the end of the file.
SECTION_ORDER = (
    "Objective",
    "Fixed inputs",
    "Completion test",
    "Return fields",
) + EXECUTOR_SECTIONS
SECTION_RANK = {name.lower(): i for i, name in enumerate(SECTION_ORDER)}
# The sections a ticket carries whatever its state. `## Handoff` is the one
# optional section — it exists only once a ticket suspends — so it is the
# one name in SECTION_ORDER that is not required here.
OPTIONAL_SECTION = "Handoff"
REQUIRED_SECTIONS = tuple(name for name in SECTION_ORDER if name != OPTIONAL_SECTION)
# contracts/work-item.md: the one `isolation` value that means this item
# executes in a workspace of its own. The sibling script grades the same
# declaration; the spelling belongs to the contract, not to either script.
REQUIRED_ISOLATION = "required"
# Each pack's `workspace` cell names its mechanism first, before the cell's
# colon; this is that name, per pack. Only a git mechanism has a workspace
# `scripts/workspace.py start` can establish, so only those packs are emitted
# a step for. Mirrors packs/; tests/test_sync.py holds the two in sync,
# because an installed copy of this script runs against a target repository
# with no library tree to read the cell from.
PACK_WORKSPACE_MECHANISMS = {
    "orch-code-pack": "git",
    "orch-content-pack": "document tree",
    "orch-design-pack": "git plus render",
    "orch-research-pack": "evidence store",
}
# The mechanisms above that are a git ref, and so establishable from here.
GIT_WORKSPACE_MECHANISMS = frozenset({"git", "git plus render"})
# rules/visibility.md §6's `.orch/` trees a run writes into, as a closed set.
# `runs/` is the worklog's own and stays the default, so every pre-existing
# call site lands exactly where it always did. The other three are named
# across the library and had no writer at all: anything meant for them was
# written by hand at a path each author guessed, or simply lost. Closed and
# refused by name rather than open, because `.orch/tickets/` is the tracker's
# and `.orch/friction/` is the logger's — neither is writable from here.
RUN_STATE_TREES = ("runs", "research", "improvement", "handoffs")
DEFAULT_RUN_STATE_TREE = "runs"
# contracts/worklog.md's run-level `terminal` set, in the contract's order.
# Deliberately not VALID_STATUSES: the contract states the two are not one
# set — `stalled` exists only at run level, `suspended` only at ticket level.
TERMINAL_STATES = ("complete", "blocked", "stalled", "limited", "failed")
WORKLOG_NAME = "worklog.md"
# The heading that closes a worklog. Written only by `--terminal`, so a
# worklog carries no terminal placeholder until it closes and the marker
# means what it says: while it is absent the run is open.
TERMINAL_HEADING = "## terminal"
RESULT_USAGE = (
    "result <run> <id> --section <name> (--file <path> | --text <string>) "
    "[--append | --replace]"
)
RUN_STATE_USAGE = (
    "run-state <run> [--tree <name>] (--note <line> | "
    "(--artifact <name> [--replace] | --terminal <state>) "
    "(--file <path> | --text <string>))"
)
NEW_USAGE = (
    "new <run> <id> --executor E --objective TEXT --criterion C "
    "[--criterion C ...] [--depends-on a,b] [--write-scope p[,p]] [--bound B] "
    "[--pack P] [--input I ...] [--excluded X ...] [--profile P] "
    "[--independence gate|checker] [--isolation required|none] "
    "[--return-fields TEXT] | new <run> --file <path>"
)
# The one field `new` supplies a default for: contracts/work-item.md reads an
# absent lease as DEFAULT_BOUND_MINUTES, so writing that same number is the
# declaration the reader already gets, said out loud.
NEW_DEFAULT_BOUND = f"{DEFAULT_BOUND_MINUTES}m"
NEW_DEFAULT_INPUTS = "None."
NEW_DEFAULT_RETURN_FIELDS = (
    "status; result (what changed, by identity); verification; feedback; risks"
)
# contracts/work-item.md's two optional enums, checked at the interface that
# writes them rather than only where they are read.
INDEPENDENCE_VALUES = ("gate", "checker")
ISOLATION_VALUES = (REQUIRED_ISOLATION, "none")
IMPROVEMENT_USAGE = (
    "improvement (--proposal <name> (--file <path> | --text <string>) "
    "| --covered <line>)"
)
# The two improvement evidence streams, under the sink's `improvement/`.
# One is whole-file and named; one is a shared append-only stream every
# self-improvement pass adds a line to.
PROPOSALS_DIR = "proposals"
COVERAGE_RECORD_NAME = "covered.jsonl"
SUBCOMMAND_USAGE = {
    "new": NEW_USAGE,
    "list": "list [--run R]",
    "ready": "ready [--run R]",
    "claim": "claim <run> <id> --by <name>",
    "set-status": "set-status <run> <id> <status>",
    "packet": "packet <run> <id> --reply-to <name> [--workspace <path>]",
    "result": RESULT_USAGE,
    "run-state": RUN_STATE_USAGE,
    "improvement": IMPROVEMENT_USAGE,
}
SUBCOMMAND_SUMMARY = {
    "new": "Issue one ticket into the run, refusing any shape `ticket_defects` "
    "reports before anything is written; --file places one already written.",
    "list": "Every ticket in the tracker, or in one run, as summaries.",
    "ready": "The tickets whose dependencies are complete and whose claim is "
    "free or stale; promotes an eligible `pending` to `ready`.",
    "claim": "Take one ready or stale ticket, losing the race rather than "
    "overwriting a live claim.",
    "set-status": f"Set one ticket's status; terminal status is the join's "
    f"alone. One of {sorted(VALID_STATUSES)}.",
    "packet": "The by-reference dispatch packet for one ticket: path, parts, "
    "and the commands the child runs from its own workspace.",
    "result": f"Write one of the executor's own sections {list(EXECUTOR_SECTIONS)}; "
    "a section already carrying content is refused without --append or --replace.",
    "run-state": "Write this run's state under the one user-scope sink, "
    f"in one of {list(RUN_STATE_TREES)} (default "
    f"{DEFAULT_RUN_STATE_TREE}); an artifact that already exists is refused "
    f"without --replace. --terminal closes the worklog, one of "
    f"{list(TERMINAL_STATES)}, after which no note is written.",
    "improvement": "Write one improvement evidence record under the sink: "
    "a named proposal file, or one appended line of the coverage record.",
}
HELP_FLAGS = frozenset({"--help", "-h"})
# The bare word only heads the command line. Inside a subcommand `help` is
# an ordinary token — a ticket could be named it — so only the dashed flags
# ask for usage there.
HELP_COMMANDS = HELP_FLAGS | {"help"}
# Every flag that consumes the token after it. A help flag standing as one of
# those values is that value, not a request for usage: `--note --help` writes
# the note `--help`, exactly as `_extract_flag` would read it.
VALUE_FLAGS = frozenset(
    {
        "--run",
        "--by",
        "--executor",
        "--objective",
        "--criterion",
        "--depends-on",
        "--write-scope",
        "--bound",
        "--pack",
        "--input",
        "--excluded",
        "--profile",
        "--independence",
        "--isolation",
        "--return-fields",
        "--set",
        "--section",
        "--file",
        "--text",
        "--note",
        "--artifact",
        "--terminal",
        "--tree",
        "--reply-to",
        "--workspace",
        "--proposal",
        "--covered",
    }
)


def normalized_isolation(declared) -> str:
    """contracts/work-item.md's `isolation`, read one way by both scripts.

    Absent or empty reads `none`. Backticks are ordinary frontmatter
    punctuation here, stripped exactly as `_normalized_scope` and the
    executor check strip them, so the value this script emits an
    establishment step for is the value `scripts/workspace.py` grades.
    Normalizing it in two places is how an emitted step and a skipped
    grade can disagree behind a green suite.
    """

    return str(declared or "none").strip().strip("`").strip() or "none"


def establishes_a_git_workspace(pack) -> bool:
    """Whether `pack`'s workspace cell names a mechanism this script can
    establish a workspace in.

    A pack absent from the table answers yes. The table is only as current as
    its last sync, and the two mistakes are not equal: a child handed a step
    its mechanism has no meaning for fails at its first act, in the open,
    while a child not handed one it needed works in the shared tree and loses
    that work at the join with nothing to see.
    """

    name = str(pack or "").strip().strip("`").strip()
    mechanism = PACK_WORKSPACE_MECHANISMS.get(name)
    return mechanism is None or mechanism in GIT_WORKSPACE_MECHANISMS


# --- sink / filesystem helpers ----------------------------------------------

# rules/visibility.md §3: ``scripts/state_root.py`` is the single owner of both
# the sink root and the repository a path belongs to. These are the private
# spellings sibling scripts already import (``scripts/cutcheck.py``); the
# bodies live in one module and no second copy survives under ``scripts/``.
_main_checkout_root = state_root.main_checkout_root
_find_repo_root = state_root.find_repo_root


def _cwd() -> Path:
    """The directory this invocation is standing in.

    Every question that starts from the caller's location asks here, so the
    location has one source rather than one per caller. Sink paths do not go
    through it at all — those are user-scope and the same from anywhere; what
    the caller's directory decides is only who is writing, and from which
    workspace of them.
    """

    return Path.cwd().resolve()


def _tickets_root():
    """The sink's ticket tree, or ``None`` when no root can be resolved."""

    try:
        return state_root.tickets_root()
    except Exception:
        return None


def _runs_root():
    """The sink's run tree, or ``None`` when no root can be resolved."""

    try:
        return state_root.runs_root()
    except Exception:
        return None


def _improvement_root():
    """The sink's improvement tree, or ``None`` when no root can be resolved."""

    try:
        return state_root.improvement_root()
    except Exception:
        return None


def _run_state_root(tree: str):
    """One of the sink's run-state trees, or ``None`` when unresolvable.

    ``--tree`` names the tree; the set is closed and checked by the
    caller, so anything reaching here is one of ``RUN_STATE_TREES``.
    """

    try:
        return state_root.state_root() / tree
    except Exception:
        return None


def _segment_error(kind: str, value: str):
    """Refuse, by name, anything that is not one path segment under the root."""

    if not value or not value.strip():
        return {"error": f"{kind} is empty"}
    if "/" in value or "\\" in value or ".." in value or value == ".":
        return {
            "error": f"unsafe {kind} '{value}': one path segment only, with no "
            "path separator and no '..'"
        }
    return None


def _iter_run_dirs(tickets_root: Path, run_filter):
    if tickets_root is None or not tickets_root.is_dir():
        return []
    if run_filter:
        candidate = tickets_root / run_filter
        return [candidate] if candidate.is_dir() else []
    return sorted(p for p in tickets_root.iterdir() if p.is_dir())


# --- run identity -----------------------------------------------------------


def _origin_url(main_root: Path):
    """The ``origin`` remote's url, read out of ``<main_root>/.git/config``.

    Read, never asked for. This script shells out to nothing — that is what
    lets a child in a workspace it may not run ``git`` in reach the sink at
    all — so git's config is parsed here in the small, the way frontmatter
    is: the ``[remote "origin"]`` section, its ``url`` key, nothing else.
    Both spellings of the header are accepted because git accepts both.
    """

    try:
        text = (main_root / ".git" / "config").read_text(
            encoding="utf-8", errors="replace"
        )
    except OSError:
        return None
    in_origin = False
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped[0] in "#;":
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            inner = stripped[1:-1].replace(".", " ")
            in_origin = [part.strip('"') for part in inner.split()] == [
                "remote",
                "origin",
            ]
            continue
        if in_origin:
            key, separator, value = stripped.partition("=")
            if separator and key.strip().lower() == "url":
                return value.strip() or None
    return None


def _normalized_origin(origin) -> str:
    """One remote, one spelling.

    A trailing ``/`` and a trailing ``.git`` are the two ways one transport
    writes one url, so both come off. Nothing tries to canonicalize ssh
    against https: guessing that two spellings mean one repository is how a
    run silently acquires a second project, which is what this exists to
    refuse. Empty for a repository with no remote.
    """

    text = str(origin or "").strip().rstrip("/")
    if text.endswith(".git"):
        text = text[: -len(".git")]
    return text.rstrip("/")


def _project_key(project: dict) -> str:
    """The name a project is refused by: its origin url, else its root."""

    return _normalized_origin(project.get("origin")) or str(project.get("root"))


def _same_project(recorded: dict, writing: dict) -> bool:
    """Whether two writes belong to one project.

    Origin first: two clones of one origin are one project with two
    workspaces, wherever on disk they sit. When either side has no origin
    there is nothing to compare but the main checkout root — so two
    repositories with no remote are two projects, and one repository that
    gained or lost its remote after the run opened is still itself rather
    than an impostor locked out of its own run.
    """

    theirs = _normalized_origin(recorded.get("origin"))
    mine = _normalized_origin(writing.get("origin"))
    if theirs and mine:
        return theirs == mine
    return str(recorded.get("root")) == str(writing.get("root"))


def _workspace_root(start: Path):
    """The checkout the caller is standing in, *not* dereferenced.

    ``state_root.find_repo_root`` owns the other half of a run's identity —
    which project — and follows a linked worktree's pointer to the main
    checkout to answer it. This one stops at the first ``.git`` instead of
    following it, because two worktrees of one project are exactly what
    ``workspaces[]`` distinguishes. The walk bound is the resolver's, never
    a second one.
    """

    current = Path(start).resolve()
    for _ in range(state_root.MAX_WALK_UP):
        if (current / ".git").exists():
            return current
        if current.parent == current:
            break
        current = current.parent
    return None


def _writer_identity():
    """``(project, workspace)`` for the caller: who is writing, from where."""

    cwd = _cwd()
    root = state_root.find_repo_root(cwd)
    workspace = _workspace_root(cwd) or cwd
    if root is None:
        # Outside any checkout the caller's own directory is all the identity
        # there is. A write from nowhere is still attributable to somewhere.
        return {"root": str(cwd), "origin": None, "name": cwd.name}, str(workspace)
    return (
        {"root": str(root), "origin": _origin_url(root), "name": root.name},
        str(workspace),
    )


# Windows has no unconditional atomic replace, and both sides of one pay
# for it. ``MoveFileEx`` answers ERROR_ACCESS_DENIED -- WinError 5, which
# reads like a permission problem and is not one -- for as long as any other
# handle holds the destination open, and an ``open`` of that same name is
# refused for the instant the move is in flight. So two workspaces opening
# one run refuse each other in both directions: the writer for someone
# else's read, the reader for someone else's write. Every such window is
# microseconds wide and closes by itself, so both are waited out on one
# bounded budget rather than reported. POSIX ``rename`` and ``open`` never
# collide this way, so there the first answer is the only one and a refusal
# is real.
REPLACE_BUDGET_SECONDS = 2.0
REPLACE_RETRY_SECONDS = 0.005


def _waiting_out_windows(action):
    """Run ``action``, retrying only the refusal only Windows raises.

    ``PermissionError`` alone, never ``OSError``: a missing file and an
    unreachable directory are answers, and waiting two seconds for one of
    those on every run that has yet to open would cost the ordinary path
    to spare the rare one.
    """

    deadline = time.monotonic() + REPLACE_BUDGET_SECONDS
    while True:
        try:
            return action()
        except PermissionError:
            if msvcrt is None or time.monotonic() >= deadline:
                raise
            time.sleep(REPLACE_RETRY_SECONDS)


def _read_identity(path: Path):
    """``(document, error)``: the run's identity, ``(None, None)`` when absent.

    A corrupt identity is refused rather than replaced. Overwriting it would
    attribute the run to whoever wrote last, which is the confusion the
    document exists to prevent.
    """

    try:
        text = _waiting_out_windows(lambda: path.read_text(encoding="utf-8"))
    except (FileNotFoundError, NotADirectoryError):
        # No document, and no reachable place for one. An unreachable sink is
        # the run-state write's own error to report, in its own words.
        return None, None
    except OSError as error:
        return None, {"error": f"unreadable run identity {path}: {error}"}
    try:
        data = json.loads(text)
    except ValueError as parse_error:
        # bound to a name of its own: Python unbinds an `except ... as` name
        # at the end of its block, and this one is read after it
        reason = str(parse_error)
    else:
        if isinstance(data, dict):
            return data, None
        reason = "the document is not an object"
    return None, {
        "error": f"run identity {path} is unreadable ({reason}); repair or "
        "remove it. Refusing to overwrite a run's identity with a guess"
    }


def _identity_document(run: str, path: Path, project: dict, workspace: str, now):
    """``(document_to_write, error)`` — create, extend, or refuse.

    ``project`` and ``opened_at`` are the first writer's and are never
    rewritten; a later workspace of the same project only appends itself.
    ``None`` for both means the identity is already correct and no write is
    owed, so an ordinary note does not rewrite this file every time.
    """

    existing, error = _read_identity(path)
    if error is not None:
        return None, error
    stamp = now.strftime(UTC_STAMP)
    entry = {"path": workspace, "first_seen": stamp}
    if existing is None:
        return {
            "run": run,
            "sink_convention": SINK_CONVENTION,
            "opened_at": stamp,
            "project": project,
            "workspaces": [entry],
        }, None

    updated = dict(existing)
    recorded = existing.get("project")
    if isinstance(recorded, dict) and (recorded.get("root") or recorded.get("origin")):
        if not _same_project(recorded, project):
            theirs, mine = _project_key(recorded), _project_key(project)
            return None, {
                "error": f"run '{run}' is held by project {theirs}; this write "
                f"comes from project {mine}. One run id is one project's, so "
                "nothing was written. Use a different run id, or write from a "
                f"workspace of {theirs}"
            }
    else:
        # An identity document with no project — an older layout, or one
        # written before this field existed — is adopted rather than refused:
        # there is no second project to confuse it with.
        updated["project"] = project
        updated.setdefault("run", run)
        updated.setdefault("opened_at", stamp)
        updated.setdefault("sink_convention", SINK_CONVENTION)

    seen = existing.get("workspaces")
    seen = list(seen) if isinstance(seen, list) else []
    if not any(isinstance(w, dict) and w.get("path") == workspace for w in seen):
        seen.append(entry)
        updated["workspaces"] = seen
    elif not isinstance(existing.get("workspaces"), list):
        updated["workspaces"] = seen
    return (updated, None) if updated != existing else (None, None)


def _replace_atomically(temporary: Path, target: Path) -> None:
    """Move ``temporary`` onto ``target``, waiting out a transient refusal."""

    _waiting_out_windows(lambda: temporary.replace(target))


def _write_identity(run_dir: Path, document: dict) -> None:
    """Whole-file, and atomically.

    The run id partitions this document, but two workspaces of one project
    still open it at once, and a reader must never meet a half-written one.
    Written beside the target and moved over it, so the move is the only
    thing a concurrent reader can observe.
    """

    handle = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="\n", dir=str(run_dir),
        prefix=RUN_IDENTITY_NAME + ".", suffix=".tmp", delete=False,
    )
    temporary = Path(handle.name)
    try:
        with handle:
            handle.write(json.dumps(document, ensure_ascii=False, indent=2) + "\n")
        _replace_atomically(temporary, run_dir / RUN_IDENTITY_NAME)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


# --- manual frontmatter parsing ---------------------------------------------


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _parse_frontmatter(text: str) -> dict:
    """Parse the leading ``---``-delimited block: scalars and simple lists."""

    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}

    data: dict = {}
    i = 1
    while i < end:
        line = lines[i]
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in line:
            i += 1
            continue
        key, _, rest = line.partition(":")
        key = key.strip()
        rest = rest.strip()
        if rest == "":
            items = []
            j = i + 1
            while j < end:
                item_stripped = lines[j].strip()
                if item_stripped.startswith("- "):
                    items.append(_unquote(item_stripped[2:].strip()))
                    j += 1
                elif item_stripped == "-":
                    j += 1
                else:
                    break
            data[key] = items
            i = j if items else i + 1
        elif rest.startswith("[") and rest.endswith("]"):
            inner = rest[1:-1].strip()
            data[key] = [] if not inner else [_unquote(p.strip()) for p in inner.split(",")]
            i += 1
        else:
            data[key] = _unquote(rest)
            i += 1
        continue
    return data


def _set_frontmatter_field(text: str, key: str, value: str) -> str:
    """Replace or insert one scalar frontmatter field, leaving the rest byte-exact."""

    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        raise ValueError("ticket is missing frontmatter")
    end = None
    for i in range(1, len(lines)):
        if lines[i].rstrip("\r\n") == "---":
            end = i
            break
    if end is None:
        raise ValueError("ticket frontmatter is not terminated")
    newline = "\r\n" if lines[0].endswith("\r\n") else "\n"
    for i in range(1, end):
        line_key = lines[i].split(":", 1)[0].strip()
        if line_key == key:
            lines[i] = f"{key}: {value}{newline}"
            return "".join(lines)
    lines.insert(end, f"{key}: {value}{newline}")
    return "".join(lines)


class TicketFormatError(ValueError):
    """The ticket's markdown cannot be written safely as it stands."""


def _fence_run(line: str):
    """The ``` or ~~~ run this line opens or closes a fenced block with.

    None at four or more columns of indentation: CommonMark 4.4-4.5 makes
    that indented-code content rather than a fence, and a ticket quoting an
    indented snippet is ordinary. Opening a block there opens one nothing
    closes, which now costs the whole write (`_write_section`).
    """

    if line.startswith("\t") or len(line) - len(line.lstrip(" ")) >= 4:
        return None
    stripped = line.strip()
    for char in ("`", "~"):
        if stripped.startswith(char * 3):
            return char * (len(stripped) - len(stripped.lstrip(char)))
    return None


def _scan_sections(lines, start: int = 0):
    """The ``## `` boundary indices below ``start``, and any unclosed fence.

    A ``## `` line inside a fenced block is quoted content, not a heading:
    every deliverable in this repository is markdown with ``## `` headings
    and executors quote them at length. Counting a quotation as a boundary
    truncates the span a replacement rewrites -- deleting the opening
    fence, orphaning the closing one, and promoting the quoted heading to
    a real one that `_sections` then resolves last-writer-wins.

    The second return value is the index of a fence still open at the end
    of the scan. Below it no heading is findable, so a reader sees fewer
    sections than the file means and a writer would create a duplicate of
    one that is already there; only the writer treats it as fatal.
    """

    found = []
    fence = None
    opened_at = None
    for i in range(start, len(lines)):
        line = lines[i]
        run = _fence_run(line)
        if fence is None:
            if run is not None:
                fence = run  # an info string is allowed on the opener
                opened_at = i
            elif line.startswith("## "):
                found.append(i)
        elif (
            run is not None
            and run[0] == fence[0]
            and len(run) >= len(fence)
            and not line.strip()[len(run):].strip()  # a closer carries none
        ):
            fence = None
            opened_at = None
    return found, opened_at


def _heading_lines(lines, start: int = 0) -> list:
    """Indices of the ``## `` lines that are section boundaries."""

    return _scan_sections(lines, start)[0]


def _sections(text: str) -> dict:
    """Map each ``## Heading`` to its stripped body text."""

    sections: dict = {}
    heading = None
    body: list = []
    lines = text.splitlines()
    starts = set(_heading_lines(lines))
    for i, line in enumerate(lines):
        if i in starts:
            if heading is not None:
                sections[heading] = "\n".join(body).strip()
            heading = line[3:].strip()
            body = []
        elif heading is not None:
            body.append(line)
    if heading is not None:
        sections[heading] = "\n".join(body).strip()
    return sections


def _frontmatter_end(lines) -> int:
    """The first index below the frontmatter block; 0 when there is none.

    Both the writer and the overwrite guard look for headings only below
    this line: a wrapped frontmatter value can begin a line with ``## ``,
    and reading one as a section is how a guard comes to report on a
    heading that is not a section at all.
    """

    if not lines or lines[0].rstrip("\r\n") != "---":
        return 0
    for i in range(1, len(lines)):
        if lines[i].rstrip("\r\n") == "---":
            return i + 1
    return 0


def _section_body(text: str, heading: str) -> str:
    """One section's current body, found the way ``_write_section`` finds it.

    Same frontmatter skip, same fence-aware scan, same case-insensitive
    match, so the content the overwrite guard reads is the content of the
    very span the writer is about to overwrite. A guard resolving a
    different heading than the writer writes is a guard that passes while
    the clobber happens.
    """

    lines = text.splitlines()
    starts, _ = _scan_sections(lines, _frontmatter_end(lines))
    for position, index in enumerate(starts):
        if lines[index][3:].strip().lower() != heading.strip().lower():
            continue
        end = starts[position + 1] if position + 1 < len(starts) else len(lines)
        return "\n".join(lines[index + 1 : end]).strip()
    return ""


def _body_block(body: str, newline: str) -> str:
    """Normalize a body to the file's line ending, ending in exactly one."""

    normalized = body.replace("\r\n", "\n").replace("\r", "\n").strip("\n")
    if not normalized:
        return ""
    return newline.join(normalized.split("\n")) + newline


def _write_section(text: str, heading: str, body: str, append: bool = False) -> str:
    """Replace or create one ``## Heading`` body, leaving every other byte alone."""

    lines = text.splitlines(keepends=True)
    newline = "\r\n" if lines and lines[0].endswith("\r\n") else "\n"
    # Headings are looked for below the frontmatter only: a wrapped
    # frontmatter value can begin a line with "## ", and frontmatter is
    # never this writer's to touch.
    starts, unclosed = _scan_sections(lines, _frontmatter_end(lines))
    if unclosed is not None:
        # Every heading below the open fence reads as quoted content, so the
        # section named here looks absent however present it is: writing it
        # would append a second `## <heading>` that `_sections` resolves to
        # neither. Nothing this writer can do to such a file is safe.
        raise TicketFormatError(
            f"unterminated fence opened at line {unclosed + 1} "
            f"({lines[unclosed].strip()}): every heading below it reads as "
            f"quoted content, so writing '## {heading}' would create a "
            "second one. Close the fence in the ticket, then retry"
        )
    found = None
    for i in starts:
        if lines[i][3:].strip().lower() == heading.lower():
            found = i
            break

    if found is None:
        block = _body_block(body, newline)
        segment = f"## {heading}{newline}{newline}{block}" if block else f"## {heading}{newline}"
        insert_at = None
        target_rank = SECTION_RANK.get(heading.lower())
        if target_rank is not None:
            for i in starts:
                rank = SECTION_RANK.get(lines[i][3:].strip().lower())
                if rank is not None and rank > target_rank:
                    insert_at = i
                    break
        if insert_at is None:
            prefix = "".join(lines).rstrip("\r\n")
            if prefix:
                prefix += newline + newline
            return prefix + segment
        return "".join(lines[:insert_at]) + segment + newline + "".join(lines[insert_at:])

    end = next((i for i in starts if i > found), len(lines))
    if append:
        prior = "".join(lines[found + 1 : end]).rstrip().lstrip("\r\n")
        if prior:
            body = f"{prior}\n\n{body}"
    block = _body_block(body, newline)
    head = lines[found]
    if not head.endswith("\n"):
        head += newline
    segment = head + newline + block if block else head
    if end < len(lines):
        segment += newline
    return "".join(lines[:found]) + segment + "".join(lines[end:])


def _load_ticket(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        return {"id": path.stem, "path": str(path), "error": f"unreadable ticket: {error}"}
    try:
        data = _parse_frontmatter(text)
    except Exception:
        return {"id": path.stem, "path": str(path), "error": "unparsable frontmatter"}
    ticket_id = data.get("id") or path.stem
    result = dict(data)
    result["id"] = ticket_id
    result["path"] = str(path)
    executor = data.get("executor")
    if isinstance(executor, str) and executor.strip().strip("`") in ENGINE_EXECUTORS:
        result["error"] = (
            f"executor '{executor.strip().strip('`')}' is an engine; an engine "
            "dispatches a ticket's executor and cannot be one. Name the "
            "recording or unit skill that does the work, or return a "
            "decision gap from the cut."
        )
    result["summary"] = {
        "run": data.get("run") or path.parent.name,
        "id": ticket_id,
        "status": data.get("status"),
        "executor": data.get("executor"),
        "depends_on": data.get("depends_on") or [],
        "path": str(path),
    }
    if "error" in result:
        result["summary"]["error"] = result["error"]
    return result


# --- ticket shape -----------------------------------------------------------
#
# The one owner of ticket-shape law in code. `new`, `instantiate` and
# `packet` all grade through these two functions and nothing grades a
# ticket any other way: a second spelling of the same law is how an issued
# ticket passes the cutter and is refused by the dispatcher.


def _criteria(section_text: str) -> list:
    """The completion-test criteria in ``section_text``, one string each.

    A criterion is a bullet; the lines under it that are not bullets are its
    own continuation, because a criterion long enough to wrap carries its
    oracle on the second line and reading each line as a criterion would
    report a defect on a clean one. A bullet inside a fenced block is quoted
    content — every deliverable here is markdown and executors quote ticket
    bodies at length — so fences are skipped exactly as ``_scan_sections``
    skips them.
    """

    criteria: list = []
    fence = None
    for line in section_text.splitlines():
        run = _fence_run(line)
        if fence is not None:
            if run is not None and run[0] == fence[0] and len(run) >= len(fence):
                fence = None
            continue
        if run is not None:
            fence = run
            continue
        stripped = line.strip()
        if not stripped:
            continue
        match = CRITERION_BULLET_RE.match(line)
        if match:
            criteria.append(line[match.end():].strip())
        elif criteria:
            criteria[-1] = f"{criteria[-1]} {stripped}"
    return criteria


def criterion_defects(section_text: str) -> list:
    """Every defect in one ``## Completion test`` section, criterion by
    criterion.

    Per contracts/work-item.md a criterion names its oracle and its
    oracle_class, and may name its provenance; per contracts/verdict.md the
    classes are a closed set. Graded per criterion rather than over the
    section, because a section whose first criterion names a class and whose
    second names none satisfies any whole-section test while dispatching an
    unverifiable item.
    """

    criteria = _criteria(section_text)
    if not criteria:
        return [
            "completion test states no criterion: one bullet per criterion, "
            "each naming `oracle:` and `oracle_class:`"
        ]
    defects = []
    for number, text in enumerate(criteria, start=1):
        oracle = ORACLE_RE.search(text)
        if oracle is None or not oracle.group(1).strip(" `.,;*"):
            defects.append(
                f"criterion {number} names no `oracle:` — the exact check that "
                f"decides it: {text[:60]!r}"
            )
        oracle_class = ORACLE_CLASS_RE.search(text)
        value = oracle_class.group(1).strip().lower() if oracle_class else ""
        if not value:
            defects.append(
                f"criterion {number} names no `oracle_class:` — one of "
                f"{list(ORACLE_CLASSES)}: {text[:60]!r}"
            )
        elif value not in ORACLE_CLASSES:
            defects.append(
                f"criterion {number} names oracle_class '{value}', not one of "
                f"{list(ORACLE_CLASSES)}"
            )
        provenance = PROVENANCE_RE.search(text)
        declared = provenance.group(1).strip().lower() if provenance else ""
        if provenance is not None and declared not in ORACLE_PROVENANCES:
            defects.append(
                f"criterion {number} names provenance '{declared}', not one of "
                f"{list(ORACLE_PROVENANCES)}"
            )
    return defects


def ticket_defects(text: str, stub: bool = False) -> list:
    """Every way ``text`` is not a ticket per contracts/work-item.md.

    ``stub=True`` grades a template's stub: a ticket missing only ``run``,
    ``status`` and ``claimed_*``, which instantiation adds. Everything else
    is graded identically, so a stub admitted into a template is a ticket
    the moment it is instantiated.

    A file with no frontmatter is that one defect and no other: every check
    below reads the frontmatter or the body it heads, so listing what a
    non-ticket also lacks says nothing a reader can act on.
    """

    data = _parse_frontmatter(text)
    if not data:
        return [
            "no frontmatter: a ticket opens with a '---' block "
            "(contracts/work-item.md)"
        ]
    defects = []
    required = REQUIRED_TICKET_KEYS if stub else (
        REQUIRED_TICKET_KEYS + REQUIRED_LIFECYCLE_KEYS
    )
    for key in ("id", "run", "status", "executor", "depends_on", "write_scope", "bound"):
        if key in required and key not in data:
            defects.append(f"frontmatter has no '{key}'")
    status = data.get("status")
    if isinstance(status, str) and status.strip():
        # A stub carries no status, but one that carries a wrong status is
        # refused as any ticket is: the enum is the contract's, not the
        # lifecycle stage's.
        normalized = status.strip().strip("`").strip()
        if normalized not in VALID_STATUSES:
            defects.append(
                f"status '{normalized}' is not one of {sorted(VALID_STATUSES)}"
            )
    sections = {name.strip().lower(): body for name, body in _sections(text).items()}
    for name in REQUIRED_SECTIONS:
        if name.lower() not in sections:
            defects.append(f"no '## {name}' section")
    completion = sections.get("completion test")
    if completion is not None:
        defects.extend(criterion_defects(completion))
    return defects


# --- claim staleness --------------------------------------------------------


def _parse_bound_minutes(bound) -> int:
    if isinstance(bound, str):
        match = DURATION_RE.match(bound.strip())
        if match:
            value = int(match.group(1))
            unit = match.group(2)
            return value * 60 if unit == "h" else value
    return DEFAULT_BOUND_MINUTES


def _parse_iso(value):
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except Exception:
        return None


def _is_stale(claimed_at, bound_minutes: int, now: datetime) -> bool:
    """A claim with no timestamp or an unparsable one is treated as stale."""

    parsed = _parse_iso(claimed_at)
    if parsed is None:
        return True
    return (now - parsed) > timedelta(minutes=bound_minutes)


# --- argument helpers --------------------------------------------------------


def _extract_flag(args: list, flag: str):
    if flag in args:
        idx = args.index(flag)
        if idx + 1 < len(args):
            value = args[idx + 1]
            del args[idx : idx + 2]
            return value
        del args[idx : idx + 1]
    return None


def _extract_all(args: list, flag: str) -> list:
    """Every value of a flag that may be repeated, in the order given.

    ``--criterion`` and ``--input`` name one thing each; a ticket has as
    many as the cut found. ``_extract_flag`` answers the first and removes
    it, so draining it is the whole implementation — and a trailing flag
    with no value is removed and ends the drain rather than looping on it.
    """

    values = []
    while flag in args:
        value = _extract_flag(args, flag)
        if value is None:
            break
        values.append(value)
    return values


# --- issuing ------------------------------------------------------------


def _split_commas(value) -> list:
    """One comma-separated flag value as a list, empty entries dropped."""

    return [part.strip() for part in str(value or "").split(",") if part.strip()]


def _frontmatter_list(key: str, values) -> list:
    """One frontmatter list, as the lines that carry it.

    Inline ``[a, b]`` unless a value carries a comma, which the inline
    reader (``_parse_frontmatter``) splits on: an excluded action is prose
    and prose has commas in it, so those go one per line instead. Both
    shapes read back as the same list.
    """

    items = list(values)
    if any("," in item for item in items):
        return [f"{key}:"] + [f"- {item}" for item in items]
    return [f"{key}: [{', '.join(items)}]"]


def _render_ticket(fields: dict, sections: list) -> str:
    """One ticket's markdown: frontmatter in the contract's key order, then
    its body sections in the contract's section order.

    ``fields`` values are already strings or lists; ``None`` omits an
    optional key entirely, so nothing is written that the reader would have
    to interpret as absent.
    """

    lines = ["---"]
    for key, value in fields.items():
        if value is None:
            continue
        if isinstance(value, list):
            lines.extend(_frontmatter_list(key, value))
        else:
            lines.append(f"{key}: {value}" if value != "" else f"{key}:")
    lines.append("---")
    body = []
    for heading, content in sections:
        # A blank line under the heading, the shape `_write_section` writes
        # back into: an executor's first result must not have to reflow the
        # section the cut left it.
        body.append(f"\n## {heading}\n")
        if content:
            body.append(f"\n{content}\n")
    return "\n".join(lines) + "\n" + "".join(body)


def _cmd_new(rest):
    """Issue one ticket into the run, or place one already written.

    The cut's own refusal: everything ``ticket_defects`` reports is refused
    here, before any directory is created, so a ticket that reaches the sink
    is one every later subcommand accepts. An off-contract cut that lands
    and is refused at dispatch costs the dispatch; refusing it here costs
    the flag that was wrong.

    ``--file`` places a ticket its author already wrote, through the same
    validation and the same refusal to overwrite an id that exists. The run
    argument and the file's own ``run`` must agree: the argument decides
    where it lands, and a ticket landing in a run it does not name is a
    ticket no reader can trace back.
    """

    args = list(rest)
    file_arg = _extract_flag(args, "--file")
    executor = _extract_flag(args, "--executor")
    objective = _extract_flag(args, "--objective")
    criteria = _extract_all(args, "--criterion")
    depends_on = _extract_flag(args, "--depends-on")
    write_scope = _extract_flag(args, "--write-scope")
    bound = _extract_flag(args, "--bound")
    pack = _extract_flag(args, "--pack")
    inputs = _extract_all(args, "--input")
    excluded = _extract_all(args, "--excluded")
    profile = _extract_flag(args, "--profile")
    independence = _extract_flag(args, "--independence")
    isolation = _extract_flag(args, "--isolation")
    return_fields = _extract_flag(args, "--return-fields")
    stray = next((arg for arg in args if arg.startswith("-")), None)
    if stray is not None:
        return {"error": f"new does not accept {stray}. usage: {NEW_USAGE}"}

    if file_arg is not None:
        supplied = [
            name
            for name, value in (
                ("--executor", executor), ("--objective", objective),
                ("--criterion", criteria or None), ("--depends-on", depends_on),
                ("--write-scope", write_scope), ("--bound", bound),
                ("--pack", pack), ("--input", inputs or None),
                ("--excluded", excluded or None), ("--profile", profile),
                ("--independence", independence), ("--isolation", isolation),
                ("--return-fields", return_fields),
            )
            if value is not None
        ]
        if supplied:
            return {
                "error": f"--file places a ticket already written; it takes none "
                f"of {supplied}. usage: {NEW_USAGE}"
            }
        if len(args) != 1:
            return {"error": f"usage: {NEW_USAGE}"}
        return _place_ticket(args[0], file_arg)

    if len(args) != 2:
        return {"error": f"usage: {NEW_USAGE}"}
    run, ticket_id = args
    for kind, value in (("run id", run), ("ticket id", ticket_id)):
        invalid = _segment_error(kind, value)
        if invalid is not None:
            return invalid
    missing = [
        name
        for name, value in (
            ("--executor", executor), ("--objective", objective),
            ("--criterion", criteria or None),
        )
        if value is None
    ]
    if missing:
        return {
            "error": f"new requires {', '.join(missing)}. usage: {NEW_USAGE}"
        }
    for flag, value, allowed in (
        ("--independence", independence, INDEPENDENCE_VALUES),
        ("--isolation", isolation, ISOLATION_VALUES),
    ):
        if value is not None and value.strip() not in allowed:
            return {
                "error": f"{flag} '{value}' is not one of {list(allowed)} "
                "(contracts/work-item.md)"
            }

    dependencies = _split_commas(depends_on)
    fields = {
        "id": ticket_id,
        "run": run,
        # contracts/work-item.md: an item issued with an incomplete
        # depends_on starts pending; orch-frontier owns its exit to ready.
        "status": "pending" if dependencies else "ready",
        "executor": executor,
        "pack": pack,
        "independence": independence,
        "depends_on": dependencies,
        "write_scope": _split_commas(write_scope),
        "excluded_actions": excluded or None,
        "isolation": isolation,
        "bound": bound or NEW_DEFAULT_BOUND,
        "claimed_by": "",
        "claimed_at": "",
        "profile": profile,
    }
    sections = [
        ("Objective", objective),
        ("Fixed inputs", "\n".join(f"- {item}" for item in inputs) or NEW_DEFAULT_INPUTS),
        ("Completion test", "\n".join(f"- {item}" for item in criteria)),
        ("Return fields", return_fields or NEW_DEFAULT_RETURN_FIELDS),
        ("Result", ""),
        ("Verification", ""),
        ("Feedback", "[]"),
        ("Risks", "[]"),
    ]
    return _issue_ticket(run, ticket_id, _render_ticket(fields, sections))


def _place_ticket(run: str, source: str):
    """``new --file``: one already-written ticket, validated and placed."""

    invalid = _segment_error("run id", run)
    if invalid is not None:
        return invalid
    try:
        text = Path(source).read_text(encoding="utf-8")
    except OSError as error:
        return {"error": f"unreadable ticket file: {error}"}
    data = _parse_frontmatter(text)
    ticket_id = data.get("id") if isinstance(data.get("id"), str) else None
    if not ticket_id:
        return {"error": f"ticket file {source} names no 'id' in its frontmatter"}
    invalid = _segment_error("ticket id", ticket_id)
    if invalid is not None:
        return invalid
    declared = data.get("run")
    if isinstance(declared, str) and declared.strip() and declared.strip() != run:
        return {
            "error": f"ticket file {source} names run '{declared.strip()}', placed "
            f"into run '{run}': one ticket belongs to one run"
        }
    return _issue_ticket(run, ticket_id, text)


def _issue_ticket(run: str, ticket_id: str, text: str):
    """Grade one rendered ticket, then write it — in that order.

    Nothing is created before the grade: a refused cut leaves the run
    directory exactly as it found it, including not existing.
    """

    defects = ticket_defects(text)
    if defects:
        return {
            "error": f"ticket {run}/{ticket_id} is off contract "
            f"(contracts/work-item.md): " + "; ".join(defects)
        }
    tickets_root = _tickets_root()
    if tickets_root is None:
        return {"error": NO_SINK_ERROR}
    ticket_path = tickets_root / run / f"{ticket_id}.md"
    if ticket_path.exists():
        return {
            "error": f"ticket id '{ticket_id}' is already issued in run '{run}': "
            f"{ticket_path}. An id is stable once issued (contracts/work-item.md)"
        }
    try:
        ticket_path.parent.mkdir(parents=True, exist_ok=True)
        with open(ticket_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    except OSError as error:
        return {"error": f"unwritable ticket: {error}"}
    return {
        "new": {
            "run": run,
            "id": ticket_id,
            "path": str(ticket_path),
            "status": _parse_frontmatter(text).get("status"),
        }
    }


# --- subcommands --------------------------------------------------------


def _cmd_list(rest):
    args = list(rest)
    run_filter = _extract_flag(args, "--run")
    if args:
        return {"error": f"unexpected arguments: {' '.join(args)}"}
    tickets_root = _tickets_root()
    if tickets_root is None:
        return {"error": NO_SINK_ERROR}
    items = []
    for run_dir in _iter_run_dirs(tickets_root, run_filter):
        for ticket_path in sorted(run_dir.glob("*.md")):
            loaded = _load_ticket(ticket_path)
            items.append(loaded.get("summary") or loaded)
    return {"tickets": items}


def _cmd_ready(rest):
    args = list(rest)
    run_filter = _extract_flag(args, "--run")
    if args:
        return {"error": f"unexpected arguments: {' '.join(args)}"}
    tickets_root = _tickets_root()
    if tickets_root is None:
        return {"error": NO_SINK_ERROR}
    now = datetime.now(timezone.utc)
    ready_items = []
    for run_dir in _iter_run_dirs(tickets_root, run_filter):
        tickets = {}
        for ticket_path in sorted(run_dir.glob("*.md")):
            loaded = _load_ticket(ticket_path)
            tickets[loaded["id"]] = loaded
        for data in tickets.values():
            if "error" in data:
                continue
            depends_on = data.get("depends_on") or []
            deps_complete = all(
                tickets.get(dep, {}).get("status") == "complete" for dep in depends_on
            )
            if not deps_complete:
                continue
            status = data.get("status")
            eligible = False
            if status == "ready":
                eligible = True
            elif status == "pending":
                # contracts/work-item.md: a pending ticket whose dependencies
                # are all complete is promoted to ready; persist it here so
                # orch-frontier's promotion clause has mechanical support.
                try:
                    ticket_path = Path(data["path"])
                    text = ticket_path.read_text(encoding="utf-8")
                    ticket_path.write_text(
                        _set_frontmatter_field(text, "status", "ready"),
                        encoding="utf-8",
                    )
                except (OSError, ValueError):
                    continue
                data["summary"]["status"] = "ready"
                eligible = True
            elif status == "claimed":
                bound_minutes = _parse_bound_minutes(data.get("bound"))
                eligible = _is_stale(data.get("claimed_at"), bound_minutes, now)
            if eligible:
                ready_items.append(data["summary"])
    return {"ready": ready_items}


def _do_claim(ticket_path: Path, prior_text: str, claimed_by: str, now: datetime) -> dict:
    """Claim against the ``prior_text`` snapshot the caller read.

    Re-reads the file and compares it to ``prior_text`` before writing: if
    another claim already landed since ``prior_text`` was read, this attempt
    loses the race and reports an error instead of silently overwriting the
    winner (claim was previously a blind read-modify-write with no such
    check, so two concurrent claimants could both believe they had won).
    """

    try:
        current_text = ticket_path.read_text(encoding="utf-8")
    except OSError as error:
        return {"error": f"unreadable ticket: {error}"}
    if current_text != prior_text:
        return {"error": "ticket changed since read; lost the claim race, retry"}
    data = _parse_frontmatter(prior_text)
    status = data.get("status")
    if status == "claimed":
        bound_minutes = _parse_bound_minutes(data.get("bound"))
        if not _is_stale(data.get("claimed_at"), bound_minutes, now):
            return {"error": f"ticket already claimed and not stale: {ticket_path.stem}"}
    elif status != "ready":
        return {"error": f"ticket is not claimable in status '{status}': {ticket_path.stem}"}
    timestamp = now.strftime(UTC_STAMP)
    updated = _set_frontmatter_field(prior_text, "status", "claimed")
    updated = _set_frontmatter_field(updated, "claimed_by", claimed_by)
    updated = _set_frontmatter_field(updated, "claimed_at", timestamp)
    ticket_path.write_text(updated, encoding="utf-8")
    return {"claimed": {"id": ticket_path.stem, "claimed_by": claimed_by, "claimed_at": timestamp}}


def _cmd_claim(rest):
    args = list(rest)
    claimed_by = _extract_flag(args, "--by")
    if claimed_by is None:
        return {"error": "claim requires --by <name>"}
    if len(args) != 2:
        return {"error": f"usage: {SUBCOMMAND_USAGE['claim']}"}
    run, ticket_id = args
    tickets_root = _tickets_root()
    if tickets_root is None:
        return {"error": NO_SINK_ERROR}
    ticket_path = tickets_root / run / f"{ticket_id}.md"
    if not ticket_path.is_file():
        return {"error": f"ticket not found: {run}/{ticket_id}"}
    loaded = _load_ticket(ticket_path)
    if "error" in loaded:
        return {"error": loaded["error"]}
    prior_text = ticket_path.read_text(encoding="utf-8")
    now = datetime.now(timezone.utc)
    result = _do_claim(ticket_path, prior_text, claimed_by, now)
    if "error" in result:
        return result
    claimed = dict(result["claimed"])
    claimed["run"] = run
    return {"claimed": claimed}


def _cmd_set_status(rest):
    args = list(rest)
    if len(args) != 3:
        return {"error": f"usage: {SUBCOMMAND_USAGE['set-status']}"}
    run, ticket_id, status = args
    if status not in VALID_STATUSES:
        return {"error": f"invalid status '{status}'; must be one of {sorted(VALID_STATUSES)}"}
    tickets_root = _tickets_root()
    if tickets_root is None:
        return {"error": NO_SINK_ERROR}
    ticket_path = tickets_root / run / f"{ticket_id}.md"
    if not ticket_path.is_file():
        return {"error": f"ticket not found: {run}/{ticket_id}"}
    text = ticket_path.read_text(encoding="utf-8")
    updated = _set_frontmatter_field(text, "status", status)
    ticket_path.write_text(updated, encoding="utf-8")
    return {"set_status": {"run": run, "id": ticket_id, "status": status}}


def _cmd_packet(rest):
    """Emit the by-reference dispatch packet for one ticket.

    The dispatcher never has to read the ticket body: this refuses a packet
    missing a part and names it (contracts/delegation.md, orch-delegate), and
    resolves the one absolute ticket path every worktree agrees on
    (contracts/work-item.md). Only the three values a ticket cannot carry are
    supplied here — reply_to belongs to the dispatch rather than the item, the
    workspace is derived from the pack's cell at dispatch, and the profile
    binding is a spawn argument, not prompt text.
    """

    args = list(rest)
    reply_to = _extract_flag(args, "--reply-to")
    workspace = _extract_flag(args, "--workspace")
    if len(args) != 2:
        return {"error": f"usage: {SUBCOMMAND_USAGE['packet']}"}
    run, ticket_id = args
    tickets_root = _tickets_root()
    if tickets_root is None:
        return {"error": NO_SINK_ERROR}
    ticket_path = tickets_root / run / f"{ticket_id}.md"
    if not ticket_path.is_file():
        return {"error": f"ticket not found: {run}/{ticket_id}"}
    loaded = _load_ticket(ticket_path)
    if "error" in loaded:
        return {"error": loaded["error"]}
    try:
        sections = _sections(ticket_path.read_text(encoding="utf-8"))
    except OSError as error:
        return {"error": f"unreadable ticket: {error}"}

    executor = (loaded.get("executor") or "").strip().strip("`")
    missing = []
    if not reply_to:
        missing.append("reply_to (--reply-to)")
    if not executor:
        missing.append("executor (frontmatter)")
    if not loaded.get("write_scope"):
        missing.append("authority (write_scope)")
    if not loaded.get("bound"):
        missing.append("bounds (bound)")
    for part, heading in PACKET_SECTIONS:
        if not sections.get(heading):
            missing.append(f"{part} (## {heading})")
    completion = sections.get("Completion test", "")
    if not completion:
        missing.append("completion test (## Completion test)")
    else:
        # Through the shape owner, criterion by criterion. The substring test
        # this replaces read the section once and reported on "every
        # criterion", so a ticket whose first criterion named a class and
        # whose second named none was dispatched under a message that said
        # otherwise.
        missing.extend(criterion_defects(completion))
    if missing:
        return {"error": "packet incomplete: " + "; ".join(missing)}

    prompt = [
        f"Apply skill {executor} to ticket {ticket_path}.",
        "Read the ticket; it is your complete delegation packet — objective, "
        "fixed inputs, authority (write_scope, excluded_actions), bounds, "
        "return fields. Gather nothing outside its fixed inputs.",
    ]
    if workspace:
        prompt.append(f"Workspace: {workspace}")
    prompt.append(
        "Write your result into the ticket's own sections as you produce it, "
        "never in one write at the end; the join alone sets terminal status."
    )
    run_id = loaded.get("run") or run
    script = Path(__file__).resolve()
    # contracts/work-item.md's `isolation`: absent reads `none`, and only
    # `required` is told to establish anything, so a lane that must not stamp
    # itself is never handed the command. The pack is the second condition:
    # `required` says the item works alone, its pack's workspace cell says
    # what working alone is made of, and only a git mechanism is made of
    # something this command can establish. The sibling resolves from this
    # file's own location, so it points at whichever copy is running.
    isolation = normalized_isolation(loaded.get("isolation"))
    if isolation == REQUIRED_ISOLATION and establishes_a_git_workspace(
        loaded.get("pack")
    ):
        prompt.append(
            "Workspace establishment (isolation: required), your first act, "
            "run from inside your own workspace:"
        )
        prompt.append(
            f"{sys.executable} {script.with_name('workspace.py')} "
            f"start {run_id} {loaded['id']}"
        )
    # Every packet carries the channel, isolated or not: a child learns how to
    # write run state from its own dispatch, never by reading a sibling's
    # ticket. Built from `sys.executable` and this file's own resolved path so
    # the tokens are absolute wherever the script was installed, and shaped one
    # token per argument — no pipe, redirect or `&&` — because a host guard may
    # refuse a command it cannot statically verify.
    prompt.append(
        "Run-state channel (rules/visibility.md §6), from your own workspace, "
        "with TEXT and NAME replaced:"
    )
    prompt.append(f"{sys.executable} {script} run-state {run_id} --note TEXT")
    prompt.append(f"{sys.executable} {script} run-state {run_id} --artifact NAME --text TEXT")
    prompt.append(f"reply_to: {reply_to} — address your closing message to `{reply_to}`.")

    return {
        "packet": {
            "run": loaded.get("run") or run,
            "id": loaded["id"],
            "path": str(ticket_path),
            "executor": executor,
            "pack": loaded.get("pack"),
            "profile": loaded.get("profile"),
            "independence": loaded.get("independence") or "checker",
            "isolation": isolation,
            "reply_to": reply_to,
            "workspace": workspace,
            "prompt": "\n".join(prompt),
        }
    }


def _cmd_result(rest):
    """Write one reserved section of a ticket in the state sink.

    The executor runs this from inside its own isolated worktree: ``--file``
    reads the body from that workspace while ``_tickets_root()`` resolves the
    user-scope sink, the one ticket path every workspace in every repository
    agrees on (contracts/work-item.md).
    """

    args = list(rest)
    section = _extract_flag(args, "--section")
    file_arg = _extract_flag(args, "--file")
    text_arg = _extract_flag(args, "--text")
    append = "--append" in args
    while "--append" in args:
        args.remove("--append")
    replace = "--replace" in args
    while "--replace" in args:
        args.remove("--replace")
    if append and replace:
        return {
            "error": "result takes one of --append or --replace, not both: they "
            f"are the two ways to write a section that already carries content. "
            f"usage: {RESULT_USAGE}"
        }
    stray = next((arg for arg in args if arg.startswith("-")), None)
    if stray is not None:
        return {
            "error": f"result does not accept {stray}: it writes body sections only, "
            "never frontmatter — terminal status is set by the join (orch-integrate) "
            f"through `set-status`. usage: {RESULT_USAGE}"
        }
    if len(args) != 2:
        return {"error": f"usage: {RESULT_USAGE}"}
    run, ticket_id = args
    if section is None:
        return {"error": f"result requires --section <name>, one of {list(EXECUTOR_SECTIONS)}"}
    canonical = EXECUTOR_SECTIONS_BY_KEY.get(section.strip().strip("#").strip().lower())
    if canonical is None:
        return {
            "error": f"section '{section}' is not one of the sections an executor "
            f"writes: {list(EXECUTOR_SECTIONS)}"
        }
    if file_arg is not None and text_arg is not None:
        return {"error": "result takes one of --file <path> or --text <string>, not both"}
    if file_arg is None and text_arg is None:
        return {"error": f"result requires --file <path> or --text <string>. usage: {RESULT_USAGE}"}
    if file_arg is not None:
        # read from the caller's own workspace, while the ticket written is
        # the main checkout's — that split is the point of this subcommand
        try:
            body = Path(file_arg).read_text(encoding="utf-8")
        except OSError as error:
            return {"error": f"unreadable body file: {error}"}
    else:
        body = text_arg
    tickets_root = _tickets_root()
    if tickets_root is None:
        return {"error": NO_SINK_ERROR}
    ticket_path = tickets_root / run / f"{ticket_id}.md"
    if not ticket_path.is_file():
        return {"error": f"ticket not found: {run}/{ticket_id}"}
    try:
        text = ticket_path.read_text(encoding="utf-8")
        # Rendered before the overwrite guard reads anything, and written
        # after it: a ticket this writer cannot write safely is refused as
        # such whatever flags were passed, and the guard never reports on a
        # file whose headings `_sections` cannot see (an unterminated fence
        # hides every one below it, which would read as an empty section and
        # wave the clobber through). `_write_section` is pure, so nothing is
        # on disk until the write below.
        rendered = _write_section(text, canonical, body, append)
    except TicketFormatError as error:
        return {"error": f"{error}. ticket: {ticket_path}"}
    except OSError as error:
        return {"error": f"unreadable ticket: {error}"}
    prior = _section_body(text, canonical)
    if prior and not append and not replace:
        # contracts/worklog.md's closing law, read across to the ticket the
        # same executor writes: a write over content already there is refused
        # by default and the refusal names the path. A ticket is cut with its
        # executor sections present and empty, so a first write is free; what
        # is guarded is the second writer silently erasing the first — the
        # §10 checker over the executor, or a resumed agent over its own pass.
        return {
            "error": f"'## {canonical}' already carries content: refusing to "
            "overwrite it silently. Pass --append to add after it, or "
            f"--replace to overwrite it deliberately. ticket: {ticket_path}"
        }
    try:
        ticket_path.write_text(rendered, encoding="utf-8")
    except OSError as error:
        return {"error": f"unwritable ticket: {error}"}
    if append:
        mode = "append"
    elif replace:
        mode = "replace"
    else:
        mode = "write"
    return {
        "result": {
            "run": run,
            "id": ticket_id,
            "path": str(ticket_path),
            "section": canonical,
            "mode": mode,
        }
    }


def _is_terminal_heading(line: str) -> bool:
    """Whether one line closes a worklog.

    Case-insensitive, and the prefix must end the word: ``## terminal`` and
    ``## terminal: complete`` close, ``## terminals`` is an ordinary
    heading. A note that would read as one is refused rather than written,
    so nothing but ``--terminal`` can ever put this marker in the file.
    """

    stripped = line.strip()
    if not stripped.lower().startswith(TERMINAL_HEADING):
        return False
    remainder = stripped[len(TERMINAL_HEADING) :]
    return remainder == "" or remainder.startswith(":")


def _append_one_line(path: Path, block: str) -> None:
    """Append in one write, serialised where the platform does not do it.

    POSIX ``O_APPEND`` places a write at end-of-file atomically, so append mode
    alone is the whole guarantee there. The Windows CRT emulates append with a
    seek and then a write, and those are two steps: two writers take the same
    offset and one whole line disappears -- seen here as seven notes of eight
    surviving, every survivor intact, on a job that had passed the run before.
    A torn line would have been obvious; a missing one reads like a writer that
    never ran.

    So Windows locks and POSIX does not, and byte zero is the mutex: every
    appender contends on the same byte and no reader takes it, so an append
    blocks only another append. Nothing here read-modify-writes. The lock
    serialises the seek the platform hides inside ``write``.
    """

    with open(path, "a", encoding="utf-8", newline="\n") as handle:
        if msvcrt is None:
            handle.write(block)
            return
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        try:
            handle.write(block)
            handle.flush()
        finally:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def _worklog_terminal(path: Path):
    """The state a worklog closed with, or ``None`` while it is open.

    A read, never a read-modify-write: the note that follows is still one
    append in one call, so a line another workspace added in between
    survives untouched.
    """

    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    for line in text.splitlines():
        if _is_terminal_heading(line):
            return line.strip()[len(TERMINAL_HEADING) :].strip(" :")
    return None


def _cmd_run_state(rest):
    """Write this run's state into the one user-scope state sink.

    The channel rules/visibility.md §6 names. The root is resolved the way
    every other subcommand resolves it — ``scripts/state_root.py``, an
    environment variable and a home directory, no subprocess — so a child in
    its own workspace, in any repository or none, reaches the run's state
    without a git call it may not be allowed to make.

    ``--note`` appends to one shared log, so it opens in append mode with an
    explicit ``newline`` (``scripts/friction.py``) and writes one line in one
    call through ``_append_one_line``, which serialises that call on the
    platform where append is not itself atomic: two workspaces write one
    repository's worklog concurrently and neither may read-modify-write it. ``--artifact`` is whole-file, which is
    safe only because the run id partitions it.

    One sink holds every project's runs, so a run says which project it is:
    the first write stamps ``run.json`` beside the worklog, a later write
    from another workspace of the same project appends itself to it, and a
    write from a *different* project is refused by name. Without that, two
    projects that pick one run id interleave into one worklog and neither
    can tell which line is whose.

    There is no fallback. A write that cannot reach that root is reported as
    an error and lands nowhere else: a run-state write that silently
    succeeds in the caller's own tree is the loss this channel exists to end.
    """

    args = list(rest)
    note = _extract_flag(args, "--note")
    artifact = _extract_flag(args, "--artifact")
    terminal = _extract_flag(args, "--terminal")
    file_arg = _extract_flag(args, "--file")
    text_arg = _extract_flag(args, "--text")
    tree = _extract_flag(args, "--tree")
    replace = "--replace" in args
    while "--replace" in args:
        args.remove("--replace")
    stray = next((arg for arg in args if arg.startswith("-")), None)
    if stray is not None:
        return {"error": f"run-state does not accept {stray}. usage: {RUN_STATE_USAGE}"}
    if len(args) != 1:
        return {"error": f"usage: {RUN_STATE_USAGE}"}
    run = args[0]
    chosen = [
        name
        for name, value in (
            ("--note", note), ("--artifact", artifact), ("--terminal", terminal)
        )
        if value is not None
    ]
    if len(chosen) != 1:
        return {
            "error": "run-state takes exactly one of --note <line>, --artifact "
            f"<name> or --terminal <state>; got {chosen or 'none'}. "
            f"usage: {RUN_STATE_USAGE}"
        }
    invalid = _segment_error("run id", run)
    if invalid is not None:
        return invalid
    if tree is None:
        tree = DEFAULT_RUN_STATE_TREE
    if tree not in RUN_STATE_TREES:
        return {
            "error": f"unknown run-state tree '{tree}': one of "
            f"{list(RUN_STATE_TREES)}"
        }
    body = None
    if artifact is not None or terminal is not None:
        owner = "--artifact" if artifact is not None else "--terminal"
        if artifact is not None:
            invalid = _segment_error("artifact name", artifact)
            if invalid is not None:
                return invalid
        else:
            if terminal not in TERMINAL_STATES:
                return {
                    "error": f"unknown terminal state '{terminal}': one of "
                    f"{list(TERMINAL_STATES)}. A ticket status is not a run's "
                    "terminal state (contracts/worklog.md)"
                }
        if (file_arg is None) == (text_arg is None):
            carries = (
                "the deciding evidence" if terminal is not None else "its body"
            )
            return {
                "error": f"{owner} takes one of --file <path> or --text <string> "
                f"for {carries}. usage: {RUN_STATE_USAGE}"
            }
        if file_arg is not None:
            # read from the caller's own workspace, write at the main root
            try:
                body = Path(file_arg).read_text(encoding="utf-8")
            except OSError as error:
                return {"error": f"unreadable body file: {error}"}
        else:
            body = text_arg
    elif file_arg is not None or text_arg is not None:
        return {
            "error": "--note carries its own line; --file and --text belong to "
            f"--artifact and --terminal. usage: {RUN_STATE_USAGE}"
        }
    elif _is_terminal_heading(note):
        # Only `--terminal` may put the marker in the file. A note that would
        # read as one is refused, so the guard below can never be walked past
        # by a line that merely looks like a close.
        return {
            "error": f"a note may not read as a terminal heading "
            f"('{TERMINAL_HEADING}'): close the run with --terminal <state> "
            f"instead, one of {list(TERMINAL_STATES)}"
        }

    tree_root = _run_state_root(tree)
    runs_root = _runs_root()
    if tree_root is None or runs_root is None:
        return {"error": NO_SINK_ERROR}
    run_dir = tree_root / run
    # The run's identity sits beside its worklog whichever tree the payload
    # lands in: contracts/worklog.md puts `run.json` at `runs/<run>/`, and a
    # run has one identity, not one per tree it happens to write into.
    identity_dir = runs_root / run
    if note is not None or terminal is not None:
        # contracts/worklog.md: "no note is written past a terminal section".
        # A closed worklog is closed once: a second close would leave two
        # answers to "how did this run exit", and a note after one would be
        # state recorded where no reader looks.
        closed = _worklog_terminal(run_dir / WORKLOG_NAME)
        if closed is not None:
            attempt = "a note" if note is not None else f"a '{terminal}' close"
            return {
                "error": f"this worklog closed '{closed}': no note is written "
                f"past a terminal section, and {attempt} would be. "
                f"worklog: {run_dir / WORKLOG_NAME}"
            }
    replaced = False
    if artifact is not None:
        target = run_dir / artifact
        # contracts/worklog.md: "Writing an artifact that already exists is
        # refused by default, the refusal naming the existing path." This is
        # the one whole-file write on a channel two workspaces share, so a
        # truncation here erases a sibling's evidence leaving no trace that
        # it existed. The run id partitions the path, which is what makes the
        # same artifact name under two runs two different files.
        if target.exists() and not replace:
            return {
                "error": f"artifact already exists: {target}. Pass --replace to "
                "overwrite it deliberately, or write it under another name"
            }
        replaced = target.exists()
    project, workspace = _writer_identity()
    document, refusal = _identity_document(
        run,
        identity_dir / RUN_IDENTITY_NAME,
        project,
        workspace,
        datetime.now(timezone.utc),
    )
    # The identity gate runs before the payload and before either directory
    # exists: a refused write leaves the worklog, the artifact and the
    # identity document all exactly as it found them, and creates nothing.
    if refusal is not None:
        return refusal
    try:
        run_dir.mkdir(parents=True, exist_ok=True)
        if document is not None:
            identity_dir.mkdir(parents=True, exist_ok=True)
            _write_identity(identity_dir, document)
        if artifact is not None:
            path = run_dir / artifact
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(body)
        else:
            path = run_dir / WORKLOG_NAME
            if note is not None:
                block = note.rstrip("\r\n") + "\n"
            else:
                # The close is an append like every other line on this log:
                # the section goes after what is already there, never over it.
                evidence = body.replace("\r\n", "\n").replace("\r", "\n").strip("\n")
                block = f"\n{TERMINAL_HEADING}: {terminal}\n\n{evidence}\n"
            _append_one_line(path, block)
    except OSError as error:
        return {"error": f"unwritable run state: {error}"}
    if artifact is not None:
        mode = "artifact"
    elif terminal is not None:
        mode = "terminal"
    else:
        mode = "note"
    written = {"run": run, "tree": tree, "path": str(path), "mode": mode}
    if artifact is not None:
        written["replaced"] = replaced
    if terminal is not None:
        written["terminal"] = terminal
    return {"run_state": written}


def _help_requested(rest) -> bool:
    """Whether a help flag in ``rest`` stands as its own token.

    A help flag consumed as a value-taking flag's value is that value
    (``VALUE_FLAGS``), so ``--note --help`` writes the note and never
    answers usage: a run-state line whose text happens to be a help flag
    must not be swallowed silently.
    """

    return any(
        token in HELP_FLAGS and (i == 0 or rest[i - 1] not in VALUE_FLAGS)
        for i, token in enumerate(rest)
    )


def _cmd_help(command=None):
    """Usage, answered before any argument is resolved.

    A request for usage is a request this script serves, never an unhandled
    case it renders as the ordinary error path. It carries no ``error`` key
    and so exits 0, and it touches no repository: `--help` outside a
    checkout, or on a subcommand whose required arguments are absent, is
    still answerable and is the case a reader most often needs it in.
    """

    if command is None:
        return {
            "help": {
                "usage": "tickets.py <subcommand> [options]",
                "subcommands": {
                    name: {"usage": SUBCOMMAND_USAGE[name], "summary": SUBCOMMAND_SUMMARY[name]}
                    for name in SUBCOMMAND_USAGE
                },
                "help": f"tickets.py {' | '.join(sorted(HELP_FLAGS))} | "
                "help, or <subcommand> --help",
                "output": "exactly one JSON document on stdout; a payload "
                "carrying 'error' exits 1, every other payload exits 0",
            }
        }
    return {
        "help": {
            "subcommand": command,
            "usage": SUBCOMMAND_USAGE[command],
            "summary": SUBCOMMAND_SUMMARY[command],
        }
    }


def _cmd_improvement(rest):
    """Write an improvement evidence record into the one user-scope sink.

    ``_cmd_run_state``'s sibling, for the other two records the channel
    rules/visibility.md §6 covers: a proposal and the coverage record.
    Same root resolution, same two shapes — one whole-file, one
    single-call append — and the same refusal to reach for a fallback.

    ``--proposal`` is whole-file, safe because the name partitions it, and
    the name goes through ``_segment_error`` so nothing can climb out of
    ``proposals/``. ``--covered`` appends to a stream every pass shares, so
    it opens in append mode with an explicit ``newline`` and writes one
    line in one call: a read-modify-write here loses a concurrent writer's
    line, which is the whole reason the record is JSONL.

    Neither body is read, parsed or validated. This is a channel; what a
    proposal says and what a coverage line carries belong to
    ``orch-self-improve``.

    There is no fallback. A write that cannot reach the resolved root is
    reported as an error and lands nowhere else.
    """

    args = list(rest)
    proposal = _extract_flag(args, "--proposal")
    covered = _extract_flag(args, "--covered")
    file_arg = _extract_flag(args, "--file")
    text_arg = _extract_flag(args, "--text")
    stray = next((arg for arg in args if arg.startswith("-")), None)
    if stray is not None:
        return {"error": f"improvement does not accept {stray}. usage: {IMPROVEMENT_USAGE}"}
    if args:
        return {
            "error": f"improvement takes no positional argument: got {args[0]}. "
            f"usage: {IMPROVEMENT_USAGE}"
        }
    if (proposal is None) == (covered is None):
        return {
            "error": "improvement takes one of --proposal <name> or --covered <line>. "
            f"usage: {IMPROVEMENT_USAGE}"
        }
    body = None
    if proposal is not None:
        invalid = _segment_error("proposal name", proposal)
        if invalid is not None:
            return invalid
        if (file_arg is None) == (text_arg is None):
            return {
                "error": "--proposal takes one of --file <path> or --text <string>. "
                f"usage: {IMPROVEMENT_USAGE}"
            }
        if file_arg is not None:
            # read from the caller's own workspace, write in the sink
            try:
                body = Path(file_arg).read_text(encoding="utf-8")
            except OSError as error:
                return {"error": f"unreadable body file: {error}"}
        else:
            body = text_arg
    elif file_arg is not None or text_arg is not None:
        return {
            "error": "--covered carries its own line; --file and --text belong to "
            f"--proposal. usage: {IMPROVEMENT_USAGE}"
        }

    improvement_root = _improvement_root()
    if improvement_root is None:
        return {"error": NO_SINK_ERROR}
    try:
        if proposal is not None:
            path = improvement_root / PROPOSALS_DIR / proposal
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(body)
        else:
            path = improvement_root / COVERAGE_RECORD_NAME
            improvement_root.mkdir(parents=True, exist_ok=True)
            # Through the serialised writer, not a bare `open(..., "a")`:
            # this record is the one file every workspace on the machine
            # appends to, and on Windows an unserialised append is a seek
            # and a write, so two writers take one offset and a whole line
            # disappears. Same channel as the worklog, same guarantee.
            _append_one_line(path, covered.rstrip("\r\n") + "\n")
    except OSError as error:
        return {"error": f"unwritable improvement record: {error}"}
    return {
        "improvement": {
            "mode": "proposal" if proposal is not None else "covered",
            "name": proposal,
            "path": str(path),
        }
    }


def _dispatch(argv):
    if not argv:
        return {
            "error": "missing subcommand: new | list | ready | claim | "
            "set-status | packet | result | run-state | improvement"
        }
    command, rest = argv[0], argv[1:]
    if command in HELP_COMMANDS:
        return _cmd_help()
    if command in SUBCOMMAND_USAGE and _help_requested(rest):
        return _cmd_help(command)
    if command == "new":
        return _cmd_new(rest)
    if command == "list":
        return _cmd_list(rest)
    if command == "ready":
        return _cmd_ready(rest)
    if command == "claim":
        return _cmd_claim(rest)
    if command == "set-status":
        return _cmd_set_status(rest)
    if command == "packet":
        return _cmd_packet(rest)
    if command == "result":
        return _cmd_result(rest)
    if command == "run-state":
        return _cmd_run_state(rest)
    if command == "improvement":
        return _cmd_improvement(rest)
    return {"error": f"unknown subcommand: {command}"}


def main(argv=None):
    arguments = sys.argv[1:] if argv is None else argv
    try:
        result = _dispatch(arguments)
    except Exception as error:
        result = {"error": str(error)}
    print(json.dumps(result, ensure_ascii=False))
    return 1 if "error" in result else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
