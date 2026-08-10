"""Runner seam: the core owns dispatch, and the run a manifest becomes.

*Dispatch.* Adapters are reached only through the literal branches in
:func:`descriptor_for` and :func:`call_adapter` — one ``if`` per adapter
module, statically imported, both covering exactly :data:`ADAPTER_IDS`. There
is no registry, no dynamic import, and no ``getattr`` dispatch, so exact
search over an adapter's name finds every place the core can call it.

*The run.* One validated manifest becomes one immutable artifact and the
ledger of how: steps in declared order whatever the mode, one native page per
adapter call, and the core alone owning the caps and the stop. Nothing here
runs concurrently and nothing here pages: :func:`planned_calls` is the only
production constructor of an ``AdapterRequest`` and never sets a cursor, so a
discovery step authorizes exactly one call.

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
from dataclasses import replace
from typing import Callable, Dict, List, Optional, Tuple

from . import cache, normalize, router, schema, transport
from .adapters import AdapterDescriptor, AdapterRequest, NativePage
from .adapters import fake, github_rest, hacker_news, instagram_public
from .adapters import linkedin_jobs, linkedin_public, public_page, reddit_archive
from .adapters import reddit_feed
from .adapters import rss_atom, web_search
from .adapters import x_guest, x_syndication, youtube_innertube
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
    "fake",
    "github_rest",
    "hacker_news",
    "instagram_public",
    "linkedin_jobs",
    "linkedin_public",
    "public_page",
    "reddit_archive",
    "reddit_feed",
    "rss_atom",
    "web_search",
    "x_guest",
    "x_syndication",
    "youtube_innertube",
)


class RunnerError(RuntimeError):
    """The core was asked for something it refuses to guess at."""


def descriptor_for(adapter_id: str) -> Optional[AdapterDescriptor]:
    """Literal branches only. An unknown adapter is refused, never guessed."""

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
    if adapter_id == "public_page":
        return public_page.DESCRIPTOR
    if adapter_id == "reddit_archive":
        return reddit_archive.DESCRIPTOR
    if adapter_id == "reddit_feed":
        return reddit_feed.DESCRIPTOR
    if adapter_id == "rss_atom":
        return rss_atom.DESCRIPTOR
    if adapter_id == "web_search":
        return web_search.DESCRIPTOR
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
    if adapter_id == "public_page":
        return public_page.fetch_native_page(carrier, request)
    if adapter_id == "reddit_archive":
        return reddit_archive.fetch_native_page(carrier, request)
    if adapter_id == "reddit_feed":
        return reddit_feed.fetch_native_page(carrier, request)
    if adapter_id == "rss_atom":
        return rss_atom.fetch_native_page(carrier, request)
    if adapter_id == "web_search":
        return web_search.fetch_native_page(carrier, request)
    if adapter_id == "x_guest":
        return x_guest.fetch_native_page(carrier, request)
    if adapter_id == "x_syndication":
        return x_syndication.fetch_native_page(carrier, request)
    if adapter_id == "youtube_innertube":
        return youtube_innertube.fetch_native_page(carrier, request)
    raise RunnerError("no adapter branch for " + adapter_id)


def surface_descriptors(adapter_id: str) -> Tuple[AdapterDescriptor, ...]:
    """Every route one adapter can reach, one descriptor each.

    Most adapters read one route and this is its one descriptor. Two do not:
    ``hacker_news`` reads two origins, and ``github_rest`` reads one origin
    whose anonymous hour is counted in two separate buckets. A budget belongs
    to whoever sets it, so an adapter like those declares one descriptor per
    route and this is where the second becomes reachable. Literal branches,
    like the two above: a surface the core cannot see here is a route the
    scheduler would refuse to pace.
    """

    if adapter_id == "github_rest":
        return github_rest.SURFACE_DESCRIPTORS
    if adapter_id == "hacker_news":
        return hacker_news.SURFACE_DESCRIPTORS
    if adapter_id == "public_page":
        return public_page.SURFACE_DESCRIPTORS
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
        return ((AdapterRequest(step_id=step.step_id, query=step.query), ""),)
    return tuple(
        (
            AdapterRequest(step_id=step.step_id, target_ids=(hit.target_id,)),
            normalize.normalized_locator(hit.discovery_locator),
        )
        for hit in step.selected_hits
    )


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

    Two ways it did not, and until an adapter could refuse there was only one.
    A run's own memory answered, which is what ``cache_hit`` says. Or the
    adapter refused before making a call at all — a target it does not serve
    costs a page and no read — and billing that as a call would put work in the
    ledger that no origin ever saw. ``refused`` is the one outcome that means
    the read never left: every other one, including a failure, describes
    something an origin or the local network actually answered.
    """

    return page.outcome != "refused" and cache.CACHE_HIT not in page.loss


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

    for page_index, (request, discovery_locator) in enumerate(planned_calls(step)):
        if len(records) >= step.max_items:
            # The core owns stop: no further call is made once the cap is met.
            truncated = True
            break
        began_us = tick_us(clock)
        page = call_adapter(step.adapter_id, carrier, request)
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
        room = step.max_items - len(records)
        if len(page.records) > room:
            truncated = True
        records.extend(
            normalize.normalize_page(
                replace(page, records=page.records[:room]),
                step,
                artifact_id,
                manifest_id,
                page_index=page_index,
                list_index_start=len(records),
                discovery_locator=discovery_locator,
            )
        )

    if truncated:
        # A raw cap counts every received record and may drop unseen uniques.
        loss.append("recall_window_partial")
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


def run_scheduled(
    manifest: schema.AcquisitionManifest,
    carrier: Optional[transport.Transport] = None,
    clock: Callable[[], float] = time.monotonic,
    dispatch_ordinal: int = 0,
    start_tick_us: int = 0,
) -> ScheduledRun:
    """Run one validated manifest to one immutable artifact and its work ledger.

    Steps are executed in declared order whatever the mode, so an artifact is
    the same artifact either way; the mode reaches only the schedule the ledger
    records.

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
    for step in manifest.steps:
        result, step_records, step_operations = run_step(
            step, reached, artifact_id, manifest.manifest_id, clock=clock
        )
        steps.append(result)
        records.extend(step_records)
        operations.extend(step_operations)

    loss = tuple(sorted({code for step in steps for code in step.loss}))
    artifact = schema.AcquisitionArtifact(
        artifact_id=artifact_id,
        manifest_id=manifest.manifest_id,
        mode=manifest.mode,
        as_of=manifest.as_of,
        records=tuple(records),
        steps=tuple(steps),
        edges=normalize.link_discovery_hydration(records),
        groups=normalize.group_records(records),
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
) -> schema.AcquisitionArtifact:
    """Run one validated manifest to one immutable artifact.

    Naming no carrier composes the paced, caching one; see
    :func:`run_scheduled`.
    """

    return run_scheduled(manifest, carrier, clock=clock).artifact
