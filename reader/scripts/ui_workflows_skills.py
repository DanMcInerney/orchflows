"""Derive exact T1 workflow-skill calls from canonical inline code spans."""

from __future__ import annotations

import re
from pathlib import Path

from scripts._bootstrap import ROOT
from scripts.tickets_format import _parse_frontmatter
from reader.scripts import ui_workflows_identity as identity

# ``ROOT`` reads the same directory ``_bootstrap.ROOT`` names in both the
# checkout and the installed-library layout: this file ships alongside
# ``scripts/_bootstrap.py`` at a fixed relative depth in the reader
# payload (installer/planning_support.py's lib_copies), and every caller
# here already imports ``scripts.*`` unconditionally, so ``scripts`` is
# always importable by the time this module loads.
DETAIL_SCHEMA = "orchflows.workflow-detail.v1"
NODE_KIND_ORDER = {"workflow": 0, "work": 1, "skill": 2, "script": 3}
INLINE_CODE_RE = re.compile(r"(?<!`)`([^`]+)`(?!`)", re.DOTALL)
SKILL_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9._-])(orch-[A-Za-z0-9][A-Za-z0-9._-]*)(?![A-Za-z0-9._-])"
)
SCRIPT_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9._/\\-])"
    r"([A-Za-z0-9_.-]+(?:[/\\][A-Za-z0-9_.-]+)*\.py)"
    r"(?![A-Za-z0-9._/\\-])"
)
DIAGNOSTIC_MESSAGES = {
    "duplicate-node": "Canonical source declares this node more than once.",
    "unresolved-reference": "The canonical call does not resolve to an installed source.",
}


class WorkflowSkillError(ValueError):
    """A workflow-skill source cannot form the exact detail projection."""


def workflow_skill_path(root: Path, workflow_id: str) -> Path | None:
    """Locate one callable skill across the installed tier layout.

    Two homes, one shape. A T1 callable lives under its tier in ``skills/``; a
    workflow — a skill whose prose calls those callables — lives in
    ``example-workflows/<name>/SKILL.md``. Neither is a template any more,
    so the lookup is the same file name in both places.
    """

    root = Path(root)
    candidates = sorted(
        (root / "skills").glob(f"*/{workflow_id}/SKILL.md"),
        key=lambda path: path.relative_to(root).as_posix(),
    )
    candidates.append(root / "example-workflows" / workflow_id / "SKILL.md")
    for path in candidates:
        if _contained_file(root, path):
            return path
    return None


def _contained_file(root: Path, path: Path) -> bool:
    return identity.contained_file(root, path)


def _read_skill(root: Path, path: Path) -> tuple[dict, str]:
    try:
        text = identity.read_contained_text(root, path)
        fields = _parse_frontmatter(text)
    except (identity.ContainedFileError, ValueError) as error:
        raise WorkflowSkillError("workflow skill source is unreadable") from error
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise WorkflowSkillError("workflow skill frontmatter is malformed")
    for index, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            return fields, "".join(lines[index + 1 :])
    raise WorkflowSkillError("workflow skill frontmatter is malformed")


def skill_index(root: Path) -> tuple[dict[str, str], set[str]]:
    """Return canonical skill and standard names mapped to installed lib paths.

    Standards belong here because a callable call stamps exactly one of them, and
    the standard is what carries that call's standard. Leaving them out reported
    every workflow's own standard as an unresolved reference.
    """

    root = Path(root)
    resolved = {}
    duplicates = set()
    paths = sorted(
        list((root / "skills").glob("*/*/SKILL.md"))
        + list((root / "standards").glob("*/SKILL.md")),
        key=lambda path: path.relative_to(root).as_posix(),
    )
    for path in paths:
        if not _contained_file(root, path):
            continue
        try:
            fields, _ = _read_skill(root, path)
        except WorkflowSkillError:
            continue
        name = fields.get("name")
        if not isinstance(name, str) or name != path.parent.name:
            continue
        installed_path = "lib/" + path.relative_to(root).as_posix()
        if name in resolved:
            duplicates.add(name)
            continue
        resolved[name] = installed_path
    return resolved, duplicates


