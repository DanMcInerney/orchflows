"""Schema seam: closed enums, immutable values, and manifest validation.

Every value this module returns is frozen. Validation is total and runs
before any transport call, so an invalid manifest can never reach the
network.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Sequence, Tuple

MANIFEST_SCHEMA_VERSION = 2

# The one spelling every instant in this package is written in, owned here
# because this is the module that validates. `ordering.instant_seconds` parses
# with it and returns nothing for anything else, so an `as_of` this module
# admitted in another spelling would leave the ordering's horizon unset and
# every snapshot eligible — the frozen replay silently stops being frozen. A
# total validation is one that catches that here rather than nowhere.
INSTANT_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

# A `staged` manifest round-trips through the caller between discovery and
# hydration; a `fused` manifest collapses that latency without collapsing
# lineage. Both emit discovery and hydration as distinct linked records.
ACQUISITION_MODES = ("staged", "fused")

STEP_KINDS = ("discovery", "hydration")

# Ordered by severity for `reduce_outcomes`; a usable record never hides a
# failure and a failure never erases a usable record.
OUTCOMES = ("ok", "empty", "partial", "failed", "refused")

# Preference order, not authority order: every class but K5 is uncredentialed,
# and `offline` is the fixture adapter's class.
ACCESS_CLASSES = ("K0", "K1", "K2", "K3", "K4", "K5", "offline")

REPRESENTATION_KINDS = ("index", "native", "page", "feed", "transcript")

TIME_CONFIDENCES = ("authoritative", "reported", "derived", "unknown")

PROVENANCE_EDGE_KINDS = ("discovery_hydration",)

GROUP_KEY_KINDS = ("strong", "weak", "ungrouped")

MAX_ENGAGEMENT_VALUE = 2 ** 63 - 1

MANIFEST_KEYS = ("schema_version", "manifest_id", "mode", "as_of", "steps")
STEP_KEYS = (
    "step_id",
    "kind",
    "adapter_id",
    "query",
    "prior_step_id",
    "selected_hits",
    "max_items",
    "window_start",
    "window_end",
)
SELECTED_HIT_KEYS = ("discovery_locator", "target_id")


class ManifestError(ValueError):
    """A manifest is malformed, incomplete, or names something unknown."""


@dataclass(frozen=True)
class SelectedHit:
    """One caller-frozen discovery hit chosen for hydration.

    ``discovery_locator`` is the exact normalized locator the caller saw in
    the discovery step's output. It is the only thing that ties a hydration
    record back to its discovery record: nothing is inferred by similarity.
    """

    discovery_locator: str
    target_id: str


@dataclass(frozen=True)
class AcquisitionStep:
    step_id: str
    kind: str
    adapter_id: str
    query: str = ""
    prior_step_id: str = ""
    selected_hits: Tuple[SelectedHit, ...] = ()
    max_items: int = 0
    # How many pages this step wants, where it wants a particular number. Zero
    # is the ordinary case: the step named none, and `runner.MAX_PAGES_PER_STEP`
    # — the core's backstop against an origin that never stops offering — is
    # the only page bound it has. A number here is the caller's own bound, like
    # `max_items`: reaching it is the step finishing rather than a recall cut
    # short, and it only ever lowers the count, because the backstop still
    # stops a step that declared more than the core will spend.
    #
    # No `STEP_KEYS` entry names it, so no manifest can set one. The caller
    # that declares a bound is this package's own smoke, in process, where one
    # read is the whole of what a liveness check is authorized to cost.
    max_pages: int = 0
    # The window this step's records must fall in, as two instants in
    # `INSTANT_FORMAT`, either or both empty. A dated record outside it is
    # dropped by the core before the cap counts it, so the cap is spent on
    # the window rather than on an origin's all-time-top ordering; a record
    # with no publication time is kept, because dropping it would decide the
    # unknown. Adapters whose origin takes a date bound push it server-side
    # and say so in their own terms; the core's filter holds either way.
    window_start: str = ""
    window_end: str = ""


@dataclass(frozen=True)
class AcquisitionManifest:
    manifest_id: str
    mode: str
    as_of: str
    steps: Tuple[AcquisitionStep, ...]
    schema_version: int = MANIFEST_SCHEMA_VERSION


@dataclass(frozen=True)
class EngagementSnapshot:
    """One native metric as one route reported it at one moment."""

    metric_name: str
    value: int
    observed_at: str


@dataclass(frozen=True)
class AcquisitionRecord:
    """One immutable row of an AcquisitionArtifact.

    Grouping never rewrites one of these: two records that describe the same
    thing are linked by a group's membership or by a provenance edge, and
    each keeps its own body, time, route, and metric snapshots.
    """

    record_id: str
    artifact_id: str
    manifest_id: str
    step_id: str
    adapter_id: str
    adapter_version: str
    route_id: str
    access_class: str
    operator_identity: str
    platform: str
    native_identity_namespace: str
    group_scope: str
    representation_kind: str
    canonical_content_kind: str
    native_item_id: str
    native_parent_id: str
    canonical_locator: str
    normalized_locator: str
    exact_content_hash: str
    title: str
    body: str
    author: str
    community: str
    published_at: str
    observed_at: str
    time_confidence: str
    usable_basis_time: str
    engagement: Tuple[EngagementSnapshot, ...]
    page_index: int
    list_index: int
    native_position: int
    discovery_locator: str
    outcome: str
    loss: Tuple[str, ...]
    # Named string facts the route reported that no other field here means,
    # carried under the route's own names and repeating where the route
    # repeated them. Last and defaulted, because most routes report none and
    # every existing construction site names its fields by keyword.
    attributes: Tuple[Tuple[str, str], ...] = ()


@dataclass(frozen=True)
class ProvenanceEdge:
    """A link between two records. It is never an identity merge."""

    edge_kind: str
    from_record_id: str
    to_record_id: str


@dataclass(frozen=True)
class RecordGroup:
    """Records that describe one thing, held side by side and never folded."""

    key_kind: str
    key: Tuple[str, ...]
    member_record_ids: Tuple[str, ...]


@dataclass(frozen=True)
class StepResult:
    """What one manifest step consumed and produced.

    ``warnings`` is every page's own account of itself, in the order the step's
    calls returned them. A loss code says which kind of thing went wrong and a
    warning says what the adapter actually saw — which container it looked for,
    which status the origin named, which identifier it would need renewed. The
    two are not interchangeable: `schema_drift` alone leaves a reader to guess
    where to look, and dropping the sentence that says so at this seam would
    discard the only part of the page that names a recovery.
    """

    step_id: str
    adapter_id: str
    route_id: str
    pages: int
    records_received: int
    records_kept: int
    outcome: str
    loss: Tuple[str, ...] = ()
    warnings: Tuple[str, ...] = ()


@dataclass(frozen=True)
class AcquisitionArtifact:
    artifact_id: str
    manifest_id: str
    mode: str
    as_of: str
    records: Tuple[AcquisitionRecord, ...]
    steps: Tuple[StepResult, ...]
    edges: Tuple[ProvenanceEdge, ...] = ()
    groups: Tuple[RecordGroup, ...] = ()
    outcome: str = "ok"
    loss: Tuple[str, ...] = ()


def reduce_outcomes(outcomes: Sequence[str]) -> str:
    """Reduce step outcomes to one batch outcome, exactly and without rounding up."""

    if not outcomes:
        return "empty"
    distinct = set(outcomes)
    if distinct == {"refused"}:
        return "refused"
    if distinct <= {"ok", "empty"}:
        return "ok" if "ok" in distinct else "empty"
    usable = distinct & {"ok", "empty", "partial"}
    if not usable:
        return "failed"
    return "partial"


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ManifestError("{0} must be a mapping, got {1}".format(label, type(value).__name__))
    return value


def _reject_unknown_keys(payload: Mapping[str, Any], allowed: Sequence[str], label: str) -> None:
    unknown = sorted(key for key in payload if key not in allowed)
    if unknown:
        raise ManifestError("{0} names unknown field(s): {1}".format(label, ", ".join(unknown)))


def _require_text(payload: Mapping[str, Any], key: str, label: str) -> str:
    value = payload.get(key, "")
    if not isinstance(value, str) or not value:
        raise ManifestError("{0} requires a nonempty string {1}".format(label, key))
    return value


def _parse_selected_hit(payload: Any, label: str) -> SelectedHit:
    mapping = _require_mapping(payload, label)
    _reject_unknown_keys(mapping, SELECTED_HIT_KEYS, label)
    return SelectedHit(
        discovery_locator=_require_text(mapping, "discovery_locator", label),
        target_id=_require_text(mapping, "target_id", label),
    )


def _parse_step(payload: Any, position: int) -> AcquisitionStep:
    label = "step[{0}]".format(position)
    mapping = _require_mapping(payload, label)
    _reject_unknown_keys(mapping, STEP_KEYS, label)

    step_id = _require_text(mapping, "step_id", label)
    label = "step {0}".format(step_id)

    kind = _require_text(mapping, "kind", label)
    if kind not in STEP_KINDS:
        raise ManifestError("{0} names unknown kind {1}".format(label, kind))

    adapter_id = _require_text(mapping, "adapter_id", label)

    hits = tuple(
        _parse_selected_hit(hit, "{0} selected_hits[{1}]".format(label, index))
        for index, hit in enumerate(mapping.get("selected_hits", ()))
    )
    if kind == "hydration" and not hits:
        raise ManifestError("{0} is a hydration step and requires selected_hits".format(label))
    if kind == "discovery" and hits:
        raise ManifestError("{0} is a discovery step and forbids selected_hits".format(label))

    max_items = mapping.get("max_items", 0)
    if not isinstance(max_items, int) or isinstance(max_items, bool) or max_items < 1:
        raise ManifestError("{0} requires a hard positive max_items cap".format(label))

    window = []
    for key in ("window_start", "window_end"):
        value = mapping.get(key, "")
        if value == "" or value is None:
            window.append("")
            continue
        if not isinstance(value, str) or not _is_instant(value):
            raise ManifestError(
                "{0} {1} must be spelled YYYY-MM-DDTHH:MM:SSZ or left empty, got"
                " {2!r}: a bound the core cannot read bounds nothing".format(label, key, value)
            )
        window.append(value)
    if window[0] and window[1] and window[0] > window[1]:
        raise ManifestError(
            "{0} window_start {1} is after window_end {2}".format(label, window[0], window[1])
        )

    return AcquisitionStep(
        step_id=step_id,
        kind=kind,
        adapter_id=adapter_id,
        query=mapping.get("query", ""),
        prior_step_id=mapping.get("prior_step_id", ""),
        selected_hits=hits,
        max_items=max_items,
        window_start=window[0],
        window_end=window[1],
    )


def _is_instant(value: str) -> bool:
    try:
        datetime.strptime(value, INSTANT_FORMAT)
    except ValueError:
        return False
    return True


def parse_manifest(payload: Any) -> AcquisitionManifest:
    """Validate ``payload`` into an immutable manifest, or raise ManifestError."""

    mapping = _require_mapping(payload, "manifest")
    _reject_unknown_keys(mapping, MANIFEST_KEYS, "manifest")

    schema_version = mapping.get("schema_version")
    if schema_version != MANIFEST_SCHEMA_VERSION:
        raise ManifestError(
            "manifest schema_version must be {0}, got {1!r}".format(
                MANIFEST_SCHEMA_VERSION, schema_version
            )
        )

    manifest_id = _require_text(mapping, "manifest_id", "manifest")

    mode = _require_text(mapping, "mode", "manifest")
    if mode not in ACQUISITION_MODES:
        raise ManifestError("manifest names unknown mode {0}".format(mode))

    as_of = _require_text(mapping, "as_of", "manifest")
    try:
        datetime.strptime(as_of, INSTANT_FORMAT)
    except ValueError:
        raise ManifestError(
            "manifest as_of must be spelled YYYY-MM-DDTHH:MM:SSZ, got {0!r}: an"
            " as_of the ordering cannot parse bounds nothing, and the frozen"
            " replay stops being frozen without saying so".format(as_of)
        )

    raw_steps = mapping.get("steps", ())
    if not isinstance(raw_steps, Sequence) or isinstance(raw_steps, str) or not raw_steps:
        raise ManifestError("manifest requires a nonempty steps sequence")
    steps = tuple(_parse_step(step, index) for index, step in enumerate(raw_steps))

    seen = set()
    for step in steps:
        if step.step_id in seen:
            raise ManifestError("manifest repeats step_id {0}".format(step.step_id))
        seen.add(step.step_id)
    for step in steps:
        if step.prior_step_id and step.prior_step_id not in seen:
            raise ManifestError(
                "step {0} names unknown prior_step_id {1}".format(step.step_id, step.prior_step_id)
            )

    return AcquisitionManifest(
        manifest_id=manifest_id,
        mode=mode,
        as_of=as_of,
        steps=steps,
        schema_version=schema_version,
    )
