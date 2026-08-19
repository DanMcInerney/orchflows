"""Closed, read-only projection for the rendered observability experience."""

from __future__ import annotations

from pathlib import Path

try:
    from scripts.ui_discovery import (
        discover,
        find_session,
        find_ticket,
        read_friction,
        read_sessions,
        run_tickets,
    )
    from scripts.ui_model import parse_verification
    from scripts.ui_readiness import explain_run
    from scripts.ui_sessions import read_session
except ImportError:
    from ui_discovery import discover, find_session, find_ticket, read_friction, read_sessions, run_tickets
    from ui_model import parse_verification
    from ui_readiness import explain_run
    from ui_sessions import read_session

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


def is_spa_path(path: str) -> bool:
    parts = path.strip("/").split("/") if path != "/" else []
    return path in ("/", "/observe", "/now", "/runs", "/sessions", "/friction") or (
        len(parts) == 2 and parts[0] in ("runs", "sessions")
    ) or (len(parts) == 4 and parts[0] == "runs" and parts[2] == "tickets")


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


def _ticket_summary(ticket: dict, explanations: dict) -> dict:
    ticket_id = _text(ticket.get("id"))
    return {
        "id": ticket_id,
        "status": _text(ticket.get("status")),
        "executor": _text(ticket.get("executor")),
        "bound": _text(ticket.get("bound")),
        "claimed_at": _text(ticket.get("claimed_at")),
        "claimed_by": _text(ticket.get("claimed_by")),
        "depends_on": [_text(item) for item in ticket.get("depends_on", ())],
        "readiness": explanations.get(
            ticket_id,
            {"state": "unknown", "dependencies": [], "explanation": "ticket is unreadable"},
        ),
        "unreadable": bool(ticket.get("unreadable")),
    }


def _ticket_detail(ticket: dict, explanations: dict) -> dict:
    record = _ticket_summary(ticket, explanations)
    sections = ticket.get("sections") or {}
    record["sections"] = {
        name.lower(): _text(sections[name])
        for name in VISIBLE_SECTIONS
        if name in sections
    }
    record["verification"] = parse_verification(_text(sections.get("Verification")))
    return record


def _run_record(root: Path, run: str):
    tickets = run_tickets(root, run)
    if tickets is None:
        return None
    explanations = explain_run(tickets)
    records = [_ticket_summary(ticket, explanations) for ticket in tickets]
    return {
        "id": run,
        "active": any(ticket["status"] in ("claimed", "ready") for ticket in records),
        "tickets": records,
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
    explanations = explain_run(run_tickets(root, run) or []) if run else {}
    session_id = _text(query.get("session"))
    sessions = read_sessions(transcripts)
    friction = read_friction(root)
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
        "runs": [
            {
                "id": item["run"],
                "ticket_count": len(item["tickets"]),
                "active": any(t.get("status") in ("claimed", "ready") for t in item["tickets"]),
            }
            for item in discover(root)["runs"]
        ],
        "run": run_record,
        "ticket": _ticket_detail(ticket, explanations) if ticket is not None else None,
        "sessions": {
            "items": [_session_summary(item) for item in sessions["sessions"]],
            "diagnostics": [_text(item) for item in sessions["diagnostics"]],
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
