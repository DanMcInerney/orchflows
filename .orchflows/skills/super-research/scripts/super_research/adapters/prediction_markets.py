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
from datetime import datetime, timezone
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

# Where a Polymarket event or market lives, and where a Kalshi market lives.
# Both are the platform's own site and neither is a route's origin, so
# `transport.origin_locator` cannot resolve them — it resolves against the
# route that answered, which here would name an API host. Neither payload
# publishes an item's address in any form, so it is composed from the slug or
# ticker, the way `hacker_news.HN_ITEM_ORIGIN` composes an item's address from
# its id: a host no route in this package reads is not a host the transport
# seam owns. Measured 2026-08-17: `polymarket.com/event/<event-slug>` and
# `polymarket.com/event/<event-slug>/<market-slug>` answered 200, and
# `polymarket.com/market/<market-slug>` answered 307 to the second form;
# `kalshi.com/markets/<ticker>` answered 200 (after a 308 to its lowercase
# spelling). Manifold publishes each market's `url` and it is carried as is.
POLYMARKET_SITE_ORIGIN = "https://polymarket.com"
POLYMARKET_EVENT_PATH = "/event/"
POLYMARKET_MARKET_PATH = "/market/"
KALSHI_SITE_ORIGIN = "https://kalshi.com"
KALSHI_MARKET_PATH = "/markets/"

# The three surfaces. Polymarket is this adapter's primary descriptor because
# its search is what a bare query means and its event read is what a bare
# target means.
DESCRIPTOR = AdapterDescriptor(
    adapter_id="prediction_markets",
    adapter_version="1",
    access_class="K0",
    route_id=transport.POLYMARKET_GAMMA_ROUTE,
    platform="polymarket",
    native_identity_namespace="polymarket",
    representation_kind="native",
    operator_identity="polymarket",
    # The 2026-08-17 probes saw no throttle on any of the three; a ceiling
    # nobody measured is not one to spend, so one read a second with a burst
    # of three is declared for all three rather than a figure invented per
    # origin.
    min_interval_ms=1000,
    burst=3,
    # An event states an exact count of its own comments. Nothing on this
    # route states a count of replies, and neither name is inferred.
    comment_count_metric="commentCount",
    # Five events per public-search page, as measured; every event carries
    # its markets, so a page holds more records than this. The list endpoints
    # take the `limit` this module sends, declared beside each operation.
    page_size=5,
)

KALSHI_DESCRIPTOR = AdapterDescriptor(
    adapter_id="prediction_markets",
    adapter_version="1",
    access_class="K0",
    route_id=transport.KALSHI_MARKETS_ROUTE,
    platform="kalshi",
    native_identity_namespace="kalshi",
    representation_kind="native",
    operator_identity="kalshi",
    min_interval_ms=1000,
    burst=3,
    page_size=100,
)

MANIFOLD_DESCRIPTOR = AdapterDescriptor(
    adapter_id="prediction_markets",
    adapter_version="1",
    access_class="K0",
    route_id=transport.MANIFOLD_MARKETS_ROUTE,
    platform="manifold",
    native_identity_namespace="manifold",
    representation_kind="native",
    operator_identity="manifold",
    min_interval_ms=1000,
    burst=3,
    page_size=100,
)

# Every route this adapter can reach, one descriptor each. The core collects
# route budgets from here, because a route nothing declares a budget for is a
# route the scheduler refuses to pace.
SURFACE_DESCRIPTORS = (DESCRIPTOR, KALSHI_DESCRIPTOR, MANIFOLD_DESCRIPTOR)

