"""K0 prediction markets over three origins: Polymarket, Kalshi and Manifold.

Measured 2026-08-17 (prediction markets), all three keyless and all 200:
``gamma-api.polymarket.com/public-search?q=SpaceX`` answered five events a
page, each carrying its own ``markets`` list, under a ``pagination`` block
stating ``hasMore``; a query nothing matched answered ``{"pagination":
{"hasMore": false, "totalResults": 0}}`` with no ``events`` key at all, and so
did the page past the last one. ``events?closed=false&order=volume24hr`` and
``markets?closed=false&order=volume24hr`` answered bare JSON lists, and
``events?slug=`` answered a one-event list or ``[]``.
``api.elections.kalshi.com/trade-api/v2/markets?status=open`` answered
``{"cursor", "markets"}`` where every price and volume is a decimal string
(``yes_bid_dollars``, ``volume_fp``, ``open_interest_fp``) and the integer
``volume`` and ``open_interest`` of the older shape are gone; ``cursor`` is
Kalshi's own next-page token and is empty on the last page, which is also how
``markets?tickers=`` and ``series_ticker=ZZZ`` answered nothing:
``{"cursor": "", "markets": []}``. ``events?status=open&with_nested_markets=
true`` answered ``{"cursor", "events", "milestones"}``. Kalshi has no search
endpoint. ``api.manifold.markets/v0/search-markets?term=`` answered a bare
list of markets carrying ``probability`` (a float, and absent on
multi-outcome markets), ``uniqueBettorCount`` (an int) and epoch-millisecond
``createdTime``; a term nothing matched answered ``[]``, and ``offset=`` pages.

**Three origins, three routes, one call each.** This module holds one
descriptor per origin and spends exactly one of them per call. A market's
prices are its whole substance and every one of them is a float or a decimal
string, so nothing here is a count except what an origin publishes as one:
Polymarket's ``commentCount`` on an event and Manifold's ``uniqueBettorCount``
on a market. Every price, volume and probability travels in ``attributes`` as
the exact text the origin gave it, under the origin's own name, and never
parsed into a number.

**An absence is not a shape change, and a Polymarket absence has no
container.** Polymarket's public search answers a query nothing matched with
the pagination block alone — the ``events`` key is not there. That is the
origin saying there is nothing, so it is `empty`, and it is told apart from
``schema_drift`` by the pagination block that is still there: a body carrying
neither is a payload this module no longer reads. Kalshi and Manifold answer
an absence with an empty container, the ordinary way.

**Every operation is named.** One adapter reads three origins and eight
endpoints, so a caller names the one it means with a prefix; a bare query is
a Polymarket search and a bare target is a Polymarket event read by slug,
because those are the two the evidence measured first and the two a reader
most often means. Nothing is inferred from the characters in an argument.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .. import transport
from . import (
    AdapterDescriptor,
    AdapterRequest,
    NativePage,
    NativeRecord,
    build_native_page,
    fetch_one_page,
)
from ._support.prediction_markets_config import (
    ACTIVE_KEY, ARGUMENT_OPTIONAL_OPERATIONS, BEST_ASK_KEY, BEST_BID_KEY,
    CATEGORY_KEY, CLOSED_KEY, CLOSE_TIME_KEY, CLOSE_TIME_MS_KEY,
    COMMENT_COUNT_METRIC, CREATED_AT_KEY, CREATED_TIME_KEY, CREATOR_USERNAME_KEY,
    CURSOR_PARAM, DESCRIPTION_KEY, DESCRIPTOR, END_DATE_KEY,
    EVENT_ID_ATTRIBUTE, EVENT_KIND, EVENT_SLUG_ATTRIBUTE, EVENT_TICKER_KEY,
    EVENT_TITLE_ATTRIBUTE, EVENTS_KEY, FIELD_OMITTED, FIRST_SEARCH_PAGE,
    HAS_MORE_KEY, HTTP_STATUS, ID_KEY, IS_RESOLVED_KEY,
    KALSHI_CURSOR_KEY, KALSHI_DESCRIPTOR, KALSHI_EVENTS_LIMIT,
    KALSHI_EVENTS_OPERATION, KALSHI_EVENT_ATTRIBUTES, KALSHI_EVENT_ROW_KEYS,
    KALSHI_LIST_PARAMS, KALSHI_MARKETS_LIMIT, KALSHI_MARKETS_OPERATION,
    KALSHI_MARKET_ATTRIBUTES, KALSHI_MARKET_OPERATION, KALSHI_MARKET_PATH,
    KALSHI_MARKET_ROW_KEYS, KALSHI_NESTED_MARKETS_PARAM, KALSHI_SITE_ORIGIN,
    LAST_PRICE_KEY, LAST_TRADE_PRICE_KEY, LIMIT_PARAM, LIQUIDITY_KEY,
    MALFORMED_JSON, MANIFOLD_DESCRIPTOR, MANIFOLD_LIMIT,
    MANIFOLD_MARKET_ATTRIBUTES, MANIFOLD_MARKET_ROW_KEYS,
    MANIFOLD_SEARCH_OPERATION, MARKET_KIND, MARKET_OPERATIONS, MARKETS_KEY,
    MILLISECONDS_PER_SECOND, NATIVE_ORDERS, OFFSET_PARAM, ONE_DAY_PRICE_CHANGE_KEY,
    ONE_WEEK_PRICE_CHANGE_KEY, OPEN_INTEREST_FP_KEY, OPEN_TIME_KEY,
    OPERATION_SURFACES, OUTCOMES_KEY, OUTCOME_PRICES_KEY, OUTCOME_TYPE_KEY,
    PAGE_PARAM, PAGINATION_KEY, POLYMARKET_EVENTS_LIMIT,
    POLYMARKET_EVENTS_OPERATION, POLYMARKET_EVENT_ATTRIBUTES,
    POLYMARKET_EVENT_OPERATION, POLYMARKET_EVENT_PATH, POLYMARKET_EVENT_ROW_KEYS,
    POLYMARKET_LIST_PARAMS, POLYMARKET_MARKETS_LIMIT,
    POLYMARKET_MARKETS_OPERATION, POLYMARKET_MARKET_ATTRIBUTES,
    POLYMARKET_MARKET_PATH, POLYMARKET_MARKET_ROW_KEYS,
    POLYMARKET_SEARCH_OPERATION, POLYMARKET_SITE_ORIGIN, PROBABILITY_KEY,
    QUERY_PARAM, QUESTION_KEY, RECORD_INSTANT_FORMAT, ROUTE_INSTANT_FORMAT,
    RULES_PRIMARY_KEY, RULES_PRIMARY_LIMIT, SCHEMA_DRIFT, SERIES_TICKER_KEY,
    SLUG_KEY, SLUG_PARAM, STATUS_KEY, SUB_TITLE_KEY, SURFACE_DESCRIPTORS,
    TAG_SLUG_PARAM, TERM_PARAM, TICKERS_PARAM, TICKER_KEY, TITLE_KEY,
    TOTAL_LIQUIDITY_KEY, UNIQUE_BETTOR_COUNT_METRIC, URL_KEY, VOLUME_24HR_KEY,
    VOLUME_24H_FP_KEY, VOLUME_FP_KEY, VOLUME_KEY, VOLUME_NUM_KEY,
    YES_ASK_KEY, YES_BID_KEY, YES_SUB_TITLE_KEY,
)
from ._support.prediction_markets_records import (
    RECORD_BUILDERS, _attributes, _engagement, _kalshi_event_record,
    _kalshi_event_records, _kalshi_market_record, _kalshi_market_records,
    _manifold_market_record, _manifold_market_records, _missing,
    _polymarket_event_record, _polymarket_event_records,
    _polymarket_market_record, _polymarket_market_records, _text,
    epoch_ms_to_utc_iso, exact_count, id_text, kalshi_locator,
    polymarket_event_locator, polymarket_market_locator, route_instant_to_utc_iso,
    scalar_text,
)

def _answered(
    descriptor: AdapterDescriptor,
    response: transport.TransportResponse,
    native_order: str,
    records: Tuple[NativeRecord, ...] = (),
    outcome: str = "ok",
    cursor_out: str = "",
    warnings: Tuple[str, ...] = (),
    loss: Tuple[str, ...] = (),
) -> NativePage:
    return build_native_page(
        descriptor,
        records,
        observed_at=response.observed_at,
        cursor_out=cursor_out,
        native_order=native_order,
        warnings=warnings,
        outcome=outcome,
        loss=loss,
    )


def _failed(
    descriptor: AdapterDescriptor,
    response: transport.TransportResponse,
    native_order: str,
    loss: str,
    warning: str,
) -> NativePage:
    return _answered(
        descriptor, response, native_order, outcome="failed", warnings=(warning,), loss=(loss,)
    )


def _payload_of(
    descriptor: AdapterDescriptor,
    response: transport.TransportResponse,
    native_order: str,
    operation: str,
) -> Tuple[Any, Optional[NativePage]]:
    """One answer's json, or the typed page that says why there is none."""

    if response.status != 200:
        return (
            None,
            _failed(
                descriptor,
                response,
                native_order,
                HTTP_STATUS,
                "http status {0} from {1}".format(response.status, descriptor.route_id),
            ),
        )
    try:
        return (json.loads(response.body), None)
    except ValueError:
        return (
            None,
            _failed(
                descriptor,
                response,
                native_order,
                MALFORMED_JSON,
                "{0} answered 200 with no json body".format(operation),
            ),
        )


