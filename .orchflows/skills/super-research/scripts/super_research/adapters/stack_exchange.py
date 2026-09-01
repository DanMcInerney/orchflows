"""K0 Stack Exchange search/advanced with unix-second window bounds.

Measured 2026-09-01, keyless and 200: ``GET api.stackexchange.com``
``/2.3/search/advanced?site=stackoverflow&q=python&pagesize=30&order=desc``
``&sort=creation`` answered ``{"items": [...], "has_more": true,``
``"quota_max": 300, "quota_remaining": 293}``, the anonymous daily quota this
answer itself reports. Each item carried ``question_id``, ``title`` (HTML
entity-escaped — ``Can&#39;t get virtual environment...`` was one of them),
``owner.display_name``, ``creation_date`` (unix seconds), ``score``,
``answer_count``, ``view_count``, ``is_answered``, ``link`` and ``tags``.
``fromdate``/``todate`` (unix seconds) genuinely filtered: every
``creation_date`` on a bounded read fell inside the sent range. Reading a
second page with ``page=2`` returned thirty different question ids with its
own ``has_more``, and a query nothing matches answered 200 with
``{"items": [], "has_more": false, ...}`` rather than an error. Via this
package's own opener (no ``Accept-Encoding`` sent) the answer still arrived
gzip-compressed — unlike most K0 routes in this roster — and
``transport.decoded_body`` already honors the stated ``Content-Encoding``
either way, so nothing here adds a header.

**One operation, one deterministic shape.** The whole query is ``q`` against
``site`` ``stackoverflow`` (:data:`DEFAULT_SITE`) unless the caller's argument
opens with the token ``site:<name> `` (measured live against
``site=serverfault``), in which case that name is the site and the remainder
is ``q``. Every call sorts ``creation`` descending rather than by relevance:
relevance is not a native metric this roster can snapshot and re-derive, and a
windowed read on creation order spends the origin's own recency ordering
inside the window the caller asked for, where ``fromdate``/``todate`` narrow
what the origin itself returns rather than what this adapter discards
afterward.

**Paging is the origin's own page number, never a cursor this module
invents.** The origin states only whether another page exists
(``has_more``), not which page answered, so the page just sent is read back
off the call that made it: an unset ``request.cursor`` means page one, and
the next page offered is one more than that. The core spends
``cursor_out`` as the next call's own ``cursor``, so this module never walks
its own pages.

**A title is unescaped because the route documents it escaped.** Stack
Exchange spells the entities it makes for HTML embedding, and reading them
back out — the same move ``rss_atom`` makes on its own feed text — is
reading the route's stated encoding, not inventing a transform on top of it.

**Every count is a native integer or it is absent.** ``score``,
``answer_count`` and ``view_count`` are omitted rather than zeroed when the
payload does not carry them as an exact int; a bool is never a count. A
downvoted question's negative ``score`` (measured on this same page: several
items answered with ``-3`` through ``-10``) is also omitted — the artifact's
engagement family admits only non-negative exact integers, so a negative
score is a count this adapter cannot report rather than one reported past
the ladder that would receive it unsigned.
``is_answered`` rides as an attribute, its two JSON spellings ``"true"``
and ``"false"`` carried exactly rather than folded into engagement, because
it answers a question and reports no count.

**Deferred:** hydrating a question's own answers (``/2.3/questions/{id}/``
``answers``) is not shipped — this route only ever discovers questions —
and reopens if a caller needs answer bodies rather than the ``answer_count``
this search already states.
"""

from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from typing import Any, List, Mapping, Optional, Tuple

from .. import transport
from . import (
    AdapterDescriptor,
    AdapterRequest,
    NativePage,
    NativeRecord,
    build_native_page,
    fetch_one_page,
)

