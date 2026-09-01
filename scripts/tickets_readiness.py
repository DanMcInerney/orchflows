"""Pure ticket readiness facts shared by lifecycle admission and the reader.

A dependency is satisfied when it is terminal *and* left a Result behind,
which is ``tickets_format.RESULT_BEARING_STATES`` and never a literal here:
admission accepts a `limited` dependency for exactly the same reason -- part
of the Goal delivered with honest accounting is still evidence the next item
is written against -- and this module went on requiring `complete` after it
stopped, so the reader called a promotable item blocked and the grader
admitted it.
"""

from __future__ import annotations

if __package__:
    from .tickets_format import (
        RESULT_BEARING_STATES, VALID_STATUSES,
    )
else:
    from tickets_format import (
        RESULT_BEARING_STATES, VALID_STATUSES,
    )


def readiness_facts(ticket: dict, tickets: dict) -> dict:
    """Return canonical status and dependency facts without writing state."""

    dependencies = [str(value) for value in (ticket.get("depends_on") or [])]
    dangling = [value for value in dependencies if value not in tickets]
    incomplete = [
        value
        for value in dependencies
        if value in tickets
        and str(tickets[value].get("status") or "") not in RESULT_BEARING_STATES
    ]
    status = str(ticket.get("status") or "")
    return {
        "status_valid": status in VALID_STATUSES,
        "dangling": dangling,
        "incomplete": incomplete,
        "dependencies_complete": not dangling and not incomplete,
    }
