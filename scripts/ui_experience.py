"""Closed, read-only projection for the rendered observability experience."""

from __future__ import annotations

import re
from pathlib import Path

try:
    from scripts.ui_discovery import (
        discover,
        find_session,
        find_ticket,
        graph_input,
        identity_diagnostics,
        read_events,
        read_friction,
        read_sessions,
        run_tickets,
    )
    from scripts.ui_layout import DIAGNOSTIC_CYCLE, DIAGNOSTIC_DANGLING, graph_layout
    from scripts.ui_model import parse_verification
    from scripts.ui_readiness import explain_run
    from scripts.ui_sessions import DIAGNOSTIC_UNDECODABLE_SLUG, read_session
except ImportError:
    from ui_discovery import (
        discover, find_session, find_ticket, graph_input, identity_diagnostics,
        read_events, read_friction, read_sessions, run_tickets,
    )
    from ui_layout import DIAGNOSTIC_CYCLE, DIAGNOSTIC_DANGLING, graph_layout
    from ui_model import parse_verification
    from ui_readiness import explain_run
    from ui_sessions import DIAGNOSTIC_UNDECODABLE_SLUG, read_session

SCHEMA = "orchflows.experience.v1"
SPA_ROUTE_PATTERNS = (
    "/", "/observe", "/now", "/runs", "/runs/{run}",
    "/runs/{run}/tickets/{ticket}", "/sessions", "/sessions/{session}", "/friction",
)
NAVIGATION = (
    ("now", "Now", "/now", False, ""),
    ("run-map", "Workflows", "/runs", False, ""),
    (
        "create", "Create", "", True,
        "Future workflow authoring is unavailable in this read-only observer.",
    ),
    ("sessions", "Sessions", "/sessions", False, ""),
    ("friction", "Friction", "/friction", False, ""),
)
VIEW_IDS = {"now", "run-map", "ticket", "sessions", "session-graph", "friction"}
VISIBLE_SECTIONS = ("Objective", "Result", "Feedback", "Risks")
FRICTION_FIELDS = ("ts", "category", "host", "observed", "expected", "run", "ticket")
WINDOWS_HOST_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:[A-Za-z]:[\\/]|\\\\)[^\s`\"'<>]+"
)
POSIX_HOST_PATH_RE = re.compile(
    r"(?<![:A-Za-z0-9_])/(?:Users|home|tmp|private|var|opt|srv|mnt|Volumes)(?:/[^\s`\"'<>]+)+"
)
REDACTED_HOST_PATH = "[redacted-host-path]"


def is_spa_path(path: str) -> bool:
    parts = path.strip("/").split("/") if path != "/" else []
    return path in ("/", "/observe", "/now", "/runs", "/sessions", "/friction") or (
        len(parts) == 2 and parts[0] in ("runs", "sessions")
    ) or (len(parts) == 4 and parts[0] == "runs" and parts[2] == "tickets")


def browser_navigation(path: str, headers) -> bool:
    """Distinguish document navigation from the legacy no-Accept reader API."""

    accept = next((value for name, value in headers.items() if name.lower() == "accept"), "")
    return path == "/observe" or "text/html" in accept.lower()


def _text(value) -> str:
    return value if isinstance(value, str) else "" if value is None else str(value)


def _session_summary(session: dict) -> dict:
    return {
        "id": _text(session.get("id")),
        "title": _text(session.get("title")),
        "modified": _text(session.get("modified")),
        "agent_count": int(session.get("agent_count") or 0),
        "diagnostics": [_text(item) for item in session.get("diagnostics", ())],
    }


def _session_list_summary(session: dict) -> dict:
    record = _session_summary(session)
    named_cwd = _text(session.get("named_cwd")).rstrip("/\\")
    record["client"] = ""
    record["project"] = re.split(r"[\\/]", named_cwd)[-1] if named_cwd else ""
    return record


def _session_diagnostic(message) -> str:
    """Keep local slug identity out of the browser-safe projection."""

    message = _text(message)
    if message.startswith(DIAGNOSTIC_UNDECODABLE_SLUG + ":"):
        return DIAGNOSTIC_UNDECODABLE_SLUG
    return message


