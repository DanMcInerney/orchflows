"""Read-only projection boundary for the friction payload."""

from __future__ import annotations

try:
    from scripts.ui_discovery import read_friction
except ImportError:
    from ui_discovery import read_friction

ROUTE_SPECS = (("GET", "/api/v1/friction", "project_friction"),)


def project_friction(root) -> dict:
    log = read_friction(root)
    return {
        "api_version": "v1",
        "entries": len(log["entries"]),
        "skipped": log["skipped"],
        "unreadable": len(log["unreadable"]),
    }
