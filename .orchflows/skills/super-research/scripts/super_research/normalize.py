"""Normalize seam: native pages become immutable artifact records.

Normalization derives; it never invents. Every field here comes from the
page that reported it, from the step that requested it, or from a rule
stated in this module. Nothing is inferred by similarity, and no record is
ever rewritten from another record.
"""

from __future__ import annotations

import hashlib
import unicodedata
import urllib.parse
from typing import Any, Sequence, Tuple

from . import schema
from .adapters import NativePage

# A third-party archive reports the platform's time; it is not the platform
# speaking, so its times are `reported` rather than `authoritative`.
REPORTED_ACCESS_CLASSES = ("K3",)


class NormalizeError(ValueError):
    """A native page carried a value no artifact record may hold."""


def normalized_locator(locator: str) -> str:
    """Canonical comparison form: NFC, lowercase scheme and host, no fragment.

    One trailing slash is dropped so ``/comments/1abc234/`` and
    ``/comments/1abc234`` are the same locator. Query strings are kept: they
    distinguish targets on several routes in the roster.
    """

    if not locator:
        return ""
    parts = urllib.parse.urlsplit(unicodedata.normalize("NFC", locator.strip()))
    path = parts.path[:-1] if parts.path.endswith("/") and len(parts.path) > 1 else parts.path
    return urllib.parse.urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), path, parts.query, "")
    )


def content_hash(body: str) -> str:
    """SHA-256 over the NFC/UTF-8 content body; empty content hashes to nothing."""

    if not body:
        return ""
    return hashlib.sha256(unicodedata.normalize("NFC", body).encode("utf-8")).hexdigest()


def engagement_snapshots(
    pairs: Sequence[Tuple[str, Any]], observed_at: str
) -> Tuple[schema.EngagementSnapshot, ...]:
    """Admit only exact native integer metrics; a bool or a negative is invalid."""

    snapshots = []
    for metric_name, value in pairs:
        if isinstance(value, bool) or not isinstance(value, int):
            raise NormalizeError("engagement metric {0} is not an integer".format(metric_name))
        if value < 0 or value > schema.MAX_ENGAGEMENT_VALUE:
            raise NormalizeError("engagement metric {0} is out of range".format(metric_name))
        snapshots.append(
            schema.EngagementSnapshot(
                metric_name=metric_name, value=value, observed_at=observed_at
            )
        )
    return tuple(snapshots)


def time_confidence_for(access_class: str, published_at: str) -> str:
    if not published_at:
        return "unknown"
    if access_class in REPORTED_ACCESS_CLASSES:
        return "reported"
    return "authoritative"


def group_scope_for(page: NativePage) -> str:
    """Platform or instance identity when the page has one, else route identity."""

    return page.platform or page.route_id


def normalize_page(
    page: NativePage,
    step: schema.AcquisitionStep,
    artifact_id: str,
    manifest_id: str,
    page_index: int = 0,
    list_index_start: int = 0,
    discovery_locator: str = "",
) -> Tuple[schema.AcquisitionRecord, ...]:
    """Turn one native page into immutable artifact records, in page order."""

    group_scope = group_scope_for(page)
    records = []
    for offset, native in enumerate(page.records):
        list_index = list_index_start + offset
        published_at = native.published_at
        records.append(
            schema.AcquisitionRecord(
                record_id="{0}#{1}.{2}".format(step.step_id, page_index, list_index),
                artifact_id=artifact_id,
                manifest_id=manifest_id,
                step_id=step.step_id,
                adapter_id=page.adapter_id,
                adapter_version=page.adapter_version,
                route_id=page.route_id,
                access_class=page.access_class,
                operator_identity=page.operator_identity,
                platform=page.platform,
                native_identity_namespace=page.native_identity_namespace,
                group_scope=group_scope,
                representation_kind=page.representation_kind,
                canonical_content_kind=native.canonical_content_kind,
                native_item_id=native.native_item_id,
                native_parent_id=native.native_parent_id,
                canonical_locator=native.canonical_locator,
                normalized_locator=normalized_locator(native.canonical_locator),
                exact_content_hash=content_hash(native.body),
                title=native.title,
                body=native.body,
                author=native.author,
                community=native.community,
                published_at=published_at,
                observed_at=page.observed_at,
                time_confidence=time_confidence_for(page.access_class, published_at),
                usable_basis_time=published_at,
                engagement=engagement_snapshots(native.engagement, page.observed_at),
                page_index=page_index,
                list_index=list_index,
                native_position=native.native_position,
                discovery_locator=discovery_locator,
                outcome="ok",
                loss=tuple(native.loss),
            )
        )
    return tuple(records)
