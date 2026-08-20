"""Closed source inventory and contained reads for Workflows."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

try:
    from scripts import (
        ui_workflows_compositions as compositions,
        ui_workflows_identity as identity,
        ui_workflows_skills as skills,
    )
except ImportError:
    import ui_workflows_compositions as compositions
    import ui_workflows_identity as identity
    import ui_workflows_skills as skills


ROOT = Path(__file__).resolve().parent.parent
SOURCE_SCHEMA = "orchflows.workflow-source.v1"
SOURCE_ID_RE = re.compile(r"src_[A-Za-z0-9_-]{43}\Z")
WINDOWS_HOST_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:[A-Za-z]:[\\/]|\\\\)[^\s`\"'<>]+"
)
POSIX_HOST_PATH_RE = re.compile(
    r"(?<![:A-Za-z0-9_])/(?:Users|home|tmp|private|var|opt|srv|mnt|Volumes)"
    r"(?:/[^\s`\"'<>]+)+"
)
REDACTED_HOST_PATH = "[redacted-host-path]"
NOT_FOUND = {"error": {"code": "not_found", "message": "resource not found"}}
UNREADABLE = {
    "error": {
        "code": "unreadable_source",
        "message": "workflow source is unavailable",
    }
}


class WorkflowSourceError(ValueError):
    """A canonical workflow cannot form its closed source inventory."""


def _workflow_type(root: Path, workflow_id: object) -> str | None:
    try:
        identity.workflow_node_id(workflow_id)
    except identity.WorkflowIdentityError:
        return None
    if (root / "compositions" / workflow_id / "template.md").is_file():
        return "composition"
    if (root / "skills" / "workflows" / workflow_id / "SKILL.md").is_file():
        return "workflow-skill"
    return None


def _composition_paths(root: Path, workflow_id: str) -> set[str]:
    detail = compositions.project_composition(root, workflow_id)
    installed_skills, _ = skills.skill_index(root)
    installed = {f"lib/compositions/{workflow_id}/template.md"}
    for node in detail["nodes"]:
        if "source_id" not in node:
            continue
        if node["kind"] == "work":
            installed.add(f"lib/compositions/{workflow_id}/{node['label']}.md")
        elif node["kind"] == "skill":
            path = installed_skills.get(node["label"])
            if path is None:
                raise WorkflowSourceError("composition source inventory is inconsistent")
            installed.add(path)
    return installed


def _workflow_skill_paths(root: Path, workflow_id: str) -> set[str]:
    detail = skills.project_workflow_skill(root, workflow_id)
    installed_skills, _ = skills.skill_index(root)
    installed = {f"lib/skills/workflows/{workflow_id}/SKILL.md"}
    for node in detail["nodes"]:
        if "source_id" not in node or node["kind"] == "workflow":
            continue
        if node["kind"] == "skill":
            path = installed_skills.get(node["label"])
            if path is None:
                raise WorkflowSourceError("workflow source inventory is inconsistent")
            installed.add(path)
        elif node["kind"] == "script":
            installed.add(node["label"])
    return installed


def _inventory(root: Path, workflow_id: str, workflow_type: str) -> dict[str, str]:
    try:
        if workflow_type == "composition":
            paths = _composition_paths(root, workflow_id)
        else:
            paths = _workflow_skill_paths(root, workflow_id)
        return {identity.source_id(path): path for path in paths}
    except (
        compositions.WorkflowCompositionError,
        skills.WorkflowSkillError,
        identity.WorkflowIdentityError,
    ) as error:
        raise WorkflowSourceError("workflow source inventory is unreadable") from error


def source_inventory(root: Path = ROOT, workflow_id: str = "") -> tuple[str, ...]:
    """Return only the exhaustive opaque source IDs for one workflow."""

    root = Path(root)
    workflow_type = _workflow_type(root, workflow_id)
    if workflow_type is None:
        return ()
    return tuple(sorted(_inventory(root, workflow_id, workflow_type)))


def _resolved_source(root: Path, installed_path: str) -> Path | None:
    try:
        installed = identity.normalize_installed_path(installed_path)
    except identity.WorkflowIdentityError:
        return None
    root = root.resolve()
    if installed.startswith("lib/"):
        boundary = root
        candidate = root / installed.removeprefix("lib/")
    elif installed.startswith("bin/") and installed.count("/") == 1:
        boundary = (root / "scripts").resolve()
        candidate = boundary / installed.removeprefix("bin/")
    else:
        return None
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(boundary)
    except (OSError, RuntimeError, ValueError):
        return None
    return resolved if resolved.is_file() else None


def _redact(text: str, root: Path) -> tuple[str, bool]:
    delivered = text
    markers = {str(root.resolve()), root.resolve().as_posix()}
    for marker in sorted(markers, key=len, reverse=True):
        delivered = delivered.replace(marker, REDACTED_HOST_PATH)
    delivered = WINDOWS_HOST_PATH_RE.sub(REDACTED_HOST_PATH, delivered)
    delivered = POSIX_HOST_PATH_RE.sub(REDACTED_HOST_PATH, delivered)
    return delivered, delivered != text


def _language(installed_path: str) -> str:
    if installed_path.endswith(".md"):
        return "markdown"
    if installed_path.endswith(".py"):
        return "python"
    return "text"


def project_source(
    root: Path = ROOT,
    workflow_id: str = "",
    source_id: str = "",
) -> tuple[int, dict]:
    """Return one closed source response without accepting a filesystem path."""

    root = Path(root)
    if not isinstance(source_id, str) or SOURCE_ID_RE.fullmatch(source_id) is None:
        return 404, NOT_FOUND
    workflow_type = _workflow_type(root, workflow_id)
    if workflow_type is None:
        return 404, NOT_FOUND
    try:
        installed_path = _inventory(root, workflow_id, workflow_type).get(source_id)
    except WorkflowSourceError:
        return 422, UNREADABLE
    if installed_path is None:
        return 404, NOT_FOUND
    path = _resolved_source(root, installed_path)
    if path is None:
        return 404, NOT_FOUND
    try:
        raw = path.read_bytes()
        text = raw.decode("utf-8")
    except (OSError, UnicodeError):
        return 422, UNREADABLE
    delivered, redacted = _redact(text, root)
    return 200, {
        "schema": SOURCE_SCHEMA,
        "id": source_id,
        "text": delivered,
        "sha256": hashlib.sha256(delivered.encode("utf-8")).hexdigest(),
        "language": _language(installed_path),
        "redacted": redacted,
    }
