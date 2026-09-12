"""Selected X posts and conversations through the independent FxTwitter operator.

A selected numeric post ID reads its root, self-thread and available replies in
one request. No search, profile, timeline, retry or conversation paging is offered.
Every row carries third_party_archive; counts are observations of this operator.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
from .. import transport, schema
from . import AdapterDescriptor, AdapterError, AdapterRequest, NativePage, NativeRecord, build_native_page, fetch_one_page

THIRD_PARTY_ARCHIVE = "third_party_archive"
STANDING_LOSS = (THIRD_PARTY_ARCHIVE,)
ID_KEY = "id"
STATUS_KEY = "status"
URL_KEY = "url"
TEXT_KEY = "text"
AUTHOR_KEY = "author"
SCREEN_NAME_KEY = "screen_name"
CREATED_AT_KEY = "created_at"
CREATED_TIMESTAMP_KEY = "created_timestamp"
LANG_KEY = "lang"
SOURCE_KEY = "source"
PROVIDER_KEY = "provider"
POSSIBLY_SENSITIVE_KEY = "possibly_sensitive"
IS_NOTE_TWEET_KEY = "is_note_tweet"
REPLYING_TO_KEY = "replying_to"
LIKES_METRIC = "likes"
REPOSTS_METRIC = "reposts"
REPLIES_METRIC = "replies"
QUOTES_METRIC = "quotes"
BOOKMARKS_METRIC = "bookmarks"
VIEWS_METRIC = "views"
STATUS_METRICS = (
    LIKES_METRIC,
    REPOSTS_METRIC,
    REPLIES_METRIC,
    QUOTES_METRIC,
    BOOKMARKS_METRIC,
    VIEWS_METRIC,
)
STATUS_ATTRIBUTES = (
    LANG_KEY,
    SOURCE_KEY,
    # The operator's own spelling of the moment, beside the exact epoch the
    # record's instant is read from. Two statements of one fact, and the
    # record keeps both because they are both the origin's.
    CREATED_AT_KEY,
    POSSIBLY_SENSITIVE_KEY,
    IS_NOTE_TWEET_KEY,
    PROVIDER_KEY,
)
AUTHOR_ID_ATTRIBUTE = "author.id"
REPLYING_TO_URL_ATTRIBUTE = "replying_to.url"
STATUS_ROW_KEYS = (ID_KEY, TEXT_KEY, SCREEN_NAME_KEY, CREATED_TIMESTAMP_KEY)
RECORD_INSTANT_FORMAT = schema.INSTANT_FORMAT
FIELD_OMITTED = "field_omitted"
POST_KIND = "post"
DESCRIPTOR = AdapterDescriptor(
    adapter_id="x_fxtwitter",
    adapter_version="2",
    access_class="K3",
    route_id=transport.FXTWITTER_API_ROUTE,
    platform="x",
    native_identity_namespace="x",
    representation_kind="native",
    operator_identity="fxtwitter",
    standing_loss=STANDING_LOSS,
    min_interval_ms=1000,
    burst=5,
    page_size=0,
)
CONVERSATION_OPERATION = "conversation"
CODE_KEY = "code"
MESSAGE_KEY = "message"
OK_CODE = 200
NOT_FOUND_CODE = 404
THREAD_KEY = "thread"
REPLIES_KEY = "replies"
HTTP_STATUS = "http_status"
MALFORMED_JSON = "malformed_json"
SCHEMA_DRIFT = "schema_drift"


def _text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def exact_count(value: Any) -> Optional[int]:
    """One count this operator published as an exact number, or nothing at all.

    A bool is not a count and ``null`` is not one either: every count here
    arrives as a json integer, so anything else is a count this adapter was
    not given rather than one it can recover.
    """

    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def id_text(value: Any) -> str:
    """One identifier as its text, which is the only form a record holds.

    Every id this operator publishes is a string; a number here would be an
    origin that changed its mind, and its decimal digits are still the
    identifier.
    """

    if isinstance(value, bool):
        return ""
    if isinstance(value, int):
        return str(value)
    return value if isinstance(value, str) else ""


def scalar_text(value: Any) -> str:
    """One payload scalar as the exact text a record carries, or nothing.

    A string travels verbatim. A bool is spelled the way json spells one, and
    a number as its own decimal text. Nothing here is rounded, parsed, or
    compared: an attribute states a fact the origin stated.
    """

    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return ""


def epoch_to_utc_iso(seconds: Any) -> str:
    """A status's exact epoch second as the artifact's instant, or nothing.

    A value that is not a whole number is a missing time, and so is one no
    clock can represent — a payload that moved must arrive as a typed answer
    rather than as an exception.
    """

    if isinstance(seconds, bool) or not isinstance(seconds, int):
        return ""
    try:
        moment = datetime.fromtimestamp(seconds, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return ""
    return moment.strftime(RECORD_INSTANT_FORMAT)


def _nested(payload: Any, *keys: str) -> Any:
    """One value under a key path, or None the moment the path leaves a mapping."""

    held: Any = payload
    for key in keys:
        if not isinstance(held, Mapping):
            return None
        held = held.get(key)
    return held


def _missing(row: Mapping[str, Any], keys: Sequence[str]) -> Tuple[str, ...]:
    """Which of this row's declared fields the payload did not report."""

    return tuple(key for key in keys if not row.get(key))


