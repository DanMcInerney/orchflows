"""Closed, read-only projection for the rendered observability experience."""

from __future__ import annotations

import json
import re
from pathlib import Path

from reader.scripts import ui_friction_projection, ui_runs_projection, ui_sessions_projection
from reader.scripts.ui_discovery import (
    discover, find_ticket, graph_input, identity_diagnostics, read_events,
    read_friction, read_run_identity, read_sessions, run_tickets,
)
from reader.scripts.ui_layout import DIAGNOSTIC_CYCLE, DIAGNOSTIC_DANGLING, graph_layout
from reader.scripts.ui_model import _scalar, parse_verification
from reader.scripts.ui_readiness import explain_run
from reader.scripts.ui_sessions import DIAGNOSTIC_UNDECODABLE_SLUG

SCHEMA = "orchflows.experience.v1"
SPA_ROUTE_PATTERNS = (
    "/", "/observe", "/now", "/workflows", "/workflows/{workflow}",
    "/workflows/{workflow}/sources/{source}", "/runs", "/runs/{run}",
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
# The current ticket grammar first, then the section names the sink still
# holds. This viewer is the one consumer that reads user state written under
# earlier contracts -- history is never rewritten (contracts/work-item.md) --
# and it writes nothing, so reading a name no writer produces any more shows a
# reader what is there rather than reviving a filing route.
VISIBLE_SECTIONS = (
    "Goal", "Context", "Details", "Report",
    "Result", "Verification", "Feedback", "Risks", "Handoff",
)
REPORT_SECTION = "Report"
FRICTION_FIELDS = ("ts", "host", "observed", "expected", "run", "ticket")
WINDOWS_HOST_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:[A-Za-z]:[\\/]|\\\\)[^\s`\"'<>]+"
)
POSIX_HOST_PATH_RE = re.compile(
    r"(?<![:A-Za-z0-9_])/(?:Users|home|tmp|private|var|opt|srv|mnt|Volumes)(?:/[^\s`\"'<>]+)+"
)
REDACTED_HOST_PATH = "[redacted-host-path]"
OPAQUE_ARTIFACT_RE = re.compile(r"^art_[A-Za-z0-9_-]{43}$")
CANONICAL_WORKFLOW_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,126}$")
VIEW_SLICES = {
    "now": ("orchflows.now.v1", ("runs",)),
    "run-map": ("orchflows.run-map.v1", ("runs", "run")),
    "inspector": ("orchflows.inspector.v1", ("run", "ticket")),
    "sessions": ("orchflows.sessions.v1", ("sessions",)),
    "session-graph": ("orchflows.session-graph.v1", ("session",)),
    "friction": ("orchflows.friction.v1", ("friction",)),
}


def is_spa_path(path: str) -> bool:
    parts = path.strip("/").split("/") if path != "/" else []
    return (
        path in ("/", "/observe", "/now", "/workflows", "/runs", "/sessions", "/friction")
        or (len(parts) == 2 and parts[0] in ("workflows", "runs", "sessions"))
        or (len(parts) == 4 and parts[0] == "runs" and parts[2] == "tickets")
        or (len(parts) == 4 and parts[0] == "workflows" and parts[2] == "sources")
    )


def browser_navigation(path: str, headers) -> bool:
    """Distinguish document navigation from API requests."""

    accept = next((value for name, value in headers.items() if name.lower() == "accept"), "")
    return path == "/observe" or "text/html" in accept.lower()


def _text(value) -> str:
    return value if isinstance(value, str) else "" if value is None else str(value)


def _rationale_identity(value) -> dict:
    try:
        identity = json.loads(_text(value))
    except (TypeError, ValueError):
        identity = None
    available = (
        isinstance(identity, dict)
        and set(identity) == {"kind", "id"}
        and identity.get("kind") == "artifact"
        and isinstance(identity.get("id"), str)
        and OPAQUE_ARTIFACT_RE.fullmatch(identity["id"]) is not None
    )
    return {
        "state": "available" if available else "unavailable",
        "identity": identity if available else None,
    }


