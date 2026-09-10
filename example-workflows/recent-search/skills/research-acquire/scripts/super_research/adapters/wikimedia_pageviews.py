"""K0 Wikimedia per-article pageviews: attention over time, window in the path.

Measured 2026-09-01: keyless ``GET`` on the per-article pageviews endpoint
answered 200 with ``items``: one row per day inside the requested range, each
row carrying its own ``project``, ``article``, ``granularity``, ``access``,
``agent``, a ``timestamp`` spelled ``YYYYMMDD00``, and an integer ``views``.
Exactly the days inside the inclusive range come back — an eleven-day request
answered eleven rows, a three-day request three. A title the origin holds no
data for (nonexistent article or a range before the article existed) answered
404 with a JSON body naming its own ``detail`` sentence. A percent-encoded
segment (``%28``/``%29`` for the parentheses a disambiguated title carries)
answered identically to the literal characters, so the ordinary path quoting
``_support.transport_request.path_segments`` already does needs nothing
special here. A cold first request from a fresh address answered 429 once and
200 on the next attempt; the package's own pacing and cooldown cover that
without this module retrying anything.

**The window is the path, not a parameter.** This origin serves nothing but a
dated range: ``start`` and ``end`` are two of the route's seven declared path
segments, so a call with no ``window_start`` has no valid path to leave on at
all. Rather than default one, a hydration naming no window is refused here —
the same shape ``open_page`` refuses an address its policy will not read
before ever making a call. A ``window_start`` with no ``window_end`` is not
the same gap: measured the same day, a far-future end segment
(:data:`FAR_FUTURE_END`) answered 200 and simply returned through the latest
day the origin holds, so an open-ended window is spent as that sentinel
rather than refused. It is a spelled constant and never the wall clock, so
the same window asked twice builds the same request.

**Every record is date-precision.** The origin reports a day, never a moment
inside it, so ``DESCRIPTOR.standing_loss`` carries ``date_precision_only`` on
every row this module ever returns — the same standing declaration
``linkedin_jobs`` makes for its own day-only dates.

**Identity and locator are composed from the row's own fields, not from what
the request asked for.** A row states its own ``project`` and ``article``,
and those are what ``native_item_id`` and ``canonical_locator`` are built
from: the origin's own answer is the better claim, and the two need not be
byte-identical to the request in case of any origin-side title
normalization. No full host literal is spelled here — the route-ownership
scan reserves the declared origin string for the modules that declare it —
so a document's address is assembled at read time from the row's ``project``
plus the fixed ``.org/wiki/`` path every Wikimedia project answers on.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Mapping, Optional, Tuple

from .. import schema, transport
from . import (
    AdapterDescriptor,
    AdapterRequest,
    NativePage,
    NativeRecord,
    build_native_page,
    fetch_one_page,
)

# The one namespace a target with no ``<project>:`` prefix reads. Spelled as a
# constant and never inferred from the article's own spelling, because nothing
# about an article title says which project it belongs to.
DEFAULT_PROJECT = "en.wikipedia"

# The three path segments this module never varies. A caller cannot ask this
# route for mobile-only or bot-only counts; the roster's one row promises
# attention over time on the whole article, at day resolution.
ACCESS = "all-access"
AGENT = "all-agents"
GRANULARITY = "daily"

# The route's own path-segment names, in `_support/route_contracts.py`'s
# declared order, spelled here once so a params dict can be built without
# re-typing the route's grammar.
PROJECT_PARAM = "project"
ACCESS_PARAM = "access"
AGENT_PARAM = "agent"
ARTICLE_PARAM = "article"
GRANULARITY_PARAM = "granularity"
START_PARAM = "start"
END_PARAM = "end"

# Measured 2026-09-01: a far-future end segment answers 200 and returns
# through the latest day the origin holds, rather than refusing. A spelled
# constant rather than a value derived from the wall clock, so a window with
# no end builds the identical request every time it is built.
FAR_FUTURE_END = "2100010100"

CONTENT_KIND = "pageview_count"
NATIVE_ORDER = "wikimedia_pageviews_daily_order"

# The instant shapes this module reads and writes. `window_start`/`window_end`
# arrive in the manifest's own spelling; the origin's own `timestamp` is a
# different, fixed-width shape. Each adapter owns its own tiny parser for its
# own instants rather than reaching into `ordering`, which stays a core-only
# import — the same convention `linkedin_jobs.py` documents for the same
# reason.
WINDOW_INSTANT_FORMAT = schema.INSTANT_FORMAT
ORIGIN_TIMESTAMP_FORMAT = "%Y%m%d%H"
RECORD_INSTANT_FORMAT = schema.INSTANT_FORMAT

# Where the answer keeps its rows, and what each row names. Declared, never
# searched for: the value of a typed drift is that it says the payload
# reshaped rather than that the range holds nothing.
ITEMS_KEY = "items"
PROJECT_KEY = "project"
ARTICLE_KEY = "article"
TIMESTAMP_KEY = "timestamp"
VIEWS_KEY = "views"
GRANULARITY_KEY = "granularity"
ACCESS_KEY = "access"
AGENT_KEY = "agent"
DETAIL_KEY = "detail"

GRANULARITY_ATTRIBUTE = "granularity"
ACCESS_ATTRIBUTE = "access"
AGENT_ATTRIBUTE = "agent"

# Every code this module can attach, spelled once each so a search over a name
# finds the branch that emits it.
HTTP_STATUS = "http_status"
MALFORMED_JSON = "malformed_json"
SCHEMA_DRIFT = "schema_drift"
FIELD_OMITTED = "field_omitted"
DATE_PRECISION_ONLY = "date_precision_only"
UNSELECTED_TARGET = "unselected_target"

DESCRIPTOR = AdapterDescriptor(
    adapter_id="wikimedia_pageviews",
    adapter_version="1",
    access_class="K0",
    route_id=transport.WIKIMEDIA_PAGEVIEWS_ROUTE,
    platform="wikimedia",
    native_identity_namespace="wikimedia",
    representation_kind="native",
    operator_identity="wikimedia",
    # True of every row this route will ever answer, not of some of them: the
    # origin reports a day and never a moment inside it.
    standing_loss=(DATE_PRECISION_ONLY,),
    min_interval_ms=1000,
    burst=1,
)

SURFACE_DESCRIPTORS = (DESCRIPTOR,)


def target_grammar(target: str) -> Tuple[str, str]:
    """``(project, article)`` from ``<article>`` or ``<project>:<article>``.

    A project is never inferred from an article's own spelling: a caller
    names one with the ``<project>:`` prefix, or reads :data:`DEFAULT_PROJECT`.
    ``("", "")`` says the target named no article at all, which is the one
    shape :func:`fetch_native_page` refuses before ever building a request.
    """

    stripped = (target or "").strip()
    if not stripped:
        return ("", "")
    project, separator, article = stripped.partition(":")
    if not separator:
        return (DEFAULT_PROJECT, stripped)
    project = project.strip()
    article = article.strip()
    if not project or not article:
        return ("", "")
    return (project, article)


def path_date(instant: str) -> str:
    """One manifest instant as this route's own ``YYYYMMDD00`` path segment.

    Empty for an empty or unparseable instant: a bound this module cannot
    read is a bound it cannot spend, and a caller reading an empty answer is
    better placed to say so than a malformed path segment sent to the origin.
    """

    if not instant:
        return ""
    try:
        moment = datetime.strptime(instant, WINDOW_INSTANT_FORMAT)
    except ValueError:
        return ""
    return moment.strftime("%Y%m%d") + "00"


def published_at_from(timestamp: Any) -> str:
    """This row's own day, as the artifact's midnight-UTC instant, or nothing.

    Only the origin's exact ``YYYYMMDD00`` shape is read; anything else is a
    missing date rather than a guessed one.
    """

    if not isinstance(timestamp, str):
        return ""
    try:
        moment = datetime.strptime(timestamp, ORIGIN_TIMESTAMP_FORMAT)
    except ValueError:
        return ""
    return moment.replace(tzinfo=timezone.utc).strftime(RECORD_INSTANT_FORMAT)


def _text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _engagement_of(row: Mapping[str, Any]) -> Tuple[Tuple[str, int], ...]:
    views = row.get(VIEWS_KEY)
    if isinstance(views, bool) or not isinstance(views, int) or views < 0:
        # A count the row did not report cleanly is not a count: `views`
        # absent from this record's engagement, never a zero this module
        # invented.
        return ()
    return ((VIEWS_KEY, views),)


def _record_for(position: int, row: Mapping[str, Any]) -> Optional[NativeRecord]:
    """One row as an identified record, or nothing when it names no article day.

    ``None`` rather than a record with blanks: a row naming no project,
    article or timestamp identifies nothing this module can group or address,
    which is the same reasoning `reddit_archive.submission_fullname` states
    for a post naming no id.
    """

    project = row.get(PROJECT_KEY)
    article = row.get(ARTICLE_KEY)
    timestamp = row.get(TIMESTAMP_KEY)
    if not isinstance(project, str) or not project:
        return None
    if not isinstance(article, str) or not article:
        return None
    if not isinstance(timestamp, str) or not timestamp:
        return None

    published_at = published_at_from(timestamp)
    engagement = _engagement_of(row)
    missing = () if (published_at and engagement) else (FIELD_OMITTED,)

    return NativeRecord(
        canonical_content_kind=CONTENT_KIND,
        # Composed from the row's own identifiers: `project` + "/" + `article`
        # + "/" + `timestamp`, the origin's own vocabulary and nothing this
        # module invents.
        native_item_id=project + "/" + article + "/" + timestamp,
        # Composed at read time from the row's own project, never a spelled
        # host literal: the route-ownership scan reserves the declared origin
        # string for the modules that declare it.
        canonical_locator="https://" + project + ".org/wiki/" + article,
        published_at=published_at,
        engagement=engagement,
        attributes=(
            (GRANULARITY_ATTRIBUTE, _text(row.get(GRANULARITY_KEY))),
            (ACCESS_ATTRIBUTE, _text(row.get(ACCESS_KEY))),
            (AGENT_ATTRIBUTE, _text(row.get(AGENT_KEY))),
        ),
        native_position=position,
        loss=DESCRIPTOR.standing_loss + missing,
    )


def _http_status_page(response: transport.TransportResponse) -> NativePage:
    """A non-200 answer, with the origin's own ``detail`` sentence if it sent one."""

    detail = ""
    try:
        payload = json.loads(response.body)
        if isinstance(payload, Mapping):
            detail = _text(payload.get(DETAIL_KEY))
    except ValueError:
        pass
    warning = "http status {0} from {1}".format(response.status, DESCRIPTOR.route_id)
    if detail:
        warning = warning + ": " + detail
    return build_native_page(
        DESCRIPTOR,
        (),
        observed_at=response.observed_at,
        native_order=NATIVE_ORDER,
        warnings=(warning,),
        outcome="failed",
        loss=(HTTP_STATUS,),
    )


