"""Runner facade: literal adapter dispatch, paging, and ``run_step``.

Every adapter is statically imported and reached through one literal branch in
both :func:`descriptor_for` and :func:`call_adapter`. The facade alone turns a
returned cursor into another request and applies the caller and core caps.
Planning and scheduling live in private support, while their established names
remain available here for the suite and CLI. The carrier and clock stay
injected, so this seam reaches neither network nor filesystem on its own.
"""

from __future__ import annotations

import time
from dataclasses import replace
from typing import Callable, Dict, List, Optional, Tuple

from . import cache, normalize, router, schema, transport
from .adapters import AdapterDescriptor, AdapterRequest, NativePage, build_native_page
from .adapters import bluesky, fake, github_rest, hacker_news, instagram_public
from .adapters import linkedin_jobs, linkedin_public, open_page, prediction_markets
from .adapters import public_page
from .adapters import reddit_archive
from .adapters import reddit_feed, reddit_shreddit
from .adapters import rss_atom, stocktwits, web_search
from .adapters import x_fxtwitter, x_guest, x_syndication, youtube_innertube
from .ledger import (
    ADDITIVE_METRICS,
    METRIC_ORDINALS,
    NATIVE_PAGE,
    OPERATION_KIND_ORDINALS,
    PlannedOperation,
    ScheduledOperation,
    ScheduledRun,
    WorkLedgerEvent,
    causal_key,
    fake_makespan_us,
    ledger_of,
    ledger_sums,
    planned_operations,
    schedule_of,
)
from .ordering import (
    FAMILY_SCOPED_ORDERS,
    INSTANT_FORMAT,
    MISSING,
    ORDERING_CONTRACT,
    PRESENT,
    OrderingError,
    content_family,
    eligible_snapshot,
    instant_seconds,
    order_records,
    ordering_key,
)
from .pacing import (
    US_PER_MS,
    US_PER_SECOND,
    OriginRead,
    RateGovernor,
    RouteBudget,
    budget_of,
    budgets_from,
    paced_carrier,
    route_budgets,
    tick_us,
)
from ._support.runner_plan import artifact_id_for, in_window, planned_calls, reached_origin
from ._support.runner_plan import offers_another_page as _offers_another_page
from ._support.runner_plan import refused_step as _refused_step
from ._support.runner_schedule import MAX_CONCURRENT_LANES, StepOutcome, lanes_of
from ._support import runner_schedule
from ._support.window_reach import WindowReachError, reach_for, step_window_loss
_RUN_STEPS_IMPL = runner_schedule.run_steps
# Every adapter this core can reach, spelled once. It is a literal tuple, not a
# registry: exact search over an id still finds the two branches below, and a
# later adapter listed here without both of them fails loudly.
ADAPTER_IDS = (
    "bluesky",
    "fake",
    "github_rest",
    "hacker_news",
    "instagram_public",
    "linkedin_jobs",
    "linkedin_public",
    "open_page",
    "prediction_markets",
    "public_page",
    "reddit_archive",
    "reddit_feed",
    "reddit_shreddit",
    "rss_atom",
    "stocktwits",
    "web_search",
    "x_fxtwitter",
    "x_guest",
    "x_syndication",
    "youtube_innertube",
)


# The most pages one discovery step may read, whatever the origin keeps
# offering and whatever the step asked for: a step declaring its own
# `max_pages` lowers the count, and one declaring more than this still stops
# here. Every other way out of the page loop is the origin's own statement —
# it stopped naming a cursor, or it named one this step already spent — and an
# origin that never makes either statement would spend a budget nobody set, so
# the last stop is the core's. Five, because the roster's measured pages hold
# ten to twenty-five rows, which reaches fifty to a hundred and twenty-five
# records; and because at the slowest measured ceiling, one read per thirty
# seconds, five reads is the most a single step can cost before it is a session
# rather than a step.
MAX_PAGES_PER_STEP = 5


class RunnerError(RuntimeError):
    """The core was asked for something it refuses to guess at."""


