"""Load the UI-owned compact semantic summaries for Workflows."""

from __future__ import annotations

import json
import re
from collections.abc import Collection
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = ROOT / "reader" / "docs" / "workflow-summary-manifest.json"
SUMMARY_SCHEMA = "orchflows.workflow-summary.v1"
CANONICAL_WORKFLOW_IDS = frozenset({
    "benchmaker",
    "browser-game",
    "drift-canary",
    "evolve",
    "orch-check",
    "orch-decompose",
    "orch-execute",
    "orch-frontier",
    "orch-integrate",
    "orch-loop",
    "orch-outline",
    "renovate",
    "self-improve",
    "skill-tournament",
})
EDGE_KINDS = frozenset({"sequence", "branch", "loop"})
NODE_ID_RE = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")


class SummaryManifestError(ValueError):
    """The workflow summary manifest violates its closed contract."""


def _closed_object(value: object, fields: set[str], subject: str) -> dict:
    if not isinstance(value, dict) or set(value) != fields:
        raise SummaryManifestError(f"{subject} must contain exactly {sorted(fields)}")
    return value


def _adjacency(node_ids: set[str], edges: list[dict]) -> dict[str, set[str]]:
    adjacent = {node_id: set() for node_id in node_ids}
    for edge in edges:
        adjacent[edge["source"]].add(edge["target"])
    return adjacent


def _has_cycle(adjacent: dict[str, set[str]]) -> bool:
    visiting = set()
    visited = set()

    def visit(node_id: str) -> bool:
        if node_id in visiting:
            return True
        if node_id in visited:
            return False
        visiting.add(node_id)
        if any(visit(target) for target in adjacent[node_id]):
            return True
        visiting.remove(node_id)
        visited.add(node_id)
        return False

    return any(visit(node_id) for node_id in adjacent)


def _can_reach(adjacent: dict[str, set[str]], start: str, target: str) -> bool:
    pending = [start]
    visited = set()
    while pending:
        node_id = pending.pop()
        if node_id == target:
            return True
        if node_id in visited:
            continue
        visited.add(node_id)
        pending.extend(adjacent[node_id] - visited)
    return False


def _validate_cycles(workflow_id: str, node_ids: set[str], edges: list[dict]) -> None:
    ordinary_edges = [edge for edge in edges if edge["kind"] != "loop"]
    if _has_cycle(_adjacency(node_ids, ordinary_edges)):
        raise SummaryManifestError(f"{workflow_id} has a cycle without a loop edge")

    for loop_edge in (edge for edge in edges if edge["kind"] == "loop"):
        other_edges = [edge for edge in edges if edge is not loop_edge]
        adjacent = _adjacency(node_ids, other_edges)
        if not _can_reach(adjacent, loop_edge["target"], loop_edge["source"]):
            raise SummaryManifestError(f"{workflow_id} has a loop outside a cycle")


def _validate_summary(workflow_id: str, summary: object) -> None:
    summary = _closed_object(summary, {"nodes", "edges"}, workflow_id)
    nodes = summary["nodes"]
    edges = summary["edges"]
    if not isinstance(nodes, list) or not nodes:
        raise SummaryManifestError(f"{workflow_id} nodes must be a non-empty list")
    if not isinstance(edges, list):
        raise SummaryManifestError(f"{workflow_id} edges must be a list")

    node_ids = set()
    for index, value in enumerate(nodes):
        node = _closed_object(value, {"id", "label"}, f"{workflow_id} node {index}")
        node_id = node["id"]
        label = node["label"]
        if not isinstance(node_id, str) or NODE_ID_RE.fullmatch(node_id) is None:
            raise SummaryManifestError(f"{workflow_id} has a malformed node id")
        if node_id in node_ids:
            raise SummaryManifestError(f"{workflow_id} has a duplicate node id")
        if (
            not isinstance(label, str)
            or not label
            or label != label.strip()
            or "\n" in label
            or "\r" in label
            or len(label) > 40
        ):
            raise SummaryManifestError(f"{workflow_id} has an invalid node label")
        node_ids.add(node_id)

    edge_tuples = set()
    for index, value in enumerate(edges):
        edge = _closed_object(
            value, {"source", "target", "kind"}, f"{workflow_id} edge {index}"
        )
        source = edge["source"]
        target = edge["target"]
        kind = edge["kind"]
        if not all(isinstance(value, str) for value in (source, target, kind)):
            raise SummaryManifestError(f"{workflow_id} has a malformed edge")
        if source not in node_ids or target not in node_ids:
            raise SummaryManifestError(f"{workflow_id} has an unknown edge endpoint")
        if kind not in EDGE_KINDS:
            raise SummaryManifestError(f"{workflow_id} has an unknown edge kind")
        edge_tuple = (source, target, kind)
        if edge_tuple in edge_tuples:
            raise SummaryManifestError(f"{workflow_id} has a duplicate edge")
        edge_tuples.add(edge_tuple)
    _validate_cycles(workflow_id, node_ids, edges)


def validate_manifest(
    manifest: object,
    expected_workflow_ids: Collection[str] = CANONICAL_WORKFLOW_IDS,
) -> dict:
    """Validate and return one closed compact-summary manifest."""

    manifest = _closed_object(manifest, {"schema", "workflows"}, "manifest")
    if manifest["schema"] != SUMMARY_SCHEMA:
        raise SummaryManifestError("manifest has an unknown schema")
    workflows = manifest["workflows"]
    if not isinstance(workflows, dict):
        raise SummaryManifestError("manifest workflows must be an object")
    if set(workflows) != set(expected_workflow_ids):
        raise SummaryManifestError("manifest workflow coverage is not exact")
    for workflow_id, summary in workflows.items():
        _validate_summary(workflow_id, summary)
    return manifest


def load_manifest(path: Path = DEFAULT_MANIFEST) -> dict:
    """Read and validate one UTF-8 workflow summary manifest."""

    return validate_manifest(json.loads(path.read_text(encoding="utf-8")))
