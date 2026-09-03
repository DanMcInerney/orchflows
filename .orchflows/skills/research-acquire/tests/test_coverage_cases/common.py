"""Shared builders for coverage-seam checks."""

from __future__ import annotations

from super_research import schema
from super_research.adapters import youtube_innertube


def record(
    record_id,
    adapter_id,
    native_item_id="n1",
    locator="https://example.invalid/a",
    discovery_locator="",
    representation_kind="index",
    native_parent_id="",
    step_id="s1",
):
    """One discovery record, with every field the schema requires supplied."""

    return schema.AcquisitionRecord(
        record_id=record_id,
        artifact_id="art",
        manifest_id="man",
        step_id=step_id,
        adapter_id=adapter_id,
        adapter_version="1",
        route_id="r",
        access_class="K2",
        operator_identity="",
        platform="p",
        native_identity_namespace="ns",
        group_scope="g",
        representation_kind=representation_kind,
        canonical_content_kind="post",
        native_item_id=native_item_id,
        native_parent_id=native_parent_id,
        canonical_locator=locator,
        normalized_locator=locator,
        exact_content_hash="h",
        title="t",
        body="b",
        author="a",
        community="c",
        published_at="2026-08-17T00:00:00Z",
        observed_at="2026-08-17T00:00:00Z",
        time_confidence="authoritative",
        usable_basis_time="2026-08-17T00:00:00Z",
        engagement=(),
        page_index=0,
        list_index=0,
        native_position=0,
        discovery_locator=discovery_locator,
        outcome="ok",
        loss=(),
    )


def step(step_id, kind, adapter_id, **kw):
    return schema.AcquisitionStep(
        step_id=step_id, kind=kind, adapter_id=adapter_id, max_items=kw.pop("max_items", 500), **kw
    )


def step_result(step_id, adapter_id, kind="discovery", query="", outcome="ok", loss=()):
    """One `StepResult`, saying what its step was the way `runner` fills it."""

    return schema.StepResult(
        step_id=step_id,
        adapter_id=adapter_id,
        route_id="r",
        pages=1,
        records_received=0,
        records_kept=0,
        outcome=outcome,
        loss=tuple(loss),
        warnings=(),
        kind=kind,
        query=query,
    )


def manifest(*steps):
    return schema.AcquisitionManifest(
        manifest_id="m", mode="fused", as_of="2026-08-17T19:00:00Z", steps=tuple(steps)
    )


def artifact(steps=(), records=()):
    return schema.AcquisitionArtifact(
        artifact_id="a",
        manifest_id="m",
        mode="fused",
        as_of="2026-08-17T19:00:00Z",
        records=tuple(records),
        steps=tuple(steps),
        edges=(),
        groups=(),
        outcome="ok",
        loss=(),
    )


# The representation kinds this adapter's own descriptors declare, read off the
# source rather than spelled here. They are what a *record* carries, and the
# fixtures below set them so a record looks like what it would look like in the
# field. The review no longer reads them at all: deciding depth from the kind a
# record arrived at is the inference this change deleted, and it is what marked
# plain search rows as deepened. A literal here would let the fixtures drift
# from the adapter; a sentence saying the review consults them would leave the
# wrong mental model exactly where the next author opens the file.
YOUTUBE_DISCOVERED_AS = youtube_innertube.DESCRIPTOR.representation_kind
YOUTUBE_TRANSCRIPT_AS = youtube_innertube.TRANSCRIPT_DESCRIPTOR.representation_kind


def codes(advisories):
    return sorted({found.code for found in advisories})


def subjects(advisories, code):
    return sorted(found.subject for found in advisories if found.code == code)
