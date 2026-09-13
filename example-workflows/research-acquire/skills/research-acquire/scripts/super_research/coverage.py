"""Bounded depth targets and advisories about limits and recorded losses.

Reliability bar: zero I/O. This module opens no file, resolves no path, and
reaches no socket. It reads a manifest, or an artifact, or a list of records
the caller already holds, and returns steps or advisories. It runs nothing.

``plan_depth`` builds bounded steps from caller-selected records. It makes no
selection, never runs a step, and never constructs a document URL. Reviews
report configured bounds and recorded losses; step shape cannot establish
what evidence the returned content supports.
Every depth target makes one hydration call; discovery can spend bounded
continuations independently.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Sequence, Tuple, Iterable

from . import runner, schema, transport
from urllib.parse import urlsplit


class CoverageError(ValueError):
    """A plan named an adapter, an operation, or a bound it may not have."""


# Each retained depth operation makes one call addressed by this carried field.
# Open documents use the exact canonical URL; normalized URLs link provenance.
DEPTH_TARGETS: Dict[str, Dict[str, str]] = {
    "open_page": {"": "canonical_locator"},
    "reddit_shreddit": {"comments": "normalized_locator"},
    "hacker_news": {
        "tree": "native_item_id",
        "item": "native_item_id",
    },
    "x_fxtwitter": {
        "conversation": "native_item_id",
    },
    "reddit_archive": {"": "native_item_id"},
}


def can_address(record: schema.AcquisitionRecord, adapter_id: str, operation: str) -> bool:
    """Whether this operation can address the record; relevance and route authorization are the caller's.

    Archive posts and publisher feed entries can carry Reddit permalinks for
    an independently authorized comments read. Both observations retain their
    source identity and join through the exact selected locator.
    """
    if adapter_id == "open_page" and operation == "":
        # A scholarly metadata row is native to its registry, but its carried
        # original document address can still be read. Use that exact address;
        # normalization is for provenance comparison, never URL construction.
        return (record.adapter_id in ("open_page", "scholarly")
                or record.representation_kind in ("index", "feed")) and not transport.open_read_refusal(
                    record.canonical_locator)
    if record.adapter_id == adapter_id:
        return True
    try:
        address = urlsplit(record.normalized_locator)
        port = address.port
    except ValueError:
        return False
    if adapter_id == "reddit_shreddit" and operation == "comments":
        parts = address.path.strip("/").split("/")
        return ((record.adapter_id == "reddit_archive" or record.representation_kind == "feed")
                and address.scheme == "https"
                and address.hostname in ("reddit.com", "www.reddit.com", "old.reddit.com")
                and not (address.username or address.password or port or address.query or address.fragment)
                and len(parts) in (4, 5) and parts[0] == "r" and parts[2] == "comments"
                and parts[1].replace("_", "").isalnum() and parts[3].isalnum())
    return False


@dataclass(frozen=True)
class SkippedRecord:
    """One record the plan could not address, and the reason it could not."""

    record_id: str
    reason: str


@dataclass(frozen=True)
class DepthPlan:
    """One hydration step with all selected hits, plus every skipped record.

    An empty selection still returns its step. Skips distinguish missing IDs,
    unsupported records, prior hydration and the caller's selection limit.
    """

    steps: Tuple[schema.AcquisitionStep, ...]
    skipped: Tuple[SkippedRecord, ...]


def plan_depth(
    records: Iterable[schema.AcquisitionRecord],
    adapter_id: str,
    operation: str,
    step_id: str,
    max_items: int,
    limit: int = 0,
) -> DepthPlan:
    """Build one hydration step for these records without selecting or reading.

    ``operation`` is a key of this adapter's :data:`DEPTH_TARGETS` row, and an
    operation the row does not name is refused rather than passed through to an
    adapter that would read it as a query. ``limit`` caps how many records are
    addressed — zero means every addressable one — and the records past it are
    reported in ``skipped`` rather than dropped, so a caller can see that its
    own bound, not the data, ended the selection.

    ``max_items`` bounds each authorized call. Every selected hit is called
    once, so a rich first answer cannot starve the rest and no continuation
    is spent.
    """

    row = DEPTH_TARGETS.get(adapter_id)
    if row is None:
        raise CoverageError(
            "no depth target declared for adapter {0!r}; declared: {1}".format(
                adapter_id, ", ".join(sorted(DEPTH_TARGETS))
            )
        )
    if operation not in row:
        raise CoverageError(
            "adapter {0!r} declares no depth operation {1!r}; declared: {2}".format(
                adapter_id, operation, ", ".join(sorted(name for name in row if name))
            )
        )
    if type(max_items) is not int or max_items <= 0:
        raise CoverageError("max_items must be a positive integer, got {0!r}".format(max_items))
    if type(limit) is not int or limit < 0:
        raise CoverageError("limit must be a nonnegative integer, got {0!r}".format(limit))

    id_from = row[operation]
    hits = []
    skipped = []
    for record in records:
        if not can_address(record, adapter_id, operation):
            skipped.append(
                SkippedRecord(record.record_id, "off adapter {0}".format(record.adapter_id))
            )
            continue
        if record.representation_kind != "index" and record.discovery_locator:
            # A hydration record already is a hydration. Feeding one back would
            # ask the route to deepen its own answer, and the edge it formed
            # names a discovery this artifact holds — re-hydrating it would put
            # a second record under the same locator with no way to tell which
            # read produced which.
            skipped.append(SkippedRecord(record.record_id, "already hydrated"))
            continue
        addressed = getattr(record, id_from)
        if not addressed:
            skipped.append(
                SkippedRecord(
                    record.record_id,
                    "carries no {0} to address".format(
                        "native item id" if id_from == "native_item_id" else "locator"
                    ),
                )
            )
            continue
        if not record.normalized_locator:
            # The locator is the only thing that ties a hydration record back
            # to its discovery record, and nothing is matched by similarity. A
            # record with none can be read but never linked, so the edge would
            # be missing and the run would type `discovery_not_recorded`
            # against itself.
            skipped.append(SkippedRecord(record.record_id, "carries no normalized locator"))
            continue
        if limit and len(hits) >= limit:
            skipped.append(SkippedRecord(record.record_id, "past the caller's limit"))
            continue
        named = addressed if operation == "" else operation + ":" + addressed
        hits.append(schema.SelectedHit(record.normalized_locator, named))

    return DepthPlan(
        steps=(
            schema.AcquisitionStep(
                step_id=step_id,
                kind="hydration",
                adapter_id=adapter_id,
                query=operation,
                selected_hits=tuple(hits),
                max_items=max_items,
            ),
        ),
        skipped=tuple(skipped),
    )


# ---------------------------------------------------------------------------
# Review
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Advisory:
    """One diagnostic about configured bounds or recorded acquisition losses.

    ``code`` is stable and greppable; ``subject`` is the step id or adapter id
    it is about; ``message`` explains the concrete limitation. Content support
    is judged from inspected evidence, never inferred from missing steps.
    """

    code: str
    subject: str
    message: str


# The window check uses runner.WINDOW_REACH for the exact operation. It warns
# only when that operation could have narrowed discovery at the origin.

WINDOW_ABSENT = "window_absent"
CAP_BELOW_PAGE_SIZE = "cap_below_page_size"
STEP_CARRIED_LOSS = "step_carried_loss"
RECALL_WAS_A_WINDOW = "recall_was_a_window"


def _page_size(adapter_id: str) -> int:
    """The largest page any of this adapter's surfaces declares, or zero."""

    surfaces = runner.surface_descriptors(adapter_id)
    sizes = [surface.page_size for surface in surfaces if surface.page_size]
    return max(sizes) if sizes else 0