def _engagement(row: Mapping[str, Any], names: Sequence[str]) -> Tuple[Tuple[str, int], ...]:
    counted: List[Tuple[str, int]] = []
    for name in names:
        exact = exact_count(row.get(name))
        if exact is not None:
            counted.append((name, exact))
    return tuple(counted)


def _attributes(row: Mapping[str, Any], names: Sequence[str]) -> List[Tuple[str, str]]:
    """The facts a row carries under the names declared for it, as exact text."""

    named: List[Tuple[str, str]] = []
    for name in names:
        text = scalar_text(row.get(name))
        if text:
            named.append((name, text))
    return named


def _record_loss(row: Mapping[str, Any], keys: Sequence[str]) -> Tuple[str, ...]:
    """This record's standing loss, plus what the payload left out.

    The standing half is on every record without exception: it is the fact
    that an independent operator answered, and it does not depend on what the
    row carried.
    """

    return STANDING_LOSS + ((FIELD_OMITTED,) if _missing(row, keys) else ())


def _status_record(position: int, status: Mapping[str, Any]) -> NativeRecord:
    """One status as this operator described it."""

    screen_name = _text(_nested(status, AUTHOR_KEY, SCREEN_NAME_KEY))
    row = {
        ID_KEY: id_text(status.get(ID_KEY)),
        TEXT_KEY: _text(status.get(TEXT_KEY)),
        SCREEN_NAME_KEY: screen_name,
        CREATED_TIMESTAMP_KEY: epoch_to_utc_iso(status.get(CREATED_TIMESTAMP_KEY)),
    }
    named = _attributes(status, STATUS_ATTRIBUTES)
    for name, value in (
        (AUTHOR_ID_ATTRIBUTE, id_text(_nested(status, AUTHOR_KEY, ID_KEY))),
        (REPLYING_TO_URL_ATTRIBUTE, _text(_nested(status, REPLYING_TO_KEY, URL_KEY))),
    ):
        if value:
            named.append((name, value))
    return NativeRecord(
        canonical_content_kind=POST_KIND,
        # The address this operator published for it, which is the platform's
        # own and is carried as published: nothing is composed here.
        canonical_locator=_text(status.get(URL_KEY)),
        native_item_id=row[ID_KEY],
        # The status this one answers, when it answers one. A reply never
        # carries its parent's counts: the parent is named and nothing else of
        # it travels onto this record.
        native_parent_id=id_text(_nested(status, REPLYING_TO_KEY, STATUS_KEY)),
        body=row[TEXT_KEY],
        author=screen_name,
        published_at=row[CREATED_TIMESTAMP_KEY],
        engagement=_engagement(status, STATUS_METRICS),
        attributes=tuple(named),
        native_position=position,
        loss=_record_loss(row, STATUS_ROW_KEYS),
    )


def _status_records(rows: Sequence[Any]) -> Tuple[List[NativeRecord], int]:
    records: List[NativeRecord] = []
    unidentified = 0
    for status in rows:
        if not isinstance(status, Mapping) or not id_text(status.get(ID_KEY)):
            unidentified += 1
            continue
        records.append(_status_record(len(records), status))
    return (records, unidentified)


def _answered(
    response: transport.TransportResponse,
    native_order: str,
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
        native_order=native_order,
        warnings=warnings,
        outcome=outcome,
        loss=loss,
    )


def _failed(
    response: transport.TransportResponse,
    native_order: str,
    loss: str,
    warnings: Tuple[str, ...],
) -> NativePage:
    return _answered(response, native_order, outcome="failed", warnings=warnings, loss=(loss,))


def stated_message(payload: Any) -> str:
    """This operator's own sentence about an answer, or nothing at all."""

    stated = payload.get(MESSAGE_KEY) if isinstance(payload, Mapping) else None
    return " ".join(stated.split()) if isinstance(stated, str) and stated.strip() else ""


def stated_code(payload: Any) -> Optional[int]:
    """The code the envelope itself states, or None when it states none."""

    return exact_count(payload.get(CODE_KEY)) if isinstance(payload, Mapping) else None


def _payload_of(
    response: transport.TransportResponse, native_order: str, operation: str
) -> Tuple[Any, Optional[NativePage]]:
    """One answer's json, or the typed page that says why there is none.

    The status line is read before the body, so an answer that never got here
    is never typed on what a body claims. This route is documented keyless and
    carries no credential, so no status it returns is a report that one was
    needed: a refusal here is this operator declining this read.
    """

    if response.status != 200:
        return (
            None,
            _failed(
                response,
                native_order,
                HTTP_STATUS,
                ("http status {0} from {1}".format(response.status, DESCRIPTOR.route_id),),
            ),
        )
    try:
        return (json.loads(response.body), None)
    except ValueError:
        return (
            None,
            _failed(
                response,
                native_order,
                MALFORMED_JSON,
                ("{0} answered 200 with no json body".format(operation),),
            ),
        )


