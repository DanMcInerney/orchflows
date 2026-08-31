"""Closed public Workflows projections."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from reader.scripts import (
    ui_workflows_catalog as catalog,
    ui_workflows_compositions as compositions,
    ui_workflows_skills as skills,
    ui_workflows_sources as sources,
)
from reader.scripts.ui_discovery import discover
from reader.scripts.ui_model import ACTIVE_STATUS

# Public definition routes are assembled by ui_api; this module owns projection
# data only and has no second route assembly mechanism.
ROUTE_SPECS = ()
PUBLIC_ROUTE_SPECS = (
    ("GET", "/api/v1/workflows", "project_workflow_catalog"),
    ("GET", "/api/v1/workflows/{workflow_id}", "project_workflow"),
    (
        "GET",
        "/api/v1/workflows/{workflow_id}/sources/{source_id}",
        "project_workflow_source",
    ),
    ("GET", "/api/v1/workflows/{workflow_id:path}", "project_workflow"),
)
CATALOG_SCHEMA = "orchflows.workflow-catalog.v1"
PACKAGE_ROOT = catalog.ROOT
LIBRARY_ROOT = (
    PACKAGE_ROOT if (PACKAGE_ROOT / "example-workflows").is_dir() else PACKAGE_ROOT / "lib"
)
SUMMARY_RELATIVE_PATH = Path("reader") / "docs" / "workflow-summary-manifest.json"


class WorkflowProjectionError(ValueError):
    """Canonical owners disagree about a closed public projection."""


def project_workflow_catalog(root=LIBRARY_ROOT, summary_path=None) -> dict:
    """Return the exact canonical catalog and UI-owned compact summaries."""

    root = Path(root)
    summary_path = (
        root / SUMMARY_RELATIVE_PATH if summary_path is None else Path(summary_path)
    )
    resolved_summary_path = summary_path.resolve()
    if not resolved_summary_path.is_file():
        raise WorkflowProjectionError(
            f"workflow summary manifest is missing: {resolved_summary_path}"
        )
    projected = catalog.project_catalog(root, resolved_summary_path)
    return {"schema": CATALOG_SCHEMA, "workflows": projected}


def project_workflow(root=LIBRARY_ROOT, workflow_id: str = ""):
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


def project_workflow_source(root=LIBRARY_ROOT, workflow_id: str = "", source_id: str = ""):
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
