"""Provider declarations for the prediction-markets adapter."""

from ... import transport
from .. import AdapterDescriptor

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
