"""Ordering seam: the five named views over a frozen ``as_of``.

No wall clock participates, and an engagement metric is read by the exact name
its adapter declares. Four of the five rank inside one platform/content family
and refuse a mixed set rather than ranking a Reddit post against a web hit;
chronology is the one that crosses source roles on purpose.

Reliability bar: pure. The only thing reached outside this module is the
core's adapter table, read at call time to learn which surface published a
metric name.
"""

from __future__ import annotations

import unicodedata
from datetime import datetime, timezone
from typing import Dict, Iterable, Optional, Tuple

from . import schema
from .adapters import AdapterDescriptor


# The five named views, and which of them stay inside one platform/content
# family. Chronology is the one that crosses source roles on purpose; the other
# four rank things that are only comparable when they are the same kind of
# thing on the same platform.
ORDERING_CONTRACT = (
    "newest",
    "cross_source_chronology",
    "native_top",
    "most_commented",
    "most_replied",
)
FAMILY_SCOPED_ORDERS = ("newest", "native_top", "most_commented", "most_replied")

# A missing value sorts after every present one, and every string is compared
# as unsigned UTF-8 bytes over its NFC form, so ordering never depends on a
# locale or on how a string happened to be composed.
PRESENT = 0
MISSING = 1
INSTANT_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class OrderingError(ValueError):
    """An order was asked for that the contract does not name, or cannot answer."""


def instant_seconds(value: str) -> Optional[int]:
    """One UTC instant as whole seconds, or None when there is no usable one.

    Parsed, never approximated: an unparseable time is missing rather than
    guessed, and no wall clock is read here or anywhere the ordering reaches.
    """

    if not value:
        return None
    try:
        moment = datetime.strptime(value, INSTANT_FORMAT).replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return int(moment.timestamp())


def snapshot_id(record: schema.AcquisitionRecord, position: int) -> str:
    """One engagement snapshot's stable id.

    Derived from the record and the snapshot's declared position rather than
    stored: ``schema.EngagementSnapshot`` carries no id of its own, and a
    record's snapshots are an immutable tuple, so position is stable for as
    long as the record is.
    """

    return "{0}#e{1}".format(record.record_id, position)


def eligible_snapshot(
    record: schema.AcquisitionRecord, metric_name: str, as_of: str
) -> Optional[schema.EngagementSnapshot]:
    """The snapshot a frozen ``as_of`` replays to: the greatest observation at or before it.

    Equal observation times break by smallest stable snapshot id, never by
    value — picking the larger of two simultaneous readings would let a
    comparator improve its own inputs. An observation after ``as_of`` is not
    eligible at all: the replay must answer the same way whenever it runs.
    """

    if not metric_name:
        return None
    horizon = instant_seconds(as_of)
    best: Optional[Tuple[int, str, schema.EngagementSnapshot]] = None
    for position, snapshot in enumerate(record.engagement):
        if snapshot.metric_name != metric_name:
            continue
        observed = instant_seconds(snapshot.observed_at)
        if observed is None or (horizon is not None and observed > horizon):
            continue
        candidate = (observed, snapshot_id(record, position), snapshot)
        if best is None or candidate[:2] > best[:2]:
            best = candidate
    return None if best is None else best[2]


def content_family(record: schema.AcquisitionRecord) -> Tuple[str, str]:
    return (record.platform, record.canonical_content_kind)


def _text(value: str) -> bytes:
    return unicodedata.normalize("NFC", value).encode("utf-8")


def _presence(value: str) -> int:
    return PRESENT if value else MISSING


def _instant_key(value: str) -> Tuple[int, int]:
    seconds = instant_seconds(value)
    return (MISSING, 0) if seconds is None else (PRESENT, -seconds)


def _ordinal_key(position: int) -> Tuple[int, int]:
    return (MISSING, 0) if position < 0 else (PRESENT, position)


