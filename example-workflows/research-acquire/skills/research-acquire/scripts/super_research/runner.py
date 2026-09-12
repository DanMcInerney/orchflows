"""Runner: planning, window reach, ``run_step``, and lane scheduling.

The literal adapter table is :mod:`.dispatch`'s and its names are re-exported
here. This module alone turns a returned cursor into another request and
applies the caller and core caps. The carrier and clock stay injected, so it
reaches neither network nor filesystem on its own.
"""

from __future__ import annotations

import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from typing import Callable, Dict, List, Optional, Tuple

from . import cache, normalize, schema, transport
from .adapters import AdapterDescriptor, AdapterRequest, NativePage, build_native_page
from .dispatch import (
    ADAPTER_IDS,
    RunnerError,
    call_adapter,
    declared_descriptors,
    descriptor_for,
    operation_for,
    surface_descriptors,
)
from .ledger import (
    ADDITIVE_METRICS,
    METRIC_ORDINALS,
    NATIVE_PAGE,
    OPERATION_KIND_ORDINALS,
    PlannedOperation,
    ScheduledOperation,
    ScheduledRun,
    WorkLedgerEvent,
    causal_key,
    fake_makespan_us,
    ledger_of,
    ledger_sums,
    planned_operations,
    schedule_of,
)
from .ordering import (
    FAMILY_SCOPED_ORDERS,
    INSTANT_FORMAT,
    MISSING,
    ORDERING_CONTRACT,
    PRESENT,
    OrderingError,
    content_family,
    eligible_snapshot,
    instant_seconds,
    order_records,
    ordering_key,
)
from .pacing import (
    US_PER_MS,
    US_PER_SECOND,
    OriginRead,
    RateGovernor,
    RouteBudget,
    budget_of,
    budgets_from,
    paced_carrier,
    route_budgets,
    tick_us,
)

# The most pages one discovery step may read, whatever the origin keeps
# offering. Every other way out of the page loop is the origin's own statement —
# it stopped naming a cursor, or it named one this step already spent — and an
# origin that never makes either statement would spend a budget nobody set, so
# the last stop is the core's. Five, because the roster's measured pages hold
# ten to twenty-five rows, which reaches fifty to a hundred and twenty-five
# records; and because at the slowest measured ceiling, one read per thirty
# seconds, five reads is the most a single step can cost before it is a session
# rather than a step.
MAX_PAGES_PER_STEP = 5

MAX_CONCURRENT_LANES = 8

StepOutcome = Tuple[
    schema.StepResult, Tuple[schema.AcquisitionRecord, ...], Tuple[PlannedOperation, ...]
]


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


