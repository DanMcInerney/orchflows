"""Lane execution and artifact scheduling for the runner facade."""

from __future__ import annotations

import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Dict, List, Optional, Tuple

from .. import normalize, schema, transport
from ..ledger import PlannedOperation, ScheduledRun, ledger_of
from ..pacing import paced_carrier
from .runner_plan import artifact_id_for

MAX_CONCURRENT_LANES = 8

StepOutcome = Tuple[
    schema.StepResult, Tuple[schema.AcquisitionRecord, ...], Tuple[PlannedOperation, ...]
]
RunStep = Callable[
    [schema.AcquisitionStep, transport.Transport, str, str, Callable[[], float]],
    StepOutcome,
]


def lanes_of(
    steps: Tuple[schema.AcquisitionStep, ...],
) -> "OrderedDict[str, List[schema.AcquisitionStep]]":
    """The steps grouped by adapter, each group in declared order."""

    lanes: "OrderedDict[str, List[schema.AcquisitionStep]]" = OrderedDict()
    for step in steps:
        lanes.setdefault(step.adapter_id, []).append(step)
    return lanes


def run_lane(
    steps: List[schema.AcquisitionStep],
    carrier: transport.Transport,
    artifact_id: str,
    manifest_id: str,
    clock: Callable[[], float],
    run_step: RunStep,
) -> List[StepOutcome]:
    return [run_step(step, carrier, artifact_id, manifest_id, clock) for step in steps]


def run_steps(
    manifest: schema.AcquisitionManifest,
    carrier: transport.Transport,
    artifact_id: str,
    run_step: RunStep,
    clock: Callable[[], float] = time.monotonic,
    lanes: int = MAX_CONCURRENT_LANES,
) -> Tuple[StepOutcome, ...]:
    """Every step's outcome, in declared order, however the mode ran them."""

    grouped = lanes_of(manifest.steps)
    workers = max(1, min(lanes, MAX_CONCURRENT_LANES, len(grouped)))
    if manifest.mode != "fused" or workers < 2:
        return tuple(
            run_lane(
                list(manifest.steps),
                carrier,
                artifact_id,
                manifest.manifest_id,
                clock,
                run_step,
            )
        )
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(
                run_lane,
                steps,
                carrier,
                artifact_id,
                manifest.manifest_id,
                clock,
                run_step,
            )
            for steps in grouped.values()
        ]
        by_step_id: Dict[str, StepOutcome] = {}
        for future in futures:
            for outcome in future.result():
                by_step_id[outcome[0].step_id] = outcome
    return tuple(by_step_id[step.step_id] for step in manifest.steps)


def run_scheduled(
    manifest: schema.AcquisitionManifest,
    run_step: RunStep,
    carrier: Optional[transport.Transport] = None,
    clock: Callable[[], float] = time.monotonic,
    dispatch_ordinal: int = 0,
    start_tick_us: int = 0,
    lanes: int = MAX_CONCURRENT_LANES,
) -> ScheduledRun:
    """Run one validated manifest to one immutable artifact and its work ledger."""

    reached = paced_carrier(clock=clock) if carrier is None else carrier
    artifact_id = artifact_id_for(manifest.manifest_id)
    steps: List[schema.StepResult] = []
    records: List[schema.AcquisitionRecord] = []
    operations: List[PlannedOperation] = []
    for result, step_records, step_operations in run_steps(
        manifest, reached, artifact_id, run_step, clock=clock, lanes=lanes
    ):
        steps.append(result)
        records.extend(step_records)
        operations.extend(step_operations)

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