def _script_path(root: Path, token: str) -> tuple[str, bool]:
    portable = token.replace("\\", "/")
    try:
        normalized = identity.normalize_installed_path(portable)
    except identity.WorkflowIdentityError:
        return portable, False
    if "/" not in normalized:
        installed = "bin/" + normalized
    else:
        installed = normalized
    try:
        identity.script_node_id(installed)
    except identity.WorkflowIdentityError:
        return installed, False
    location = identity.installed_source(root, installed)
    if location is None:
        return installed, False
    boundary, source = location
    return installed, _contained_file(boundary, source)


def _calls(root: Path, body: str) -> tuple[set[str], dict[str, bool]]:
    skills = set()
    scripts = {}
    for match in INLINE_CODE_RE.finditer(body):
        span = match.group(1)
        skills.update(SKILL_TOKEN_RE.findall(span))
        for token in SCRIPT_TOKEN_RE.findall(span):
            installed_path, resolved = _script_path(root, token)
            scripts[installed_path] = scripts.get(installed_path, False) or resolved
    return skills, scripts


def _edge(kind: str, source: str, target: str, label: str) -> dict:
    return {
        "id": identity.edge_id(kind, source, target),
        "kind": kind,
        "from": source,
        "to": target,
        "label": label,
    }


def project_workflow_skill(root: Path = ROOT, workflow_id: str = "") -> dict:
    """Project one T1 workflow skill without treating prose as calls."""

    root = Path(root)
    try:
        identity.workflow_node_id(workflow_id)
    except identity.WorkflowIdentityError as error:
        raise WorkflowSkillError("workflow skill identity is malformed") from error
    path = workflow_skill_path(root, workflow_id)
    if path is None:
        raise WorkflowSkillError("workflow skill source is unreadable")
    fields, body = _read_skill(root, path)
    if fields.get("name") != workflow_id:
        raise WorkflowSkillError("workflow skill identity is malformed")

    workflow_node = identity.workflow_node_id(workflow_id)
    workflow_source = "lib/" + path.relative_to(root).as_posix()
    nodes = {
        workflow_node: {
            "id": workflow_node,
            "kind": "workflow",
            "label": workflow_id,
            "source_id": identity.source_id(workflow_source),
        }
    }
    edges = {}
    diagnostics = {}

    def diagnose(code: str, subject_id: str) -> None:
        diagnostics[(code, subject_id)] = {
            "code": code,
            "subject_id": subject_id,
            "message": DIAGNOSTIC_MESSAGES[code],
        }

    installed_skills, duplicate_skills = skill_index(root)
    skill_calls, script_calls = _calls(root, body)
    for name in sorted(skill_calls):
        node_id = identity.skill_node_id(name)
        node = {"id": node_id, "kind": "skill", "label": name}
        installed_path = installed_skills.get(name)
        if installed_path is None:
            diagnose("unresolved-reference", node_id)
        else:
            node["source_id"] = identity.source_id(installed_path)
        if name in duplicate_skills:
            diagnose("duplicate-node", node_id)
        nodes[node_id] = node
        edge = _edge("skill-call", workflow_node, node_id, "calls skill")
        edges[edge["id"]] = edge

    for installed_path in sorted(script_calls):
        node_id = identity.script_node_id(installed_path)
        node = {"id": node_id, "kind": "script", "label": installed_path}
        if script_calls[installed_path]:
            node["source_id"] = identity.source_id(installed_path)
        else:
            diagnose("unresolved-reference", node_id)
        nodes[node_id] = node
        edge = _edge("script-call", workflow_node, node_id, "calls script")
        edges[edge["id"]] = edge

    ordered_nodes = sorted(
        nodes.values(), key=lambda node: (NODE_KIND_ORDER[node["kind"]], node["id"])
    )
    ordered_edges = sorted(
        edges.values(),
        key=lambda edge: (edge["from"], edge["kind"], edge["to"], edge["id"]),
    )
    return {
        "schema": DETAIL_SCHEMA,
        "id": workflow_id,
        "type": "workflow-skill",
        "nodes": ordered_nodes,
        "edges": ordered_edges,
        "relations": [dict(edge) for edge in ordered_edges],
        "diagnostics": [diagnostics[key] for key in sorted(diagnostics)],
    }


__all__ = (
    "WorkflowSkillError",
    "workflow_skill_path",
    "skill_index",
    "project_workflow_skill",
)