def descriptor_for(adapter_id: str) -> Optional[AdapterDescriptor]:
    """Literal branches only. An unknown adapter is refused, never guessed."""

    if adapter_id == "bluesky":
        return bluesky.DESCRIPTOR
    if adapter_id == "fake":
        return fake.DESCRIPTOR
    if adapter_id == "github_rest":
        return github_rest.DESCRIPTOR
    if adapter_id == "hacker_news":
        return hacker_news.DESCRIPTOR
    if adapter_id == "instagram_public":
        return instagram_public.DESCRIPTOR
    if adapter_id == "linkedin_jobs":
        return linkedin_jobs.DESCRIPTOR
    if adapter_id == "linkedin_public":
        return linkedin_public.DESCRIPTOR
    if adapter_id == "open_page":
        return open_page.DESCRIPTOR
    if adapter_id == "prediction_markets":
        return prediction_markets.DESCRIPTOR
    if adapter_id == "public_page":
        return public_page.DESCRIPTOR
    if adapter_id == "reddit_archive":
        return reddit_archive.DESCRIPTOR
    if adapter_id == "reddit_feed":
        return reddit_feed.DESCRIPTOR
    if adapter_id == "reddit_shreddit":
        return reddit_shreddit.DESCRIPTOR
    if adapter_id == "rss_atom":
        return rss_atom.DESCRIPTOR
    if adapter_id == "stocktwits":
        return stocktwits.DESCRIPTOR
    if adapter_id == "web_search":
        return web_search.DESCRIPTOR
    if adapter_id == "x_fxtwitter":
        return x_fxtwitter.DESCRIPTOR
    if adapter_id == "x_guest":
        return x_guest.DESCRIPTOR
    if adapter_id == "x_syndication":
        return x_syndication.DESCRIPTOR
    if adapter_id == "youtube_innertube":
        return youtube_innertube.DESCRIPTOR
    return None


def call_adapter(
    adapter_id: str, carrier: transport.Transport, request: AdapterRequest
) -> NativePage:
    """One bounded adapter call returning exactly one NativePage."""

    if adapter_id == "bluesky":
        return bluesky.fetch_native_page(carrier, request)
    if adapter_id == "fake":
        return fake.fetch_native_page(carrier, request)
    if adapter_id == "github_rest":
        return github_rest.fetch_native_page(carrier, request)
    if adapter_id == "hacker_news":
        return hacker_news.fetch_native_page(carrier, request)
    if adapter_id == "instagram_public":
        return instagram_public.fetch_native_page(carrier, request)
    if adapter_id == "linkedin_jobs":
        return linkedin_jobs.fetch_native_page(carrier, request)
    if adapter_id == "linkedin_public":
        return linkedin_public.fetch_native_page(carrier, request)
    if adapter_id == "open_page":
        return open_page.fetch_native_page(carrier, request)
    if adapter_id == "prediction_markets":
        return prediction_markets.fetch_native_page(carrier, request)
    if adapter_id == "public_page":
        return public_page.fetch_native_page(carrier, request)
    if adapter_id == "reddit_archive":
        return reddit_archive.fetch_native_page(carrier, request)
    if adapter_id == "reddit_feed":
        return reddit_feed.fetch_native_page(carrier, request)
    if adapter_id == "reddit_shreddit":
        return reddit_shreddit.fetch_native_page(carrier, request)
    if adapter_id == "rss_atom":
        return rss_atom.fetch_native_page(carrier, request)
    if adapter_id == "stocktwits":
        return stocktwits.fetch_native_page(carrier, request)
    if adapter_id == "web_search":
        return web_search.fetch_native_page(carrier, request)
    if adapter_id == "x_fxtwitter":
        return x_fxtwitter.fetch_native_page(carrier, request)
    if adapter_id == "x_guest":
        return x_guest.fetch_native_page(carrier, request)
    if adapter_id == "x_syndication":
        return x_syndication.fetch_native_page(carrier, request)
    if adapter_id == "youtube_innertube":
        return youtube_innertube.fetch_native_page(carrier, request)
    raise RunnerError("no adapter branch for " + adapter_id)


def surface_descriptors(adapter_id: str) -> Tuple[AdapterDescriptor, ...]:
    """Every route one adapter can reach, one descriptor each.

    Most adapters read one route and this is its one descriptor. Ten do not.
    Six read a second route plainly — ``bluesky``, ``prediction_markets``,
    ``reddit_shreddit``, ``stocktwits``, ``web_search`` and
    ``youtube_innertube`` — and four are worth a reason each: ``hacker_news``
    reads two origins, ``github_rest`` reads one origin whose anonymous hour is
    counted in two separate buckets, ``public_page`` selects between two
    documents, and ``x_guest`` spends an activation to authorize the route it
    reads. A budget belongs to whoever sets it, so an adapter like those
    declares one descriptor per route and this is where the second becomes
    reachable. Literal branches, like the two above: a surface the core cannot
    see here is a route the scheduler would refuse to pace.

    A surface is not always something a caller reads. ``x_guest``'s activation
    returns a token rather than a record, so it appears here — where budgets
    are collected — and never in :func:`descriptor_for`, which answers what an
    adapter reads.
    """

    if adapter_id == "bluesky":
        return bluesky.SURFACE_DESCRIPTORS
    if adapter_id == "github_rest":
        return github_rest.SURFACE_DESCRIPTORS
    if adapter_id == "hacker_news":
        return hacker_news.SURFACE_DESCRIPTORS
    if adapter_id == "prediction_markets":
        return prediction_markets.SURFACE_DESCRIPTORS
    if adapter_id == "public_page":
        return public_page.SURFACE_DESCRIPTORS
    if adapter_id == "reddit_shreddit":
        return reddit_shreddit.SURFACE_DESCRIPTORS
    if adapter_id == "stocktwits":
        return stocktwits.SURFACE_DESCRIPTORS
    if adapter_id == "web_search":
        return web_search.SURFACE_DESCRIPTORS
    if adapter_id == "x_guest":
        return x_guest.SURFACE_DESCRIPTORS
    if adapter_id == "youtube_innertube":
        return youtube_innertube.SURFACE_DESCRIPTORS
    descriptor = descriptor_for(adapter_id)
    return () if descriptor is None else (descriptor,)


