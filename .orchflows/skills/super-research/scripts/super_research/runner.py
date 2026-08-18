"""Runner seam: the core owns dispatch, and the run a manifest becomes.

*Dispatch.* Adapters are reached only through the literal branches in
:func:`descriptor_for` and :func:`call_adapter` — one ``if`` per adapter
module, statically imported, both covering exactly :data:`ADAPTER_IDS`. There
is no registry, no dynamic import, and no ``getattr`` dispatch, so exact
search over an adapter's name finds every place the core can call it.

*The run.* One validated manifest becomes one immutable artifact and the
ledger of how: one native page per adapter call, and the core alone owning
the caps and the stop. Paging is here and nowhere else: :func:`planned_calls`
is the only place a manifest becomes an ``AdapterRequest`` and never sets a
cursor, so the continuation :func:`run_step` builds from the page it just read
is the single site one enters a request at, bounded by the step's ``max_items``,
by its own ``max_pages`` where it declares one, and by
:data:`MAX_PAGES_PER_STEP` where it does not.

*Concurrency, and where it stops.* A ``staged`` run executes its steps one at
a time in declared order. A ``fused`` run executes them as **lanes** — one lane
per adapter, each lane serial in declared order, lanes overlapping — which is
exactly the placement :func:`ledger.schedule_of` has always modelled for that
mode; the model is now what runs. What makes overlap safe is not here: the
governor takes an origin's lock around every read (:mod:`.pacing`), so an origin
sees one read at a time whatever the lanes do, and a step's inputs are frozen
in the manifest, so no lane reads what another produced. The artifact is the
same either way — records are assembled in declared step order after every lane
returns — and the one thing the mode moves is wall clock. This is the one
module that holds a pool.

Three concerns this module used to own were moved to one-read-size siblings
and are re-exported below under the names they have always had —
:mod:`.pacing` for the measured ceiling waited out per route, :mod:`.ledger`
for the work ledger and the schedule a mode admits, and :mod:`.ordering` for
the five named views. Each name still has exactly one definition; this module
stays the one address the suite and the CLI reach it at.

Reliability bar: nothing here reaches the network or the filesystem. The
carrier is injected, the clock is injected, and both have offline stand-ins.
"""

from __future__ import annotations

import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
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


def planned_calls(step: schema.AcquisitionStep) -> Tuple[Tuple[AdapterRequest, str], ...]:
    """Every bounded call this step authorizes, paired with its discovery locator.

    A discovery step authorizes one call. A hydration step authorizes one
    call per caller-frozen selected hit, which is what makes each hydration
    record's provenance exact rather than inferred.
    """

    if step.kind == "discovery":
        return (
            (
                AdapterRequest(
                    step_id=step.step_id,
                    query=step.query,
                    window_start=step.window_start,
                    window_end=step.window_end,
                ),
                "",
            ),
        )
    return tuple(
        (
            AdapterRequest(
                step_id=step.step_id,
                target_ids=(hit.target_id,),
                window_start=step.window_start,
                window_end=step.window_end,
            ),
            normalize.normalized_locator(hit.discovery_locator),
        )
        for hit in step.selected_hits
    )


def in_window(step: schema.AcquisitionStep, published_at: str) -> bool:
    """Whether one record's own time falls inside the step's window.

    A record stating no time is inside every window: the filter drops what the
    origin dated outside the bounds and never decides the unknown. A bound the
    step left empty binds nothing. Instants compare as the ordering compares
    them — parsed, never as strings — so a stamp in another spelling sorts as
    missing and is kept.
    """

    if not step.window_start and not step.window_end:
        return True
    moment = instant_seconds(published_at)
    if moment is None:
        return True
    start = instant_seconds(step.window_start) if step.window_start else None
    end = instant_seconds(step.window_end) if step.window_end else None
    if start is not None and moment < start:
        return False
    if end is not None and moment > end:
        return False
    return True


def artifact_id_for(manifest_id: str) -> str:
    return "artifact:" + manifest_id


def _refused_step(step: schema.AcquisitionStep, route_id: str, reason: str) -> schema.StepResult:
    return schema.StepResult(
        step_id=step.step_id,
        adapter_id=step.adapter_id,
        route_id=route_id,
        pages=0,
        records_received=0,
        records_kept=0,
        outcome="refused",
        loss=(reason,),
    )


