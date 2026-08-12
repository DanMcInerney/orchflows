"""Adapter protocol: one bounded request in, exactly one NativePage out.

Every adapter module exposes exactly two public names: ``DESCRIPTOR`` and
``fetch_native_page(carrier, request)``. An adapter parses one response
and stops. It never paginates, retries, falls back, calls another adapter,
or persists anything — the core owns the cap and the stop, and a cursor an
adapter finds is surfaced through ``cursor_out`` for the core to decide on.

**The core spends one.** ``runner.planned_calls`` is still the only place a
manifest becomes an ``AdapterRequest`` and still sets no ``cursor``; the
continuation is ``runner.run_step``'s, built from the page it has just read. A
discovery step therefore reads the page its ``cursor_out`` names, and the page
that one names, to ``runner.MAX_PAGES_PER_STEP``, with ``max_items`` bounding
the whole step rather than one page of it. Six adapters read a cursor and five
surface one, and neither half decides anything: an adapter that followed its own
would be deciding how far a step goes, which is the core's to bound. There is no
concurrency here either: no thread, task, coroutine, or process anywhere in the
package.

It also never makes the call itself: :func:`fetch_one_page` does, so the
channel verdict is read in one place for every adapter there will ever be.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable, Mapping, Tuple

from .. import cache, schema, transport


class AdapterError(RuntimeError):
    """An adapter could not turn a response into a NativePage."""


# What one route's ceiling is until its adapter declares a measured one. Every
# measured ceiling in the roster is looser than this, so an undeclared route is
# paced conservatively rather than freely: a limit nobody has measured is not
# one to spend.
DEFAULT_MIN_INTERVAL_MS = 1000
DEFAULT_BURST = 1
DEFAULT_COOLDOWN_MS = 60000


@dataclass(frozen=True)
class VolatileIdentifier:
    """A vendor identifier that rotates, and the documented way back to a current one.

    Declaring one without its recovery would leave a scheduled outage with no
    procedure attached, so both halves are required together or neither is
    admitted.
    """

    name: str
    recovery: str


@dataclass(frozen=True)
class AdapterDescriptor:
    """The static declaration a route's adapter makes about itself.

    ``min_interval_ms``, ``burst`` and ``cooldown_ms`` are that route's
    measured ceiling, declared here and enforced by the scheduler per route:
    the ceiling belongs to the origin, so two adapters reading one route must
    declare the same three numbers.

    ``comment_count_metric`` and ``reply_count_metric`` name at most one exact
    native metric each, for the two orders that rank by engagement. A name is
    never inferred, aliased, summed, or compared across platforms — an adapter
    that declares neither has no eligible metric, which is a stated absence
    rather than a zero nobody reported.

    ``access_class`` is exactly one class off the ladder :mod:`schema` owns,
    and it is checked here because three separate rules read it and none of
    them can tell an unnamed class from a wrong one: the router admits a step
    on it, ``time_confidence_for`` decides on it how far a record's time is
    trusted, and the artifact publishes it to a caller. A descriptor declaring
    a class nothing names would carry that quietly past all three, so the
    module that declares one fails at import instead.
    """

    adapter_id: str
    adapter_version: str
    access_class: str
    route_id: str
    platform: str
    native_identity_namespace: str
    representation_kind: str
    operator_identity: str = ""
    standing_loss: Tuple[str, ...] = ()
    min_interval_ms: int = DEFAULT_MIN_INTERVAL_MS
    burst: int = DEFAULT_BURST
    cooldown_ms: int = DEFAULT_COOLDOWN_MS
    volatile_identifiers: Tuple[VolatileIdentifier, ...] = ()
    comment_count_metric: str = ""
    reply_count_metric: str = ""

    def __post_init__(self) -> None:
        if self.access_class not in schema.ACCESS_CLASSES:
            raise AdapterError(
                "adapter {0} declares access class {1!r}, which is not one of the"
                " ladder's: {2}".format(
                    self.adapter_id, self.access_class, ", ".join(schema.ACCESS_CLASSES)
                )
            )
        for identifier in self.volatile_identifiers:
            if not identifier.name or not identifier.recovery:
                raise AdapterError(
                    "adapter {0} declares a volatile identifier without both a name"
                    " and a recovery procedure: {1!r}".format(self.adapter_id, identifier)
                )


@dataclass(frozen=True)
class AdapterRequest:
    """One bounded call's inputs, already frozen by the caller."""

    step_id: str
    query: str = ""
    target_ids: Tuple[str, ...] = ()
    cursor: str = ""


@dataclass(frozen=True)
class NativeRecord:
    """One row as the route itself reported it, before normalization.

    ``attributes`` carries named string facts a route reported that no other
    field on this record means — a structured public page's own vocabulary,
    where ``title`` and ``body`` and ``community`` each already mean something
    else. A name repeats when the route reported it more than once, in the
    route's own order, and every value is the exact string as reported.

    Nothing here is inferred, aliased across platforms, or parsed further: a
    name means what the route that emitted it means by it, which is the same
    law ``comment_count_metric`` and ``reply_count_metric`` carry for the two
    counted ones. A route that reports no such fact carries none.
    """

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
    attributes: Tuple[Tuple[str, str], ...] = ()
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
    if response.status == transport.RATE_LIMITED_STATUS:
        # A refusal is typed here for the same reason an interception is: an
        # adapter that met it alone would report it as an ordinary http status,
        # and a caller could not tell "the origin asked for fewer requests"
        # from "the origin has nothing". Neither is a reason to try elsewhere.
        return build_native_page(
            descriptor,
            (),
            observed_at=response.observed_at,
            native_order=native_order,
            warnings=(
                "route {0} asked for fewer requests: http status {1}".format(
                    descriptor.route_id, response.status
                ),
            ),
            outcome="failed",
            loss=(transport.RATE_LIMITED,),
        )
    page = parse(response)
    return _served_from_cache(page) if response.cache_hit else page


def _served_from_cache(page: NativePage) -> NativePage:
    """Mark one page, and every record on it, as answered from a run's own memory.

    The record carries it as well as the page because a record's loss is built
    from the record's own, never from the page's: a caller reading one record
    would otherwise have to correlate it back to a step to learn that what it
    holds is a repeat of a read made earlier. The moment is untouched — a
    cached record states when the origin was read, not when memory answered.
    """

    return replace(
        page,
        records=tuple(
            replace(record, loss=record.loss + (cache.CACHE_HIT,)) for record in page.records
        ),
        loss=page.loss + (cache.CACHE_HIT,),
    )