def _rows_of(payload: Any, operation: str) -> Optional[Sequence[Any]]:
    """The rows this answer carries, or None when its container is not there.

    Four shapes across eight operations, each read where the endpoint puts it
    rather than found by looking for something list-shaped. Polymarket's
    search is the one that answers an absence with no container: the events
    are under ``events`` when there are any, and the ``pagination`` block is
    there either way, so a body with the block and no events is a query that
    matched nothing and a body with neither is a payload that moved.
    """

    if operation == POLYMARKET_SEARCH_OPERATION:
        if not isinstance(payload, Mapping):
            return None
        events = payload.get(EVENTS_KEY)
        if isinstance(events, list):
            return events
        if events is None and isinstance(payload.get(PAGINATION_KEY), Mapping):
            return ()
        return None
    if operation in (KALSHI_MARKETS_OPERATION, KALSHI_MARKET_OPERATION):
        markets = payload.get(MARKETS_KEY) if isinstance(payload, Mapping) else None
        return markets if isinstance(markets, list) else None
    if operation == KALSHI_EVENTS_OPERATION:
        events = payload.get(EVENTS_KEY) if isinstance(payload, Mapping) else None
        return events if isinstance(events, list) else None
    return payload if isinstance(payload, list) else None


def search_page_number(cursor: str) -> int:
    """The page a Polymarket search call asks for: the cursor's, else the first."""

    return int(cursor) if cursor.isdigit() else FIRST_SEARCH_PAGE


