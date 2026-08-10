"""Offline adapter: deterministic fixture pages, never live evidence.

``fake`` stands in for a route the roster has not implemented yet, and it
is the only adapter whose declaration comes from its payload rather than
from its own descriptor: a fixture page states which platform, identity
namespace, and representation it speaks for. Its route resolves to a
``fixture://`` origin, which the default opener refuses, so this adapter
cannot reach the network even by mistake.
"""

from __future__ import annotations

import json
from typing import Any, Mapping, Tuple

from .. import transport
from . import AdapterDescriptor, AdapterRequest, NativePage, NativeRecord, build_native_page

DESCRIPTOR = AdapterDescriptor(
    adapter_id="fake",
    adapter_version="1",
    access_class="offline",
    route_id=transport.FAKE_OFFLINE_ROUTE,
    platform="fixture",
    native_identity_namespace="fixture",
    representation_kind="native",
    operator_identity="super-research-fixture",
)

RECORD_FIELDS = (
    "canonical_content_kind",
    "canonical_locator",
    "native_item_id",
    "native_parent_id",
    "title",
    "body",
    "author",
    "community",
    "published_at",
    "native_position",
)


def _record_for(position: int, row: Mapping[str, Any]) -> NativeRecord:
    fields = {name: row[name] for name in RECORD_FIELDS if name in row}
    fields.setdefault("native_position", position)
    return NativeRecord(
        engagement=tuple((name, value) for name, value in row.get("engagement", ())),
        loss=tuple(row.get("loss", ())),
        **fields
    )


def _declaration_from(payload: Mapping[str, Any]) -> AdapterDescriptor:
    return AdapterDescriptor(
        adapter_id=DESCRIPTOR.adapter_id,
        adapter_version=DESCRIPTOR.adapter_version,
        access_class=DESCRIPTOR.access_class,
        route_id=DESCRIPTOR.route_id,
        platform=payload.get("platform") or DESCRIPTOR.platform,
        native_identity_namespace=(
            payload.get("native_identity_namespace") or DESCRIPTOR.native_identity_namespace
        ),
        representation_kind=(
            payload.get("representation_kind") or DESCRIPTOR.representation_kind
        ),
        operator_identity=DESCRIPTOR.operator_identity,
    )


def fetch_native_page(carrier: transport.Transport, request: AdapterRequest) -> NativePage:
    """Return exactly one NativePage built from the named offline fixture."""

    response = carrier.fetch(
        transport.build_transport_request(
            DESCRIPTOR.route_id, {"target": ",".join(request.target_ids)}
        )
    )
    try:
        payload = json.loads(response.body)
        rows = payload["records"]
    except (ValueError, KeyError, TypeError):
        return build_native_page(
            DESCRIPTOR,
            (),
            warnings=("fixture payload was not a record-bearing json object",),
            outcome="failed",
            loss=("malformed_json",),
        )

    records: Tuple[NativeRecord, ...] = tuple(
        _record_for(position, row) for position, row in enumerate(rows)
    )
    return build_native_page(
        _declaration_from(payload),
        records,
        cursor_out=payload.get("cursor_out", ""),
        native_order=payload.get("native_order", ""),
        outcome=payload.get("outcome", "ok" if records else "empty"),
        loss=tuple(payload.get("loss", ())),
    )
