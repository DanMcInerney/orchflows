"""Load the UI-owned compact semantic summaries for Workflows."""

from __future__ import annotations

import json
import re
from collections.abc import Collection
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "docs" / "ui" / "workflow-summary-manifest.json"
SUMMARY_SCHEMA = "orchflows.workflow-summary.v1"
CANONICAL_WORKFLOW_IDS = frozenset({
    "benchmaker",
    "drift-canary",
    "evolve",
    "fix",
    "orch-build",
    "orch-eval-design",
    "orch-fixture",
    "orch-repair",
    "orch-self-improve",
    "orch-spec",
    "orch-triage",
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
        if source not in node_ids or target not in node_ids:
            raise SummaryManifestError(f"{workflow_id} has an unknown edge endpoint")
        if kind not in EDGE_KINDS:
            raise SummaryManifestError(f"{workflow_id} has an unknown edge kind")
        edge_tuple = (source, target, kind)
        if edge_tuple in edge_tuples:
            raise SummaryManifestError(f"{workflow_id} has a duplicate edge")
        edge_tuples.add(edge_tuple)


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