def _code_refused(
    response: transport.TransportResponse, native_order: str, operation: str, payload: Any
) -> Optional[NativePage]:
    """The typed page for a 200 whose envelope states a code of its own, or None.

    A subject this operator holds nothing for is `empty` and says so in the
    operator's own words; every other code it states is the status the read
    got, arriving one layer in. Neither is `schema_drift`: the envelope is
    exactly the shape this module declares, and it is being read correctly.
    """

    code = stated_code(payload)
    if code is None or code == OK_CODE:
        return None
    stated = stated_message(payload)
    sentence = "{0} answered 200 with {1} {2}".format(operation, CODE_KEY, code)
    warnings = (sentence + ": " + stated,) if stated else (sentence,)
    if code == NOT_FOUND_CODE:
        return _answered(response, native_order, outcome="empty", warnings=warnings)
    return _failed(response, native_order, HTTP_STATUS, warnings)


def _page_from(
    response: transport.TransportResponse, operation: str, argument: str
) -> NativePage:
    """Turn one answer this operator sent into exactly one page."""

    native_order = NATIVE_ORDERS[operation]
    container = OPERATION_CONTAINERS[operation]
    payload, refused = _payload_of(response, native_order, operation)
    if refused is not None:
        return refused
    stated = _code_refused(response, native_order, operation, payload)
    if stated is not None:
        return stated

    rows = _rows_of(payload, operation)
    if rows is None:
        return _failed(
            response,
            native_order,
            SCHEMA_DRIFT,
            (
                "{0} answered 200 with no {1}: the payload this adapter reads has"
                " changed shape".format(operation, container),
            ),
        )
    records, unidentified = RECORD_BUILDERS[operation](rows)
    if records:
        warnings = (
            (
                "{0} answered 200 with {1} row(s) naming no {2}: they are not rows"
                " this adapter can identify".format(operation, unidentified, ID_KEY),
            )
            if unidentified
            else ()
        )
        return _answered(
            response,
            native_order,
            records=tuple(records),
            warnings=warnings,
        )
    if rows:
        # The container is present and holds rows, and not one of them names an
        # id. That is the payload reshaping, not an answer with nothing in it:
        # reporting it as "there is nothing here" is the one thing a caller
        # cannot tell from a real absence.
        return _failed(
            response,
            native_order,
            SCHEMA_DRIFT,
            (
                "{0} answered 200 with {1} row(s) and no {2} on any of them: the"
                " payload has changed shape".format(operation, len(rows), ID_KEY),
            ),
        )
    return _answered(
        response,
        native_order,
        outcome="empty",
        warnings=(
            "{0} answered 200 with an empty {1} list: {2} has nothing here".format(
                operation, container, argument or operation
            ),
        ),
    )


NATIVE_ORDERS = {CONVERSATION_OPERATION: "fxtwitter_conversation_order"}
OPERATION_CONTAINERS = {CONVERSATION_OPERATION: STATUS_KEY}
RECORD_BUILDERS = {CONVERSATION_OPERATION: _status_records}


def _rows_of(payload: Any, operation: str) -> Optional[Sequence[Any]]:
    if not isinstance(payload, Mapping) or not isinstance(payload.get(STATUS_KEY), Mapping):
        return None
    root = payload[STATUS_KEY]
    thread = payload.get(THREAD_KEY)
    rows = list(thread) if isinstance(thread, list) and thread else [root]
    replies = payload.get(REPLIES_KEY)
    if isinstance(replies, list):
        rows.extend(replies)
    return rows


def operation_for(request: AdapterRequest) -> Tuple[str, str]:
    named = request.target_ids[0] if request.target_ids else request.query
    kind, separator, argument = named.partition(":")
    if not separator and request.target_ids:
        argument = named
    elif kind != CONVERSATION_OPERATION:
        raise AdapterError("x_fxtwitter requires a selected post ID or conversation:<id>")
    if not argument.isdigit():
        raise AdapterError("x_fxtwitter requires a numeric selected post ID")
    return CONVERSATION_OPERATION, argument


def operation_params(operation: str, argument: str, cursor: str) -> Dict[str, str]:
    return {"subject": argument}


def fetch_native_page(carrier: transport.Transport, request: AdapterRequest) -> NativePage:
    operation, argument = operation_for(request)
    return fetch_one_page(
        DESCRIPTOR, carrier, params=operation_params(operation, argument, request.cursor),
        parse=lambda response: _page_from(response, operation, argument),
        native_order=NATIVE_ORDERS[operation],
    )
