"""Runner seam: the core owns route selection, pacing, caps, page count, and stop.

Adapters are reached only through the literal branches in
:func:`descriptor_for` and :func:`call_adapter` — one ``if`` per adapter
module, statically imported. There is no registry, no dynamic import, and
no ``getattr`` dispatch, so exact search over an adapter's name finds every
place the core can call it.

This module also owns the rate governor. A measured ceiling is a constraint
this package waits out, never one it works around: there is no proxy pool, no
address rotation, no second identity, and no substituted route anywhere in it.
The one lever it has is time.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, replace
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from . import cache, normalize, router, schema, transport
from .adapters import AdapterDescriptor, AdapterRequest, NativePage
from .adapters import fake, reddit_archive, web_search

US_PER_SECOND = 1000000
US_PER_MS = 1000

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


def route_budgets() -> Dict[str, RouteBudget]:
    """Every route this core can read, paired with the ceiling its adapter declares."""

    return budgets_from(
        descriptor for descriptor in map(descriptor_for, ADAPTER_IDS) if descriptor is not None
    )


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
        self._origin_us = int(round(clock() * US_PER_SECOND))
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
        return int(round(self._clock() * US_PER_SECOND)) - self._origin_us

    def _wait_until(self, ready_us: int) -> int:
        """Spend time, and only time, to come inside a route's budget."""

        waited_us = ready_us - self._elapsed_us()
        if waited_us <= 0:
            return 0
        self._sleep(waited_us / float(US_PER_SECOND))
        return waited_us


def artifact_id_for(manifest_id: str) -> str:
    return "artifact:" + manifest_id


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


def run_step(
    step: schema.AcquisitionStep,
    carrier: transport.Transport,
    artifact_id: str,
    manifest_id: str,
) -> Tuple[schema.StepResult, Tuple[schema.AcquisitionRecord, ...]]:
    descriptor = descriptor_for(step.adapter_id)
    if descriptor is None:
        return (
            schema.StepResult(
                step_id=step.step_id,
                adapter_id=step.adapter_id,
                route_id="",
                pages=0,
                records_received=0,
                records_kept=0,
                outcome="refused",
                loss=("no_route",),
            ),
            (),
        )

    decision = router.select_route(step, descriptor, transport.route_admissions())
    if not decision.admitted:
        return (
            schema.StepResult(
                step_id=step.step_id,
                adapter_id=step.adapter_id,
                route_id=decision.route_id,
                pages=0,
                records_received=0,
                records_kept=0,
                outcome="refused",
                loss=(decision.refusal_reason,),
            ),
            (),
        )

    records: List[schema.AcquisitionRecord] = []
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
        page = call_adapter(step.adapter_id, carrier, request)
        pages += 1
        page_outcomes.append(page.outcome)
        loss.extend(page.loss)
        received += len(page.records)
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
    )


def run_acquisition(
    manifest: schema.AcquisitionManifest, carrier: transport.Transport
) -> schema.AcquisitionArtifact:
    """Run one validated manifest to one immutable artifact."""

    artifact_id = artifact_id_for(manifest.manifest_id)
    steps: List[schema.StepResult] = []
    records: List[schema.AcquisitionRecord] = []
    for step in manifest.steps:
        result, step_records = run_step(step, carrier, artifact_id, manifest.manifest_id)
        steps.append(result)
        records.extend(step_records)

    loss = tuple(sorted({code for step in steps for code in step.loss}))
    return schema.AcquisitionArtifact(
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