def reached_origin(page: NativePage) -> bool:
    """Whether this page cost the origin a read.

    Three ways it did not, and until an adapter could refuse there was only one.
    A run's own memory answered, which is what ``cache_hit`` says. Or the
    adapter refused before making a call at all — a target it does not serve
    costs a page and no read — and billing that as a call would put work in the
    ledger that no origin ever saw. Or the read raised instead of answering,
    which is what ``unreachable`` says: nothing took the request, and the
    governor — the one place a route's budget is spent — charges no interval
    and logs no read for a fetch that raised (``pacing.RateGovernor._paced_fetch``
    charges and logs only after the carrier returns). Billing it here would put
    a call in the ledger that the governor's own log does not have, and the two
    are pinned equal. ``refused`` and ``unreachable`` are the two outcomes that
    mean no origin was asked to spend anything; every other one, failures
    included, describes an answer this host actually got.
    """

    return (
        page.outcome != "refused"
        and cache.CACHE_HIT not in page.loss
        and transport.UNREACHABLE not in page.loss
    )


def _offers_another_page(
    step: schema.AcquisitionStep, page: NativePage, kept: int, calls_made: int
) -> bool:
    """Whether this page leaves a next one the step could still want.

    Four questions, and only the first is about the page. A hydration step
    never pages: its calls are one per hit the caller froze, which is what makes
    each hydration record's provenance exact rather than inferred, and a page
    read off a cursor was authorized by nobody. A page that names no cursor is
    the origin saying there is nothing after it. And a step whose cap is already
    met wants nothing further, nor does one that has read every page it asked
    for — both of those are the caller's own bound reached, and every stop this
    function makes is therefore a step finishing rather than a recall cut short.
    That is the whole difference between here and the two refusals in the loop:
    those stop a step that still wanted more, and say so with a loss code.

    ``max_pages`` only ever lowers the count. A step declaring more than
    :data:`MAX_PAGES_PER_STEP` is stopped by the core's backstop in the loop,
    where stopping is a loss, because a bound the core imposed is not one the
    caller reached.
    """

    if step.max_pages and calls_made >= step.max_pages:
        return False
    return step.kind == "discovery" and bool(page.cursor_out) and kept < step.max_items


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
        ),
        tuple(records),
        tuple(operations),
    )


# The most lanes a fused run overlaps. Lanes are per adapter, so this bounds
# how many origins this package has a read in flight at, and it is well under
# the roster's adapter count on purpose: a run naming every adapter still puts
# at most this many reads on the wire at once, and the governor's origin locks
# hold each origin to one whatever this number is.
MAX_CONCURRENT_LANES = 8

StepOutcome = Tuple[
    schema.StepResult, Tuple[schema.AcquisitionRecord, ...], Tuple[PlannedOperation, ...]
]


def lanes_of(
    steps: Tuple[schema.AcquisitionStep, ...],
) -> "OrderedDict[str, List[schema.AcquisitionStep]]":
    """The steps grouped by adapter, each group in declared order.

    A lane is one adapter's steps in the order the manifest declared them.
    Grouping by adapter rather than by origin is the honest cut from here:
    which route a step reads is the adapter's decision at read time, and every
    route one adapter reads is paced and locked by the governor whatever lane
    it runs in. Two adapters on one origin (Reddit's feed and its shreddit
    partials, YouTube's InnerTube and its channel feed) still take turns —
    at the origin's lock rather than here.
    """

    lanes: "OrderedDict[str, List[schema.AcquisitionStep]]" = OrderedDict()
    for step in steps:
        lanes.setdefault(step.adapter_id, []).append(step)
    return lanes


def _run_lane(
    steps: List[schema.AcquisitionStep],
    carrier: transport.Transport,
    artifact_id: str,
    manifest_id: str,
    clock: Callable[[], float],
) -> List[StepOutcome]:
    return [run_step(step, carrier, artifact_id, manifest_id, clock=clock) for step in steps]


