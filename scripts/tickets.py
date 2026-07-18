#!/usr/bin/env python3
"""Mechanical ticket queries over ``.orch/tickets/<run>/*.md``.

Stdlib-only, cross-platform. Tickets are markdown work items per
``contracts/work-item.md``; frontmatter is parsed manually (no third-party
YAML dependency). Every subcommand exits 0 and prints exactly one JSON
document to stdout — failures are reported as ``{"error": "..."}"``, never
as a non-zero exit or a raised traceback, so this stays safe to call from
any host without argument-parsing surprises.

Subcommands:
    list [--run R]
    ready [--run R]
    claim <run> <id> --by <name>
    set-status <run> <id> <status>
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
DURATION_RE = re.compile(r"^(\d+)(m|h)$")
DEFAULT_BOUND_MINUTES = 60
MAX_WALK_UP = 200


# --- repository / filesystem helpers ---------------------------------------


def _find_repo_root(start: Path):
    current = start.resolve()
    for _ in range(MAX_WALK_UP):
        if (current / ".git").exists():
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
    result["summary"] = {
        "run": data.get("run") or path.parent.name,
        "id": ticket_id,
        "status": data.get("status"),
        "executor": data.get("executor"),
        "depends_on": data.get("depends_on") or [],
        "path": str(path),
    }
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


def _dispatch(argv):
    if not argv:
        return {"error": "missing subcommand: list | ready | claim | set-status"}
    command, rest = argv[0], argv[1:]
    if command == "list":
        return _cmd_list(rest)
    if command == "ready":
        return _cmd_ready(rest)
    if command == "claim":
        return _cmd_claim(rest)
    if command == "set-status":
        return _cmd_set_status(rest)
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
