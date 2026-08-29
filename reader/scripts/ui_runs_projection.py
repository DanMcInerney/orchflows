"""Read-only projection boundary for run and ticket payloads."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from reader.scripts.ui_discovery import (
    discover,
    find_ticket,
    graph_input,
    identity_diagnostics,
    read_events,
    read_friction,
    run_tickets,
)
from reader.scripts.ui_layout import graph_layout
from reader.scripts.ui_model import ACTIVE_STATUS, parse_verification

API_VERSION = "v1"

ROUTE_SPECS = (
    ("GET", "/api/v1/runs", "project_runs"),
    ("GET", "/api/v1/runs/{run}", "project_run"),
    ("GET", "/api/v1/runs/{run}/tickets/{ticket}", "project_ticket"),
)


def _ticket_record(ticket: dict) -> dict:
    verification = parse_verification(ticket["sections"].get("Verification", ""))
    return {
        "id": ticket["id"],
        "status": ticket["status"],
        "executor": ticket["executor"],
        "bound": ticket["bound"],
        "claimed_at": ticket["claimed_at"],
        "claimed_by": ticket["claimed_by"],
        "depends_on": list(ticket["depends_on"]),
        "evidence": {
            "state": verification["state"],
            "entries": len(verification["rows"]),
        },
        "source": {"file_id": ticket["file_id"], "unreadable": ticket["unreadable"]},
    }


def _run_record(root: Path, run: str, tickets: list) -> dict:
    layout = graph_layout(*graph_input(tickets))
    events = read_events(root, run)
    return {
        "api_version": API_VERSION,
        "run": run,
        "active": any(ticket["status"] == ACTIVE_STATUS for ticket in tickets),
        "nodes": [
            {"id": ticket["id"], "label": ticket["id"], "status": ticket["status"]}
            for ticket in tickets
        ],
        "edges": [
            {
                "id": "{0}->{1}".format(source, target),
                "source": source,
                "target": target,
            }
            for source, target in layout["edges"]
        ],
        "diagnostics": identity_diagnostics(tickets) + layout["diagnostics"],
        "events": {
            "present": events is not None,
            "entries": len(events["entries"]) if events else 0,
            "skipped": events["skipped"] if events else 0,
            "unreadable": bool(events and events["unreadable"]),
        },
    }


def project_runs(root: Path) -> dict:
    found = discover(root)
    projected = []
    for item in found["runs"]:
        counts = Counter(ticket["status"] for ticket in item["tickets"])
        projected.append({
            "id": item["run"],
            "ticket_count": len(item["tickets"]),
            "active": bool(counts.get(ACTIVE_STATUS)),
            "statuses": dict(sorted(counts.items())),
        })
    return {"api_version": API_VERSION, "runs": projected, "empty": found["empty"]}


def project_run(root: Path, run: str):
    tickets = run_tickets(root, run)
    return None if tickets is None else _run_record(root, run, tickets)


def project_ticket(root: Path, run: str, ticket_id: str):
    ticket = find_ticket(root, run, ticket_id)
    if ticket is None:
        return None
    friction = read_friction(root)
    linked = sum(
        1
        for entry in friction["entries"]
        if entry.get("run") == run and entry.get("ticket") == ticket_id
    )
    return {
        "api_version": API_VERSION,
        "run": run,
        "ticket": _ticket_record(ticket),
        "linked_friction": linked,
        "friction_health": {
            "skipped": friction["skipped"],
            "unreadable": list(friction["unreadable"]),
        },
    }
