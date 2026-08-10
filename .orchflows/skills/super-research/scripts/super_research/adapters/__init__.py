"""Adapter protocol: one bounded request in, exactly one NativePage out.

Every adapter module exposes exactly two public names: ``DESCRIPTOR`` and
``fetch_native_page(carrier, request)``. An adapter parses one response
and stops. It never paginates, retries, falls back, calls another adapter,
or persists anything — the core owns pagination, caps, concurrency, and
stop, and a cursor an adapter finds is surfaced through ``cursor_out`` for
the core to decide on.

It also never makes the call itself: :func:`fetch_one_page` does, so the
channel verdict is read in one place for every adapter there will ever be.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping, Tuple

from .. import transport


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
    """Exactly one adapter call's return. It can hold no next call and no judgment.

    A page is self-describing: it states which platform it speaks for, under
    which identity namespace, and at which representation. A live adapter
    copies that from its own ``DESCRIPTOR``; the offline ``fake`` adapter
    takes it from the fixture whose route it is standing in for.
    """

    adapter_id: str
    adapter_version: str
    route_id: str
    access_class: str
    platform: str
    native_identity_namespace: str
    representation_kind: str
    records: Tuple[NativeRecord, ...]
    operator_identity: str = ""
    observed_at: str = ""
    cursor_out: str = ""
    native_order: str = ""
    warnings: Tuple[str, ...] = ()
    outcome: str = "ok"
    loss: Tuple[str, ...] = ()


def build_native_page(
    descriptor: AdapterDescriptor,
    records: Tuple[NativeRecord, ...],
    observed_at: str = "",
    cursor_out: str = "",
    native_order: str = "",
    warnings: Tuple[str, ...] = (),
    outcome: str = "ok",
    loss: Tuple[str, ...] = (),
) -> NativePage:
    """Stamp one page with the declaration the calling adapter is making."""

    return NativePage(
        adapter_id=descriptor.adapter_id,
        adapter_version=descriptor.adapter_version,
        route_id=descriptor.route_id,
        access_class=descriptor.access_class,
        platform=descriptor.platform,
        native_identity_namespace=descriptor.native_identity_namespace,
        representation_kind=descriptor.representation_kind,
        records=records,
        operator_identity=descriptor.operator_identity,
        observed_at=observed_at,
        cursor_out=cursor_out,
        native_order=native_order,
        warnings=warnings,
        outcome=outcome,
        loss=loss,
    )


def fetch_one_page(
    descriptor: AdapterDescriptor,
    carrier: transport.Transport,
    params: Mapping[str, str],
    parse: Callable[[transport.TransportResponse], NativePage],
    native_order: str = "",
) -> NativePage:
    """Make one bounded call and give the answering party's verdict to the page.

    The channel verdict is consulted here, once, ahead of any status test a
    ``parse`` may run: a response the local network produced never reaches
    ``parse`` and is recorded as `network_intercepted`, so findings.md §0's
    rule — a local block is never a platform gap — holds for every adapter,
    including the ones that do not exist yet. An adapter inherits it by
    calling this function rather than ``carrier.fetch``, and needs no branch
    of its own.
    """

    response = carrier.fetch(transport.build_transport_request(descriptor.route_id, params))
    if response.channel_verdict == transport.NETWORK_INTERCEPTED:
        return build_native_page(
            descriptor,
            (),
            observed_at=response.observed_at,
            native_order=native_order,
            warnings=(
                "route {0} was answered by the local network, not the origin:"
                " http status {1}".format(descriptor.route_id, response.status),
            ),
            outcome="failed",
            loss=(transport.NETWORK_INTERCEPTED,),
        )
    return parse(response)