def _ticket_summary(ticket: dict, explanations: dict, indexed: dict, malformed_ids) -> dict:
    ticket_id = _text(ticket.get("id"))
    dependencies = [_text(item) for item in ticket.get("depends_on", ())]
    readiness = dict(explanations.get(
        ticket_id,
        {"state": "unknown", "dependencies": [], "explanation": "ticket is unreadable"},
    ))
    dependency_statuses = [_text(indexed.get(item, {}).get("status")) for item in dependencies]
    if ticket_id in malformed_ids or any(item not in indexed for item in dependencies):
        cause = "malformed_topology"
    elif "failed" in dependency_statuses:
        cause = "failed_upstream"
    elif any(item in ("blocked", "limited", "stalled") for item in dependency_statuses):
        cause = "blocked_upstream"
    elif _text(ticket.get("status")) == "suspended":
        cause = "suspended_handoff"
    elif readiness.get("state") == "waiting":
        cause = "pending_dependency"
    else:
        cause = "none"
    readiness["cause"] = cause
    readiness["causal_chain"] = dependencies
    return {
        "id": ticket_id,
        "status": _text(ticket.get("status")),
        "executor": _text(ticket.get("executor")),
        "bound": _text(ticket.get("bound")),
        "claimed_at": _text(ticket.get("claimed_at")),
        "claimed_by": _text(ticket.get("claimed_by")),
        "depends_on": dependencies,
        "readiness": readiness,
        "unreadable": bool(ticket.get("unreadable")),
    }


def _redact_host_paths(text: str, root: Path, ticket: dict) -> str:
    known = [str(root), root.as_posix(), _text(ticket.get("path"))]
    known.extend(_text(item) for item in ticket.get("write_scope", ()))
    for marker in sorted((item for item in known if item), key=len, reverse=True):
        text = text.replace(marker, REDACTED_HOST_PATH)
    text = WINDOWS_HOST_PATH_RE.sub(REDACTED_HOST_PATH, text)
    return POSIX_HOST_PATH_RE.sub(REDACTED_HOST_PATH, text)


def _ticket_detail(ticket: dict, run_record: dict, root: Path, run: str) -> dict:
    record = next(item for item in run_record["tickets"] if item["id"] == ticket["id"])
    record = dict(record)
    sections = ticket.get("sections") or {}
    record["sections"] = {
        name.lower(): _text(sections[name])
        for name in VISIBLE_SECTIONS
        if name in sections
    }
    record["verification"] = parse_verification(_text(sections.get("Verification")))
    record["inputs"] = [
        line.strip()[2:].strip()
        for line in _redact_host_paths(
            _text(sections.get("Fixed inputs")), root, ticket
        ).splitlines()
        if line.strip().startswith(("- ", "* ", "+ "))
    ]
    record["write_scope"] = [_redact_host_paths(_text(item), root, {}) for item in ticket.get("write_scope", ())]
    record["pack"] = _text(ticket.get("pack"))
    events = read_events(root, run)
    record["history"] = [
        {
            "ts": _text(item.get("ts")),
            "event": _text(item.get("event")),
            "agent": _text(item.get("agent")),
            "detail": _redact_host_paths(_text(item.get("detail")), root, ticket),
        }
        for item in ((events or {}).get("entries") or ())
        if item.get("ticket") == record["id"]
    ]
    record["raw"] = _redact_host_paths(_text(ticket.get("raw")), root, ticket)
    return record


def _run_diagnostics(tickets) -> list:
    messages = identity_diagnostics(tickets) + graph_layout(*graph_input(tickets))["diagnostics"]
    ticket_ids = [_text(ticket.get("id")) for ticket in tickets]
    records = []
    for message in messages:
        if message.startswith(DIAGNOSTIC_CYCLE):
            kind = "cycle"
        elif message.startswith(DIAGNOSTIC_DANGLING):
            kind = "dangling"
        elif "one id declared by two files" in message:
            kind = "duplicate"
        else:
            kind = "unreadable"
        records.append({
            "kind": kind,
            "ticket_ids": [ticket_id for ticket_id in ticket_ids if ticket_id in message],
            "message": _text(message),
        })
    return records


