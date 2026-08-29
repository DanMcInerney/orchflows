"""Read-only projection boundary for the current Now payload."""

from __future__ import annotations

import hashlib
import json

from reader.scripts.ui_discovery import discover, graph_input, run_tickets
from reader.scripts.ui_layout import graph_layout
from reader.scripts.ui_model import ACTIVE_STATUS

ROUTE_SPECS = ()


def _run_graph(root, run: str) -> dict:
    tickets = run_tickets(root, run) or []
    layout = graph_layout(*graph_input(tickets))
    return {
        "active": any(ticket["status"] == ACTIVE_STATUS for ticket in tickets),
        "nodes": [
            {"id": ticket["id"], "label": ticket["id"], "status": ticket["status"]}
            for ticket in tickets
        ],
        "edges": [
            {"id": source + "->" + target, "source": source, "target": target}
            for source, target in layout["edges"]
        ],
    }


def project_observe(root, requested_run: str) -> dict:
    """Project the selected run's glanceable graph without exposing paths."""

    found = discover(root)
    names = [item["run"] for item in found["runs"]]
    selected = requested_run if requested_run in names else ""
    if not selected:
        selected = next(
            (
                item["run"]
                for item in found["runs"]
                if any(ticket["status"] == ACTIVE_STATUS for ticket in item["tickets"])
            ),
            names[0] if names else "",
        )
    graph = _run_graph(root, selected) if selected else {
        "active": False,
        "nodes": [],
        "edges": [],
    }
    basis = {key: graph[key] for key in ("active", "nodes", "edges")}
    encoded = json.dumps(
        basis, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    encoded = encoded.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
    encoded = encoded.encode("utf-8")
    revision = hashlib.sha256(encoded).hexdigest()
    return {"revision": revision, **basis}
