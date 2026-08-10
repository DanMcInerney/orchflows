"""Runner seam: the core owns dispatch, pacing, the work ledger, and ordering.

Four concerns, in the order they appear below, because each one needs the one
before it.

*Dispatch.* Adapters are reached only through the literal branches in
:func:`descriptor_for` and :func:`call_adapter` — one ``if`` per adapter
module, statically imported, both covering exactly :data:`ADAPTER_IDS`. There
is no registry, no dynamic import, and no ``getattr`` dispatch, so exact
search over an adapter's name finds every place the core can call it.

*Pacing.* A measured ceiling is a constraint this package waits out, never one
it works around: there is no proxy pool, no address rotation, no second
identity, and no substituted route anywhere in it. The one lever
:class:`RateGovernor` has is time.

*The work ledger.* What a dispatch consumed, as additive per-operation deltas
in one causal order, plus the schedule a mode admits. ``staged`` and ``fused``
produce the same artifact and differ only in that schedule, which is what
"collapses latency, never lineage" means arithmetically.

*Ordering.* The five named views over a frozen ``as_of``. No wall clock
participates, and an engagement metric is read by the exact name its adapter
declares.

Reliability bar: nothing here reaches the network or the filesystem. The
carrier is injected, the clock is injected, and both have offline stand-ins.
"""

from __future__ import annotations

import time
import unicodedata
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from . import cache, normalize, router, schema, transport
from .adapters import AdapterDescriptor, AdapterRequest, NativePage
from .adapters import fake, reddit_archive, web_search

US_PER_SECOND = 1000000
US_PER_MS = 1000


def tick_us(clock: Callable[[], float]) -> int:
    """One clock reading as whole microseconds, which is the unit a tick is in."""

    return int(round(clock() * US_PER_SECOND))

# Every adapter this core can reach, spelled once. It is a literal tuple, not a
# registry: exact search over an id still finds the two branches below, and a
# later adapter listed here without both of them fails loudly.
ADAPTER_IDS = ("fake", "reddit_archive", "web_search")


class RunnerError(RuntimeError):
    """The core was asked for something it refuses to guess at."""


def descriptor_for(adapter_id: str) -> Optional[AdapterDescriptor]:
    """Literal branches only. An unknown adapter is refused, never guessed."""

    if adapter_id == "fake":
        return fake.DESCRIPTOR
    if adapter_id == "reddit_archive":
        return reddit_archive.DESCRIPTOR
    if adapter_id == "web_search":
        return web_search.DESCRIPTOR
    return None


def call_adapter(
    adapter_id: str, carrier: transport.Transport, request: AdapterRequest
) -> NativePage:
    """One bounded adapter call returning exactly one NativePage."""

    if adapter_id == "fake":
        return fake.fetch_native_page(carrier, request)
    if adapter_id == "reddit_archive":
        return reddit_archive.fetch_native_page(carrier, request)
    if adapter_id == "web_search":
        return web_search.fetch_native_page(carrier, request)
    raise RunnerError("no adapter branch for " + adapter_id)


@dataclass(frozen=True)
class RouteBudget:
    """One route's measured ceiling: how often, how many at once, how long after a refusal."""

    min_interval_ms: int
    burst: int
    cooldown_ms: int


def budget_of(descriptor: AdapterDescriptor) -> RouteBudget:
    """The ceiling one adapter declares for the route it reads."""

    return RouteBudget(
        min_interval_ms=descriptor.min_interval_ms,
        burst=descriptor.burst,
        cooldown_ms=descriptor.cooldown_ms,
    )


def budgets_from(descriptors: Iterable[AdapterDescriptor]) -> Dict[str, RouteBudget]:
    """Collect declared ceilings per route, refusing a route two adapters disagree on.

    The ceiling belongs to the origin, not to the adapter, so a disagreement is
    a contradiction rather than a preference: resolving it silently would pace
    one route by whichever adapter happened to be declared last.
    """

    budgets: Dict[str, RouteBudget] = {}
    for descriptor in descriptors:
        declared = budget_of(descriptor)
        held = budgets.get(descriptor.route_id)
        if held is not None and held != declared:
            raise RunnerError(
                "route {0} is declared two different budgets: {1} and {2}".format(
                    descriptor.route_id, held, declared
                )
            )
        budgets[descriptor.route_id] = declared
    return budgets