# The eight operations, spelled once each. A caller names one with a prefix,
# because three origins answer different questions; absent a prefix the step's
# own shape decides, and never the characters in the argument.
POLYMARKET_SEARCH_OPERATION = "polymarket"
POLYMARKET_EVENTS_OPERATION = "polymarket_events"
POLYMARKET_EVENT_OPERATION = "polymarket_event"
POLYMARKET_MARKETS_OPERATION = "polymarket_markets"
KALSHI_MARKETS_OPERATION = "kalshi"
KALSHI_MARKET_OPERATION = "kalshi_market"
KALSHI_EVENTS_OPERATION = "kalshi_events"
MANIFOLD_SEARCH_OPERATION = "manifold"
MARKET_OPERATIONS = (
    POLYMARKET_SEARCH_OPERATION,
    POLYMARKET_EVENTS_OPERATION,
    POLYMARKET_EVENT_OPERATION,
    POLYMARKET_MARKETS_OPERATION,
    KALSHI_MARKETS_OPERATION,
    KALSHI_MARKET_OPERATION,
    KALSHI_EVENTS_OPERATION,
    MANIFOLD_SEARCH_OPERATION,
)

# The operations that take no argument, so a query spelling exactly one of
# their names — with or without the colon — is that operation. A caller who
# wants Polymarket searched for the word `kalshi` writes `polymarket:kalshi`.
# The two Kalshi lists and the Polymarket event list also take an optional
# scope after the colon: a `series_ticker` and a `tag_slug` respectively.
ARGUMENT_OPTIONAL_OPERATIONS = (
    POLYMARKET_EVENTS_OPERATION,
    POLYMARKET_MARKETS_OPERATION,
    KALSHI_MARKETS_OPERATION,
    KALSHI_EVENTS_OPERATION,
)

# Every read this module can perform: which route it goes to, and which
# endpoint it names on that route. This table is the reachable operation set —
# nothing else in this file reaches the carrier, and no endpoint here is
# composed from a caller's argument.
OPERATION_SURFACES = {
    POLYMARKET_SEARCH_OPERATION: (DESCRIPTOR, "public-search"),
    POLYMARKET_EVENTS_OPERATION: (DESCRIPTOR, "events"),
    POLYMARKET_EVENT_OPERATION: (DESCRIPTOR, "events"),
    POLYMARKET_MARKETS_OPERATION: (DESCRIPTOR, "markets"),
    KALSHI_MARKETS_OPERATION: (KALSHI_DESCRIPTOR, "markets"),
    KALSHI_MARKET_OPERATION: (KALSHI_DESCRIPTOR, "markets"),
    KALSHI_EVENTS_OPERATION: (KALSHI_DESCRIPTOR, "events"),
    MANIFOLD_SEARCH_OPERATION: (MANIFOLD_DESCRIPTOR, ""),
}

NATIVE_ORDERS = {
    POLYMARKET_SEARCH_OPERATION: "polymarket_search_relevance_order",
    POLYMARKET_EVENTS_OPERATION: "polymarket_volume24hr_order",
    POLYMARKET_EVENT_OPERATION: "polymarket_event_order",
    POLYMARKET_MARKETS_OPERATION: "polymarket_volume24hr_order",
    KALSHI_MARKETS_OPERATION: "kalshi_market_list_order",
    KALSHI_MARKET_OPERATION: "kalshi_market_list_order",
    KALSHI_EVENTS_OPERATION: "kalshi_event_list_order",
    MANIFOLD_SEARCH_OPERATION: "manifold_search_relevance_order",
}

# The parameters each list operation sends beside the caller's argument, in
# the origin's own names. `limit` is sent explicitly on every list so the page
# a call reads is a stated size and never the origin's default of the day; the
# Polymarket lists are bounded lower than the origin allows because an event
# carries every market under it, and the largest measured today was 41 markets
# and 150 KB. Kalshi's event list is bounded lowest for the same reason: an
# hourly price-range series answered two events in 513 KB.
POLYMARKET_LIST_PARAMS = (("closed", "false"), ("order", "volume24hr"), ("ascending", "false"))
POLYMARKET_EVENTS_LIMIT = "20"
POLYMARKET_MARKETS_LIMIT = "50"
KALSHI_LIST_PARAMS = (("status", "open"),)
KALSHI_MARKETS_LIMIT = "100"
KALSHI_EVENTS_LIMIT = "10"
KALSHI_NESTED_MARKETS_PARAM = ("with_nested_markets", "true")
MANIFOLD_LIMIT = "100"

