"""Projection seam: a pure, bounded view of one artifact.

Reliability bar: zero I/O. This module opens no file, resolves no path,
and reaches no socket; it reads exactly the artifact handed to it and the
record ids the caller named. It selects nothing on the caller's behalf and
ranks nothing — an unknown record id is refused rather than dropped, and a
selection larger than its own cap is refused rather than truncated.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from . import schema


class ProjectionError(ValueError):
    """A projection named an artifact, a record, or a size it may not have."""


@dataclass(frozen=True)
class ProjectionManifest:
    projection_id: str
    source_artifact_id: str
    record_ids: Tuple[str, ...]
    max_records: int


@dataclass(frozen=True)
class ContextProjection:
    projection_id: str
    source_artifact_id: str
    records: Tuple[schema.AcquisitionRecord, ...]
    groups: Tuple[schema.RecordGroup, ...]
    edges: Tuple[schema.ProvenanceEdge, ...]
    loss: Tuple[str, ...] = ()


def project_context(
    manifest: ProjectionManifest, artifact: schema.AcquisitionArtifact
) -> ContextProjection:
    """Project the named records, in artifact order, with their lineage intact."""

    if manifest.source_artifact_id != artifact.artifact_id:
        raise ProjectionError(
            "projection names artifact {0}, got {1}".format(
                manifest.source_artifact_id, artifact.artifact_id
            )
        )
    if len(manifest.record_ids) > manifest.max_records:
        raise ProjectionError(
            "projection selects {0} records over its cap of {1}".format(
                len(manifest.record_ids), manifest.max_records
            )
        )

    available = {record.record_id for record in artifact.records}
    unknown = sorted(set(manifest.record_ids) - available)
    if unknown:
        raise ProjectionError("projection names unknown record(s): " + ", ".join(unknown))

    selected = set(manifest.record_ids)
    records = tuple(record for record in artifact.records if record.record_id in selected)
    # A group or edge that touches a selected record is kept whole: hiding a
    # co-member or a lineage endpoint would understate what was acquired.
    groups = tuple(
        group
        for group in artifact.groups
        if selected.intersection(group.member_record_ids)
    )
    edges = tuple(
        edge
        for edge in artifact.edges
        if edge.from_record_id in selected or edge.to_record_id in selected
    )
    return ContextProjection(
        projection_id=manifest.projection_id,
        source_artifact_id=artifact.artifact_id,
        records=records,
        groups=groups,
        edges=edges,
        loss=artifact.loss,
    )