DESCRIPTOR = AdapterDescriptor(
    adapter_id="stack_exchange",
    adapter_version="1",
    access_class="K0",
    route_id=transport.STACKEXCHANGE_SEARCH_ROUTE,
    platform="stackexchange",
    native_identity_namespace="stackexchange",
    representation_kind="native",
    operator_identity="stackexchange",
    min_interval_ms=1000,
    burst=1,
    reply_count_metric="answer_count",
    page_size=30,
)

SURFACE_DESCRIPTORS = (DESCRIPTOR,)

# The one operation this adapter performs, named for the messages it prints.
SEARCH_OPERATION = "search_advanced"
NATIVE_ORDER = "stackexchange_search_creation_order"

# `q` means "search this site" unless the caller's argument names another.
DEFAULT_SITE = "stackoverflow"
SITE_PREFIX = "site:"

SITE_PARAM = "site"
QUERY_PARAM = "q"
PAGESIZE_PARAM = "pagesize"
PAGESIZE_VALUE = "30"
ORDER_PARAM = "order"
ORDER_VALUE = "desc"
SORT_PARAM = "sort"
SORT_VALUE = "creation"
PAGE_PARAM = "page"
FROMDATE_PARAM = "fromdate"
TODATE_PARAM = "todate"

QUESTION_KIND = "question"
ITEMS_KEY = "items"
HAS_MORE_KEY = "has_more"
QUESTION_ID_KEY = "question_id"
TITLE_KEY = "title"
OWNER_KEY = "owner"
DISPLAY_NAME_KEY = "display_name"
LINK_KEY = "link"
CREATION_DATE_KEY = "creation_date"
SCORE_KEY = "score"
ANSWER_COUNT_KEY = "answer_count"
VIEW_COUNT_KEY = "view_count"
IS_ANSWERED_KEY = "is_answered"
TAGS_KEY = "tags"

TAG_ATTRIBUTE = "tag"
IS_ANSWERED_ATTRIBUTE = "is_answered"
TRUE_SPELLING = "true"
FALSE_SPELLING = "false"

RECORD_INSTANT_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

SCHEMA_DRIFT = "schema_drift"
MALFORMED_JSON = "malformed_json"
HTTP_STATUS = "http_status"


def _text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def exact_count(value: Any) -> Optional[int]:
    """One count Stack Exchange published as an exact number, or nothing at all.

    A bool is not a count: every count this route publishes rides as a json
    number, so anything else is a field this adapter was not given rather
    than one it can recover. ``score`` is the one field here that is
    genuinely negative on the wire — a downvoted question — and the artifact
    contract's engagement family admits only non-negative exact integers
    (`normalize.engagement_snapshots` raises rather than carry one), so a
    negative score is a count this adapter cannot report rather than one it
    reports as though it were unsigned.
    """

    if isinstance(value, bool) or not isinstance(value, int):
        return None
    if value < 0:
        return None
    return value


def id_text(value: Any) -> str:
    """One question id as its decimal spelling, or nothing without one."""

    if isinstance(value, bool):
        return ""
    if isinstance(value, int):
        return str(value)
    return ""


