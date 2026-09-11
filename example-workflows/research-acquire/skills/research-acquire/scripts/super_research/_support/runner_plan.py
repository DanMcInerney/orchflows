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


def offers_another_page(
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
    That is the whole difference between here and the two refusals in
    `runner.run_step`'s own loop: those stop a step that still wanted more, and
    say so with a loss code.

    ``max_pages`` only ever lowers the count. A step declaring more than
    `runner.MAX_PAGES_PER_STEP` is stopped by the core's backstop in the loop,
    where stopping is a loss, because a bound the core imposed is not one the
    caller reached.
    """

    if step.max_pages and calls_made >= step.max_pages:
        return False
    return step.kind == "discovery" and bool(page.cursor_out) and kept < step.max_items
