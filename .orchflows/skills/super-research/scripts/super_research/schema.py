"""Schema seam: closed enums, immutable values, and manifest validation.

Every value this module returns is frozen. Validation is total and runs
before any transport call, so an invalid manifest can never reach the
network.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence, Tuple

MANIFEST_SCHEMA_VERSION = 2

# A `staged` manifest round-trips through the caller between discovery and
# hydration; a `fused` manifest collapses that latency without collapsing
# lineage. Both emit discovery and hydration as distinct linked records.
ACQUISITION_MODES = ("staged", "fused")

STEP_KINDS = ("discovery", "hydration")

MANIFEST_KEYS = ("schema_version", "manifest_id", "mode", "as_of", "steps")
STEP_KEYS = (
    "step_id",
    "kind",
    "adapter_id",
    "query",
    "prior_step_id",
    "selected_hits",
    "max_items",
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


@dataclass(frozen=True)
class AcquisitionManifest:
    manifest_id: str
    mode: str
    as_of: str
    steps: Tuple[AcquisitionStep, ...]
    schema_version: int = MANIFEST_SCHEMA_VERSION


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
    if not isinstance(max_items, int) or isinstance(max_items, bool) or max_items < 0:
        raise ManifestError("{0} requires a nonnegative integer max_items".format(label))

    return AcquisitionStep(
        step_id=step_id,
        kind=kind,
        adapter_id=adapter_id,
        query=mapping.get("query", ""),
        prior_step_id=mapping.get("prior_step_id", ""),
        selected_hits=hits,
        max_items=max_items,
    )


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