def next_search_page(payload: Any, cursor: str) -> str:
    """The page after this one, when Polymarket says there is one.

    ``hasMore`` is the origin's own statement that more exists. The number is
    the one after the page this call asked for, because the origin states
    which page it wants next only by taking a page number; nothing is derived
    from a row count.
    """

    if not isinstance(payload, Mapping):
        return ""
    pagination = payload.get(PAGINATION_KEY)
    if not isinstance(pagination, Mapping) or pagination.get(HAS_MORE_KEY) is not True:
        return ""
    return str(search_page_number(cursor) + 1)


def kalshi_cursor(payload: Any) -> str:
    """Kalshi's own next-page token, which it leaves empty on the last page."""

    token = payload.get(KALSHI_CURSOR_KEY) if isinstance(payload, Mapping) else None
    return token if isinstance(token, str) else ""


def next_cursor(payload: Any, operation: str, cursor: str) -> str:
    """The token the core spends for the next page, on the two surfaces that state one.

    Polymarket's search states ``hasMore`` and Kalshi states a ``cursor``.
    The Polymarket lists and Manifold take an ``offset`` and state nothing
    about whether more exists, so nothing is surfaced for them: deriving a
    next offset from the number of rows returned would make this adapter the
    thing that decides there is more. A caller that wants the next page of
    one of those says so.
    """

    if operation == POLYMARKET_SEARCH_OPERATION:
        return next_search_page(payload, cursor)
    if operation in (KALSHI_MARKETS_OPERATION, KALSHI_EVENTS_OPERATION):
        return kalshi_cursor(payload)
    return ""


def _page_from(
    response: transport.TransportResponse, operation: str, argument: str, cursor: str
) -> NativePage:
    """Turn one response the origin itself sent into exactly one page."""

    descriptor, endpoint = OPERATION_SURFACES[operation]
    native_order = NATIVE_ORDERS[operation]
    payload, refused = _payload_of(descriptor, response, native_order, operation)
    if refused is not None:
        return refused

    rows = _rows_of(payload, operation)
    if rows is None:
        return _failed(
            descriptor,
            response,
            native_order,
            SCHEMA_DRIFT,
            "{0} answered 200 with a body this adapter cannot read as {1} rows: the"
            " payload has changed shape".format(operation, endpoint or operation),
        )

    records, unidentified_rows, unidentified_nested = RECORD_BUILDERS[operation](rows)
    warnings: List[str] = []
    if unidentified_nested:
        warnings.append(
            "{0} answered 200 with {1} nested market(s) naming no id: they are not"
            " rows this adapter can identify".format(operation, unidentified_nested)
        )
    if records:
        if unidentified_rows:
            warnings.append(
                "{0} answered 200 with {1} row(s) naming no id: they are not rows"
                " this adapter can identify".format(operation, unidentified_rows)
            )
        return _answered(
            descriptor,
            response,
            native_order,
            records=tuple(records),
            cursor_out=next_cursor(payload, operation, cursor),
            warnings=tuple(warnings),
        )
    if rows:
        # The container is present and holds rows, and not one of them names
        # an id. That is the payload reshaping, not an answer with nothing in
        # it: reporting it as "this query has none" is the one thing a caller
        # cannot tell from a real absence.
        return _failed(
            descriptor,
            response,
            native_order,
            SCHEMA_DRIFT,
            "{0} answered 200 with {1} row(s) and no id on any of them: the payload"
            " has changed shape".format(operation, len(rows)),
        )
    warnings.append(
        "{0} answered 200 with nothing under {1}: this query or scope has"
        " none".format(operation, argument or operation)
    )
    return _answered(
        descriptor,
        response,
        native_order,
        outcome="empty",
        cursor_out=next_cursor(payload, operation, cursor),
        warnings=tuple(warnings),
    )


