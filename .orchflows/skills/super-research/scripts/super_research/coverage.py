"""Coverage seam: what a run is about to acquire, and what it did not.

Reliability bar: zero I/O. This module opens no file, resolves no path, and
reaches no socket. It reads a manifest, or an artifact, or a list of records
the caller already holds, and returns steps or advisories. It runs nothing.

Two jobs, one owner, because they are the same question asked twice:

- :func:`plan_hydration` turns discovery records into the hydration step that
  would deepen them, so a caller does not hand-write per-adapter target
  grammar. Depth is where the evidence is — comments, transcripts, exact
  counts all live behind hydration, and a run that stops at discovery ships
  titles.
- :func:`review_manifest` and :func:`review_artifact` say what a manifest is
  about to miss and what an artifact already missed.

Why this exists at all. The failure this package actually sees is not a
malformed manifest — :func:`schema.parse_manifest` is total and rejects
unknown keys before any transport call, so malformed manifests never run. It
is a **valid manifest that under-acquires**: every field well-formed, every
step legal, and the run comes back thin. Two of those were measured on
2026-08-17 in one session, by a caller that had read the contract:

1. `window_start`/`window_end` omitted on two `web_search` steps while every
   other step in the same manifest carried them. Valid; the news lane reached
   back four months and spent its cap there.
2. `search:` called on `youtube_innertube` and the run reported "no
   transcripts, no view counts". Valid; the adapter serves four operations and
   the other three are where both of those live.

Neither is a validation problem, so no amount of stricter parsing reaches
them. Both are visible in the manifest before it runs, which is what this
module reads.

**Nothing here plans, selects, ranks, or judges.** :func:`plan_hydration`
builds steps and never runs one; the caller passes the records it chose, and
the selection is frozen in the manifest exactly as before — this is the
ceremony removed, not the authorization model changed. The reviews warn and
return: an advisory is a sentence, never an edit. A module that added the
missing step would be the internal planner this package deliberately does not
have, and the frozen inputs it would give up are the whole reason a fused
manifest can run its lanes at once.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Sequence, Tuple

from . import runner, schema


class CoverageError(ValueError):
    """A plan named an adapter, an operation, or a bound it may not have."""


# ---------------------------------------------------------------------------
# Where depth lives
# ---------------------------------------------------------------------------

# The hydration operations that deepen a discovery record, per adapter, and
# what each one is worth. Declared rather than discovered: an adapter's
# operation tuple says which names it answers to, and says nothing about which
# of them a caller who wants evidence should spend. This table is that second
# fact, and it is the single source for both jobs in this module — the plan
# builds targets off it and the review warns off the same rows, so a route
# added to one is never missing from the other.
#
# `id_from` names which field of a discovery record addresses the target:
#
#   "locator"  the normalized locator the discovery row carried. Reddit's
#              comments grammar takes a permalink directly, so nothing is
#              taken apart and no subreddit is re-derived here.
#   "native"   the platform-native item id.
#
# Neither is inferred. A record missing the named field is reported as skipped
# rather than addressed by the other one, because guessing which id a route
# meant is how a hydration lands on the wrong item and still looks authorized.
HYDRATION_TARGETS: Dict[str, Dict[str, str]] = {
    "reddit_shreddit": {"comments": "locator"},
    "youtube_innertube": {
        "player": "native",
        "transcript": "native",
        "next": "native",
    },
    "hacker_news": {"tree": "native", "item": "native"},
    "x_fxtwitter": {"conversation": "native", "user": "native"},
    "reddit_archive": {"": "native"},
}

# What a caller loses by never hydrating, in the adapter's own terms. Read
# only by `review_manifest`/`review_artifact`, and written as the thing a
# report would be missing rather than as the name of a step.
DEPTH_FORGONE: Dict[str, str] = {
    "reddit_shreddit": "comment text and per-comment scores",
    "youtube_innertube": (
        "exact view counts and transcripts; a search row carries"
        " `viewCountText` as the origin's own rounded string, never an"
        " exact count"
    ),
    "hacker_news": "the story's comment tree",
    "x_fxtwitter": "the conversation under a post",
    "reddit_archive": "the submission's score and comment count",
}


# ---------------------------------------------------------------------------
# Plan
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SkippedRecord:
    """One record the plan could not address, and the reason it could not."""

    record_id: str
    reason: str


@dataclass(frozen=True)
class HydrationPlan:
    """The step a caller would run, and every record it left behind.

    Both halves, for the reason :func:`relevance.partition` returns both: a
    selection whose leftovers were never listed is a silent drop wearing a
    plan's clothes. `skipped` is the audit — a record off another adapter, a
    record with no addressable id, and a record past the caller's own limit
    each land here with which of the three it was.
    """

    step: schema.AcquisitionStep
    skipped: Tuple[SkippedRecord, ...]


def plan_hydration(
    records: Iterable[schema.AcquisitionRecord],
    adapter_id: str,
    operation: str,
    step_id: str,
    max_items: int,
    limit: int = 0,
) -> HydrationPlan:
    """One hydration step over the records this adapter can address.

    ``operation`` is a key of this adapter's :data:`HYDRATION_TARGETS` row, and
    an operation the row does not name is refused rather than passed through to
    an adapter that would read it as a query. ``limit`` caps how many hits the
    step carries — zero means every addressable record — and the records past
    it are reported in ``skipped`` rather than dropped, so a caller can see
    that its own bound, not the data, ended the selection.

    ``max_items`` bounds each authorized call, which is what a hydration step's
    cap means: every selected hit was named by the caller and every one is
    called, so a first hit that answers richly cannot starve the rest.
    """

    row = HYDRATION_TARGETS.get(adapter_id)
    if row is None:
        raise CoverageError(
            "no hydration target declared for adapter {0!r}; declared: {1}".format(
                adapter_id, ", ".join(sorted(HYDRATION_TARGETS))
            )
        )
    if operation not in row:
        raise CoverageError(
            "adapter {0!r} declares no hydration operation {1!r}; declared: {2}".format(
                adapter_id, operation, ", ".join(sorted(name for name in row if name))
            )
        )
    if max_items <= 0:
        raise CoverageError("max_items must be a positive integer, got {0!r}".format(max_items))
    if limit < 0:
        raise CoverageError("limit must not be negative, got {0!r}".format(limit))

    id_from = row[operation]
    hits = []
    skipped = []
    for record in records:
        if record.adapter_id != adapter_id:
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
        addressed = record.normalized_locator if id_from == "locator" else record.native_item_id
        if not addressed:
            skipped.append(
                SkippedRecord(
                    record.record_id,
                    "carries no {0} to address".format(
                        "locator" if id_from == "locator" else "native item id"
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
        target = addressed if operation == "" else operation + ":" + addressed
        hits.append(schema.SelectedHit(record.normalized_locator, target))

    return HydrationPlan(
        step=schema.AcquisitionStep(
            step_id=step_id,
            kind="hydration",
            adapter_id=adapter_id,
            query=operation,
            selected_hits=tuple(hits),
            max_items=max_items,
        ),
        skipped=tuple(skipped),
    )


# ---------------------------------------------------------------------------
# Review
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Advisory:
    """One thing a run is about to miss, or already missed.

    ``code`` is stable and greppable; ``subject`` is the step id or adapter id
    it is about; ``message`` is the sentence a report would need. An advisory
    is never a loss code: a loss says an origin refused or a payload moved,
    and an advisory says the caller asked for less than it could have.
    """

    code: str
    subject: str
    message: str


# The adapters that spend a step's window at the origin, in the origin's own
# terms — Google News `when:`, HN Algolia `numericFilters`, Bluesky
# `since`/`until`. Read back off the source: these are exactly the adapter
# modules whose executable code names `window_start`/`window_end`.
#
# The window check below fires only for these, and the narrowing is what makes
# it worth reading. Every unwindowed step spends its cap on whatever the origin
# ranks first; on these three that is also a bound the origin would have
# applied itself, so omitting it is strictly wasteful and never a choice. On
# the rest it is frequently deliberate — `prediction_markets` wants open
# markets closing next year, and warning about those trained a reader to skip
# the line that mattered. Measured 2026-08-17: unnarrowed, this fired on five
# steps of which three were correct as written.
SERVER_SIDE_WINDOW = ("bluesky", "hacker_news", "web_search")

DEPTH_NOT_PLANNED = "depth_not_planned"
WINDOW_ABSENT = "window_absent"
CAP_BELOW_PAGE_SIZE = "cap_below_page_size"
STEP_CARRIED_LOSS = "step_carried_loss"
RECALL_WAS_A_WINDOW = "recall_was_a_window"
NOTHING_HYDRATED = "nothing_hydrated"


def _page_size(adapter_id: str) -> int:
    """The largest page any of this adapter's surfaces declares, or zero."""

    try:
        surfaces = runner.surface_descriptors(adapter_id)
    except Exception:  # pragma: no cover - an adapter the core does not declare
        return 0
    sizes = [surface.page_size for surface in surfaces if surface.page_size]
    return max(sizes) if sizes else 0