def epoch_to_utc_iso(seconds: Any) -> str:
    """The origin's unix-second stamp as the artifact's instant, or nothing.

    A value that is not a whole number of seconds, or that no clock can
    represent, is a missing time rather than an approximated one.
    """

    if isinstance(seconds, bool) or not isinstance(seconds, int):
        return ""
    try:
        moment = datetime.fromtimestamp(seconds, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return ""
    return moment.strftime(RECORD_INSTANT_FORMAT)


def instant_to_epoch_text(instant: str) -> str:
    """One manifest instant as the unix seconds the origin filters on, or nothing.

    A bound this function cannot read is a bound not sent — the core's own
    window filter still holds on every row that comes back — rather than a
    bound sent wrong, which would narrow the origin's answer to a range
    nobody asked for.
    """

    if not instant:
        return ""
    try:
        moment = datetime.strptime(instant, RECORD_INSTANT_FORMAT)
    except ValueError:
        return ""
    return str(int(moment.replace(tzinfo=timezone.utc).timestamp()))


def _engagement(pairs: Tuple[Tuple[str, Any], ...]) -> Tuple[Tuple[str, int], ...]:
    counted = []
    for name, value in pairs:
        exact = exact_count(value)
        if exact is not None:
            counted.append((name, exact))
    return tuple(counted)


def site_and_query(argument: str) -> Tuple[str, str]:
    """This call's site and its ``q``, parsed off the caller's own grammar.

    A query beginning with the token ``site:<name> `` selects that site and
    the remainder is ``q``; anything else means :data:`DEFAULT_SITE` and the
    whole argument is the query, unchanged. Neither is inferred from the
    characters in the argument — a bare ``site:`` with no name and no space
    is not a selection, and is read as an ordinary query.
    """

    prefix_token, separator, remainder = argument.partition(" ")
    if separator and prefix_token.startswith(SITE_PREFIX):
        site = prefix_token[len(SITE_PREFIX):]
        if site:
            return (site, remainder)
    return (DEFAULT_SITE, argument)


def _next_page(cursor: str, has_more: bool) -> str:
    """The page after this one, as the origin's own ``has_more`` says there is.

    The origin never states which page answered, only whether another
    exists, so the page just spent is read back off the call that made it:
    an empty ``cursor`` means page one was just read, and the next page
    offered is one more than whichever page that was.
    """

    if not has_more:
        return ""
    try:
        current = int(cursor) if cursor else 1
    except ValueError:
        current = 1
    return str(current + 1)


def _question_record(position: int, item: Any) -> Optional[NativeRecord]:
    """One question as the search listed it, or nothing without a question_id."""

    if not isinstance(item, Mapping):
        return None
    question_id = id_text(item.get(QUESTION_ID_KEY))
    if not question_id:
        return None
    owner = item.get(OWNER_KEY)
    author = _text(owner.get(DISPLAY_NAME_KEY)) if isinstance(owner, Mapping) else ""
    named: List[Tuple[str, str]] = []
    tags = item.get(TAGS_KEY)
    for tag in tags if isinstance(tags, list) else ():
        if isinstance(tag, str) and tag:
            named.append((TAG_ATTRIBUTE, tag))
    is_answered = item.get(IS_ANSWERED_KEY)
    if isinstance(is_answered, bool):
        named.append(
            (IS_ANSWERED_ATTRIBUTE, TRUE_SPELLING if is_answered else FALSE_SPELLING)
        )
    return NativeRecord(
        canonical_content_kind=QUESTION_KIND,
        canonical_locator=_text(item.get(LINK_KEY)),
        native_item_id=question_id,
        title=html.unescape(_text(item.get(TITLE_KEY))),
        author=author,
        published_at=epoch_to_utc_iso(item.get(CREATION_DATE_KEY)),
        engagement=_engagement(
            (
                (SCORE_KEY, item.get(SCORE_KEY)),
                (ANSWER_COUNT_KEY, item.get(ANSWER_COUNT_KEY)),
                (VIEW_COUNT_KEY, item.get(VIEW_COUNT_KEY)),
            )
        ),
        attributes=tuple(named),
        native_position=position,
    )


def _answered(
    response: transport.TransportResponse,
    records: Tuple[NativeRecord, ...] = (),
    outcome: str = "ok",
    cursor_out: str = "",
    warnings: Tuple[str, ...] = (),
    loss: Tuple[str, ...] = (),
) -> NativePage:
    return build_native_page(
        DESCRIPTOR,
        records,
        observed_at=response.observed_at,
        cursor_out=cursor_out,
        native_order=NATIVE_ORDER,
        warnings=warnings,
        outcome=outcome,
        loss=loss,
    )


def _failed(response: transport.TransportResponse, loss: str, warning: str) -> NativePage:
    return _answered(response, outcome="failed", warnings=(warning,), loss=(loss,))


def _payload_of(
    response: transport.TransportResponse,
) -> Tuple[Any, Optional[NativePage]]:
    """One answer's json, or the typed page that says why there is none."""

    if response.status != 200:
        return (
            None,
            _failed(
                response,
                HTTP_STATUS,
                "http status {0} from {1}".format(response.status, DESCRIPTOR.route_id),
            ),
        )
    try:
        return (json.loads(response.body), None)
    except ValueError:
        return (
            None,
            _failed(
                response, MALFORMED_JSON, "{0} answered 200 with no json body".format(
                    SEARCH_OPERATION
                )
            ),
        )


def _search_page(
    response: transport.TransportResponse, payload: Any, cursor: str, site: str, query_text: str
) -> NativePage:
    items = payload.get(ITEMS_KEY) if isinstance(payload, Mapping) else None
    if not isinstance(items, list):
        return _failed(
            response,
            SCHEMA_DRIFT,
            "{0} answered 200 with no {1} list: the payload this adapter reads has"
            " changed shape".format(SEARCH_OPERATION, ITEMS_KEY),
        )

    records: List[NativeRecord] = []
    unidentified = 0
    for item in items:
        record = _question_record(len(records), item)
        if record is None:
            # A row this answer did not identify is not a row: a record
            # naming nothing groups with nothing and addresses nothing.
            unidentified += 1
            continue
        records.append(record)

    has_more = payload.get(HAS_MORE_KEY) is True
    cursor_out = _next_page(cursor, has_more)

    if records:
        warnings = (
            (
                "{0} answered 200 with {1} item(s) naming no {2}: they are not rows"
                " this adapter can identify".format(
                    SEARCH_OPERATION, unidentified, QUESTION_ID_KEY
                ),
            )
            if unidentified
            else ()
        )
        return _answered(
            response, records=tuple(records), cursor_out=cursor_out, warnings=warnings
        )
    if items:
        # Rows present and not one of them identified: the payload reshaping,
        # not a search with nothing in it.
        return _failed(
            response,
            SCHEMA_DRIFT,
            "{0} answered 200 with {1} item(s) and no {2} on any of them: the payload"
            " has changed shape".format(SEARCH_OPERATION, len(items), QUESTION_ID_KEY),
        )
    return _answered(
        response,
        outcome="empty",
        cursor_out=cursor_out,
        warnings=(
            "{0} answered 200 with an empty {1} list: nothing on site {2!r} matched"
            " {3!r}".format(SEARCH_OPERATION, ITEMS_KEY, site, query_text),
        ),
    )


def fetch_native_page(carrier: transport.Transport, request: AdapterRequest) -> NativePage:
    """Read one page of search/advanced and return exactly one NativePage.

    One call, one origin: paging is the core's, spent as the origin's own
    page number, and a window the caller carries is sent server-side as
    ``fromdate``/``todate`` rather than trimmed here after the fact.
    """

    argument = request.target_ids[0] if request.target_ids else request.query
    site, query_text = site_and_query(argument)
    cursor = request.cursor
    params = {
        SITE_PARAM: site,
        QUERY_PARAM: query_text,
        PAGESIZE_PARAM: PAGESIZE_VALUE,
        ORDER_PARAM: ORDER_VALUE,
        SORT_PARAM: SORT_VALUE,
    }
    if cursor:
        # The page the core froze, spent as the origin's own page number. No
        # next one is derived here: the origin states only that there is one.
        params[PAGE_PARAM] = cursor
    fromdate = instant_to_epoch_text(request.window_start)
    if fromdate:
        params[FROMDATE_PARAM] = fromdate
    todate = instant_to_epoch_text(request.window_end)
    if todate:
        params[TODATE_PARAM] = todate

    def parse(response: transport.TransportResponse) -> NativePage:
        payload, refused = _payload_of(response)
        return refused if refused is not None else _search_page(
            response, payload, cursor, site, query_text
        )

    return fetch_one_page(
        DESCRIPTOR, carrier, params=params, parse=parse, native_order=NATIVE_ORDER
    )
