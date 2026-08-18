"""Pure planning and accounting helpers for the runner facade."""

from __future__ import annotations

from typing import Tuple

from .. import cache, normalize, schema, transport
from ..adapters import AdapterRequest, NativePage
from ..ordering import instant_seconds


def planned_calls(step: schema.AcquisitionStep) -> Tuple[Tuple[AdapterRequest, str], ...]:
    """Every bounded call this step authorizes, paired with its discovery locator."""

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
    """Whether one record's own time falls inside the step's window."""

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


def refused_step(
    step: schema.AcquisitionStep, route_id: str, reason: str
) -> schema.StepResult:
    return schema.StepResult(
        step_id=step.step_id,
        adapter_id=step.adapter_id,
        route_id=route_id,
        pages=0,
        records_received=0,
        records_kept=0,
        outcome="refused",
        loss=(reason,),
        kind=step.kind,
        query=step.query,
    )


def reached_origin(page: NativePage) -> bool:
    """Whether this page cost the origin a read."""

    return (
        page.outcome != "refused"
        and cache.CACHE_HIT not in page.loss
        and transport.UNREACHABLE not in page.loss
    )
