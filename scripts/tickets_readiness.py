"""Pure ticket readiness facts shared by lifecycle admission and the reader."""

from __future__ import annotations

if __package__:
    from .tickets_format import CHECKED_BY_KEY, VALID_STATUSES
else:
    from tickets_format import CHECKED_BY_KEY, VALID_STATUSES


def readiness_facts(ticket: dict, tickets: dict) -> dict:
    """Return canonical status and dependency facts without writing state."""

    dependencies = [str(value) for value in (ticket.get("depends_on") or [])]
    dangling = [value for value in dependencies if value not in tickets]
    ticket_id = str(ticket.get("id") or "")
    checker_target = ticket_id[:-len(".check")] if ticket_id.endswith(".check") else None
    incomplete = [
        value
        for value in dependencies
        if value in tickets
        and (
            tickets[value].get("status") != "complete"
            or (
                str(tickets[value].get("independence") or "checker") == "checker"
                and not str(tickets[value].get(CHECKED_BY_KEY) or "").strip()
                and checker_target != value
            )
        )
    ]
    status = str(ticket.get("status") or "")
    return {
        "status_valid": status in VALID_STATUSES,
        "dangling": dangling,
        "incomplete": incomplete,
        "dependencies_complete": not dangling and not incomplete,
    }