# The names each origin gives the things this module sends it: the question,
# the scope, the page.
QUERY_PARAM = "q"
TERM_PARAM = "term"
SLUG_PARAM = "slug"
TAG_SLUG_PARAM = "tag_slug"
SERIES_TICKER_PARAM = "series_ticker"
TICKERS_PARAM = "tickers"
LIMIT_PARAM = "limit"
PAGE_PARAM = "page"
OFFSET_PARAM = "offset"
CURSOR_PARAM = "cursor"

# The kinds of record this module emits.
MARKET_KIND = "market"
EVENT_KIND = "event"

# Where each answer keeps what it returned. Declared, never searched for: the
# whole value of a typed drift is that it says the payload moved rather than
# that a market went quiet.
EVENTS_KEY = "events"
PAGINATION_KEY = "pagination"
HAS_MORE_KEY = "hasMore"
MARKETS_KEY = "markets"
KALSHI_CURSOR_KEY = "cursor"

# Every other key these payloads publish that this module reads, under the
# origin's own names. Polymarket first.
ID_KEY = "id"
SLUG_KEY = "slug"
TITLE_KEY = "title"
QUESTION_KEY = "question"
DESCRIPTION_KEY = "description"
CREATED_AT_KEY = "createdAt"
END_DATE_KEY = "endDate"
VOLUME_KEY = "volume"
VOLUME_NUM_KEY = "volumeNum"
VOLUME_24HR_KEY = "volume24hr"
LIQUIDITY_KEY = "liquidity"
OUTCOMES_KEY = "outcomes"
OUTCOME_PRICES_KEY = "outcomePrices"
LAST_TRADE_PRICE_KEY = "lastTradePrice"
BEST_BID_KEY = "bestBid"
BEST_ASK_KEY = "bestAsk"
ONE_DAY_PRICE_CHANGE_KEY = "oneDayPriceChange"
ONE_WEEK_PRICE_CHANGE_KEY = "oneWeekPriceChange"
CLOSED_KEY = "closed"
ACTIVE_KEY = "active"
COMMENT_COUNT_METRIC = "commentCount"
# The three facts about its event a market record carries under names of this
# module's making, because a market answered inside an event names its event
# by containment and a market answered on its own names it under `events`.
EVENT_ID_ATTRIBUTE = "event_id"
EVENT_SLUG_ATTRIBUTE = "event_slug"
EVENT_TITLE_ATTRIBUTE = "event_title"

# Kalshi.
TICKER_KEY = "ticker"
EVENT_TICKER_KEY = "event_ticker"
SERIES_TICKER_KEY = "series_ticker"
SUB_TITLE_KEY = "sub_title"
YES_SUB_TITLE_KEY = "yes_sub_title"
CATEGORY_KEY = "category"
YES_BID_KEY = "yes_bid_dollars"
YES_ASK_KEY = "yes_ask_dollars"
LAST_PRICE_KEY = "last_price_dollars"
VOLUME_FP_KEY = "volume_fp"
VOLUME_24H_FP_KEY = "volume_24h_fp"
OPEN_INTEREST_FP_KEY = "open_interest_fp"
CLOSE_TIME_KEY = "close_time"
OPEN_TIME_KEY = "open_time"
STATUS_KEY = "status"
RULES_PRIMARY_KEY = "rules_primary"
# How much of a market's rules ride along. The rules are the market's own
# statement of what resolves it and run to paragraphs; the first part says
# what the market is about, which is what a record needs.
RULES_PRIMARY_LIMIT = 500

# Manifold.
URL_KEY = "url"
CREATOR_USERNAME_KEY = "creatorUsername"
CREATED_TIME_KEY = "createdTime"
CLOSE_TIME_MS_KEY = "closeTime"
PROBABILITY_KEY = "probability"
VOLUME_24_HOURS_KEY = "volume24Hours"
OUTCOME_TYPE_KEY = "outcomeType"
TOTAL_LIQUIDITY_KEY = "totalLiquidity"
IS_RESOLVED_KEY = "isResolved"
UNIQUE_BETTOR_COUNT_METRIC = "uniqueBettorCount"