def _drifted(response: transport.TransportResponse, detail: str) -> NativePage:
    """The origin answered, and what it answered with is not what it answers with.

    Never `empty`: "this range holds nothing" and "the payload reshaped" are
    two readings a caller cannot tell apart from an empty result, and only
    one of them is a fact about the platform.
    """

    return build_native_page(
        DESCRIPTOR,
        (),
        observed_at=response.observed_at,
        native_order=NATIVE_ORDER,
        warnings=(
            "route {0} answered 200 and {1}: the payload this adapter reads has"
            " changed shape".format(DESCRIPTOR.route_id, detail),
        ),
        outcome="failed",
        loss=(SCHEMA_DRIFT,),
    )


def _page_from(response: transport.TransportResponse) -> NativePage:
    """Turn one response the origin itself sent into exactly one page."""

    if response.status != 200:
        return _http_status_page(response)

    try:
        payload = json.loads(response.body)
    except ValueError:
        return build_native_page(
            DESCRIPTOR,
            (),
            observed_at=response.observed_at,
            native_order=NATIVE_ORDER,
            warnings=("route {0} answered 200 with no json body".format(DESCRIPTOR.route_id),),
            outcome="failed",
            loss=(MALFORMED_JSON,),
        )

    if not isinstance(payload, Mapping) or ITEMS_KEY not in payload:
        return _drifted(response, "carried no {0} field".format(ITEMS_KEY))
    items = payload[ITEMS_KEY]
    if not isinstance(items, list):
        return _drifted(response, "kept a {0} that is not a list".format(ITEMS_KEY))

    records = []
    unidentified = 0
    for row in items:
        if not isinstance(row, Mapping):
            unidentified += 1
            continue
        record = _record_for(len(records), row)
        if record is None:
            unidentified += 1
            continue
        records.append(record)

    if records:
        warnings = (
            (
                "route {0} answered 200 with {1} row(s) naming no article day: they"
                " are not rows this adapter can identify".format(
                    DESCRIPTOR.route_id, unidentified
                ),
            )
            if unidentified
            else ()
        )
        return build_native_page(
            DESCRIPTOR,
            tuple(records),
            observed_at=response.observed_at,
            native_order=NATIVE_ORDER,
            warnings=warnings,
        )
    if items:
        return _drifted(
            response,
            "listed {0} entry(s) under {1} and not one of them is a pageview"
            " row".format(len(items), ITEMS_KEY),
        )
    return build_native_page(
        DESCRIPTOR,
        (),
        observed_at=response.observed_at,
        native_order=NATIVE_ORDER,
        outcome="empty",
        warnings=(
            "route {0} answered 200 with an empty {1} list: no pageviews are"
            " reported for this range".format(DESCRIPTOR.route_id, ITEMS_KEY),
        ),
    )


