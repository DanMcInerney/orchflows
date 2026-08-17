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

# Where a message and a symbol page live. It is Stocktwits' own site and not
# either route's origin, so `transport.origin_locator` cannot resolve it — it
# resolves against the route that answered, which here would name the API
# host. Neither payload publishes a message's address, so it is composed from
# the poster and the id, the way `hacker_news.HN_ITEM_ORIGIN` composes an
# item's address from its id: a host no route in this package reads is not a
# host the transport seam owns. Measured 2026-08-17:
# `stocktwits.com/<username>/message/<id>` and `stocktwits.com/symbol/<SYM>`
# both answered 200.
STOCKTWITS_SITE_ORIGIN = "https://stocktwits.com"
MESSAGE_PATH = "/message/"
SYMBOL_PATH = "/symbol/"

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

# The kinds of record this module emits.
POST_KIND = "post"
SYMBOL_KIND = "symbol"

# Where each surface keeps what it returned. Declared, never searched for.
MESSAGES_KEY = "messages"
RESULTS_KEY = "results"
CURSOR_KEY = "cursor"
MORE_KEY = "more"
MAX_KEY = "max"

# Every other key these two payloads publish that this module reads, under
# Stocktwits' own names.
ID_KEY = "id"
BODY_KEY = "body"
CREATED_AT_KEY = "created_at"
USER_KEY = "user"
USERNAME_KEY = "username"
SOURCE_KEY = "source"
TITLE_KEY = "title"
SYMBOLS_KEY = "symbols"
SYMBOL_KEY = "symbol"
EXCHANGE_KEY = "exchange"
ENTITIES_KEY = "entities"
SENTIMENT_KEY = "sentiment"
BASIC_KEY = "basic"
LIKES_KEY = "likes"
TOTAL_KEY = "total"
CONVERSATION_KEY = "conversation"
PARENT_KEY = "parent"
PARENT_MESSAGE_ID_KEY = "parent_message_id"
IN_REPLY_TO_MESSAGE_ID_KEY = "in_reply_to_message_id"
LIKES_METRIC = "likes"
WATCHLIST_COUNT_METRIC = "watchlist_count"

# What each kind of row promises, so a record short of it says so. The
# evidence records that both routes answer and what a message carries; the
# row sets are this adapter's own declaration. An id is absent from both:
# a row without one is not a row of that kind at all.
MESSAGE_ROW_KEYS = (ID_KEY, BODY_KEY, CREATED_AT_KEY, USERNAME_KEY)
SYMBOL_ROW_KEYS = (SYMBOL_KEY, TITLE_KEY)

# The stamp the stream emits is already the artifact's own instant format;
# it is read through the format rather than copied so junk stays a missing
# time and never an approximated one.
ROUTE_INSTANT_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

SCHEMA_DRIFT = "schema_drift"
MALFORMED_JSON = "malformed_json"
HTTP_STATUS = "http_status"
FIELD_OMITTED = "field_omitted"


def message_locator(username: str, message_id: str) -> str:
    """One message's address on Stocktwits' own site, or nothing without both parts."""

    if not username or not message_id:
        return ""
    return STOCKTWITS_SITE_ORIGIN + "/" + username + MESSAGE_PATH + message_id


def symbol_locator(symbol: str) -> str:
    """One symbol's stream page on Stocktwits' own site, or nothing without a symbol."""

    return STOCKTWITS_SITE_ORIGIN + SYMBOL_PATH + symbol if symbol else ""


def _text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def exact_count(value: Any) -> Optional[int]:
    """One count Stocktwits published as an exact number, or nothing at all.

    A bool is not a count and ``null`` is not one either: the origin publishes
    its counts as json integers, so anything else is a count this adapter was
    not given rather than one it can recover.
    """

    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def id_text(value: Any) -> str:
    """One Stocktwits id as its decimal spelling, which is the only form a record holds.

    The stream publishes every id as a json number; nothing is rounded,
    formatted, or made here — an identifier's decimal digits are the identifier.
    """

    if isinstance(value, bool):
        return ""
    if isinstance(value, int):
        return str(value)
    return value if isinstance(value, str) else ""


def route_instant_to_utc_iso(created_at: Any) -> str:
    """The stream's stamp as the artifact's instant, or nothing.

    The origin already writes ``%Y-%m-%dT%H:%M:%SZ``; reading it back through
    that format is what keeps a stamp that moved from riding along as a time.
    """

    if not isinstance(created_at, str) or not created_at.strip():
        return ""
    try:
        moment = datetime.strptime(created_at.strip(), ROUTE_INSTANT_FORMAT)
    except ValueError:
        return ""
    return moment.replace(tzinfo=timezone.utc).strftime(ROUTE_INSTANT_FORMAT)


def _missing(row: Mapping[str, Any], keys: Sequence[str]) -> Tuple[str, ...]:
    """Which of this row's declared fields the payload did not report.

    Absence, never falsehood: a message nobody has liked carries no `likes`
    block, and that is a count nobody reported rather than a field left out.
    """

    return tuple(key for key in keys if row.get(key) is None or row.get(key) == "")


