"""Derive exact T3 composition topology from manifests and work stubs."""

from __future__ import annotations

from pathlib import Path

try:
    from scripts.tickets_format import _parse_frontmatter
    from scripts import ui_workflows_identity as identity
except ImportError:
    from tickets_format import _parse_frontmatter
    import ui_workflows_identity as identity


ROOT = Path(__file__).resolve().parent.parent
DETAIL_SCHEMA = "orchflows.workflow-detail.v1"
NODE_KIND_ORDER = {"workflow": 0, "work": 1, "skill": 2, "script": 3}
DIAGNOSTIC_MESSAGES = {
    "duplicate-node": "Canonical source declares this node more than once.",
    "dangling-edge": "A dependency names work that this composition does not declare.",
    "unresolved-reference": "The canonical executor does not resolve to an installed skill.",
}


class WorkflowCompositionError(ValueError):
    """A composition source cannot form the exact detail projection."""


def _fields(path: Path) -> dict:
    try:
        return _parse_frontmatter(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        raise WorkflowCompositionError("composition source is unreadable") from error


def _canonical_name(value: object, subject: str) -> str:
    try:
        if subject == "workflow":
            identity.workflow_node_id(value)
        else:
            identity.skill_node_id(value)
    except identity.WorkflowIdentityError as error:
        raise WorkflowCompositionError(f"composition has an invalid {subject}") from error
    return value


def _stub(path: Path, workflow: str) -> dict:
    fields = _fields(path)
    stub_id = fields.get("id")
    executor = fields.get("executor")
    try:
        identity.work_node_id(workflow, stub_id)
        identity.skill_node_id(executor)
    except identity.WorkflowIdentityError as error:
        raise WorkflowCompositionError("composition has a malformed work stub") from error
    dependencies = fields.get("depends_on")
    if not isinstance(dependencies, list):
        raise WorkflowCompositionError("composition depends_on must be a list")
    for dependency in dependencies:
        try:
            identity.work_node_id(workflow, dependency)
        except identity.WorkflowIdentityError as error:
            raise WorkflowCompositionError("composition has a malformed dependency") from error
    bound = fields.get("bound")
    if executor == "orch-loop" and (
        not isinstance(bound, str) or not bound or bound != bound.strip()
    ):
        raise WorkflowCompositionError("loop work must declare its bound")
    installed_path = f"lib/compositions/{workflow}/{path.name}"
    return {
        "id": stub_id,
        "executor": executor,
        "depends_on": dependencies,
        "bound": bound,
        "installed_path": installed_path,
    }


def _skill_index(root: Path) -> tuple[dict[str, str], set[str]]:
    resolved = {}
    duplicates = set()
    paths = sorted(
        (root / "skills").glob("*/*/SKILL.md"),
        key=lambda path: path.relative_to(root).as_posix(),
    )
    for path in paths:
        fields = _fields(path)
        name = fields.get("name")
        if not isinstance(name, str) or name != path.parent.name:
            continue
        installed_path = "lib/" + path.relative_to(root).as_posix()
        if name in resolved:
            duplicates.add(name)
            continue
        resolved[name] = installed_path
    return resolved, duplicates


def _edge(kind: str, source: str, target: str, label: str) -> dict:
    return {
        "id": identity.edge_id(kind, source, target),
        "kind": kind,
        "from": source,
        "to": target,
        "label": label,
    }


def _loop_label(workflow: str, stub_id: str, bound: str) -> str:
    if workflow == "evolve" and stub_id == "02-campaign":
        return (
            "Write candidates; verify eligibility; score blind; select by "
            f"the frozen rule; repeat {bound}"
        )
    return f"Repeat {bound}"


def project_composition(root: Path = ROOT, workflow_id: str = "") -> dict:
    """Project one composition without inventing or repairing topology."""

    root = Path(root)
    workflow_id = _canonical_name(workflow_id, "workflow")
    directory = root / "compositions" / workflow_id
    template = directory / "template.md"
    template_fields = _fields(template)
    if template_fields.get("name") != workflow_id:
        raise WorkflowCompositionError("composition manifest identity is malformed")

    diagnostics = {}

    def diagnose(code: str, subject_id: str) -> None:
        diagnostics[(code, subject_id)] = {
            "code": code,
            "subject_id": subject_id,
            "message": DIAGNOSTIC_MESSAGES[code],
        }

    nodes = {}
    workflow_node = identity.workflow_node_id(workflow_id)
    template_source = f"lib/compositions/{workflow_id}/template.md"
    nodes[workflow_node] = {
        "id": workflow_node,
        "kind": "workflow",
        "label": workflow_id,
        "source_id": identity.source_id(template_source),
    }

    stubs = [
        _stub(path, workflow_id)
        for path in sorted(directory.glob("*.md"), key=lambda path: path.name)
        if path.name != "template.md"
    ]
    for stub in stubs:
        node_id = identity.work_node_id(workflow_id, stub["id"])
        if node_id in nodes:
            diagnose("duplicate-node", node_id)
            continue
        nodes[node_id] = {
            "id": node_id,
            "kind": "work",
            "label": stub["id"],
            "source_id": identity.source_id(stub["installed_path"]),
        }

    skill_paths, duplicate_skills = _skill_index(root)
    edges = {}
    declared_work = {
        identity.work_node_id(workflow_id, stub["id"]) for stub in stubs
    }
    for stub in stubs:
        work_id = identity.work_node_id(workflow_id, stub["id"])
        for dependency in stub["depends_on"]:
            dependency_id = identity.work_node_id(workflow_id, dependency)
            edge = _edge("dependency", dependency_id, work_id, "continues to")
            edges.setdefault(edge["id"], edge)
            if dependency_id not in declared_work:
                diagnose("dangling-edge", edge["id"])

        executor = stub["executor"]
        executor_id = identity.skill_node_id(executor)
        if executor_id not in nodes:
            node = {"id": executor_id, "kind": "skill", "label": executor}
            installed_path = skill_paths.get(executor)
            if installed_path is None:
                diagnose("unresolved-reference", executor_id)
            else:
                node["source_id"] = identity.source_id(installed_path)
            nodes[executor_id] = node
        if executor in duplicate_skills:
            diagnose("duplicate-node", executor_id)
        edge = _edge("executor", work_id, executor_id, "executes with")
        edges.setdefault(edge["id"], edge)

        if executor == "orch-loop":
            edge = _edge(
                "loop",
                work_id,
                work_id,
                _loop_label(workflow_id, stub["id"], stub["bound"]),
            )
            edges.setdefault(edge["id"], edge)

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
        "type": "composition",
        "nodes": ordered_nodes,
        "edges": ordered_edges,
        "relations": [dict(edge) for edge in ordered_edges],
        "diagnostics": [diagnostics[key] for key in sorted(diagnostics)],
    }