def _metric_key(
    record: schema.AcquisitionRecord, metric_name: str, as_of: str
) -> Tuple[int, int]:
    snapshot = eligible_snapshot(record, metric_name, as_of)
    return (MISSING, 0) if snapshot is None else (PRESENT, -snapshot.value)


def _surface_descriptor(
    record: schema.AcquisitionRecord, descriptors: Dict[str, AdapterDescriptor]
) -> Optional[AdapterDescriptor]:
    """The descriptor of the surface that produced this record.

    Almost always the one the caller handed in, and for an adapter reading one
    route it is always that one. It matters for an adapter reading two: HN's
    item store calls a story's comment count ``descendants`` and HN's index
    calls the same quantity ``num_comments``, and a metric name belongs to the
    surface that published it. Reading one surface's name off the other's rows
    would leave half a view unranked — and renaming either would be this
    package inventing a vocabulary neither origin uses.
    """

    declared = descriptors.get(record.adapter_id)
    if declared is not None and declared.route_id == record.route_id:
        return declared
    for surface in runner.surface_descriptors(record.adapter_id):
        if surface.route_id == record.route_id:
            return surface
    return declared


def _declared_metric(
    record: schema.AcquisitionRecord,
    descriptors: Dict[str, AdapterDescriptor],
    order: str,
) -> str:
    descriptor = _surface_descriptor(record, descriptors)
    if descriptor is None:
        return ""
    return (
        descriptor.comment_count_metric
        if order == "most_commented"
        else descriptor.reply_count_metric
    )


def ordering_key(
    record: schema.AcquisitionRecord,
    order: str,
    as_of: str,
    descriptors: Dict[str, AdapterDescriptor],
) -> Tuple:
    """One record's position under one named view, as the retained contract states it."""

    if order == "newest":
        return (
            _instant_key(record.usable_basis_time)
            + (_presence(record.native_item_id), _text(record.native_item_id))
            + (_text(record.record_id),)
        )
    if order == "cross_source_chronology":
        return _instant_key(record.usable_basis_time) + (
            _text(record.platform),
            _text(record.native_identity_namespace),
            _text(record.canonical_content_kind),
            _text(record.record_id),
        )
    if order == "native_top":
        return (
            _ordinal_key(record.native_position)
            + (_presence(record.native_item_id), _text(record.native_item_id))
            + (_text(record.record_id),)
        )
    return (
        _metric_key(record, _declared_metric(record, descriptors, order), as_of)
        + _instant_key(record.usable_basis_time)
        + (
            _presence(record.native_item_id),
            _text(record.native_item_id),
            _text(record.record_id),
        )
    )


def order_records(
    records: Iterable[schema.AcquisitionRecord],
    order: str,
    as_of: str,
    descriptors: Optional[Dict[str, AdapterDescriptor]] = None,
) -> Tuple[schema.AcquisitionRecord, ...]:
    """Put records in one of the five named views under one frozen ``as_of``.

    Four of the five stay inside a single platform/content family and refuse a
    mixed set rather than ranking a Reddit post against a web hit: the numbers
    are not comparable, and producing an order anyway would be the interesting
    kind of wrong. Chronology is the exception and crosses roles by design.
    """

    if order not in ORDERING_CONTRACT:
        raise OrderingError("no such order in the contract: " + order)
    ordered = tuple(records)
    if order in FAMILY_SCOPED_ORDERS:
        families = sorted({content_family(record) for record in ordered})
        if len(families) > 1:
            raise OrderingError(
                "{0} ranks within one platform/content family; got {1}".format(order, families)
            )
    declared = runner.declared_descriptors() if descriptors is None else descriptors
    return tuple(
        sorted(ordered, key=lambda record: ordering_key(record, order, as_of, declared))
    )


# Imported last, and as a module rather than by name. This module reads the
# core's adapter table at call time, and the core re-exports every public name
# above, so the two import each other. Binding the module object down here —
# after every name above exists — is what makes the pair safe to import in
# either order; a ``from .runner import ...`` at the top would fail whenever
# this module was imported before the core.
from . import runner