def _run_identity(root: Path, run: str):
    """One run's ``run.json`` only when it names the run it sits under: a
    misfiled document lends its folder and completion time to no one."""

    identity = read_run_identity(root, run)
    return identity if identity and _scalar(identity.get("run")) == run else None


def _run_workflow(root: Path, run: str):
    workflow = _scalar((_run_identity(root, run) or {}).get("workflow"))
    return workflow if CANONICAL_WORKFLOW_RE.fullmatch(workflow) else None


def _leaf(value) -> str:
    """The last path segment of a recorded name -- the only projectable part
    of a folder identity, a session's cwd and a run's ``project.name`` alike.
    The sink is untrusted, so a misrecorded path degrades to its leaf."""

    value = _scalar(value).rstrip("/\\")
    return re.split(r"[\\/]", value)[-1] if value else ""


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
    record["client"] = ""
    record["project"] = _leaf(session.get("named_cwd"))
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
    record["judgment"] = {
        "criteria": [
            {
                "criterion": _text(row.get("#")),
                "verdict": _text(row.get("verdict")),
                "oracle": _text(row.get("oracle")),
                "oracle_class": _text(row.get("class")),
                "evidence": _text(row.get("evidence")),
            }
            for row in record["verification"]["rows"]
        ],
        "result": _text(sections.get(REPORT_SECTION)) or _text(sections.get("Result")),
        "feedback": _text(sections.get("Feedback")),
        "risks": _text(sections.get("Risks")),
        "rationale": _rationale_identity(sections.get("Rationale")),
    }
    record["context"] = _redact_host_paths(_text(sections.get("Context")), root, ticket)
    record["details"] = _redact_host_paths(_text(ticket.get("details")), root, ticket)
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


def _execution_position(tickets) -> dict:
    def position(ticket: dict) -> dict:
        return {
            "id": ticket["id"],
            "status": ticket["status"],
            "state": _text(ticket.get("readiness", {}).get("state")),
        }

    current = [
        ticket for ticket in tickets
        if ticket.get("readiness", {}).get("state") == "running"
    ]
    current_ids = {ticket["id"] for ticket in current}
    if current_ids:
        upcoming = [
            ticket for ticket in tickets
            if ticket.get("readiness", {}).get("state") != "complete"
            and current_ids.intersection(ticket.get("depends_on", ()))
        ]
    else:
        upcoming = [
            ticket for ticket in tickets
            if ticket.get("readiness", {}).get("state") == "ready"
        ]
    return {
        "current": [position(ticket) for ticket in current],
        "next": [position(ticket) for ticket in upcoming],
    }


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
    workflow = _run_workflow(root, run)
    return {
        "id": run,
        "workflow": {
            "state": "available" if workflow is not None else "unavailable",
            "id": workflow or "",
        },
        "execution": _execution_position(records),
        "active": any(ticket["status"] in ("claimed", "ready") for ticket in records),
        "tickets": records,
        "diagnostics": diagnostics,
        "counts": {
            status: sum(1 for ticket in records if ticket["status"] == status)
            for status in sorted({ticket["status"] for ticket in records})
        },
    }


def _selected_run(root: Path, requested: str) -> str:
    indexed = ui_runs_projection.project_runs(root)["runs"]
    if requested in {item["id"] for item in indexed}:
        return requested
    found = discover(root)
    run_ids = [item["run"] for item in found["runs"]]
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
    value = (
        ui_sessions_projection.project_session(transcripts, session_id)
        if session_id
        else None
    )
    if value is None:
        return None
    session = value["session"]
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


