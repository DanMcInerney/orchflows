"""Phase-A boundary for the current Workflows compatibility payload."""

from __future__ import annotations

from collections import Counter

try:
    from scripts.ui_discovery import discover
    from scripts.ui_model import ACTIVE_STATUS
except ImportError:
    from ui_discovery import discover
    from ui_model import ACTIVE_STATUS

# Workflows still uses the runs route in Phase A. The facade must not
# register a second owner for that method/path pair.
ROUTE_SPECS = ()


def project_workflows(root) -> dict:
    """Return the existing run-summary payload until Workflows Phase B."""

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
    return {"api_version": "v1", "runs": projected, "empty": found["empty"]}