# The facts each kind of row carries into `attributes`, in the order they are
# carried, each under the origin's own name and as the exact text the origin
# gave. A name absent from a row is absent from its record.
POLYMARKET_EVENT_ATTRIBUTES = (
    SLUG_KEY,
    VOLUME_KEY,
    VOLUME_24HR_KEY,
    LIQUIDITY_KEY,
    END_DATE_KEY,
    CREATED_AT_KEY,
    CLOSED_KEY,
    ACTIVE_KEY,
)
POLYMARKET_MARKET_ATTRIBUTES = (
    SLUG_KEY,
    OUTCOMES_KEY,
    OUTCOME_PRICES_KEY,
    VOLUME_KEY,
    VOLUME_NUM_KEY,
    VOLUME_24HR_KEY,
    LIQUIDITY_KEY,
    LAST_TRADE_PRICE_KEY,
    BEST_BID_KEY,
    BEST_ASK_KEY,
    ONE_DAY_PRICE_CHANGE_KEY,
    ONE_WEEK_PRICE_CHANGE_KEY,
    END_DATE_KEY,
    CREATED_AT_KEY,
    CLOSED_KEY,
    ACTIVE_KEY,
)
KALSHI_MARKET_ATTRIBUTES = (
    YES_SUB_TITLE_KEY,
    YES_BID_KEY,
    YES_ASK_KEY,
    LAST_PRICE_KEY,
    VOLUME_FP_KEY,
    VOLUME_24H_FP_KEY,
    OPEN_INTEREST_FP_KEY,
    OPEN_TIME_KEY,
    CLOSE_TIME_KEY,
    STATUS_KEY,
)
KALSHI_EVENT_ATTRIBUTES = (SERIES_TICKER_KEY, SUB_TITLE_KEY, CATEGORY_KEY)
MANIFOLD_MARKET_ATTRIBUTES = (
    SLUG_KEY,
    PROBABILITY_KEY,
    VOLUME_KEY,
    VOLUME_24_HOURS_KEY,
    TOTAL_LIQUIDITY_KEY,
    OUTCOME_TYPE_KEY,
    CLOSE_TIME_MS_KEY,
    IS_RESOLVED_KEY,
)

# What each kind of row promises, so a record short of it says so. The
# evidence records that these routes answer and what they carry, not a field
# list, so these are this adapter's own declaration. An id is absent from all
# of them: a row without one is not a row of that kind at all.
POLYMARKET_EVENT_ROW_KEYS = (ID_KEY, SLUG_KEY, TITLE_KEY, CREATED_AT_KEY)
POLYMARKET_MARKET_ROW_KEYS = (
    ID_KEY,
    SLUG_KEY,
    QUESTION_KEY,
    OUTCOMES_KEY,
    OUTCOME_PRICES_KEY,
    CREATED_AT_KEY,
)
KALSHI_MARKET_ROW_KEYS = (
    TICKER_KEY,
    EVENT_TICKER_KEY,
    TITLE_KEY,
    STATUS_KEY,
    OPEN_TIME_KEY,
    YES_BID_KEY,
    YES_ASK_KEY,
    LAST_PRICE_KEY,
    VOLUME_FP_KEY,
)
KALSHI_EVENT_ROW_KEYS = (EVENT_TICKER_KEY, TITLE_KEY, SERIES_TICKER_KEY)
MANIFOLD_MARKET_ROW_KEYS = (ID_KEY, QUESTION_KEY, URL_KEY, CREATOR_USERNAME_KEY, CREATED_TIME_KEY)

# The stamps these routes emit, and the one an artifact record holds.
# Polymarket writes an ISO instant with a fraction of varying length, Kalshi
# writes one with none, and Manifold writes epoch milliseconds.
ROUTE_INSTANT_FORMAT = "%Y-%m-%dT%H:%M:%S"
RECORD_INSTANT_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
MILLISECONDS_PER_SECOND = 1000

# The page a Polymarket search starts on when the core hands back no cursor.
# The origin counts pages from one and states no page number in its answer, so
# the next page is the one after the page this call asked for.
FIRST_SEARCH_PAGE = 1

SCHEMA_DRIFT = "schema_drift"
MALFORMED_JSON = "malformed_json"
HTTP_STATUS = "http_status"
FIELD_OMITTED = "field_omitted"