def declared_descriptors() -> Dict[str, AdapterDescriptor]:
    """Every adapter this core lists, by id."""

    found: Dict[str, AdapterDescriptor] = {}
    for adapter_id in ADAPTER_IDS:
        descriptor = descriptor_for(adapter_id)
        if descriptor is not None:
            found[adapter_id] = descriptor
    return found


def run_step(
    step: schema.AcquisitionStep,
    carrier: transport.Transport,
    artifact_id: str,
    manifest_id: str,
    clock: Callable[[], float] = time.monotonic,
) -> Tuple[
    schema.StepResult, Tuple[schema.AcquisitionRecord, ...], Tuple[PlannedOperation, ...]
]:
    descriptor = descriptor_for(step.adapter_id)
    if descriptor is None:
        return (_refused_step(step, "", "no_route"), (), ())

    decision = router.select_route(step, descriptor, transport.route_admissions())
    if not decision.admitted:
        return (_refused_step(step, decision.route_id, decision.refusal_reason), (), ())

    records: List[schema.AcquisitionRecord] = []
    operations: List[PlannedOperation] = []
    page_outcomes: List[str] = []
    page_routes: List[str] = []
    loss: List[str] = []
    warnings: List[str] = []
    received = 0
    pages = 0
    truncated = False
    outside_window = 0
    window_loss: Optional[str] = None  # this step's own; window_reach.step_window_loss's

    # Every call this step will make. A discovery step's continuations are
    # appended as they are earned, one per page that offers a cursor worth
    # spending, so the loop below is the one place a step's calls are counted.
    calls = list(planned_calls(step))
    spent_cursors = {""}
    page_index = 0

    if (
        step.kind == "discovery"
        and descriptor.page_size
        and step.max_items < descriptor.page_size
    ):
        # Said before the read, because it is a fact about the cap and not
        # about the answer: on a surface that answers a page per call, a cap
        # under the page buys no saving and drops the rest of the page.
        warnings.append(
            "max_items {0} is below this surface's page size {1}: one read returns"
            " up to {1} rows and the rows past the cap are dropped at no saving".format(
                step.max_items, descriptor.page_size
            )
        )

    while page_index < len(calls):
        request, discovery_locator = calls[page_index]
        if step.kind == "discovery" and len(records) >= step.max_items:
            # The core owns stop: no further call is made once the cap is met.
            # A hydration step is not stopped here — every one of its calls was
            # authorized by name, and its cap bounds each answer rather than
            # the sum, so a first hit that answers richly cannot starve the
            # ones the caller also selected.
            truncated = True
            break
        window_loss = step_window_loss(step, request, window_loss)
        began_us = tick_us(clock)
        try:
            page = call_adapter(step.adapter_id, carrier, request)
        except transport.TransportError as error:
            # The one read that comes back with nothing to type — a refused
            # connection, an unresolvable name, a TLS handshake that failed, or
            # the transport declining to send it at all (`transport.urlopen_read`
            # raises the same class for a non-https address, a write-capable
            # method and an undeclared route or credential).
            # Typed here rather than raised, because raising discards every
            # step already run: `composition.md` §8 asks a failure path for the
            # partial result plus the evidence gathered, and everything read
            # before this call is exactly that. The error's own text is the
            # only part of it naming where to look, so it rides as a warning.
            page = build_native_page(
                descriptor,
                (),
                outcome="failed",
                loss=(transport.UNREACHABLE,),
                warnings=(str(error),),
            )
        pages += 1
        page_outcomes.append(page.outcome)
        page_routes.append(page.route_id)
        loss.extend(page.loss)
        # The page's own account of itself, carried rather than dropped: it is
        # the only part of a typed failure that names where to look next.
        warnings.extend(page.warnings)
        received += len(page.records)
        operations.append(
            PlannedOperation(
                step_id=step.step_id,
                adapter_id=step.adapter_id,
                # The route the page says answered, which is the route the read
                # actually left on. For an adapter reading one route that is
                # the descriptor's; for one reading two it is whichever surface
                # this call used, and charging both to the descriptor's would
                # bill one origin for another's read.
                route_id=page.route_id or descriptor.route_id,
                page_index=page_index,
                duration_us=tick_us(clock) - began_us,
                reached_origin=reached_origin(page),
                records_received=len(page.records),
            )
        )
        # The window first, then the cap: a row the origin dated outside the
        # step's bounds is dropped before it can spend the cap, so the cap is
        # spent in-window. Nothing undated is dropped here.
        windowed = tuple(
            native for native in page.records if in_window(step, native.published_at)
        )
        outside_window += len(page.records) - len(windowed)
        # A discovery step's cap bounds the whole step; a hydration step's cap
        # bounds each authorized call, which is what "one call per hit" makes
        # the honest unit.
        room = step.max_items if step.kind == "hydration" else step.max_items - len(records)
        if len(windowed) > room:
            truncated = True
        records.extend(
            normalize.normalize_page(
                replace(page, records=windowed[:room]),
                step,
                artifact_id,
                manifest_id,
                page_index=page_index,
                list_index_start=len(records),
                discovery_locator=discovery_locator,
            )
        )
        if _offers_another_page(step, page, len(records), len(calls)):
            if page.cursor_out in spent_cursors or len(calls) >= MAX_PAGES_PER_STEP:
                # The origin had more and the core would not spend it: a
                # cursor it has already asked on, or one page past its own cap.
                truncated = True
            else:
                spent_cursors.add(page.cursor_out)
                calls.append((replace(request, cursor=page.cursor_out), discovery_locator))
        page_index += 1

    if truncated:
        # A raw cap counts every received record and may drop unseen uniques,
        # and so does a step that stopped while the origin was still offering.
        loss.append("recall_window_partial")
    if outside_window:
        # Counted and said, never typed: the bound is the caller's own, so a
        # row outside it is the step finishing rather than a recall cut short.
        warnings.append(
            "{0} record(s) the origin dated outside the step's window were dropped"
            " before the cap counted them".format(outside_window)
        )
    if window_loss:
        loss.append(window_loss)
    outcome = "partial" if truncated else schema.reduce_outcomes(tuple(page_outcomes))
    # The route this step actually read, when its pages agree on one. They
    # always do for an adapter with one surface, and they do for a two-surface
    # adapter whose calls all hydrate or all search; a step that mixed both
    # falls back to the route it was admitted on, because no single route is
    # what it read and the records carry the exact one each came from.
    read = {route_id for route_id in page_routes if route_id}
    return (
        schema.StepResult(
            step_id=step.step_id,
            adapter_id=step.adapter_id,
            route_id=next(iter(read)) if len(read) == 1 else decision.route_id,
            pages=pages,
            records_received=received,
            records_kept=len(records),
            outcome=outcome,
            loss=tuple(loss),
            warnings=tuple(warnings),
            kind=step.kind,
            query=step.query,
        ),
        tuple(records),
        tuple(operations),
    )
