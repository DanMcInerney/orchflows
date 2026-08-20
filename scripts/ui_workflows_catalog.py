"""Derive the Workflows catalog from canonical repository owners."""

from __future__ import annotations

import json
from pathlib import Path

try:
    from scripts.tickets_format import _parse_frontmatter
    from scripts import ui_workflows_identity as identity
    from scripts.ui_workflows_summary import SummaryManifestError, validate_manifest
except ImportError:
    from tickets_format import _parse_frontmatter
    import ui_workflows_identity as identity
    from ui_workflows_summary import SummaryManifestError, validate_manifest


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SUMMARY = ROOT / "docs" / "ui" / "workflow-summary-manifest.json"
COMPOSITION_ENTRIES = frozenset({"routed", "named"})


class WorkflowCatalogError(ValueError):
    """A canonical workflow owner cannot form the closed catalog."""


def _text_field(fields: dict, key: str, subject: str) -> str:
    value = fields.get(key)
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or "\n" in value
        or "\r" in value
    ):
        raise WorkflowCatalogError(f"{subject} has an invalid {key}")
    return value


def _owner(root: Path, path: Path, workflow_type: str) -> dict:
    try:
        fields = _parse_frontmatter(identity.read_contained_text(root, path))
    except (identity.ContainedFileError, ValueError) as error:
        raise WorkflowCatalogError("workflow owner is unreadable") from error
    name = _text_field(fields, "name", path.parent.name)
    if name != path.parent.name:
        raise WorkflowCatalogError("workflow owner name does not match its package")
    description = _text_field(fields, "description", name)
    if workflow_type == "composition":
        entry = _text_field(fields, "entry", name)
        if entry not in COMPOSITION_ENTRIES:
            raise WorkflowCatalogError("composition has an unknown entry mode")
    else:
        entry = "callable"
    return {
        "id": name,
        "type": workflow_type,
        "entry": entry,
        "description": description,
    }


def _canonical_owners(root: Path) -> list[dict]:
    compositions = sorted(
        (root / "compositions").glob("*/template.md"),
        key=lambda path: path.parent.name,
    )
    workflow_skills = sorted(
        (root / "skills" / "workflows").glob("*/SKILL.md"),
        key=lambda path: path.parent.name,
    )
    owners = [_owner(root, path, "composition") for path in compositions]
    owners.extend(_owner(root, path, "workflow-skill") for path in workflow_skills)
    ids = [owner["id"] for owner in owners]
    if len(ids) != len(set(ids)):
        raise WorkflowCatalogError("canonical workflow identities are not unique")
    return owners


def _load_summary(root: Path, path: Path, workflow_ids: set[str]) -> dict:
    try:
        package_root = identity.workflow_roots(root).package
        candidate = json.loads(identity.read_contained_text(package_root, path))
        return validate_manifest(candidate, workflow_ids)
    except (
        identity.ContainedFileError,
        json.JSONDecodeError,
        SummaryManifestError,
    ) as error:
        raise WorkflowCatalogError("workflow summary manifest is invalid") from error


def project_catalog(
    root: Path = ROOT,
    summary_path: Path = DEFAULT_SUMMARY,
) -> list[dict]:
    """Return the exact catalog, joining UI summaries by canonical owner ID."""

    owners = _canonical_owners(Path(root))
    manifest = _load_summary(
        Path(root),
        Path(summary_path),
        {owner["id"] for owner in owners},
    )
    return [
        {**owner, "summary": manifest["workflows"][owner["id"]]}
        for owner in owners
    ]