def polymarket_event_locator(event_slug: str) -> str:
    """One event's address on Polymarket's own site, or nothing without a slug."""

    return POLYMARKET_SITE_ORIGIN + POLYMARKET_EVENT_PATH + event_slug if event_slug else ""


def polymarket_market_locator(event_slug: str, market_slug: str) -> str:
    """One market's address on Polymarket's own site, or nothing without a slug.

    The site addresses a market under its event, so a market whose event is
    known gets that address; one answered without an event gets the site's
    own redirecting form, which lands on the same page.
    """

    if not market_slug:
        return ""
    if event_slug:
        return POLYMARKET_SITE_ORIGIN + POLYMARKET_EVENT_PATH + event_slug + "/" + market_slug
    return POLYMARKET_SITE_ORIGIN + POLYMARKET_MARKET_PATH + market_slug


def kalshi_locator(ticker: str) -> str:
    """One market's or event's address on Kalshi's own site, or nothing without a ticker."""

    return KALSHI_SITE_ORIGIN + KALSHI_MARKET_PATH + ticker if ticker else ""


def _text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def exact_count(value: Any) -> Optional[int]:
    """One count an origin published as an exact number, or nothing at all.

    A bool is not a count and a float is not one either: a price, a volume
    and a probability are all floats on these routes, and none of them is an
    engagement figure. Only a json integer is.
    """

    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def id_text(value: Any) -> str:
    """One identifier as its text, which is the only form a record holds.

    Polymarket publishes ids as strings, Kalshi publishes tickers, and
    Manifold publishes ids as strings; a number here would be an origin that
    changed its mind, and its decimal digits are still the identifier.
    """

    if isinstance(value, bool):
        return ""
    if isinstance(value, int):
        return str(value)
    return value if isinstance(value, str) else ""


def scalar_text(value: Any) -> str:
    """One payload scalar as the exact text a record carries, or nothing.

    A string travels verbatim — Polymarket's ``outcomePrices`` is a JSON list
    spelled inside a JSON string, and it stays that string. A number is spelled
    as its own decimal text, which for a json number is what the origin wrote.
    A bool is spelled the way json spells one. Nothing here is rounded,
    parsed, or compared: a price is a fact the origin stated and this module
    carries it.
    """

    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return ""


def route_instant_to_utc_iso(stamped: Any) -> str:
    """Polymarket's or Kalshi's stamp as the artifact's instant, or nothing.

    A trailing ``Z`` and an optional fraction are the shapes these origins
    write. The fraction is dropped rather than rounded, so nothing is stated
    that the origin did not; anything else is a missing time rather than an
    approximated one.
    """

    if not isinstance(stamped, str) or not stamped.strip():
        return ""
    text = stamped.strip()
    if text.endswith("Z"):
        text = text[:-1]
    text = text.split(".")[0]
    try:
        moment = datetime.strptime(text, ROUTE_INSTANT_FORMAT)
    except ValueError:
        return ""
    return moment.replace(tzinfo=timezone.utc).strftime(RECORD_INSTANT_FORMAT)