def operation_for(request: AdapterRequest) -> Tuple[str, str]:
    """The operation this call performs, and the argument it performs it on.

    A caller names the operation, because one adapter serves three origins.
    Absent a name, the step's own shape decides: a step naming a target reads
    that Polymarket event by slug, and a step naming only a query searches
    Polymarket. A query spelling exactly the name of an operation that takes
    no argument is that operation, colon or no colon. Nothing is inferred from
    the characters in an argument, so a query that happens to contain a colon
    stays a query.
    """

    named = request.target_ids[0] if request.target_ids else request.query
    kind, separator, argument = named.partition(":")
    if separator and kind in MARKET_OPERATIONS:
        return (kind, argument)
    if not separator and named in ARGUMENT_OPTIONAL_OPERATIONS:
        return (named, "")
    return (
        POLYMARKET_EVENT_OPERATION if request.target_ids else POLYMARKET_SEARCH_OPERATION,
        named,
    )


def operation_params(operation: str, argument: str, cursor: str) -> Dict[str, str]:
    """The parameters one operation sends, in the origin's own names.

    The endpoint is the route's path segment where the route declares one,
    the argument goes under the name the origin gives it, and a cursor the
    core froze goes back under the origin's own paging name: a page number to
    Polymarket's search, an offset to its lists and to Manifold, and Kalshi's
    own token to Kalshi.
    """

    _, endpoint = OPERATION_SURFACES[operation]
    params: Dict[str, str] = {}
    if endpoint:
        params["endpoint"] = endpoint
    if operation == POLYMARKET_SEARCH_OPERATION:
        params[QUERY_PARAM] = argument
        if cursor:
            params[PAGE_PARAM] = cursor
    elif operation == POLYMARKET_EVENTS_OPERATION:
        params.update(POLYMARKET_LIST_PARAMS)
        params[LIMIT_PARAM] = POLYMARKET_EVENTS_LIMIT
        if argument:
            params[TAG_SLUG_PARAM] = argument
        if cursor:
            params[OFFSET_PARAM] = cursor
    elif operation == POLYMARKET_EVENT_OPERATION:
        params[SLUG_PARAM] = argument
    elif operation == POLYMARKET_MARKETS_OPERATION:
        params.update(POLYMARKET_LIST_PARAMS)
        params[LIMIT_PARAM] = POLYMARKET_MARKETS_LIMIT
        if cursor:
            params[OFFSET_PARAM] = cursor
    elif operation == KALSHI_MARKETS_OPERATION:
        params.update(KALSHI_LIST_PARAMS)
        params[LIMIT_PARAM] = KALSHI_MARKETS_LIMIT
        if argument:
            params[SERIES_TICKER_PARAM] = argument
        if cursor:
            params[CURSOR_PARAM] = cursor
    elif operation == KALSHI_MARKET_OPERATION:
        params[TICKERS_PARAM] = argument
    elif operation == KALSHI_EVENTS_OPERATION:
        params.update(KALSHI_LIST_PARAMS)
        params.update((KALSHI_NESTED_MARKETS_PARAM,))
        params[LIMIT_PARAM] = KALSHI_EVENTS_LIMIT
        if argument:
            params[SERIES_TICKER_PARAM] = argument
        if cursor:
            params[CURSOR_PARAM] = cursor
    else:
        params[TERM_PARAM] = argument
        params[LIMIT_PARAM] = MANIFOLD_LIMIT
        if cursor:
            params[OFFSET_PARAM] = cursor
    return params


def fetch_native_page(carrier: transport.Transport, request: AdapterRequest) -> NativePage:
    """Read one of the eight declared operations and return exactly one NativePage.

    One call on one route. Which route is the operation's own, declared in
    ``OPERATION_SURFACES``, and the three are paced apart because they are
    three origins. No window parameter is sent: none of the three takes a
    bound on the time a market was created in terms this module could state
    without inventing one, so the core's own filter is the whole window.
    """

    operation, argument = operation_for(request)
    descriptor, _ = OPERATION_SURFACES[operation]

    def parse(response: transport.TransportResponse) -> NativePage:
        return _page_from(response, operation, argument, request.cursor)

    return fetch_one_page(
        descriptor,
        carrier,
        params=operation_params(operation, argument, request.cursor),
        parse=parse,
        native_order=NATIVE_ORDERS[operation],
    )
