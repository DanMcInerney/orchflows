"""Closed public Workflows projections plus the Phase-A compatibility seam."""

from __future__ import annotations

from collections import Counter

try:
    from scripts import (
        ui_workflows_catalog as catalog,
        ui_workflows_compositions as compositions,
        ui_workflows_skills as skills,
        ui_workflows_sources as sources,
    )
    from scripts.ui_discovery import discover
    from scripts.ui_model import ACTIVE_STATUS
except ImportError:
    import ui_workflows_catalog as catalog
    import ui_workflows_compositions as compositions
    import ui_workflows_skills as skills
    import ui_workflows_sources as sources
    from ui_discovery import discover
    from ui_model import ACTIVE_STATUS

# The Phase-A compatibility projector still owns no route. Public definition
# routes are separate so legacy route-assembly consumers keep their contract.
ROUTE_SPECS = ()
PUBLIC_ROUTE_SPECS = (
    ("GET", "/api/v1/workflows", "project_workflow_catalog"),
    ("GET", "/api/v1/workflows/{workflow_id}", "project_workflow"),
    (
        "GET",
        "/api/v1/workflows/{workflow_id}/sources/{source_id}",
        "project_workflow_source",
    ),
)
CATALOG_SCHEMA = "orchflows.workflow-catalog.v1"
ROOT = catalog.ROOT


class WorkflowProjectionError(ValueError):
    """Canonical owners disagree about a closed public projection."""


def project_workflow_catalog(root=ROOT, summary_path=None) -> dict:
    """Return the exact canonical catalog and UI-owned compact summaries."""

    projected = catalog.project_catalog(root, catalog.DEFAULT_SUMMARY if summary_path is None else summary_path)
    return {"schema": CATALOG_SCHEMA, "workflows": projected}


def project_workflow(root=ROOT, workflow_id: str = ""):
    """Return one exact T3 or T1 detail, or ``None`` for an unknown ID."""

    owner = next(
        (item for item in project_workflow_catalog(root)["workflows"] if item["id"] == workflow_id),
        None,
    )
    if owner is None:
        return None
    if owner["type"] == "composition":
        detail = compositions.project_composition(root, workflow_id)
    elif owner["type"] == "workflow-skill":
        detail = skills.project_workflow_skill(root, workflow_id)
    else:
        raise WorkflowProjectionError("workflow owner has an unknown type")
    inventory = set(sources.source_inventory(root, workflow_id))
    projected = {node["source_id"] for node in detail["nodes"] if "source_id" in node}
    if inventory != projected:
        raise WorkflowProjectionError("workflow source inventory is inconsistent")
    return detail


source_inventory = sources.source_inventory


def project_workflow_source(root=ROOT, workflow_id: str = "", source_id: str = ""):
    """Return one contained source projection and its closed status."""

    return sources.project_source(root, workflow_id, source_id)


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