def review_manifest(manifest: schema.AcquisitionManifest) -> Tuple[Advisory, ...]:
    """What this manifest is about to miss, read before it runs.

    Three checks, each one a measured failure rather than a style opinion.
    Ordered by step so a caller reads them against the file it just wrote.
    """

    found = []
    discovery_by_adapter = {}
    hydration_adapters = set()
    for step in manifest.steps:
        if step.kind == "discovery":
            discovery_by_adapter.setdefault(step.adapter_id, []).append(step)
        else:
            hydration_adapters.add(step.adapter_id)

    windowed = [step for step in manifest.steps if step.window_start or step.window_end]
    unwindowed = [step for step in manifest.steps if not (step.window_start or step.window_end)]

    for adapter_id in sorted(discovery_by_adapter):
        if adapter_id in HYDRATION_TARGETS and adapter_id not in hydration_adapters:
            found.append(
                Advisory(
                    DEPTH_NOT_PLANNED,
                    adapter_id,
                    "{0} discovers here and nothing hydrates it, so this run will not"
                    " carry {1}. `coverage.plan_hydration` builds the step from the"
                    " records this manifest is about to return.".format(
                        adapter_id, DEPTH_FORGONE.get(adapter_id, "what hydration adds")
                    ),
                )
            )

    if windowed:
        for step in unwindowed:
            # A hydration step addresses hits the caller named, one call each.
            # There is no ordering for a window to bound and no cap to spend
            # in the wrong place, so an unwindowed hydration is not an
            # omission — it is the ordinary shape.
            if step.kind != "discovery":
                continue
            if step.adapter_id not in SERVER_SIDE_WINDOW:
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
    """What this artifact already missed, read before any record.

    The first check is the one that matters: a step carrying a loss code is a
    fact about the read that a report has to state. An empty answer carrying a
    loss is not an absence, and reporting it as one is the single way a run
    with typed failures still ends up lying.
    """

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

    # Read off the records rather than the step list, for the reason
    # `normalize` reads `discovery_not_recorded` off records: a record with no
    # `discovery_locator` is a discovery record, because the schema requires a
    # nonempty one on every selected hit. A step list cannot tell a
    # hydration-only dispatch from a run that discovered and never deepened.
    hydration_adapters = set()
    discovery_adapters = set()
    for record in artifact.records:
        if record.discovery_locator:
            hydration_adapters.add(record.adapter_id)
        else:
            discovery_adapters.add(record.adapter_id)

    for adapter_id in sorted(discovery_adapters):
        if adapter_id in HYDRATION_TARGETS and adapter_id not in hydration_adapters:
            found.append(
                Advisory(
                    NOTHING_HYDRATED,
                    adapter_id,
                    "this artifact holds {0} discovery records and no hydration, so"
                    " it does not carry {1}. Every hit here was discovered and"
                    " nothing deepened it.".format(
                        adapter_id, DEPTH_FORGONE.get(adapter_id, "what hydration adds")
                    ),
                )
            )

    return tuple(found)


def advisory_lines(advisories: Sequence[Advisory]) -> Tuple[str, ...]:
    """The advisories as lines, for a caller putting them in front of a reader."""

    return tuple(
        "{0} [{1}] {2}".format(found.code, found.subject, found.message)
        for found in advisories
    )
