"""Private implementation of the public coverage depth-planning seam."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Tuple

from .. import schema


class CoverageError(ValueError):
    """A plan named an adapter, an operation, or a bound it may not have."""


@dataclass(frozen=True)
class DepthTarget:
    """One depth operation: how it is addressed, and what shape it is lawful as.

    ``id_from`` names which field of a discovery record addresses the target:

      "locator"  the normalized locator the discovery row carried. Reddit's
                 comments grammar takes a permalink directly, so nothing is
                 taken apart and no subreddit is re-derived here.
      "native"   the platform-native item id.

    Neither is inferred. A record missing the named field is reported as
    skipped rather than addressed by the other one, because guessing which id a
    route meant is how a read lands on the wrong item and still looks
    authorized.

    ``kind`` is the step kind this operation answers under, and it is not a
    style choice: :func:`runner._offers_another_page` spends a continuation
    only for a discovery step, so an operation whose evidence rides one is
    reachable no other way. ``min_items`` is the floor that cap needs for the
    same reason — one page is not two.
    """

    id_from: str
    kind: str
    min_items: int = 1


# The operations that deepen a discovery record, per adapter, and what each one
# is worth. Declared rather than discovered: an adapter's operation tuple says
# which names it answers to, and says nothing about which of them a caller who
# wants evidence should spend, nor which shape spends it. This table is that
# second fact, and it is the single source for depth planning and review, so a
# route added to one is never missing from the other.
#
# The `kind` column is read off `runner._offers_another_page`, whose whole
# answer is `step.kind == "discovery" and bool(page.cursor_out) and kept <
# step.max_items`. Measured 2026-08-17, live: `next` publishes a continuation
# and puts the comment threads on page two, and `transcript` publishes one and
# puts the cues there. Planned as hydration they returned zero comments and
# zero cues while holding a token nothing would ever spend, which is the whole
# defect this column exists to close. Every other row answers in one call and
# stays hydration, where each hit's provenance is exact rather than inferred.
DEPTH_TARGETS: Dict[str, Dict[str, DepthTarget]] = {
    "reddit_shreddit": {"comments": DepthTarget("locator", "hydration")},
    "youtube_innertube": {
        "player": DepthTarget("native", "hydration"),
        # Page one is the player's caption track list; the cues are on page
        # two, which `kept < max_items` is the only clause that buys.
        "transcript": DepthTarget("native", "discovery", min_items=2),
        "next": DepthTarget("native", "discovery"),
    },
    "hacker_news": {
        "tree": DepthTarget("native", "hydration"),
        "item": DepthTarget("native", "hydration"),
    },
    "x_fxtwitter": {
        "conversation": DepthTarget("native", "hydration"),
        "user": DepthTarget("native", "hydration"),
    },
    "reddit_archive": {"": DepthTarget("native", "hydration")},
}


@dataclass(frozen=True)
class SkippedRecord:
    """One record the plan could not address, and the reason it could not."""

    record_id: str
    reason: str


@dataclass(frozen=True)
class DepthPlan:
    """The steps a caller would run, and every record they left behind.

    Both halves, for the reason :func:`relevance.partition` returns both: a
    selection whose leftovers were never listed is a silent drop wearing a
    plan's clothes. `skipped` is the audit — a record off another adapter, a
    record with no addressable id, and a record past the caller's own limit
    each land here with which of the three it was.

    ``steps`` is plural because the two shapes count differently. A hydration
    operation is one step carrying every addressable hit, and it is returned
    even when the selection came back empty, because an empty selection is a
    fact about the records and not about the plan. A paging operation is one
    discovery step per record — a discovery step forbids `selected_hits`, so
    the target rides in the query and one step can address exactly one — and
    nothing addressable means no step at all.
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
    """The steps that deepen these records, in the shape their operation pages in.

    ``operation`` is a key of this adapter's :data:`DEPTH_TARGETS` row, and an
    operation the row does not name is refused rather than passed through to an
    adapter that would read it as a query. ``limit`` caps how many records are
    addressed — zero means every addressable one — and the records past it are
    reported in ``skipped`` rather than dropped, so a caller can see that its
    own bound, not the data, ended the selection.

    What ``max_items`` bounds follows the kind the row declares, and so does
    what it costs. On a hydration step it bounds each authorized call: every
    selected hit was named by the caller and every one is called exactly once,
    so a first hit that answers richly cannot starve the rest and no
    continuation is ever spent. On a discovery step it bounds the whole step and
    is also the budget the core's paging spends, so this one record's step can
    cost up to :data:`runner.MAX_PAGES_PER_STEP` origin calls — five — against
    the single call the same record cost as a hydration. That is what a paging
    row buys with a cap, and it is why a row declaring a ``min_items`` floor
    refuses a cap under it rather than planning a step that stops one page short
    of its own evidence and reports success.
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
    if max_items <= 0:
        raise CoverageError("max_items must be a positive integer, got {0!r}".format(max_items))
    if limit < 0:
        raise CoverageError("limit must not be negative, got {0!r}".format(limit))

    target = row[operation]
    if max_items < target.min_items:
        raise CoverageError(
            "{0} {1!r} needs max_items of at least {2}, got {3}: page one of this"
            " operation is the record it starts from, and `kept < max_items` is the"
            " clause that buys page two, which is where its evidence is.".format(
                adapter_id, operation, target.min_items, max_items
            )
        )

    id_from = target.id_from
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
        named = addressed if operation == "" else operation + ":" + addressed
        hits.append(schema.SelectedHit(record.normalized_locator, named))

    if target.kind == "hydration":
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

    # One step per record, and the target in the query. A discovery step
    # forbids `selected_hits`, so the operation's own `<name>:<argument>`
    # grammar — the one an adapter reads off a step that names no target — is
    # the only place left to say which item this step is about, and it says one.
    return DepthPlan(
        steps=tuple(
            schema.AcquisitionStep(
                step_id="{0}-{1}".format(step_id, index + 1),
                kind="discovery",
                adapter_id=adapter_id,
                query=hit.target_id,
                max_items=max_items,
            )
            for index, hit in enumerate(hits)
        ),
        skipped=tuple(skipped),
    )