def declared_descriptors() -> Dict[str, AdapterDescriptor]:
    """Every adapter this core lists, by id."""

    found: Dict[str, AdapterDescriptor] = {}
    for adapter_id in ADAPTER_IDS:
        descriptor = descriptor_for(adapter_id)
        if descriptor is not None:
            found[adapter_id] = descriptor
    return found


def route_budgets() -> Dict[str, RouteBudget]:
    """Every route this core can read, paired with the ceiling its adapter declares."""

    return budgets_from(declared_descriptors().values())


@dataclass(frozen=True)
class OriginRead:
    """One read that actually reached an origin, on the clock that paced it.

    A cache hit produces no entry here: pacing lives on the miss path, so an
    answer already held costs the route's budget nothing. Times are
    microseconds since the governor was made.
    """

    route_id: str
    at_us: int
    duration_us: int
    waited_us: int
    status: int


class RateGovernor:
    """Carrier-shaped pacing: one route's declared ceiling, waited out per route.

    It stands exactly where a :class:`transport.Transport` stands, so no
    adapter changes and no adapter can bypass it. Wrapping a run cache is the
    whole composition — ``serve`` reaches the paced fetch only on a miss.

    The clock is monotonic seconds and the wait is an injected ``sleep``, which
    is what makes a thirty-second interval provable in microseconds of real
    time: a fake clock's ``sleep`` moves time without spending any.
    """

    def __init__(
        self,
        carrier: transport.Transport,
        run_cache: Optional[cache.RunCache] = None,
        budgets: Optional[Dict[str, RouteBudget]] = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._carrier = carrier
        self._cache = run_cache
        self._budgets = dict(route_budgets() if budgets is None else budgets)
        self._clock = clock
        self._sleep = sleep
        self._origin_us = tick_us(clock)
        # Per route: the arrival time the declared interval implies, and the
        # moment a refusal's cooldown ends. They are separate because a burst
        # allowance may be spent against the first and never against the
        # second — an origin that asked for fewer requests is not owed fewer.
        self._route_arrival_us: Dict[str, int] = {}
        self._route_blocked_until_us: Dict[str, int] = {}
        self.log: List[OriginRead] = []
        self.serves: List[cache.CacheServe] = []

    @property
    def calls(self) -> List[transport.TransportRequest]:
        """The carrier's own attempt log, so the governor stands where it stands."""

        return self._carrier.calls

    def fetch(self, request: transport.TransportRequest) -> transport.TransportResponse:
        """Answer one request, reaching the origin only when memory and budget say so."""

        if self._cache is None:
            return self._paced_fetch(request)
        serve = self._cache.serve(request, self._paced_fetch)
        self.serves.append(serve)
        # Copied with the flag raised, never rebuilt: ``observed_at`` stays the
        # moment the origin was really read, which is the whole point of
        # holding the response verbatim in the first place.
        return replace(serve.response, cache_hit=serve.cache_hit)

    def _paced_fetch(
        self, request: transport.TransportRequest
    ) -> transport.TransportResponse:
        """Reached only on a cache miss, which is what makes a hit free."""

        budget = self._budget_for(request.route_id)
        waited_us = self._wait_until(self._ready_at(request.route_id, budget))
        began_us = self._elapsed_us()
        response = self._carrier.fetch(request)
        stopped_us = self._elapsed_us()
        self._charge(request.route_id, budget, began_us, stopped_us, response.status)
        self.log.append(
            OriginRead(
                route_id=request.route_id,
                at_us=began_us,
                duration_us=stopped_us - began_us,
                waited_us=waited_us,
                status=response.status,
            )
        )
        return response

    def _budget_for(self, route_id: str) -> RouteBudget:
        budget = self._budgets.get(route_id)
        if budget is None:
            raise RunnerError("route {0} declares no rate budget".format(route_id))
        return budget

    def _ready_at(self, route_id: str, budget: RouteBudget) -> int:
        """The earliest moment this route's declared budget admits another read.

        Spacing is a theoretical arrival time the burst allowance may run
        behind: a route declaring sixty per hour as one bucket spends sixty
        reads at once and then refills one per minute, which is what the
        origin permits and what one interval alone would forbid.
        """

        interval_us = budget.min_interval_ms * US_PER_MS
        ready_us = self._route_blocked_until_us.get(route_id, 0)
        arrival_us = self._route_arrival_us.get(route_id)
        if arrival_us is not None:
            ready_us = max(ready_us, arrival_us - (budget.burst - 1) * interval_us)
        return ready_us

    def _charge(
        self, route_id: str, budget: RouteBudget, began_us: int, stopped_us: int, status: int
    ) -> None:
        """Spend one read against this route, and open a cooldown if it was refused."""

        arrival_us = self._route_arrival_us.get(route_id, began_us)
        self._route_arrival_us[route_id] = (
            max(arrival_us, began_us) + budget.min_interval_ms * US_PER_MS
        )
        if status == transport.RATE_LIMITED_STATUS:
            self._route_blocked_until_us[route_id] = (
                stopped_us + budget.cooldown_ms * US_PER_MS
            )

    def _elapsed_us(self) -> int:
        return tick_us(self._clock) - self._origin_us

    def _wait_until(self, ready_us: int) -> int:
        """Spend time, and only time, to come inside a route's budget."""

        waited_us = ready_us - self._elapsed_us()
        if waited_us <= 0:
            return 0
        self._sleep(waited_us / float(US_PER_SECOND))
        return waited_us


# The retained work-ledger contract's two closed sets, verbatim. Their ordinals
# are half of the causal key, so they are the contract rather than a
# convenience: a kind or a metric added without an ordinal cannot be ordered
# against the ones that have one. This core schedules exactly one kind of
# operation — one adapter call producing one native page — and emits four of
# the metrics; the rest belong to seams this module does not own.
OPERATION_KIND_ORDINALS = {
    "oauth_control": 0,
    "http_head": 1,
    "http_get": 2,
    "redirect_hop": 3,
    "gh_process": 4,
    "native_page": 5,
    "projection": 6,
}
METRIC_ORDINALS = {
    "calls": 0,
    "pages": 1,
    "items": 2,
    "bytes": 3,
    "fake_duration": 4,
    "projected_bytes": 5,
    "stop": 6,
}

# Every metric whose deltas sum to what the artifact says it consumed. `stop`
# is a marker with a zero delta and contributes to nothing. `fake_makespan_us`
# is absent on purpose: it is derived over the schedule and is not a metric, so
# it cannot be reached by summing anything.
ADDITIVE_METRICS = ("calls", "pages", "items", "bytes", "fake_duration", "projected_bytes")

NATIVE_PAGE = "native_page"


@dataclass(frozen=True)
class PlannedOperation:
    """One unit of work the core scheduled: one adapter call, one native page.

    ``reached_origin`` is false when a run's own memory answered, which is what
    separates a page from a call: the page was still produced and the call was
    still not spent.
    """

    step_id: str
    adapter_id: str
    route_id: str
    page_index: int
    duration_us: int
    reached_origin: bool
    records_received: int


@dataclass(frozen=True)
class ScheduledOperation:
    """One operation and where the mode's schedule placed it."""

    operation: PlannedOperation
    start_tick_us: int
    stop_tick_us: int


@dataclass(frozen=True)
class WorkLedgerEvent:
    """One metric delta, attributed to one operation of one dispatch.

    ``attempt`` is always 1 here, and that is the statement rather than a
    placeholder: an adapter returns after one call and never retries, so the
    absence of a second attempt is recorded as data instead of as silence.
    """

    operation_id: str
    dispatch_ordinal: int
    operation_ordinal: int
    manifest_id: str
    step_id: str
    adapter_id: str
    route_id: str
    attempt: int
    page_index: int
    operation_kind: str
    metric: str
    delta: int
    start_tick_us: int
    stop_tick_us: int
    reason: str = ""


@dataclass(frozen=True)
class ScheduledRun:
    """One dispatch: the artifact it produced, and the ledger of how."""

    artifact: schema.AcquisitionArtifact
    ledger: Tuple[WorkLedgerEvent, ...]


def causal_key(event: WorkLedgerEvent) -> Tuple[int, int, int, int, str]:
    """The retained contract's serialization key, verbatim.

    Ordinals rather than ticks, because a fused schedule deliberately overlaps
    two lanes: the order work happened in is a fact about the dispatch, and the
    order it was placed in is a fact about the mode.
    """

    return (
        event.dispatch_ordinal,
        event.operation_ordinal,
        OPERATION_KIND_ORDINALS[event.operation_kind],
        METRIC_ORDINALS[event.metric],
        event.operation_id,
    )


def ledger_sums(events: Iterable[WorkLedgerEvent]) -> Dict[str, int]:
    """Every additive metric's total. A stop marker adds to nothing."""

    sums: Dict[str, int] = {}
    for event in events:
        if event.metric in ADDITIVE_METRICS:
            sums[event.metric] = sums.get(event.metric, 0) + event.delta
    return sums


def fake_makespan_us(events: Iterable[WorkLedgerEvent]) -> int:
    """The span of the schedule these events describe, or zero with no operation.

    Derived, never accumulated: two operations that overlap are counted once
    between them, which is exactly the quantity a sum of durations cannot
    express and the only one that tells staged from fused.
    """

    ticks = [
        (event.start_tick_us, event.stop_tick_us) for event in events if event.metric != "stop"
    ]
    if not ticks:
        return 0
    return max(stop for _, stop in ticks) - min(start for start, _ in ticks)


def planned_operations(events: Iterable[WorkLedgerEvent]) -> Tuple[WorkLedgerEvent, ...]:
    """One event per operation, in causal order: the ledger's own index of the work.

    ``pages`` is emitted exactly once per operation, because one native page
    per adapter call is the package's law.
    """

    return tuple(event for event in events if event.metric == "pages")


def schedule_of(
    operations: Iterable[PlannedOperation], mode: str, start_tick_us: int = 0
) -> Tuple[ScheduledOperation, ...]:
    """Place each operation where this mode admits it.

    ``staged`` puts a caller between one step's output and the next step's
    input, so every step waits for the one before it and the schedule is a
    single line. ``fused`` freezes both steps' inputs in one manifest, so a
    step waits only for its own earlier pages and for its own route — one
    route's budget never overlaps itself, whatever the mode.

    Overlapping two steps is sound because no step here reads what another step
    produced: a hydration step's calls come from ``selected_hits`` the caller
    froze, as :func:`planned_calls` shows, so ``prior_step_id`` records where a
    selection came from rather than a dependency a scheduler must serialize.
    That is the whole of the difference between the modes — placement moves,
    and nothing a step produces does.
    """

    placed: List[ScheduledOperation] = []
    lane_free_us: Dict[str, int] = {}
    route_free_us: Dict[str, int] = {}
    serial_free_us = start_tick_us
    for operation in operations:
        if mode == "fused":
            start_us = max(
                lane_free_us.get(operation.step_id, start_tick_us),
                route_free_us.get(operation.route_id, start_tick_us),
            )
        else:
            start_us = serial_free_us
        stop_us = start_us + operation.duration_us
        lane_free_us[operation.step_id] = stop_us
        route_free_us[operation.route_id] = stop_us
        serial_free_us = max(serial_free_us, stop_us)
        placed.append(
            ScheduledOperation(operation=operation, start_tick_us=start_us, stop_tick_us=stop_us)
        )
    return tuple(placed)


def ledger_of(
    operations: Iterable[PlannedOperation],
    manifest: schema.AcquisitionManifest,
    stop_reason: str,
    dispatch_ordinal: int = 0,
    start_tick_us: int = 0,
) -> Tuple[WorkLedgerEvent, ...]:
    """Every metric delta this dispatch produced, in causal order, then its stop marker."""

    placed = schedule_of(operations, manifest.mode, start_tick_us)
    events: List[WorkLedgerEvent] = []
    ordinal = 0
    for scheduled in placed:
        operation = scheduled.operation
        ordinal += 1
        deltas = (
            ("calls", 1 if operation.reached_origin else 0),
            ("pages", 1),
            ("items", operation.records_received),
            ("fake_duration", scheduled.stop_tick_us - scheduled.start_tick_us),
        )
        for metric, delta in deltas:
            events.append(
                WorkLedgerEvent(
                    operation_id="{0}#{1}.{2}".format(
                        manifest.manifest_id, dispatch_ordinal, ordinal
                    ),
                    dispatch_ordinal=dispatch_ordinal,
                    operation_ordinal=ordinal,
                    manifest_id=manifest.manifest_id,
                    step_id=operation.step_id,
                    adapter_id=operation.adapter_id,
                    route_id=operation.route_id,
                    attempt=1,
                    page_index=operation.page_index,
                    operation_kind=NATIVE_PAGE,
                    metric=metric,
                    delta=delta,
                    start_tick_us=scheduled.start_tick_us,
                    stop_tick_us=scheduled.stop_tick_us,
                )
            )
    # One marker per dispatch, at the schedule's end, naming why the run
    # stopped. It takes the kind of the work it ends because that is the one
    # kind this core schedules, and nothing may start after it.
    end_us = max((scheduled.stop_tick_us for scheduled in placed), default=start_tick_us)
    events.append(
        WorkLedgerEvent(
            operation_id="{0}#{1}.stop".format(manifest.manifest_id, dispatch_ordinal),
            dispatch_ordinal=dispatch_ordinal,
            operation_ordinal=ordinal + 1,
            manifest_id=manifest.manifest_id,
            step_id="",
            adapter_id="",
            route_id="",
            attempt=1,
            page_index=-1,
            operation_kind=NATIVE_PAGE,
            metric="stop",
            delta=0,
            start_tick_us=end_us,
            stop_tick_us=end_us,
            reason=stop_reason,
        )
    )
    return tuple(events)


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
    loss: List[str] = []
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
        loss.extend(page.loss)
        received += len(page.records)
        operations.append(
            PlannedOperation(
                step_id=step.step_id,
                adapter_id=step.adapter_id,
                route_id=descriptor.route_id,
                page_index=page_index,
                duration_us=tick_us(clock) - began_us,
                reached_origin=cache.CACHE_HIT not in page.loss,
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
    return (
        schema.StepResult(
            step_id=step.step_id,
            adapter_id=step.adapter_id,
            route_id=decision.route_id,
            pages=pages,
            records_received=received,
            records_kept=len(records),
            outcome=outcome,
            loss=tuple(loss),
        ),
        tuple(records),
        tuple(operations),
    )


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


def _declared_metric(
    record: schema.AcquisitionRecord,
    descriptors: Dict[str, AdapterDescriptor],
    order: str,
) -> str:
    descriptor = descriptors.get(record.adapter_id)
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
    declared = declared_descriptors() if descriptors is None else descriptors
    return tuple(
        sorted(ordered, key=lambda record: ordering_key(record, order, as_of, declared))
    )


def run_scheduled(
    manifest: schema.AcquisitionManifest,
    carrier: transport.Transport,
    clock: Callable[[], float] = time.monotonic,
    dispatch_ordinal: int = 0,
    start_tick_us: int = 0,
) -> ScheduledRun:
    """Run one validated manifest to one immutable artifact and its work ledger.

    Steps are executed in declared order whatever the mode, so an artifact is
    the same artifact either way; the mode reaches only the schedule the ledger
    records.
    """

    artifact_id = artifact_id_for(manifest.manifest_id)
    steps: List[schema.StepResult] = []
    records: List[schema.AcquisitionRecord] = []
    operations: List[PlannedOperation] = []
    for step in manifest.steps:
        result, step_records, step_operations = run_step(
            step, carrier, artifact_id, manifest.manifest_id, clock=clock
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
    carrier: transport.Transport,
    clock: Callable[[], float] = time.monotonic,
) -> schema.AcquisitionArtifact:
    """Run one validated manifest to one immutable artifact."""

    return run_scheduled(manifest, carrier, clock=clock).artifact