def review_manifest(manifest: schema.AcquisitionManifest) -> Tuple[Advisory, ...]:
    """Configured window and cap limitations, read before the manifest runs."""

    found = []
    windowed = [step for step in manifest.steps if step.window_start or step.window_end]
    unwindowed = [step for step in manifest.steps if not (step.window_start or step.window_end)]

    if windowed:
        for step in unwindowed:
            # A hydration step addresses hits the caller named, one call each.
            # There is no ordering for a window to bound and no cap to spend
            # in the wrong place, so an unwindowed hydration is not an
            # omission — it is the ordinary shape.
            if step.kind != "discovery":
                continue
            if not runner.reach_for(step.adapter_id, query=step.query):
                continue
            found.append(
                Advisory(
                    WINDOW_ABSENT,
                    step.step_id,
                    "this step carries no window while {0} of {1} steps do, and {2}"
                    " would have spent the bound at the origin in the origin's own"
                    " terms. Without it the cap is spent on whatever the origin ranks"
                    " first, outside the window the rest of this run is bounded"
                    " to.".format(len(windowed), len(manifest.steps), step.adapter_id),
                )
            )

    for step in manifest.steps:
        if step.kind != "discovery":
            continue
        page = _page_size(step.adapter_id)
        if page and step.max_items < page:
            found.append(
                Advisory(
                    CAP_BELOW_PAGE_SIZE,
                    step.step_id,
                    "max_items {0} is under this surface's page size {1}: one read"
                    " returns the page whatever the cap, and the rows past it are"
                    " dropped at no saving.".format(step.max_items, page),
                )
            )

    return tuple(found)


def review_artifact(artifact: schema.AcquisitionArtifact) -> Tuple[Advisory, ...]:
    """Surface recorded losses without inferring content from step structure."""

    found = []
    for step in artifact.steps:
        # A truncated recall gets its own sentence and not the general one as
        # well. Two advisories for one loss is how a reader learns to skim
        # them, and this loss is the common one — every capped step that met
        # its cap carries it.
        other = tuple(code for code in step.loss if code != "recall_window_partial")
        if other:
            found.append(
                Advisory(
                    STEP_CARRIED_LOSS,
                    step.step_id,
                    "returned {0} with loss {1}: state this in the report — an empty"
                    " answer carrying a loss is a refusal, not an absence.".format(
                        step.outcome, ", ".join(other)
                    ),
                )
            )
        if "recall_window_partial" in step.loss:
            found.append(
                Advisory(
                    RECALL_WAS_A_WINDOW,
                    step.step_id,
                    "stopped while the origin was still offering, so this set is a"
                    " window and not the whole: say so rather than counting it.",
                )
            )

    return tuple(found)


def advisory_lines(advisories: Sequence[Advisory]) -> Tuple[str, ...]:
    """The advisories as lines, for a caller putting them in front of a reader."""

    return tuple(
        "{0} [{1}] {2}".format(found.code, found.subject, found.message)
        for found in advisories
    )
