"""K0 Stocktwits over two surfaces: a symbol's message stream, and symbol search.

Measured 2026-08-17 (Stocktwits), keyless and 200 on both:
``api.stocktwits.com/api/2/streams/symbol/SPCX.json?limit=5`` answered
``{"symbol", "cursor", "messages", "response"}`` where every message carries
an integer ``id``, a ``body``, a ``created_at`` already spelled as an instant,
its ``user.username``, its ``source.title``, the ``symbols`` it tags, a
``likes.total`` when anyone has liked it and no ``likes`` at all when nobody
has, an ``entities.sentiment.basic`` of ``Bullish`` or ``Bearish`` or a
``null`` sentiment, and a ``conversation`` block on a message that is a reply
or has replies. ``cursor`` states ``more`` and the ``max`` id the next page
starts below, and page two answered 200 to ``max=<that id>``. A symbol
nobody has posted about answered the same shape with ``"messages": []`` and
``"cursor": {"more": false, "since": null, "max": null}``; a symbol
Stocktwits does not list answered 404 with ``"Symbol not found"``.
``search/symbols.json?q=SpaceX`` answered ``{"results": [...]}`` where each
row states a ``symbol``, a ``title``, an ``exchange`` and an integer
``watchlist_count`` — ``null`` on one row, which is a count nobody reported.

**Two surfaces, two routes, one call each.** A stream read is one call and a
symbol search is another, and no call here is ever both. Paging is the
core's: the ``max`` the cursor states is surfaced and never followed.

**A count nobody reported is not zero.** A message with no ``likes`` block
has no like count on its record rather than a zero this module wrote, and a
symbol whose ``watchlist_count`` is ``null`` has none. Sentiment is a word
the poster chose and travels as that word in ``attributes``; it is never a
number and never inferred from the body.

**A 404 here is the status it is.** The surface is documented keyless, so no
status it returns is a report that a credential was needed; a symbol it does
not list is a symbol it does not list.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Mapping, Optional, Tuple

from .. import transport
from . import (
    AdapterDescriptor,
    AdapterRequest,
    NativePage,
    NativeRecord,
    build_native_page,
    fetch_one_page,
)
from ._support.stocktwits_records import (
    BASIC_KEY,
    BODY_KEY,
    CONVERSATION_KEY,
    CREATED_AT_KEY,
    ENTITIES_KEY,
    EXCHANGE_KEY,
    FIELD_OMITTED,
    ID_KEY,
    IN_REPLY_TO_MESSAGE_ID_KEY,
    LIKES_KEY,
    LIKES_METRIC,
    MESSAGE_PATH,
    MESSAGE_ROW_KEYS,
    PARENT_KEY,
    PARENT_MESSAGE_ID_KEY,
    POST_KIND,
    ROUTE_INSTANT_FORMAT,
    SENTIMENT_KEY,
    SOURCE_KEY,
    STOCKTWITS_SITE_ORIGIN,
    SYMBOL_KIND,
    SYMBOL_KEY,
    SYMBOL_PATH,
    SYMBOL_ROW_KEYS,
    SYMBOLS_KEY,
    TITLE_KEY,
    TOTAL_KEY,
    USER_KEY,
    USERNAME_KEY,
    WATCHLIST_COUNT_METRIC,
    _engagement,
    _message_record,
    _missing,
    _nested,
    _symbol_record,
    _text,
    exact_count,
    id_text,
    message_locator,
    reply_parent_of,
    route_instant_to_utc_iso,
    symbol_locator,
)

# The stream surface. It is this adapter's primary descriptor because a
# request naming a symbol reads its stream, which is the call the core makes
# most and the one an unprefixed query or target means.
DESCRIPTOR = AdapterDescriptor(
    adapter_id="stocktwits",
    adapter_version="1",
    access_class="K0",
    route_id=transport.STOCKTWITS_STREAM_ROUTE,
    platform="stocktwits",
    native_identity_namespace="stocktwits",
    representation_kind="native",
    operator_identity="stocktwits",
    # The 2026-08-17 probes saw no throttle across three reads. An unmeasured
    # ceiling is not one to spend, so one read a second with a burst of three
    # rather than a figure this adapter would have had to invent.
    min_interval_ms=1000,
    burst=3,
    # A message states no count of its own replies except inside a
    # `conversation` block that is not on every message, and no name is
    # inferred from it.
    page_size=30,
)

# The symbol search surface: the same origin, a different endpoint, and its
# own route budget because a ceiling belongs to the route that sets it.
SYMBOL_SEARCH_DESCRIPTOR = AdapterDescriptor(
    adapter_id="stocktwits",
    adapter_version="1",
    access_class="K0",
    route_id=transport.STOCKTWITS_SYMBOL_SEARCH_ROUTE,
    platform="stocktwits",
    native_identity_namespace="stocktwits",
    representation_kind="native",
    operator_identity="stocktwits",
    min_interval_ms=1000,
    burst=3,
)

# Every route this adapter can reach, one descriptor each.
SURFACE_DESCRIPTORS = (DESCRIPTOR, SYMBOL_SEARCH_DESCRIPTOR)

# The two operations, spelled once each. A caller names one with a prefix;
# absent a prefix, both a query and a target name a symbol whose stream is
# read, and never is one inferred from the characters in the argument. The
# symbol travels as the caller spelled it: this module changes no case.
STREAM_OPERATION = "stream"
SYMBOLS_OPERATION = "symbols"
STOCKTWITS_OPERATIONS = (STREAM_OPERATION, SYMBOLS_OPERATION)

OPERATION_SURFACES = {
    STREAM_OPERATION: DESCRIPTOR,
    SYMBOLS_OPERATION: SYMBOL_SEARCH_DESCRIPTOR,
}

NATIVE_ORDERS = {
    STREAM_OPERATION: "stocktwits_stream_recency_order",
    SYMBOLS_OPERATION: "stocktwits_symbol_search_order",
}

# The stream's page, sent explicitly so the page a call reads is a stated
# size: thirty is the most the origin serves per read, as measured.
STREAM_LIMIT = "30"
SYMBOL_PARAM = "symbol"
LIMIT_PARAM = "limit"
MAX_PARAM = "max"
QUERY_PARAM = "q"

# Where each surface keeps what it returned. Declared, never searched for.
MESSAGES_KEY = "messages"
RESULTS_KEY = "results"
CURSOR_KEY = "cursor"
MORE_KEY = "more"
MAX_KEY = "max"

SCHEMA_DRIFT = "schema_drift"
MALFORMED_JSON = "malformed_json"
HTTP_STATUS = "http_status"


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


def next_max(payload: Any) -> str:
    """The id the next page starts below, when the stream says there is one.

    Both facts are the origin's: it states ``more`` and it states ``max``.
    Deriving one from the number of rows returned would make this adapter the
    thing that decides there is more.
    """

    cursor = payload.get(CURSOR_KEY) if isinstance(payload, Mapping) else None
    if not isinstance(cursor, Mapping) or cursor.get(MORE_KEY) is not True:
        return ""
    return id_text(exact_count(cursor.get(MAX_KEY)))


def _stream_page(
    response: transport.TransportResponse, payload: Any, symbol: str
) -> NativePage:
    native_order = NATIVE_ORDERS[STREAM_OPERATION]
    messages = payload.get(MESSAGES_KEY) if isinstance(payload, Mapping) else None
    if not isinstance(messages, list):
        return _failed(
            DESCRIPTOR,
            response,
            native_order,
            SCHEMA_DRIFT,
            "{0} answered 200 with no {1} list: the payload this adapter reads has"
            " changed shape".format(STREAM_OPERATION, MESSAGES_KEY),
        )
    records: List[NativeRecord] = []
    unidentified = 0
    for message in messages:
        if not isinstance(message, Mapping) or not id_text(message.get(ID_KEY)):
            # A row this stream did not identify is not a row: a record naming
            # nothing groups with nothing and addresses nothing.
            unidentified += 1
            continue
        records.append(_message_record(len(records), message, symbol))
    if records:
        warnings = (
            (
                "{0} answered 200 with {1} message(s) naming no {2}: they are not"
                " rows this adapter can identify".format(STREAM_OPERATION, unidentified, ID_KEY),
            )
            if unidentified
            else ()
        )
        return _answered(
            DESCRIPTOR,
            response,
            native_order,
            records=tuple(records),
            cursor_out=next_max(payload),
            warnings=warnings,
        )
    if messages:
        # Rows present and not one of them identified: the payload reshaping,
        # not a stream with nothing in it.
        return _failed(
            DESCRIPTOR,
            response,
            native_order,
            SCHEMA_DRIFT,
            "{0} answered 200 with {1} message(s) and no {2} on any of them: the"
            " payload has changed shape".format(STREAM_OPERATION, len(messages), ID_KEY),
        )
    return _answered(
        DESCRIPTOR,
        response,
        native_order,
        outcome="empty",
        cursor_out=next_max(payload),
        warnings=(
            "{0} answered 200 with an empty {1} list: nobody has posted to {2}".format(
                STREAM_OPERATION, MESSAGES_KEY, symbol
            ),
        ),
    )


def _symbols_page(
    response: transport.TransportResponse, payload: Any, query: str
) -> NativePage:
    native_order = NATIVE_ORDERS[SYMBOLS_OPERATION]
    results = payload.get(RESULTS_KEY) if isinstance(payload, Mapping) else None
    if not isinstance(results, list):
        return _failed(
            SYMBOL_SEARCH_DESCRIPTOR,
            response,
            native_order,
            SCHEMA_DRIFT,
            "{0} answered 200 with no {1} list: the payload this adapter reads has"
            " changed shape".format(SYMBOLS_OPERATION, RESULTS_KEY),
        )
    records: List[NativeRecord] = []
    unidentified = 0
    for result in results:
        if not isinstance(result, Mapping) or not _text(result.get(SYMBOL_KEY)):
            unidentified += 1
            continue
        records.append(_symbol_record(len(records), result))
    if records:
        warnings = (
            (
                "{0} answered 200 with {1} row(s) naming no {2}: they are not rows"
                " this adapter can identify".format(SYMBOLS_OPERATION, unidentified, SYMBOL_KEY),
            )
            if unidentified
            else ()
        )
        return _answered(
            SYMBOL_SEARCH_DESCRIPTOR,
            response,
            native_order,
            records=tuple(records),
            warnings=warnings,
        )
    if results:
        return _failed(
            SYMBOL_SEARCH_DESCRIPTOR,
            response,
            native_order,
            SCHEMA_DRIFT,
            "{0} answered 200 with {1} row(s) and no {2} on any of them: the payload"
            " has changed shape".format(SYMBOLS_OPERATION, len(results), SYMBOL_KEY),
        )
    return _answered(
        SYMBOL_SEARCH_DESCRIPTOR,
        response,
        native_order,
        outcome="empty",
        warnings=(
            "{0} answered 200 with an empty {1} list: no symbol matched {2}".format(
                SYMBOLS_OPERATION, RESULTS_KEY, query
            ),
        ),
    )


def operation_for(request: AdapterRequest) -> Tuple[str, str]:
    """The operation this call performs, and the argument it performs it on.

    A caller names the operation, because two surfaces answer two different
    questions. Absent a name, both shapes of step name a symbol and read its
    stream: a step naming a target and a step naming only a query mean the
    same thing here, because a symbol is both. Neither is inferred from the
    characters in the argument.
    """

    named = request.target_ids[0] if request.target_ids else request.query
    kind, separator, argument = named.partition(":")
    if separator and kind in STOCKTWITS_OPERATIONS:
        return (kind, argument)
    return (STREAM_OPERATION, named)


def fetch_native_page(carrier: transport.Transport, request: AdapterRequest) -> NativePage:
    """Read one surface once and return exactly one NativePage.

    One call, one origin: a stream read never also searches symbols, and a
    symbol search never also reads a stream. No window parameter is sent: the
    stream's ``since`` and ``max`` are message ids and not moments, so the
    core's own filter is the whole window.
    """

    operation, argument = operation_for(request)
    if operation == SYMBOLS_OPERATION:
        return _fetch_symbols(carrier, argument)
    return _fetch_stream(carrier, argument, request.cursor)


def _fetch_stream(carrier: transport.Transport, symbol: str, cursor: str) -> NativePage:
    native_order = NATIVE_ORDERS[STREAM_OPERATION]
    params: Dict[str, str] = {SYMBOL_PARAM: symbol, LIMIT_PARAM: STREAM_LIMIT}
    if cursor:
        # The id ceiling the core froze, spent as the origin's own `max`. No
        # next one is derived here: the origin states it.
        params[MAX_PARAM] = cursor

    def parse(response: transport.TransportResponse) -> NativePage:
        payload, refused = _payload_of(DESCRIPTOR, response, native_order, STREAM_OPERATION)
        return refused if refused is not None else _stream_page(response, payload, symbol)

    return fetch_one_page(
        DESCRIPTOR, carrier, params=params, parse=parse, native_order=native_order
    )


def _fetch_symbols(carrier: transport.Transport, query: str) -> NativePage:
    native_order = NATIVE_ORDERS[SYMBOLS_OPERATION]

    def parse(response: transport.TransportResponse) -> NativePage:
        payload, refused = _payload_of(
            SYMBOL_SEARCH_DESCRIPTOR, response, native_order, SYMBOLS_OPERATION
        )
        return refused if refused is not None else _symbols_page(response, payload, query)

    return fetch_one_page(
        SYMBOL_SEARCH_DESCRIPTOR,
        carrier,
        params={QUERY_PARAM: query},
        parse=parse,
        native_order=native_order,
    )