def run_steps(
    manifest: schema.AcquisitionManifest,
    carrier: transport.Transport,
    artifact_id: str,
    clock: Callable[[], float] = time.monotonic,
    lanes: int = MAX_CONCURRENT_LANES,
) -> Tuple[StepOutcome, ...]:
    """Every step's outcome, in declared order, however the mode ran them.

    ``staged`` runs the steps one at a time in declared order — a caller
    stands between one step's output and the next step's input, and a serial
    line is what that models. ``fused`` runs each adapter's steps as one lane
    and overlaps up to ``lanes`` of them on a pool, which is the placement
    :func:`ledger.schedule_of` models for it; a manifest with one lane, or a
    caller asking for one, runs exactly as ``staged`` does. Outcomes come back
    in declared step order either way, so the artifact built from them is the
    same artifact.

    ``lanes`` is a ceiling on overlap and never a floor: one is serial, and a
    number past :data:`MAX_CONCURRENT_LANES` is that constant. A caller whose
    clock is a fake — every accounting suite in this package — asks for one,
    because a fake clock advanced by two threads at once measures the
    interleaving rather than the work.
    """

    grouped = lanes_of(manifest.steps)
    workers = max(1, min(lanes, MAX_CONCURRENT_LANES, len(grouped)))
    if manifest.mode != "fused" or workers < 2:
        return tuple(_run_lane(list(manifest.steps), carrier, artifact_id, manifest.manifest_id, clock))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(_run_lane, steps, carrier, artifact_id, manifest.manifest_id, clock)
            for steps in grouped.values()
        ]
        by_step_id: Dict[str, StepOutcome] = {}
        for future in futures:
            for outcome in future.result():
                by_step_id[outcome[0].step_id] = outcome
    return tuple(by_step_id[step.step_id] for step in manifest.steps)


def run_scheduled(
    manifest: schema.AcquisitionManifest,
    carrier: Optional[transport.Transport] = None,
    clock: Callable[[], float] = time.monotonic,
    dispatch_ordinal: int = 0,
    start_tick_us: int = 0,
    lanes: int = MAX_CONCURRENT_LANES,
) -> ScheduledRun:
    """Run one validated manifest to one immutable artifact and its work ledger.

    Outcomes are assembled in declared order whatever the mode, so an artifact
    is the same artifact either way; the mode reaches the wall clock the run
    spends and the schedule the ledger records, and nothing a step produces.

    Naming no carrier is the documented call, and it gets the composed one:
    :func:`pacing.paced_carrier`, a rate governor over a run-local cache. A
    caller reaches an unpaced origin only by constructing a carrier and handing
    it in, which is an act rather than a default — the measured extreme in the
    roster is one read per thirty seconds, and a run that spends it twice by
    omission has evaded a limit nobody chose to evade.
    """

    reached = paced_carrier(clock=clock) if carrier is None else carrier
    artifact_id = artifact_id_for(manifest.manifest_id)
    steps: List[schema.StepResult] = []
    records: List[schema.AcquisitionRecord] = []
    operations: List[PlannedOperation] = []
    for result, step_records, step_operations in run_steps(
        manifest, reached, artifact_id, clock=clock, lanes=lanes
    ):
        steps.append(result)
        records.extend(step_records)
        operations.extend(step_operations)

    # The one place the run's records and its links meet, and therefore the one
    # place a fact about the gap between them can be attached. A record is built
    # from one page and is frozen when it is built, so it cannot know at
    # construction whether another step discovered it; `type_discovery_gaps`
    # answers that across the finished set and types what it finds. Ids do not
    # change, so the links and groups below are the same either side of it.
    typed = normalize.type_discovery_gaps(tuple(records))
    loss = tuple(sorted({code for step in steps for code in step.loss}))
    artifact = schema.AcquisitionArtifact(
        artifact_id=artifact_id,
        manifest_id=manifest.manifest_id,
        mode=manifest.mode,
        as_of=manifest.as_of,
        records=typed,
        steps=tuple(steps),
        edges=normalize.link_discovery_hydration(typed),
        groups=normalize.group_records(typed),
        outcome=schema.reduce_outcomes(tuple(step.outcome for step in steps)),
        loss=loss,
    )
    return ScheduledRun(
        artifact=artifact,
        ledger=ledger_of(
            tuple(operations),
            manifest,
            stop_reason=artifact.outcome,
            dispatch_ordinal=dispatch_ordinal,
            start_tick_us=start_tick_us,
        ),
    )


def run_acquisition(
    manifest: schema.AcquisitionManifest,
    carrier: Optional[transport.Transport] = None,
    clock: Callable[[], float] = time.monotonic,
    lanes: int = MAX_CONCURRENT_LANES,
) -> schema.AcquisitionArtifact:
    """Run one validated manifest to one immutable artifact.

    Naming no carrier composes the paced, caching one; see
    :func:`run_scheduled`.
    """

    return run_scheduled(manifest, carrier, clock=clock, lanes=lanes).artifact