def epoch_ms_to_utc_iso(milliseconds: Any) -> str:
    """Manifold's stamp as the artifact's instant, or nothing.

    Epoch milliseconds are an exact instant; the artifact holds whole seconds,
    so the millisecond part is dropped the way a fraction is above. A value
    that is not a whole number is a missing time, and so is one no clock can
    represent — a payload that moved must arrive as a typed answer rather
    than as an exception.
    """

    if isinstance(milliseconds, bool) or not isinstance(milliseconds, int):
        return ""
    try:
        moment = datetime.fromtimestamp(milliseconds // MILLISECONDS_PER_SECOND, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return ""
    return moment.strftime(RECORD_INSTANT_FORMAT)


def _missing(row: Mapping[str, Any], keys: Sequence[str]) -> Tuple[str, ...]:
    """Which of this row's declared fields the payload did not report.

    Absence, never falsehood: a market nobody has traded reports a volume of
    zero, and zero is a fact.
    """

    return tuple(key for key in keys if row.get(key) is None or row.get(key) == "")


def _engagement(pairs: Sequence[Tuple[str, Any]]) -> Tuple[Tuple[str, int], ...]:
    counted = []
    for name, value in pairs:
        exact = exact_count(value)
        if exact is not None:
            counted.append((name, exact))
    return tuple(counted)


def _attributes(row: Mapping[str, Any], names: Sequence[str]) -> List[Tuple[str, str]]:
    """The facts a row carries under the names declared for it, as exact text.

    In the declared order, each under the origin's own name. A name the row
    does not carry, or carries as nothing, is not carried: an attribute states
    a fact the origin stated.
    """

    named: List[Tuple[str, str]] = []
    for name in names:
        text = scalar_text(row.get(name))
        if text:
            named.append((name, text))
    return named


def _polymarket_event_record(position: int, event: Mapping[str, Any]) -> NativeRecord:
    """One Polymarket event as the origin described it."""

    row = {
        ID_KEY: id_text(event.get(ID_KEY)),
        SLUG_KEY: _text(event.get(SLUG_KEY)),
        TITLE_KEY: _text(event.get(TITLE_KEY)),
        CREATED_AT_KEY: route_instant_to_utc_iso(event.get(CREATED_AT_KEY)),
    }
    return NativeRecord(
        canonical_content_kind=EVENT_KIND,
        canonical_locator=polymarket_event_locator(row[SLUG_KEY]),
        native_item_id=row[ID_KEY],
        title=row[TITLE_KEY],
        body=_text(event.get(DESCRIPTION_KEY)),
        published_at=row[CREATED_AT_KEY],
        engagement=_engagement(((COMMENT_COUNT_METRIC, event.get(COMMENT_COUNT_METRIC)),)),
        attributes=tuple(_attributes(event, POLYMARKET_EVENT_ATTRIBUTES)),
        native_position=position,
        loss=(FIELD_OMITTED,) if _missing(row, POLYMARKET_EVENT_ROW_KEYS) else (),
    )


def _polymarket_market_record(
    position: int, market: Mapping[str, Any], event: Mapping[str, Any]
) -> NativeRecord:
    """One Polymarket market as the origin described it, under its event.

    ``event`` is whatever the answer said about the event this market belongs
    to: the containing event on the search and event surfaces, the first entry
    under the market's own ``events`` on the market list, or nothing.
    """

    row = {
        ID_KEY: id_text(market.get(ID_KEY)),
        SLUG_KEY: _text(market.get(SLUG_KEY)),
        QUESTION_KEY: _text(market.get(QUESTION_KEY)),
        OUTCOMES_KEY: _text(market.get(OUTCOMES_KEY)),
        OUTCOME_PRICES_KEY: _text(market.get(OUTCOME_PRICES_KEY)),
        CREATED_AT_KEY: route_instant_to_utc_iso(market.get(CREATED_AT_KEY)),
    }
    event_id = id_text(event.get(ID_KEY))
    event_slug = _text(event.get(SLUG_KEY))
    event_title = _text(event.get(TITLE_KEY))
    named = _attributes(market, POLYMARKET_MARKET_ATTRIBUTES)
    for name, value in (
        (EVENT_ID_ATTRIBUTE, event_id),
        (EVENT_SLUG_ATTRIBUTE, event_slug),
        (EVENT_TITLE_ATTRIBUTE, event_title),
    ):
        if value:
            named.append((name, value))
    return NativeRecord(
        canonical_content_kind=MARKET_KIND,
        canonical_locator=polymarket_market_locator(event_slug, row[SLUG_KEY]),
        native_item_id=row[ID_KEY],
        native_parent_id=event_id,
        title=row[QUESTION_KEY],
        body=_text(market.get(DESCRIPTION_KEY)),
        published_at=row[CREATED_AT_KEY],
        # A market states prices and volumes and no count of anything: every
        # figure it carries is in `attributes`, and none of them is here.
        engagement=(),
        attributes=tuple(named),
        native_position=position,
        loss=(FIELD_OMITTED,) if _missing(row, POLYMARKET_MARKET_ROW_KEYS) else (),
    )


def _kalshi_market_record(position: int, market: Mapping[str, Any]) -> NativeRecord:
    """One Kalshi market as the origin described it.

    Every price and volume Kalshi states is a decimal string and travels as
    that string; the integer ``volume`` and ``open_interest`` of the older
    shape were not in the measured answer, so nothing here is a count.
    """

    row = {
        TICKER_KEY: _text(market.get(TICKER_KEY)),
        EVENT_TICKER_KEY: _text(market.get(EVENT_TICKER_KEY)),
        TITLE_KEY: _text(market.get(TITLE_KEY)),
        STATUS_KEY: _text(market.get(STATUS_KEY)),
        OPEN_TIME_KEY: route_instant_to_utc_iso(market.get(OPEN_TIME_KEY)),
        YES_BID_KEY: scalar_text(market.get(YES_BID_KEY)),
        YES_ASK_KEY: scalar_text(market.get(YES_ASK_KEY)),
        LAST_PRICE_KEY: scalar_text(market.get(LAST_PRICE_KEY)),
        VOLUME_FP_KEY: scalar_text(market.get(VOLUME_FP_KEY)),
    }
    named = _attributes(market, KALSHI_MARKET_ATTRIBUTES)
    rules = _text(market.get(RULES_PRIMARY_KEY))
    if rules:
        named.append((RULES_PRIMARY_KEY, rules[:RULES_PRIMARY_LIMIT]))
    return NativeRecord(
        canonical_content_kind=MARKET_KIND,
        canonical_locator=kalshi_locator(row[TICKER_KEY]),
        native_item_id=row[TICKER_KEY],
        native_parent_id=row[EVENT_TICKER_KEY],
        title=row[TITLE_KEY],
        published_at=row[OPEN_TIME_KEY],
        engagement=(),
        attributes=tuple(named),
        native_position=position,
        loss=(FIELD_OMITTED,) if _missing(row, KALSHI_MARKET_ROW_KEYS) else (),
    )


def _kalshi_event_record(position: int, event: Mapping[str, Any]) -> NativeRecord:
    """One Kalshi event as the origin listed it. It states no time of its own."""

    row = {
        EVENT_TICKER_KEY: _text(event.get(EVENT_TICKER_KEY)),
        TITLE_KEY: _text(event.get(TITLE_KEY)),
        SERIES_TICKER_KEY: _text(event.get(SERIES_TICKER_KEY)),
    }
    return NativeRecord(
        canonical_content_kind=EVENT_KIND,
        canonical_locator=kalshi_locator(row[EVENT_TICKER_KEY]),
        native_item_id=row[EVENT_TICKER_KEY],
        title=row[TITLE_KEY],
        engagement=(),
        attributes=tuple(_attributes(event, KALSHI_EVENT_ATTRIBUTES)),
        native_position=position,
        loss=(FIELD_OMITTED,) if _missing(row, KALSHI_EVENT_ROW_KEYS) else (),
    )


def _manifold_market_record(position: int, market: Mapping[str, Any]) -> NativeRecord:
    """One Manifold market as the search listed it."""

    row = {
        ID_KEY: id_text(market.get(ID_KEY)),
        QUESTION_KEY: _text(market.get(QUESTION_KEY)),
        URL_KEY: _text(market.get(URL_KEY)),
        CREATOR_USERNAME_KEY: _text(market.get(CREATOR_USERNAME_KEY)),
        CREATED_TIME_KEY: epoch_ms_to_utc_iso(market.get(CREATED_TIME_KEY)),
    }
    return NativeRecord(
        canonical_content_kind=MARKET_KIND,
        # The address Manifold published for it, absolute and carried as
        # published: this origin states an item's own address.
        canonical_locator=row[URL_KEY],
        native_item_id=row[ID_KEY],
        title=row[QUESTION_KEY],
        author=row[CREATOR_USERNAME_KEY],
        published_at=row[CREATED_TIME_KEY],
        engagement=_engagement(
            ((UNIQUE_BETTOR_COUNT_METRIC, market.get(UNIQUE_BETTOR_COUNT_METRIC)),)
        ),
        attributes=tuple(_attributes(market, MANIFOLD_MARKET_ATTRIBUTES)),
        native_position=position,
        loss=(FIELD_OMITTED,) if _missing(row, MANIFOLD_MARKET_ROW_KEYS) else (),
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


def _polymarket_event_records(rows: Sequence[Any]) -> Tuple[List[NativeRecord], int, int]:
    """Every event and every market under it, flattened in the origin's order.

    Returns the records, how many events named no id, and how many markets
    did. An event with no id is skipped with everything under it: a market
    can be neither addressed nor grouped under an event that names nothing.
    """

    records: List[NativeRecord] = []
    unidentified_events = 0
    unidentified_markets = 0
    for event in rows:
        if not isinstance(event, Mapping) or not id_text(event.get(ID_KEY)):
            unidentified_events += 1
            continue
        records.append(_polymarket_event_record(len(records), event))
        markets = event.get(MARKETS_KEY)
        for market in markets if isinstance(markets, list) else ():
            if not isinstance(market, Mapping) or not id_text(market.get(ID_KEY)):
                unidentified_markets += 1
                continue
            records.append(_polymarket_market_record(len(records), market, event))
    return (records, unidentified_events, unidentified_markets)


def _polymarket_market_records(rows: Sequence[Any]) -> Tuple[List[NativeRecord], int, int]:
    """Every market the list answered, each under the first event it names."""

    records: List[NativeRecord] = []
    unidentified = 0
    for market in rows:
        if not isinstance(market, Mapping) or not id_text(market.get(ID_KEY)):
            unidentified += 1
            continue
        events = market.get(EVENTS_KEY)
        first = events[0] if isinstance(events, list) and events else None
        event = first if isinstance(first, Mapping) else {}
        records.append(_polymarket_market_record(len(records), market, event))
    return (records, unidentified, 0)


def _kalshi_market_records(rows: Sequence[Any]) -> Tuple[List[NativeRecord], int, int]:
    records: List[NativeRecord] = []
    unidentified = 0
    for market in rows:
        if not isinstance(market, Mapping) or not _text(market.get(TICKER_KEY)):
            unidentified += 1
            continue
        records.append(_kalshi_market_record(len(records), market))
    return (records, unidentified, 0)


def _kalshi_event_records(rows: Sequence[Any]) -> Tuple[List[NativeRecord], int, int]:
    """Every event and every market nested under it, in the origin's order."""

    records: List[NativeRecord] = []
    unidentified_events = 0
    unidentified_markets = 0
    for event in rows:
        if not isinstance(event, Mapping) or not _text(event.get(EVENT_TICKER_KEY)):
            unidentified_events += 1
            continue
        records.append(_kalshi_event_record(len(records), event))
        markets = event.get(MARKETS_KEY)
        for market in markets if isinstance(markets, list) else ():
            if not isinstance(market, Mapping) or not _text(market.get(TICKER_KEY)):
                unidentified_markets += 1
                continue
            records.append(_kalshi_market_record(len(records), market))
    return (records, unidentified_events, unidentified_markets)


def _manifold_market_records(rows: Sequence[Any]) -> Tuple[List[NativeRecord], int, int]:
    records: List[NativeRecord] = []
    unidentified = 0
    for market in rows:
        if not isinstance(market, Mapping) or not id_text(market.get(ID_KEY)):
            unidentified += 1
            continue
        records.append(_manifold_market_record(len(records), market))
    return (records, unidentified, 0)


RECORD_BUILDERS = {
    POLYMARKET_SEARCH_OPERATION: _polymarket_event_records,
    POLYMARKET_EVENTS_OPERATION: _polymarket_event_records,
    POLYMARKET_EVENT_OPERATION: _polymarket_event_records,
    POLYMARKET_MARKETS_OPERATION: _polymarket_market_records,
    KALSHI_MARKETS_OPERATION: _kalshi_market_records,
    KALSHI_MARKET_OPERATION: _kalshi_market_records,
    KALSHI_EVENTS_OPERATION: _kalshi_event_records,
    MANIFOLD_SEARCH_OPERATION: _manifold_market_records,
}


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