def _run_summaries(root: Path) -> list:
    summaries = []
    for found in discover(root)["runs"]:
        detail = _run_record(root, found["run"])
        identity = _run_identity(root, found["run"]) or {}
        project = identity.get("project")
        events = read_events(root, found["run"])
        goal = next(
            (
                _text(item.get("goal"))
                for item in found["tickets"]
                if item.get("goal")
            ),
            "",
        )
        summaries.append({
            "id": found["run"],
            "workflow": detail["workflow"] if detail else {"state": "unavailable", "id": ""},
            "execution": detail["execution"] if detail else {"current": [], "next": []},
            "ticket_count": len(found["tickets"]),
            "active": bool(detail and detail["active"]),
            "objective": goal,
            "repository": _leaf(project.get("name")) if isinstance(project, dict) else "",
            # No projection-safe client source exists; held open, not guessed.
            "client": "",
            "terminal_at": _scalar(identity.get("terminal_at")),
            "terminal_status": _scalar(identity.get("terminal_status")),
            "last_activity": _text(((events or {}).get("entries") or [{}])[0].get("ts")),
            "unreadable": any(bool(item.get("unreadable")) for item in found["tickets"]),
            "tickets": detail["tickets"] if detail else [],
        })
    return summaries


def _run_selection(root: Path, query) -> tuple:
    run = _selected_run(root, _text(query.get("run")))
    run_record = _run_record(root, run) if run else None
    ticket_id = _text(query.get("ticket"))
    ticket = find_ticket(root, run, ticket_id) if run and ticket_id else None
    ticket_record = (
        _ticket_detail(ticket, run_record, root, run) if ticket is not None else None
    )
    return run, run_record, ticket_id, ticket_record


def _sessions_index(transcripts) -> dict:
    sessions = read_sessions(transcripts)
    return {
        "items": [_session_list_summary(item) for item in sessions["sessions"]],
        "diagnostics": [_session_diagnostic(item) for item in sessions["diagnostics"]],
        "empty": bool(sessions["empty"]),
    }


def _friction_projection(root: Path) -> dict:
    friction = read_friction(root)
    health = ui_friction_projection.project_friction(root)
    return {
        "items": [
            {
                field: _text(entry.get(field))
                for field in FRICTION_FIELDS
                if entry.get(field) is not None
            }
            for entry in friction["entries"]
        ],
        "skipped": int(health["skipped"]),
        "unreadable": int(health["unreadable"]),
    }


def project_experience(root, transcripts=None, query=None) -> dict:
    """Project the entire closed UI substrate without mutating either root."""

    root = Path(root).resolve()
    query = query or {}
    requested_view = _text(query.get("view"))
    view = requested_view if requested_view in VIEW_IDS else "now"
    run, run_record, ticket_id, ticket = _run_selection(root, query)
    session_id = _text(query.get("session"))
    session = _selected_session(transcripts, session_id)
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
            "session": session_id if session is not None else "",
        },
        "runs": _run_summaries(root),
        "run": run_record,
        "ticket": ticket,
        "sessions": _sessions_index(transcripts),
        "session": session,
        "friction": _friction_projection(root),
    }


def project_view(root, transcripts, view: str, query=None) -> dict:
    """Return one closed view slice without opening another domain root."""

    root = Path(root).resolve()
    query = query or {}
    schema = VIEW_SLICES[view][0]
    if view == "now":
        return {"schema": schema, "runs": _run_summaries(root)}
    if view == "run-map":
        _run, run_record, _ticket_id, _ticket = _run_selection(root, query)
        return {
            "schema": schema,
            "runs": _run_summaries(root),
            "run": run_record,
        }
    if view == "inspector":
        _run, run_record, _ticket_id, ticket = _run_selection(root, query)
        return {"schema": schema, "run": run_record, "ticket": ticket}
    if view == "sessions":
        return {"schema": schema, "sessions": _sessions_index(transcripts)}
    if view == "session-graph":
        return {
            "schema": schema,
            "session": _selected_session(transcripts, _text(query.get("session"))),
        }
    return {"schema": schema, "friction": _friction_projection(root)}
