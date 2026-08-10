"""Runner seam: the core owns route selection, caps, page count, and stop.

Adapters are reached only through the literal branches in
:func:`descriptor_for` and :func:`call_adapter` — one ``if`` per adapter
module, statically imported. There is no registry, no dynamic import, and
no ``getattr`` dispatch, so exact search over an adapter's name finds every
place the core can call it.
"""

from __future__ import annotations

from dataclasses import replace
from typing import List, Optional, Tuple

from . import normalize, router, schema, transport
from .adapters import AdapterDescriptor, AdapterRequest, NativePage, fake, reddit_archive
from .adapters import web_search


class RunnerError(RuntimeError):
    """The core was asked for an adapter branch that does not exist."""


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