def fetch_native_page(carrier: transport.Transport, request: AdapterRequest) -> NativePage:
    """Read one article's daily pageviews over one window and return one NativePage.

    The window is spent before any call is made, not after: an article this
    module cannot name, or a window with no ``window_start``, is refused here
    with no call to the origin — the same shape ``open_page`` refuses an
    address its policy will not read in. A ``window_start`` with no
    ``window_end`` spends :data:`FAR_FUTURE_END` rather than refusing, because
    the origin was measured accepting it and answering through the latest day
    it holds.
    """

    target = request.target_ids[0] if request.target_ids else request.query
    project, article = target_grammar(target)
    if not article:
        return build_native_page(
            DESCRIPTOR,
            (),
            native_order=NATIVE_ORDER,
            warnings=(
                "route {0} names no article to read: {1!r} is not '<article>' or"
                " '<project>:<article>'".format(DESCRIPTOR.route_id, target),
            ),
            outcome="refused",
            loss=(UNSELECTED_TARGET,),
        )

    start = path_date(request.window_start)
    if not start:
        return build_native_page(
            DESCRIPTOR,
            (),
            native_order=NATIVE_ORDER,
            warnings=(
                "route {0} serves only a dated range: a read naming no readable"
                " window_start names no days to read".format(DESCRIPTOR.route_id),
            ),
            outcome="refused",
            loss=(UNSELECTED_TARGET,),
        )
    end = path_date(request.window_end) if request.window_end else FAR_FUTURE_END

    params = {
        PROJECT_PARAM: project,
        ACCESS_PARAM: ACCESS,
        AGENT_PARAM: AGENT,
        ARTICLE_PARAM: article,
        GRANULARITY_PARAM: GRANULARITY,
        START_PARAM: start,
        END_PARAM: end,
    }

    return fetch_one_page(
        DESCRIPTOR, carrier, params=params, parse=_page_from, native_order=NATIVE_ORDER
    )
