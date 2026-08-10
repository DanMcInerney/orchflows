"""Work-ledger seam: what a dispatch consumed, and the schedule a mode admits.

Additive per-operation deltas in one causal order, plus the schedule a mode
admits. ``staged`` and ``fused`` produce the same artifact and differ only in
that schedule, which is what "collapses latency, never lineage" means
arithmetically.

Reliability bar: pure. Nothing here reads a clock, a socket, or a file — every
tick is a number the caller already had.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

from . import schema


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