def _run_record(root: Path, run: str):
    tickets = run_tickets(root, run)
    if tickets is None:
        return None
    explanations = explain_run(tickets)
    diagnostics = _run_diagnostics(tickets)
    malformed_ids = {
        ticket_id
        for diagnostic in diagnostics
        if diagnostic["kind"] in ("cycle", "dangling", "duplicate", "unreadable")
        for ticket_id in diagnostic["ticket_ids"]
    }
    indexed = {_text(ticket.get("id")): ticket for ticket in tickets}
    records = [
        _ticket_summary(ticket, explanations, indexed, malformed_ids)
        for ticket in tickets
    ]
    return {
        "id": run,
        "active": any(ticket["status"] in ("claimed", "ready") for ticket in records),
        "tickets": records,
        "diagnostics": diagnostics,
        "counts": {
            status: sum(1 for ticket in records if ticket["status"] == status)
            for status in sorted({ticket["status"] for ticket in records})
        },
    }


def _selected_run(root: Path, requested: str) -> str:
    found = discover(root)
    run_ids = [item["run"] for item in found["runs"]]
    if requested in run_ids:
        return requested
    active = next(
        (
            item["run"]
            for item in found["runs"]
            if any(ticket.get("status") in ("claimed", "ready") for ticket in item["tickets"])
        ),
        "",
    )
    return active or (run_ids[0] if run_ids else "")


def _selected_session(transcripts, session_id: str):
    found = find_session(transcripts, session_id) if session_id else None
    if found is None:
        return None
    session = read_session(found)
    projected = _session_summary(session)
    projected["agents"] = [
        {
            "id": _text(agent.get("id")),
            "type": _text(agent.get("type")),
            "depth": agent.get("depth"),
            "parent": _text(agent.get("parent")),
            "modified": _text(agent.get("modified")),
            "state": _text(agent.get("state")),
            "evidence": _text(agent.get("evidence")),
            "unreadable": bool(agent.get("unreadable")),
        }
        for agent in session.get("agents", ())
    ]
    return projected


def project_experience(root, transcripts=None, query=None) -> dict:
    """Project the entire closed UI substrate without mutating either root."""

    root = Path(root).resolve()
    query = query or {}
    requested_view = _text(query.get("view"))
    view = requested_view if requested_view in VIEW_IDS else "now"
    run = _selected_run(root, _text(query.get("run")))
    run_record = _run_record(root, run) if run else None
    ticket_id = _text(query.get("ticket"))
    ticket = find_ticket(root, run, ticket_id) if run and ticket_id else None
    session_id = _text(query.get("session"))
    sessions = read_sessions(transcripts)
    friction = read_friction(root)
    discovered = discover(root)
    run_summaries = []
    for found in discovered["runs"]:
        detail = _run_record(root, found["run"])
        events = read_events(root, found["run"])
        objective = next(
            (_text(item.get("objective")) for item in found["tickets"] if item.get("objective")),
            "",
        )
        run_summaries.append({
            "id": found["run"],
            "ticket_count": len(found["tickets"]),
            "active": bool(detail and detail["active"]),
            "objective": objective,
            "repository": "",
            "client": "",
            "last_activity": _text(((events or {}).get("entries") or [{}])[0].get("ts")),
            "unreadable": any(bool(item.get("unreadable")) for item in found["tickets"]),
            "tickets": detail["tickets"] if detail else [],
        })
    return {
        "schema": SCHEMA,
        "navigation": [
            {
                "id": item[0], "label": item[1], "path": item[2],
                "disabled": item[3], "explanation": item[4],
            }
            for item in NAVIGATION
        ],
        "selection": {
            "view": view,
            "run": run,
            "ticket": ticket_id if ticket is not None else "",
            "session": session_id if find_session(transcripts, session_id) is not None else "",
        },
        "runs": run_summaries,
        "run": run_record,
        "ticket": _ticket_detail(ticket, run_record, root, run) if ticket is not None else None,
        "sessions": {
            "items": [_session_list_summary(item) for item in sessions["sessions"]],
            "diagnostics": [_session_diagnostic(item) for item in sessions["diagnostics"]],
            "empty": bool(sessions["empty"]),
        },
        "session": _selected_session(transcripts, session_id),
        "friction": {
            "items": [
                {field: _text(entry.get(field)) for field in FRICTION_FIELDS if entry.get(field) is not None}
                for entry in friction["entries"]
            ],
            "skipped": int(friction["skipped"]),
            "unreadable": len(friction["unreadable"]),
        },
    }
