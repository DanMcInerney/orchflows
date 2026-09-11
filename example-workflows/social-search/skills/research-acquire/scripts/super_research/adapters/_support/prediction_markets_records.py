"""Record construction and collection for the prediction-markets adapter."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List, Mapping, Optional, Sequence, Tuple

from .. import NativeRecord
from .prediction_markets_config import (
    COMMENT_COUNT_METRIC,
    CREATED_AT_KEY,
    CREATED_TIME_KEY,
    CREATOR_USERNAME_KEY,
    DESCRIPTION_KEY,
    EVENT_ID_ATTRIBUTE,
    EVENT_KIND,
    EVENT_SLUG_ATTRIBUTE,
    EVENT_TICKER_KEY,
    EVENT_TITLE_ATTRIBUTE,
    EVENTS_KEY,
    FIELD_OMITTED,
    ID_KEY,
    KALSHI_EVENT_ATTRIBUTES,
    KALSHI_EVENTS_OPERATION,
    KALSHI_EVENT_ROW_KEYS,
    KALSHI_MARKET_ATTRIBUTES,
    KALSHI_MARKET_OPERATION,
    KALSHI_MARKET_PATH,
    KALSHI_MARKET_ROW_KEYS,
    KALSHI_MARKETS_OPERATION,
    KALSHI_SITE_ORIGIN,
    LAST_PRICE_KEY,
    MANIFOLD_MARKET_ATTRIBUTES,
    MANIFOLD_MARKET_ROW_KEYS,
    MANIFOLD_SEARCH_OPERATION,
    MARKET_KIND,
    MARKETS_KEY,
    MILLISECONDS_PER_SECOND,
    OPEN_TIME_KEY,
    OUTCOMES_KEY,
    OUTCOME_PRICES_KEY,
    POLYMARKET_EVENT_ATTRIBUTES,
    POLYMARKET_EVENT_OPERATION,
    POLYMARKET_EVENT_PATH,
    POLYMARKET_EVENT_ROW_KEYS,
    POLYMARKET_EVENTS_OPERATION,
    POLYMARKET_MARKET_ATTRIBUTES,
    POLYMARKET_MARKET_PATH,
    POLYMARKET_MARKET_ROW_KEYS,
    POLYMARKET_MARKETS_OPERATION,
    POLYMARKET_SEARCH_OPERATION,
    POLYMARKET_SITE_ORIGIN,
    QUESTION_KEY,
    RECORD_INSTANT_FORMAT,
    ROUTE_INSTANT_FORMAT,
    RULES_PRIMARY_KEY,
    RULES_PRIMARY_LIMIT,
    SERIES_TICKER_KEY,
    SLUG_KEY,
    STATUS_KEY,
    TICKER_KEY,
    TITLE_KEY,
    UNIQUE_BETTOR_COUNT_METRIC,
    URL_KEY,
    VOLUME_FP_KEY,
    YES_ASK_KEY,
    YES_BID_KEY,
)


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