def _refused_step(
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

    return page.outcome != "refused" and cache.CACHE_HIT not in page.loss


def _offers_another_page(step: schema.AcquisitionStep, page: NativePage, kept: int) -> bool:
    """Whether this page leaves a next one the step could still want.

    Three questions, and only the first is about the page. A hydration step
    never pages: its calls are one per hit the caller froze, which is what makes
    each hydration record's provenance exact rather than inferred, and a page
    read off a cursor was authorized by nobody. A page that names no cursor is
    the origin saying there is nothing after it. And a step whose cap is already
    met wants nothing further — the caller's own bound reached, so every stop
    this function makes is a step finishing rather than a recall cut short.
    That is the whole difference between here and the two refusals in
    `runner.run_step`'s own loop: those stop a step that still wanted more, and
    say so with a loss code.
    """

    return step.kind == "discovery" and bool(page.cursor_out) and kept < step.max_items


# ---------------------------------------------------------------------------
# Window reach: whether one operation's origin can bound acquisition time
# ---------------------------------------------------------------------------
#
# Capability is a property of an *operation*, not of an adapter: `bluesky`
# sends `since`/`until` on search and none on its author feed, and `x_guest`
# and `github_rest` split the same way. So `WINDOW_REACH` is keyed by adapter
# id and then by operation, and an adapter whose operations agree declares
# once under the empty-string operation. It is total over `ADAPTER_IDS`. An
# adapter or operation nothing here names raises `WindowReachError` rather
# than reading as either "can" or "cannot", because a silent default would be
# a claim nobody measured. `True` and `False` are both measured; `None` is
# declared and unmeasured, a third reading `window_loss_code` types apart.
# No bound is carried into an origin request here: that is each adapter's own.


class WindowReachError(ValueError):
    """An adapter or operation named no window-reach declaration."""


# Loud and typed, on `StepResult.loss`: a windowed step whose operation is
# declared unable to bound time at the origin carries this code, so an empty
# in-window answer (no code) and an unhonored bound (this code) are two
# readings a caller tells apart mechanically rather than by parsing a
# sentence. `runner.run_step` is the one place that appends it.
WINDOW_NOT_HONORED = "window_not_honored"

# Loud and typed, beside it: a windowed step whose operation this table names
# but has never measured carries this code instead — never both at once, and
# never silently folded into `WINDOW_NOT_HONORED`, because a limit nobody
# checked and a limit measured are two different readings for a caller to
# act on differently. `window_loss_code` is the one place that chooses
# between them.
WINDOW_CAPABILITY_UNMEASURED = "window_capability_unmeasured"

# adapter_id -> operation -> whether that operation's origin can be asked to
# bound the read by time, in the origin's own terms — `True` or `False`, both
# measured — or `None`, declared but never measured. `""` is the operation
# key for an adapter whose calls are all one shape, matching the convention
# `coverage.DEPTH_TARGETS` already uses for `reddit_archive`.
WINDOW_REACH: Dict[str, Dict[str, Optional[bool]]] = {
    # Measured: `bluesky.operation_params` sends `since`/`until` on search
    # only; the author feed takes none.
    "bluesky": {"search": True, "author": False},
    # Measured: `hacker_news._fetch_search` serves search, search_by_date and
    # comments and always applies `window_filters`; item and tree read
    # Firebase/Algolia by one id and have no ordering a window could act on.
    "hacker_news": {
        "search": True,
        "search_by_date": True,
        "comments": True,
        "item": False,
        "tree": False,
    },
    # Measured: `web_search.feed_params` sends Google's
    # `when:Nd` only on the `gnews` branch; `ddg`, `bing` and `bingnews`
    # never build one.
    "web_search": {"gnews": True, "ddg": False, "bing": False, "bingnews": False},
    # Measured: `_fetch_listing`/`_fetch_search` (`adapters/reddit_shreddit.py`)
    # both send `t=<window>`, derived from the step's own `window_start` when
    # one is carried (`_origin_window`, `origin_time_bucket`) or from the
    # argument grammar otherwise;
    # `_fetch_comments` takes no window at all.
    "reddit_shreddit": {"listing": True, "search": True, "comments": False},
    # `repo` is a single repository hydration by name: no ordering, no bound.
    # `issues` and `search` measured live: `since=` on an active
    # repository's issue list and `created:` on search both genuinely filter
    # (`adapters/github_rest.origin_since_param`, `.origin_created_qualifier`).
    # `releases` measured the same way and does not: a `since=` set minutes in
    # the future answered the identical unfiltered page, so it stays `False`
    # as a measured fact rather than a conservative default.
    "github_rest": {"repo": False, "issues": True, "releases": False, "search": True},
    # `TweetResultByRestId` and `UserByScreenName` are single-item
    # hydrations with no ordering, measured `False`. `UserTweets` is the one
    # operation with an ordering and is unmeasured: `None`, not the
    # conservative `False` a caller would read as a checked limit.
    "x_guest": {"TweetResultByRestId": False, "UserByScreenName": False, "UserTweets": None},
    # Origin accepts none, measured: neither selection carries a time
    # concept (`adapters/public_page.py`).
    "public_page": {"": False},
    # Origin accepts none: an arbitrary document fetch takes no query string
    # at all (`transport.build_transport_request` returns before one is
    # built).
    "open_page": {"": False},
    # Origin accepts none for this hydration: one archived post by id.
    "reddit_archive": {"ids": False, "search": True},
    "reddit_feed": {"feed": False, "search": None},
    "x_xcancel": {"search": None, "status": False},
    "rss_atom": {"": False},
    "x_syndication": {"": False},
    # Origin accepts none, measured: this adapter never sets `published_at`
    # at all, so there is nothing on either side for a window to act on.
    "linkedin_public": {"": False},
    "instagram_public": {"": False},
    # Origin accepts none: the stream's `since` and `max` are message ids
    # and not moments (`stocktwits._fetch_stream`); the symbol search is a
    # name lookup.
    "stocktwits": {"": False},
    # Origin accepts none (`prediction_markets.operation_params`).
    "prediction_markets": {"": False},
    # Measured live: `keywords=python` bare vs. with a candidate
    # `f_TPR=r<seconds>` moved the oldest posting's date forward, and on a
    # rarer keyword (not already saturating the page) also dropped the row
    # count 10 -> 6 (`adapters/linkedin_jobs.origin_recency_term`).
    "linkedin_jobs": {"": True},
    # `x_fxtwitter.operation_params` states no term for a bound it could send
    # without inventing a query syntax, and no live read has settled whether
    # one exists. `None`: an absence of measurement, not a proven absence of
    # capability.
    "x_fxtwitter": {"": None},
    # `search` measured live: an origin-published upload-date
    # filter value, added to the route's closed POST-body list
    # (`routes.py`), moved every returned
    # `publishedTimeText` inside the named span against a nine-year-old
    # unfiltered baseline (`adapters/youtube_innertube.origin_upload_date_
    # filter`). `player`, `next` and `transcript` read one video and have
    # no time concept regardless — confidently `False`, not re-measured.
    "youtube_innertube": {
        "search": True,
        "player": False,
        "next": False,
        "transcript": False,
    },
    # Measured, each in the origin's
    # own grammar: GDELT DOC's `startdatetime`/`enddatetime` returned only
    # in-window `seendate`s; Stack Exchange's `fromdate`/`todate` returned
    # only in-window `creation_date`s; the Wikimedia pageviews date range is
    # two path segments and the answer held exactly the days inside them;
    # OpenAlex, Crossref and arXiv each filtered publication time at the
    # origin, so `scholarly`'s three operations agree and it declares once.
    "gdelt": {"": True},
    "stack_exchange": {"": True},
    "wikimedia_pageviews": {"": True},
    "scholarly": {"": True},
    # Origin accepts none, measured: a TikTok page read and an
    # oEmbed lookup each address one item and carry no time concept.
    "tiktok_public": {"": False},
    "oembed": {"": False},
    # The offline fixture reader: no origin exists for a bound to reach.
    "fake": {"": False},
}


def can_bound_at_origin(adapter_id: str, operation: str) -> Optional[bool]:
    """Whether this exact (adapter, operation) pair can bound time at the origin.

    Three readings, not two. `True` and `False` are both measured facts;
    `None` is a declaration this table carries with no measurement behind it
    yet, for an operation a live read was blocked before it could settle.
    Raises rather than guesses where the table names nothing at all: an
    adapter this table does not name and an operation a named adapter does
    not name are both a declaration nothing made, and reading either as
    `True`, `False` or `None` would be a capability this module never
    considered.
    """

    row = WINDOW_REACH.get(adapter_id)
    if row is None:
        raise WindowReachError(
            "no window-reach declared for adapter {0!r}; declared: {1}".format(
                adapter_id, ", ".join(sorted(WINDOW_REACH))
            )
        )
    if operation not in row:
        raise WindowReachError(
            "adapter {0!r} declares no window-reach for operation {1!r}; declared: {2}".format(
                adapter_id, operation, ", ".join(sorted(row)) or "<none>"
            )
        )
    return row[operation]


def reach_for(
    adapter_id: str, query: str = "", target_ids: Tuple[str, ...] = ()
) -> Optional[bool]:
    """Whether the operation this query or target names can bound time.

    The one entry point a caller needs: it resolves the operation the same
    way a real dispatch would and reads the declaration for it, without the
    caller building an :class:`AdapterRequest` of its own. `None` when that
    operation is declared but unmeasured, same as :func:`can_bound_at_origin`.
    """

    request = AdapterRequest(step_id="", query=query, target_ids=target_ids)
    return can_bound_at_origin(adapter_id, operation_for(adapter_id, request))


def window_loss_code(reach: Optional[bool]) -> Optional[str]:
    """The loss code one windowed call's own reach reading contributes, or none.

    Where :func:`reach_for`'s three readings become the two codes a caller
    sees on `StepResult.loss`: `None` — unmeasured — becomes
    :data:`WINDOW_CAPABILITY_UNMEASURED`; `False` — measured unable —
    becomes :data:`WINDOW_NOT_HONORED`; `True` contributes nothing, because a
    call that could bound the window needs no typed statement saying so.
    `runner.run_step` is the one caller.
    """

    if reach is None:
        return WINDOW_CAPABILITY_UNMEASURED
    if not reach:
        return WINDOW_NOT_HONORED
    return None


def step_window_loss(
    step: schema.AcquisitionStep, request: AdapterRequest, found: Optional[str]
) -> Optional[str]:
    """One call's contribution to its step's running window-loss reading.

    A declaration about the call's own shape, asked before the read rather
    than the answer: whether this operation could have spent the window at
    the origin does not depend on what came back. ``found`` is the step's
    reading so far and is returned unchanged once it holds anything, because
    a hydration step's calls address hits the caller named and are not
    guaranteed to share an operation the way a discovery step's continuations
    always do, and a caller wants to know a step's window went unspent at
    least once, not how many times. `runner.run_step` folds this across every
    call a step makes and appends the result to `StepResult.loss` once, at
    the end, the same place every other reading below the read loop lands.
    """

    if found is not None or not (step.window_start or step.window_end):
        return found
    reach = can_bound_at_origin(step.adapter_id, operation_for(step.adapter_id, request))
    return window_loss_code(reach)


def run_step(
    step: schema.AcquisitionStep,
    carrier: transport.Transport,
    artifact_id: str,
    manifest_id: str,
    clock: Callable[[], float] = time.monotonic,
) -> Tuple[
    schema.StepResult, Tuple[schema.AcquisitionRecord, ...], Tuple[PlannedOperation, ...]
]:
    descriptor = descriptor_for(step.adapter_id)
    if descriptor is None:
        return (_refused_step(step, "", "no_route"), (), ())

    records: List[schema.AcquisitionRecord] = []
    operations: List[PlannedOperation] = []
    page_outcomes: List[str] = []
    page_routes: List[str] = []
    loss: List[str] = []
    warnings: List[str] = []
    received = 0
    pages = 0
    truncated = False
    outside_window = 0
    window_loss: Optional[str] = None  # folded by `step_window_loss`, one call at a time

    # Every call this step will make. A discovery step's continuations are
    # appended as they are earned, one per page that offers a cursor worth
    # spending, so the loop below is the one place a step's calls are counted.
    calls = list(planned_calls(step))
    spent_cursors = {""}
    page_index = 0

    if (
        step.kind == "discovery"
        and descriptor.page_size
        and step.max_items < descriptor.page_size
    ):
        # Said before the read, because it is a fact about the cap and not
        # about the answer: on a surface that answers a page per call, a cap
        # under the page buys no saving and drops the rest of the page.
        warnings.append(
            "max_items {0} is below this surface's page size {1}: one read returns"
            " up to {1} rows and the rows past the cap are dropped at no saving".format(
                step.max_items, descriptor.page_size
            )
        )

    while page_index < len(calls):
        request, discovery_locator = calls[page_index]
        if step.kind == "discovery" and len(records) >= step.max_items:
            # The core owns stop: no further call is made once the cap is met.
            # A hydration step is not stopped here — every one of its calls was
            # authorized by name, and its cap bounds each answer rather than
            # the sum, so a first hit that answers richly cannot starve the
            # ones the caller also selected.
            truncated = True
            break
        window_loss = step_window_loss(step, request, window_loss)
        began_us = tick_us(clock)
        try:
            page = call_adapter(step.adapter_id, carrier, request)
            reached = reached_origin(page)
        except transport.TransportError as error:
            # The one read that comes back with nothing to type — a refused
            # connection, an unresolvable name, a TLS handshake that failed,
            # the transport declining to send it at all (a non-https address,
            # a write-capable method, an undeclared route or credential), or a
            # guest token its activation never minted. Typed here rather than
            # raised, because raising would discard every step already run and
            # everything read before this call is the partial result a failure
            # owes. The error's own text is the only part of it naming where
            # to look, so it rides as a warning. The error says whether an
            # origin answered the read it cost — a refused activation did —
            # and that answer is what the ledger bills.
            page = build_native_page(
                descriptor,
                (),
                outcome="failed",
                loss=(error.loss,),
                warnings=(str(error),),
            )
            reached = error.reached
        pages += 1
        page_outcomes.append(page.outcome)
        page_routes.append(page.route_id)
        loss.extend(page.loss)
        # The page's own account of itself, carried rather than dropped: it is
        # the only part of a typed failure that names where to look next.
        warnings.extend(page.warnings)
        received += len(page.records)
        operations.append(
            PlannedOperation(
                step_id=step.step_id,
                adapter_id=step.adapter_id,
                # The route the page says answered, which is the route the read
                # actually left on: for an adapter reading two surfaces it is
                # whichever this call used, and charging both to the
                # descriptor's would bill one origin for another's read.
                route_id=page.route_id,
                page_index=page_index,
                duration_us=tick_us(clock) - began_us,
                reached_origin=reached,
                records_received=len(page.records),
            )
        )
        # The window first, then the cap: a row the origin dated outside the
        # step's bounds is dropped before it can spend the cap, so the cap is
        # spent in-window. Nothing undated is dropped here.
        windowed = tuple(
            native for native in page.records if in_window(step, native.published_at)
        )
        outside_window += len(page.records) - len(windowed)
        # A discovery step's cap bounds the whole step; a hydration step's cap
        # bounds each authorized call, which is what "one call per hit" makes
        # the honest unit.
        room = step.max_items if step.kind == "hydration" else step.max_items - len(records)
        if len(windowed) > room:
            truncated = True
        records.extend(
            normalize.normalize_page(
                replace(page, records=windowed[:room]),
                step,
                artifact_id,
                manifest_id,
                page_index=page_index,
                list_index_start=len(records),
                discovery_locator=discovery_locator,
            )
        )
        if _offers_another_page(step, page, len(records)):
            if page.cursor_out in spent_cursors or len(calls) >= MAX_PAGES_PER_STEP:
                # The origin had more and the core would not spend it: a
                # cursor it has already asked on, or one page past its own cap.
                truncated = True
            else:
                spent_cursors.add(page.cursor_out)
                calls.append((replace(request, cursor=page.cursor_out), discovery_locator))
        page_index += 1

    if truncated:
        # A raw cap counts every received record and may drop unseen uniques,
        # and so does a step that stopped while the origin was still offering.
        loss.append("recall_window_partial")
    if outside_window:
        # Counted and said, never typed: the bound is the caller's own, so a
        # row outside it is the step finishing rather than a recall cut short.
        warnings.append(
            "{0} record(s) the origin dated outside the step's window were dropped"
            " before the cap counted them".format(outside_window)
        )
    if window_loss:
        loss.append(window_loss)
    outcome = "partial" if truncated else schema.reduce_outcomes(tuple(page_outcomes))
    # The route the step's first page answered on: the route its read left on.
    # A continuation may answer on a surface page one published (a transcript's
    # caption track), and each record and each ledger operation carries the
    # exact route it came from. A step with no call to make — a hydration
    # whose caller selected nothing — is `empty` on the route it was admitted
    # to read.
    return (
        schema.StepResult(
            step_id=step.step_id,
            adapter_id=step.adapter_id,
            route_id=page_routes[0] if page_routes else descriptor.route_id,
            pages=pages,
            records_received=received,
            records_kept=len(records),
            outcome=outcome,
            loss=tuple(loss),
            warnings=tuple(warnings),
            kind=step.kind,
            query=step.query,
        ),
        tuple(records),
        tuple(operations),
    )


def lanes_of(
    steps: Tuple[schema.AcquisitionStep, ...],
) -> "OrderedDict[str, List[schema.AcquisitionStep]]":
    """The steps grouped by adapter, each group in declared order."""

    lanes: "OrderedDict[str, List[schema.AcquisitionStep]]" = OrderedDict()
    for step in steps:
        lanes.setdefault(step.adapter_id, []).append(step)
    return lanes


def run_lane(
    steps: List[schema.AcquisitionStep],
    carrier: transport.Transport,
    artifact_id: str,
    manifest_id: str,
    clock: Callable[[], float],
) -> List[StepOutcome]:
    return [run_step(step, carrier, artifact_id, manifest_id, clock) for step in steps]


def run_steps(
    manifest: schema.AcquisitionManifest,
    carrier: transport.Transport,
    artifact_id: str,
    clock: Callable[[], float] = time.monotonic,
    lanes: int = MAX_CONCURRENT_LANES,
) -> Tuple[StepOutcome, ...]:
    """Every step's outcome, in declared order, however many lanes ran them."""

    grouped = lanes_of(manifest.steps)
    workers = max(1, min(lanes, MAX_CONCURRENT_LANES, len(grouped)))
    if workers < 2:
        return tuple(
            run_lane(list(manifest.steps), carrier, artifact_id, manifest.manifest_id, clock)
        )
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(run_lane, steps, carrier, artifact_id, manifest.manifest_id, clock)
            for steps in grouped.values()
        ]
        by_step_id: Dict[str, StepOutcome] = {}
        for future in futures:
            for outcome in future.result():
                by_step_id[outcome[0].step_id] = outcome
    return tuple(by_step_id[step.step_id] for step in manifest.steps)


