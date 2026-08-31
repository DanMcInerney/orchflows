"""Coverage seam: what a run is about to acquire, and what it did not.

Reliability bar: zero I/O. This module opens no file, resolves no path, and
reaches no socket. It reads a manifest, or an artifact, or a list of records
the caller already holds, and returns steps or advisories. It runs nothing.

Two jobs, one owner, because they are the same question asked twice:

- :func:`plan_depth` turns discovery records into the steps that would deepen
  them, so a caller does not hand-write per-adapter target grammar, and does
  not have to know which operations answer in one call and which reach their
  evidence only on page two. Depth is where the evidence is — comments,
  transcripts, exact counts all live behind a second read, and a run that
  stops at discovery ships titles.
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

**Nothing here plans, selects, ranks, or judges.** :func:`plan_depth`
builds steps and never runs one; the caller passes the records it chose, and
the selection is frozen in the manifest exactly as before — this is the
ceremony removed. The reviews warn and return: an advisory is a sentence, never
an edit. A module that added the missing step would be the internal planner this
package deliberately does not have, and the frozen inputs it would give up are
the whole reason a fused manifest can run its lanes at once.

What a cap *buys* did change, for the rows :data:`DEPTH_TARGETS` declares as
paging and only those. A hydration step spends exactly one origin call per hit
the caller named, and never a continuation. A discovery step is paged by the core
while ``kept < max_items``, up to :data:`runner.MAX_PAGES_PER_STEP` — five — so
one selected record can cost five calls on `next` or `transcript` where
hydrating it cost one. Naming a cap therefore authorizes pages and not only
records: a sentence this shape owes a caller, rather than one a rename can
absorb.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Sequence, Tuple, Union

from . import runner, schema
# Keep the established ``coverage.*`` depth seam while its implementation
# lives with the other private support code.
from ._support import coverage_depth as _coverage_depth
from ._support.coverage_depth import (
    DEPTH_TARGETS,
    CoverageError,
    DepthPlan,
    DepthTarget,
    SkippedRecord,
    plan_depth as _plan_depth,
)


def plan_depth(*args, **kwargs):
    _coverage_depth.DEPTH_TARGETS = DEPTH_TARGETS
    return _plan_depth(*args, **kwargs)

# What a step is, to the two functions that ask whether one is depth. A manifest
# holds `AcquisitionStep`s and an artifact holds `StepResult`s, and both carry
# the kind and the query, so one reader answers for both.
Step = Union[schema.AcquisitionStep, schema.StepResult]


# ---------------------------------------------------------------------------
# What review says depth would have added
# ---------------------------------------------------------------------------

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


# Whether a step's own operation would have spent the window at the origin,
# in the origin's own terms — Google News `when:`, HN Algolia
# `numericFilters`, Bluesky `since`/`until`. Read from
# :data:`window_reach.WINDOW_REACH`, keyed by adapter and then by operation,
# because capability is a property of an operation and not of an adapter:
# `bluesky` sends `since`/`until` on search and none on its author feed, so a
# tuple of adapter ids could not say what is true here and this module no
# longer keeps one.
#
# The window check below fires only where the operation can, and the
# narrowing is what makes it worth reading. Every unwindowed step spends its
# cap on whatever the origin ranks first; where the operation can also bound
# it server-side, omitting the window is strictly wasteful and never a
# choice. Elsewhere it is frequently deliberate — `prediction_markets` wants
# open markets closing next year, and warning about those trained a reader to
# skip the line that mattered. Measured 2026-08-17, at the coarser
# per-adapter granularity this table has since replaced: unnarrowed, this
# fired on five steps of which three were correct as written.

DEPTH_NOT_PLANNED = "depth_not_planned"
WINDOW_ABSENT = "window_absent"
CAP_BELOW_PAGE_SIZE = "cap_below_page_size"
CAP_BELOW_DEPTH_FLOOR = "cap_below_depth_floor"
STEP_CARRIED_LOSS = "step_carried_loss"
RECALL_WAS_A_WINDOW = "recall_was_a_window"
NOTHING_HYDRATED = "nothing_hydrated"


def _depth_operation(step: Step) -> str:
    """The depth operation this step names, or "" if it names none.

    Read off the query's own `<name>:<argument>` prefix, which is where an
    adapter serving several operations reads it from on a step naming no
    target. A query whose prefix is not a declared depth operation — `search:`,
    or a plain phrase — names none, so an ordinary discovery step is unchanged.
    """

    operation = step.query.partition(":")[0]
    row = DEPTH_TARGETS.get(step.adapter_id, {})
    return operation if operation and operation in row else ""


def _is_depth(step: Step) -> bool:
    """Whether this step is depth, read off the two facts the step states.

    Depth is what a step is *for*, not which kind it wears. A hydration step is
    always depth. A discovery step is depth when its query names one of this
    adapter's paging depth operations, which is the only shape those can
    lawfully take — :func:`runner._offers_another_page` spends a continuation
    for a discovery step and no other, so an operation whose evidence rides one
    is reachable no other way.

    An `AcquisitionStep` and a `StepResult` both answer this, because both
    carry the kind and the query. That is the whole point of the pair: the
    manifest review and the artifact review decide the same question, and one
    rule read from both sides is one rule to keep true.
    """

    if step.kind == "hydration":
        return True
    operation = _depth_operation(step)
    return bool(operation) and DEPTH_TARGETS[step.adapter_id][operation].kind == "discovery"


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

    Four checks, each one a measured failure rather than a style opinion.
    Ordered by step so a caller reads them against the file it just wrote.
    """

    found = []
    discovery_adapters = set()
    deepened = set()
    for step in manifest.steps:
        if _is_depth(step):
            deepened.add(step.adapter_id)
        else:
            discovery_adapters.add(step.adapter_id)

    windowed = [step for step in manifest.steps if step.window_start or step.window_end]
    unwindowed = [step for step in manifest.steps if not (step.window_start or step.window_end)]

    for adapter_id in sorted(discovery_adapters):
        if adapter_id in DEPTH_TARGETS and adapter_id not in deepened:
            found.append(
                Advisory(
                    DEPTH_NOT_PLANNED,
                    adapter_id,
                    "{0} discovers here and nothing hydrates it, so this run will not"
                    " carry {1}. `coverage.plan_depth` builds the steps from the"
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
            try:
                can_bound = runner.reach_for(step.adapter_id, query=step.query)
            except runner.WindowReachError:
                # An adapter or operation this table does not name is not
                # this review's failure to report: `runner.run_step` is
                # where an unrecognized adapter is refused, and this
                # advisory stays as silent about it as it always has been.
                continue
            if not can_bound:
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
        # The floor `plan_depth` refuses a cap under, read at review time too.
        # A manifest hand-written or amended after planning never passed through
        # the plan, and this is the failure `evidence.md` §2 measured: a
        # `transcript:` step at max_items 1 is valid, runs, reaches no cue, and
        # reports success. The row is already in hand here.
        operation = _depth_operation(step)
        target = DEPTH_TARGETS[step.adapter_id][operation] if operation else None
        if target is not None and target.kind == "discovery" and step.max_items < target.min_items:
            found.append(
                Advisory(
                    CAP_BELOW_DEPTH_FLOOR,
                    step.step_id,
                    "max_items {0} is under the floor of {1} this {2} {3!r} step needs: page one"
                    " is the record it starts from and `kept < max_items` is the clause"
                    " that buys the page its evidence is on, so this step reaches none"
                    " of it and reports success. `coverage.plan_depth` refuses this"
                    " cap.".format(
                        step.max_items, target.min_items, step.adapter_id, operation
                    ),
                )
            )
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

    # Which reads deepened something is decided by the step each record came
    # from, and by nothing else. Every `AcquisitionRecord` carries the
    # `step_id` of the step that produced it and an artifact's `steps` are one
    # `StepResult` each, so the join is exact and nothing is matched by
    # similarity or read off a record's shape.
    #
    # It reads the step because every shape a record could be asked for is a
    # proxy, and the last one this held was wrong in the field. A paging depth
    # step's records carry no `discovery_locator` — the core sets one only on a
    # hydration step's own calls — so the clause fell back to asking a comment
    # to name a parent *this artifact holds*. Paging depth is inherently a
    # second artifact: :func:`plan_depth` takes the records a discovery run
    # returned and its steps run as their own dispatch, so the video a comment
    # names is in artifact one. That is what told a caller who had just
    # acquired 57 comment records that nothing had deepened anything, measured
    # 2026-08-17 on the artifact the comments arrived in.
    #
    # Still read off the records rather than the step list alone, for the
    # reason `normalize` reads `discovery_not_recorded` off records: a staged
    # hydration runs against a selection frozen from an artifact this one never
    # saw, so an artifact holding hydrations and no discovery established no
    # lineage and has nothing to report.
    by_step = {result.step_id: result for result in artifact.steps}
    deepened = set()
    discovery_adapters = set()
    for record in artifact.records:
        result = by_step.get(record.step_id)
        if result is None or result.kind not in schema.STEP_KINDS:
            # This artifact does not hold the step this record names, or holds
            # one assembled by hand that states no kind. Either way the step
            # cannot say what the read was, and the answer to a source that
            # cannot answer is to say nothing — reaching for the next thing the
            # record looks like is the defect above.
            continue
        if _is_depth(result):
            deepened.add(record.adapter_id)
        else:
            discovery_adapters.add(record.adapter_id)

    for adapter_id in sorted(discovery_adapters):
        if adapter_id in DEPTH_TARGETS and adapter_id not in deepened:
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
