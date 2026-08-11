"""Pacing seam: one route's declared ceiling, waited out per route.

A measured ceiling is a constraint this package waits out, never one it works
around: there is no proxy pool, no address rotation, no second identity, and
no substituted route anywhere in it. The one lever :class:`RateGovernor` has
is time.

Reliability bar: nothing here reaches the network or the filesystem. The
carrier is injected, the clock is injected, and both have offline stand-ins.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, replace
from typing import Callable, Dict, Iterable, List, Optional

from . import cache, transport
from .adapters import AdapterDescriptor


US_PER_SECOND = 1000000
US_PER_MS = 1000


def tick_us(clock: Callable[[], float]) -> int:
    """One clock reading as whole microseconds, which is the unit a tick is in."""

    return int(round(clock() * US_PER_SECOND))


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
            raise runner.RunnerError(
                "route {0} is declared two different budgets: {1} and {2}".format(
                    descriptor.route_id, held, declared
                )
            )
        budgets[descriptor.route_id] = declared
    return budgets


def route_budgets() -> Dict[str, RouteBudget]:
    """Every route this core can read, paired with the ceiling its adapter declares."""

    return budgets_from(
        descriptor
        for adapter_id in runner.ADAPTER_IDS
        for descriptor in runner.surface_descriptors(adapter_id)
    )


def cooldown_us(
    response: transport.TransportResponse, budget: RouteBudget
) -> int:
    """How long a refused route waits: the interval the origin stated, or the budget's.

    Whichever is longer, and never anything else. Reading a stated interval is
    how this package obeys a limit it was told about rather than only the one
    it measured, and there is exactly one direction the reading may move a
    wait: longer. An interval shorter than the measured ceiling, one already
    elapsed, and one nobody sent all leave the measured ceiling standing —
    taking the origin's number *instead* would be evasion wearing the shape of
    compliance, and it would look identical in a log.
    """

    stated_us = int(round(transport.stated_wait_seconds(response) * US_PER_SECOND))
    return max(budget.cooldown_ms * US_PER_MS, stated_us)


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
        self._charge(request.route_id, budget, began_us, stopped_us, response)
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
            raise runner.RunnerError("route {0} declares no rate budget".format(route_id))
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
        self,
        route_id: str,
        budget: RouteBudget,
        began_us: int,
        stopped_us: int,
        response: transport.TransportResponse,
    ) -> None:
        """Spend one read against this route, and open a cooldown if it was refused.

        The whole response is charged rather than its status alone, because an
        origin that refuses usually says how long for, and it says it in a
        header. A governor holding only the status has no way to hear that.
        """

        arrival_us = self._route_arrival_us.get(route_id, began_us)
        self._route_arrival_us[route_id] = (
            max(arrival_us, began_us) + budget.min_interval_ms * US_PER_MS
        )
        if response.status == transport.RATE_LIMITED_STATUS:
            self._route_blocked_until_us[route_id] = stopped_us + cooldown_us(response, budget)

    def _elapsed_us(self) -> int:
        return tick_us(self._clock) - self._origin_us

    def _wait_until(self, ready_us: int) -> int:
        """Spend time, and only time, to come inside a route's budget."""

        waited_us = ready_us - self._elapsed_us()
        if waited_us <= 0:
            return 0
        self._sleep(waited_us / float(US_PER_SECOND))
        return waited_us


def paced_carrier(
    carrier: Optional[transport.Transport] = None,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> RateGovernor:
    """The carrier a run gets when it does not build one: paced, and remembering.

    One constructor, because the composition is not optional. Spec change 1
    calls the run-local cache mandatory and change 2 says the scheduler enforces
    each route's budget; a `RateGovernor` that passes its own unit test while
    nothing in the delivery ever builds one satisfies neither. This is the one
    place the two are put together, so "a rate limit is respected, never evaded"
    is a property of the shipped path rather than of a test fixture.

    The cache takes the same clock the governor paces on, so a TTL and an
    interval cannot disagree about how much time has passed. Building the real
    :class:`transport.Transport` here rather than at import keeps importing this
    module free of I/O.
    """

    return RateGovernor(
        transport.Transport() if carrier is None else carrier,
        run_cache=cache.RunCache(clock=clock),
        clock=clock,
        sleep=sleep,
    )


# Imported last, and as a module rather than by name. This module reads the
# core's adapter table at call time, and the core re-exports every public name
# above, so the two import each other. Binding the module object down here —
# after every name above exists — is what makes the pair safe to import in
# either order; a ``from .runner import ...`` at the top would fail whenever
# this module was imported before the core.
from . import runner
