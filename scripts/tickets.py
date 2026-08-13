#!/usr/bin/env python3
"""Mechanical ticket queries over ``.orch/tickets/<run>/*.md``.

Stdlib-only, cross-platform. Tickets are markdown work items per
``contracts/work-item.md``; frontmatter is parsed manually (no third-party
YAML dependency). The root is the main repository root — a linked
worktree's ``.git`` pointer is dereferenced to it — so every worktree of
a repository reads and writes one run's tickets at one path. Every
subcommand exits 0 and prints exactly one JSON document to stdout —
failures are reported as ``{"error": "..."}"``, never as a non-zero exit
or a raised traceback, so this stays safe to call from any host without
argument-parsing surprises.

Subcommands:
    list [--run R]
    ready [--run R]
    claim <run> <id> --by <name>
    set-status <run> <id> <status>
    packet <run> <id> --reply-to <name> [--workspace <path>]
    result <run> <id> --section <name> (--file <path> | --text <string>) [--append]
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

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
DURATION_RE = re.compile(r"^(\d+)(m|h)$")
DEFAULT_BOUND_MINUTES = 60
MAX_WALK_UP = 200
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
RESULT_USAGE = (
    "result <run> <id> --section <name> (--file <path> | --text <string>) [--append]"
)


# --- repository / filesystem helpers ---------------------------------------


def _main_checkout_root(git_file: Path):
    """Resolve a .git pointer file (worktree/submodule) to its main root."""
    try:
        for line in git_file.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.startswith("gitdir:"):
                continue
            gitdir = Path(line.partition(":")[2].strip())
            if not gitdir.is_absolute():
                gitdir = git_file.parent / gitdir
            parts = gitdir.resolve().parts
            for i in range(len(parts) - 1, -1, -1):
                if parts[i] == ".git":
                    return Path(*parts[:i])
            break
    except Exception:
        pass
    return None


def _find_repo_root(start: Path):
    current = start.resolve()
    for _ in range(MAX_WALK_UP):
        marker = current / ".git"
        if marker.exists():
            if marker.is_file():
                main_root = _main_checkout_root(marker)
                if main_root is not None:
                    return main_root
            return current
        parent = current.parent
        if parent == current:
            return None
        current = parent
    return None


def _tickets_root():
    repo_root = _find_repo_root(Path.cwd())
    if repo_root is None:
        return None
    return repo_root / ".orch" / "tickets"


def _iter_run_dirs(tickets_root: Path, run_filter):
    if tickets_root is None or not tickets_root.is_dir():
        return []
    if run_filter:
        candidate = tickets_root / run_filter
        return [candidate] if candidate.is_dir() else []
    return sorted(p for p in tickets_root.iterdir() if p.is_dir())


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


def _sections(text: str) -> dict:
    """Map each ``## Heading`` to its stripped body text."""

    sections: dict = {}
    heading = None
    body: list = []
    for line in text.splitlines():
        if line.startswith("## "):
            if heading is not None:
                sections[heading] = "\n".join(body).strip()
            heading = line[3:].strip()
            body = []
        elif heading is not None:
            body.append(line)
    if heading is not None:
        sections[heading] = "\n".join(body).strip()
    return sections


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
    body_start = 0
    if lines and lines[0].rstrip("\r\n") == "---":
        for i in range(1, len(lines)):
            if lines[i].rstrip("\r\n") == "---":
                body_start = i + 1
                break
    starts = [
        i for i, line in enumerate(lines) if i >= body_start and line.startswith("## ")
    ]
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


# --- subcommands --------------------------------------------------------


def _cmd_list(rest):
    args = list(rest)
    run_filter = _extract_flag(args, "--run")
    if args:
        return {"error": f"unexpected arguments: {' '.join(args)}"}
    tickets_root = _tickets_root()
    if tickets_root is None:
        return {"error": "not inside a git repository"}
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
        return {"error": "not inside a git repository"}
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
    timestamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
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
        return {"error": "usage: claim <run> <id> --by <name>"}
    run, ticket_id = args
    tickets_root = _tickets_root()
    if tickets_root is None:
        return {"error": "not inside a git repository"}
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
        return {"error": "usage: set-status <run> <id> <status>"}
    run, ticket_id, status = args
    if status not in VALID_STATUSES:
        return {"error": f"invalid status '{status}'; must be one of {sorted(VALID_STATUSES)}"}
    tickets_root = _tickets_root()
    if tickets_root is None:
        return {"error": "not inside a git repository"}
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
        return {"error": "usage: packet <run> <id> --reply-to <name> [--workspace <path>]"}
    run, ticket_id = args
    tickets_root = _tickets_root()
    if tickets_root is None:
        return {"error": "not inside a git repository"}
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
    elif "oracle_class" not in completion.lower():
        missing.append("oracle_class on every completion-test criterion")
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
            "reply_to": reply_to,
            "workspace": workspace,
            "prompt": "\n".join(prompt),
        }
    }


def _cmd_result(rest):
    """Write one reserved section of a ticket at the main repository root.

    The executor runs this from inside its own isolated worktree: ``--file``
    reads the body from that workspace while ``_tickets_root()`` resolves the
    worktree's ``.git`` pointer to the one main-root ticket path every
    workspace agrees on (contracts/work-item.md).
    """

    args = list(rest)
    section = _extract_flag(args, "--section")
    file_arg = _extract_flag(args, "--file")
    text_arg = _extract_flag(args, "--text")
    append = "--append" in args
    while "--append" in args:
        args.remove("--append")
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
        return {"error": "not inside a git repository"}
    ticket_path = tickets_root / run / f"{ticket_id}.md"
    if not ticket_path.is_file():
        return {"error": f"ticket not found: {run}/{ticket_id}"}
    try:
        text = ticket_path.read_text(encoding="utf-8")
        ticket_path.write_text(
            _write_section(text, canonical, body, append), encoding="utf-8"
        )
    except OSError as error:
        return {"error": f"unwritable ticket: {error}"}
    return {
        "result": {
            "run": run,
            "id": ticket_id,
            "path": str(ticket_path),
            "section": canonical,
            "mode": "append" if append else "replace",
        }
    }


def _dispatch(argv):
    if not argv:
        return {
            "error": "missing subcommand: list | ready | claim | set-status | packet | result"
        }
    command, rest = argv[0], argv[1:]
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
    return {"error": f"unknown subcommand: {command}"}


def main(argv=None):
    arguments = sys.argv[1:] if argv is None else argv
    try:
        result = _dispatch(arguments)
    except Exception as error:
        result = {"error": str(error)}
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