def _engagement(pairs: Sequence[Tuple[str, Any]]) -> Tuple[Tuple[str, int], ...]:
    counted = []
    for name, value in pairs:
        exact = exact_count(value)
        if exact is not None:
            counted.append((name, exact))
    return tuple(counted)


def _nested(payload: Mapping[str, Any], *keys: str) -> Any:
    """One value under a key path, or None the moment the path leaves a mapping."""

    held: Any = payload
    for key in keys:
        if not isinstance(held, Mapping):
            return None
        held = held.get(key)
    return held


def reply_parent_of(message: Mapping[str, Any]) -> Tuple[str, str]:
    """The message this one answers, and the root of the thread it sits in.

    Both empty for a message that is not a reply. A ``conversation`` block
    marks a message that has replies as well as one that is a reply, and the
    two are told apart by its own ``parent`` flag: a root names itself as
    ``parent_message_id`` and answers nothing. A reply's parent is the
    message it answers — ``in_reply_to_message_id`` — and the thread's root
    is a separate fact that rides in attributes, the way an HN reply names the
    comment it answers and carries the story apart.
    """

    conversation = message.get(CONVERSATION_KEY)
    if not isinstance(conversation, Mapping) or conversation.get(PARENT_KEY) is True:
        return ("", "")
    root = id_text(conversation.get(PARENT_MESSAGE_ID_KEY))
    answered = id_text(conversation.get(IN_REPLY_TO_MESSAGE_ID_KEY)) or root
    return (answered, root)


def _message_record(position: int, message: Mapping[str, Any], symbol: str) -> NativeRecord:
    """One message as the stream listed it."""

    message_id = id_text(message.get(ID_KEY))
    username = _text(_nested(message, USER_KEY, USERNAME_KEY))
    row = {
        ID_KEY: message_id,
        BODY_KEY: _text(message.get(BODY_KEY)),
        CREATED_AT_KEY: route_instant_to_utc_iso(message.get(CREATED_AT_KEY)),
        USERNAME_KEY: username,
    }
    answered, root = reply_parent_of(message)
    named: List[Tuple[str, str]] = []
    sentiment = _text(_nested(message, ENTITIES_KEY, SENTIMENT_KEY, BASIC_KEY))
    if sentiment:
        named.append((SENTIMENT_KEY, sentiment))
    symbols = message.get(SYMBOLS_KEY)
    for tagged in symbols if isinstance(symbols, list) else ():
        # Every symbol the message tags, one pair each in the origin's order,
        # rather than a list flattened into one string this module invented.
        ticker = _text(tagged.get(SYMBOL_KEY)) if isinstance(tagged, Mapping) else ""
        if ticker:
            named.append((SYMBOL_KEY, ticker))
    source = _text(_nested(message, SOURCE_KEY, TITLE_KEY))
    if source:
        named.append((SOURCE_KEY, source))
    if root:
        # The thread's root, which `native_parent_id` does not mean: a reply's
        # parent is the message it answers.
        named.append((PARENT_MESSAGE_ID_KEY, root))
    return NativeRecord(
        canonical_content_kind=POST_KIND,
        canonical_locator=message_locator(username, message_id),
        native_item_id=message_id,
        native_parent_id=answered,
        body=row[BODY_KEY],
        author=username,
        # The stream the message was read from, as the caller named it. A
        # message tagging several symbols appears in each of their streams;
        # the ones it tags are its `symbol` attributes.
        community=symbol,
        published_at=row[CREATED_AT_KEY],
        # Present only when the origin stated one: a message nobody has liked
        # carries no `likes` block, and no zero is written for it.
        engagement=_engagement(((LIKES_METRIC, _nested(message, LIKES_KEY, TOTAL_KEY)),)),
        attributes=tuple(named),
        native_position=position,
        loss=(FIELD_OMITTED,) if _missing(row, MESSAGE_ROW_KEYS) else (),
    )


def _symbol_record(position: int, result: Mapping[str, Any]) -> NativeRecord:
    """One symbol as the search listed it."""

    row = {
        SYMBOL_KEY: _text(result.get(SYMBOL_KEY)),
        TITLE_KEY: _text(result.get(TITLE_KEY)),
    }
    exchange = _text(result.get(EXCHANGE_KEY))
    return NativeRecord(
        canonical_content_kind=SYMBOL_KIND,
        canonical_locator=symbol_locator(row[SYMBOL_KEY]),
        native_item_id=row[SYMBOL_KEY],
        title=row[TITLE_KEY],
        # How many watchlists hold it, when the origin stated a number; a
        # `null` here is a count nobody reported.
        engagement=_engagement(((WATCHLIST_COUNT_METRIC, result.get(WATCHLIST_COUNT_METRIC)),)),
        attributes=((EXCHANGE_KEY, exchange),) if exchange else (),
        native_position=position,
        loss=(FIELD_OMITTED,) if _missing(row, SYMBOL_ROW_KEYS) else (),
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
