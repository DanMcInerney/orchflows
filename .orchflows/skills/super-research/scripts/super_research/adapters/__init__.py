"""Adapter protocol: one bounded request in, exactly one NativePage out.

Every adapter module exposes exactly two public names: ``DESCRIPTOR`` and
``fetch_native_page(transport, request)``. An adapter parses one response
and stops. It never paginates, retries, falls back, calls another adapter,
or persists anything — the core owns pagination, caps, concurrency, and
stop, and a cursor an adapter finds is surfaced through ``cursor_out`` for
the core to decide on.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


class AdapterError(RuntimeError):
    """An adapter could not turn a response into a NativePage."""


@dataclass(frozen=True)
class AdapterDescriptor:
    """The static declaration a route's adapter makes about itself."""

    adapter_id: str
    adapter_version: str
    access_class: str
    route_id: str
    platform: str
    native_identity_namespace: str
    representation_kind: str
    operator_identity: str = ""
    standing_loss: Tuple[str, ...] = ()


@dataclass(frozen=True)
class AdapterRequest:
    """One bounded call's inputs, already frozen by the caller."""

    step_id: str
    query: str = ""
    target_ids: Tuple[str, ...] = ()
    cursor: str = ""


@dataclass(frozen=True)
class NativeRecord:
    """One row as the route itself reported it, before normalization."""

    canonical_content_kind: str
    canonical_locator: str
    native_item_id: str = ""
    native_parent_id: str = ""
    title: str = ""
    body: str = ""
    author: str = ""
    community: str = ""
    published_at: str = ""
    engagement: Tuple[Tuple[str, int], ...] = ()
    native_position: int = -1
    loss: Tuple[str, ...] = ()


@dataclass(frozen=True)
class NativePage:
    """Exactly one adapter call's return. It can hold no next call and no judgment."""

    adapter_id: str
    adapter_version: str
    route_id: str
    records: Tuple[NativeRecord, ...]
    cursor_out: str = ""
    native_order: str = ""
    warnings: Tuple[str, ...] = ()
    outcome: str = "ok"
    loss: Tuple[str, ...] = ()
    page_index: int = 0