def _sync_schedule_seams() -> None:
    runner_schedule.paced_carrier = paced_carrier
    runner_schedule.artifact_id_for = artifact_id_for
    runner_schedule.ledger_of = ledger_of
    runner_schedule.run_steps = _RUN_STEPS_IMPL if run_steps is _FACADE_RUN_STEPS else run_steps
def run_steps(
    manifest: schema.AcquisitionManifest,
    carrier: transport.Transport,
    artifact_id: str,
    clock: Callable[[], float] = time.monotonic,
    lanes: int = MAX_CONCURRENT_LANES,
) -> Tuple[StepOutcome, ...]:
    """Every step's outcome, in declared order, however the mode ran them."""
    _sync_schedule_seams()
    return _RUN_STEPS_IMPL(manifest, carrier, artifact_id, run_step, clock, lanes)
_FACADE_RUN_STEPS = run_steps
def run_scheduled(
    manifest: schema.AcquisitionManifest,
    carrier: Optional[transport.Transport] = None,
    clock: Callable[[], float] = time.monotonic,
    dispatch_ordinal: int = 0,
    start_tick_us: int = 0,
    lanes: int = MAX_CONCURRENT_LANES,
) -> ScheduledRun:
    """Run one validated manifest to one immutable artifact and its work ledger."""

    _sync_schedule_seams()
    return runner_schedule.run_scheduled(
        manifest, run_step, carrier, clock, dispatch_ordinal, start_tick_us, lanes
    )


def run_acquisition(
    manifest: schema.AcquisitionManifest,
    carrier: Optional[transport.Transport] = None,
    clock: Callable[[], float] = time.monotonic,
    lanes: int = MAX_CONCURRENT_LANES,
) -> schema.AcquisitionArtifact:
    """Run one validated manifest to one immutable artifact."""

    return run_scheduled(manifest, carrier, clock=clock, lanes=lanes).artifact