def run_scheduled(
    manifest: schema.AcquisitionManifest,
    carrier: Optional[transport.Transport] = None,
    clock: Callable[[], float] = time.monotonic,
    dispatch_ordinal: int = 0,
    start_tick_us: int = 0,
    lanes: int = MAX_CONCURRENT_LANES,
) -> ScheduledRun:
    """Run one validated manifest to one immutable artifact and its work ledger."""

    reached = paced_carrier(clock=clock) if carrier is None else carrier
    artifact_id = artifact_id_for(manifest.manifest_id)
    steps: List[schema.StepResult] = []
    records: List[schema.AcquisitionRecord] = []
    operations: List[PlannedOperation] = []
    for result, step_records, step_operations in run_steps(
        manifest, reached, artifact_id, clock=clock, lanes=lanes
    ):
        steps.append(result)
        records.extend(step_records)
        operations.extend(step_operations)

    typed = normalize.type_discovery_gaps(tuple(records))
    loss = tuple(sorted({code for step in steps for code in step.loss}))
    artifact = schema.AcquisitionArtifact(
        artifact_id=artifact_id,
        manifest_id=manifest.manifest_id,
        as_of=manifest.as_of,
        records=typed,
        steps=tuple(steps),
        edges=normalize.link_discovery_hydration(typed),
        groups=normalize.group_records(typed),
        outcome=schema.reduce_outcomes(tuple(step.outcome for step in steps)),
        loss=loss,
    )
    return ScheduledRun(
        artifact=artifact,
        ledger=ledger_of(
            tuple(operations),
            manifest,
            stop_reason=artifact.outcome,
            dispatch_ordinal=dispatch_ordinal,
            start_tick_us=start_tick_us,
        ),
    )


def run_acquisition(
    manifest: schema.AcquisitionManifest,
    carrier: Optional[transport.Transport] = None,
    clock: Callable[[], float] = time.monotonic,
    lanes: int = MAX_CONCURRENT_LANES,
) -> schema.AcquisitionArtifact:
    """Run one validated manifest to one immutable artifact."""

    return run_scheduled(manifest, carrier, clock=clock, lanes=lanes).artifact
