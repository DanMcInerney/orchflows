"""K3 X read through FxTwitter, an independent operator, over five operations.

Measured 2026-08-17 (X, third party), keyless and answering the package's own
static identity — no browser identity, no rotation, no header set of any kind
beyond the one every route here sends:

- ``/2/search?q=spacex&feed=latest`` answered 200 with
  ``{"code", "results", "cursor"}`` — 20 statuses, each carrying ``id``,
  ``url``, ``text``, an ``author`` object, the platform's own
  ``likes``/``reposts``/``replies``/``quotes``/``bookmarks``, a ``views``
  that is an integer on some rows and ``null`` on others, and an exact
  ``created_timestamp`` beside the platform's own ``created_at`` spelling.
  ``feed=top`` answered 21. **This is the one keyless path to an X search in
  the roster**: the guest GraphQL search is refused and the syndication
  timeline is one handle's voice.
- ``/2/profile/<handle>/statuses`` answered the same envelope, 19 rows.
- ``/2/profile/<handle>`` answered ``{"code", "message", "user"}``.
- ``/2/conversation/<id>`` answered ``{"code", "status", "thread",
  "replies", "author", "cursor"}`` — one root, its self-thread, and 35
  replies each carrying its own counts and its own ``replying_to``.

**Paging is the origin's ``cursor.bottom``, spent under the name ``cursor``,
and only where it was proved.** That token sent back under that name on
``search`` and on ``profile/<h>/statuses`` answered a second page overlapping
the first by zero rows, twice each. The same token under the name ``next``
answered the top of the timeline again — 19 of 20 rows repeated — so ``next``
is not the name and is not sent. The conversation states a ``cursor.bottom``
too, and spending it under the name the two listing operations take answered
404 three times out of three, so **no continuation is surfaced for a
conversation**: a token whose spelling nobody proved would spend a call of the
core's on a refusal.

**This origin answers 404 to reads it answers 200 to seconds later.** One
continued ``profile/SpaceX/statuses`` read answered 200 and then 404 on the
immediately following identical read, twice in a row, deterministically. Nothing
here retries — one call is one page — so an intermittent refusal is typed as
the status it is and the step says so. A caller reading `http_status` from
this adapter is reading a real answer from this operator, not a gap in X.

**Every record is `third_party_archive`, and not the page alone.** This is an
independent operator reading X on this package's behalf, which is the same law
`reddit_archive` lives under: a record that travelled through a third party
carries that fact wherever it goes, because a reader holding one record cannot
correlate it back to a page to learn it. The namespace is still ``x`` — one
tweet read here and through the syndication timeline is one tweet, and strong
identity is what makes them group.

**A code inside a 200 is an answer about the read, not about X.** The
envelope states its own ``code``; a body arriving at HTTP 200 with a code
other than 200 is typed on that code — 404 is `empty`, carrying the origin's
own sentence, and anything else is `http_status`. A non-200 status line is
read first and decides on its own, so the two never argue.
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

# The one standing fact every record from this route carries. An independent
# operator answered about X; the reader is entitled to know that on the record
# it is holding rather than on a page it would have to go find.
THIRD_PARTY_ARCHIVE = "third_party_archive"
STANDING_LOSS = (THIRD_PARTY_ARCHIVE,)

DESCRIPTOR = AdapterDescriptor(
    adapter_id="x_fxtwitter",
    adapter_version="1",
    # An independent third-party archive of platform data, which is what this
    # operator is: it reads X and answers about X, and it is not X.
    access_class="K3",
    route_id=transport.FXTWITTER_API_ROUTE,
    platform="x",
    # The platform's namespace, not the operator's. A tweet read here and the
    # same tweet read off the syndication timeline are one tweet, and they can
    # only group by strong identity if they are named in one namespace.
    native_identity_namespace="x",
    representation_kind="native",
    operator_identity="fxtwitter",
    standing_loss=STANDING_LOSS,
    # The 2026-08-17 probes met no throttle across roughly thirty reads: no
    # 429, no `Retry-After`, and the one repeated refusal was a 404 that
    # alternated with a 200 rather than a rate refusal. A ceiling nobody
    # measured is not one to spend, so one read a second with a burst of five.
    min_interval_ms=1000,
    burst=5,
    # A status states an exact count of its own replies, under this name. It
    # states no count of anything called a comment, and neither is inferred.
    reply_count_metric="replies",
    # Twenty statuses a page, as measured on both listing operations.
    page_size=20,
)

# The five operations, spelled once each. A caller names one with a prefix,
# because one route serves five questions; absent a prefix the step's own shape
# decides — a query searches, and a target names one status whose conversation
# is read — and never the characters in the argument, so a query that happens
# to be all digits stays a query.
SEARCH_OPERATION = "search"
SEARCH_TOP_OPERATION = "search_top"
TIMELINE_OPERATION = "timeline"
USER_OPERATION = "user"
CONVERSATION_OPERATION = "conversation"
FXTWITTER_OPERATIONS = (
    SEARCH_OPERATION,
    SEARCH_TOP_OPERATION,
    TIMELINE_OPERATION,
    USER_OPERATION,
    CONVERSATION_OPERATION,
)

NATIVE_ORDERS = {
    SEARCH_OPERATION: "fxtwitter_search_latest_order",
    SEARCH_TOP_OPERATION: "fxtwitter_search_top_order",
    TIMELINE_OPERATION: "fxtwitter_timeline_order",
    USER_OPERATION: "fxtwitter_profile_order",
    CONVERSATION_OPERATION: "fxtwitter_conversation_order",
}

# The endpoint each operation names on this route's first path segment, and
# the collection the two-segment ones name on its third. This table is the
# reachable operation set: nothing else in this file reaches the carrier, and
# no segment here is composed from a caller's argument.
SEARCH_ENDPOINT = "search"
PROFILE_ENDPOINT = "profile"
CONVERSATION_ENDPOINT = "conversation"
STATUSES_COLLECTION = "statuses"

# The route's own path parameters, spent in the order the route declares them.
ENDPOINT_PARAM = "endpoint"
SUBJECT_PARAM = "subject"
COLLECTION_PARAM = "collection"

# The names this operator gives what else this module sends it.
QUERY_PARAM = "q"
FEED_PARAM = "feed"
CURSOR_PARAM = "cursor"

# The two rankings the search takes, in the operator's own words.
LATEST_FEED = "latest"
TOP_FEED = "top"

# The kinds of record this module emits.
POST_KIND = "post"
PROFILE_KIND = "profile"

# The envelope every answer carries, and the two codes this module tells
# apart inside a 200. Declared, never searched for.
CODE_KEY = "code"
MESSAGE_KEY = "message"
OK_CODE = 200
NOT_FOUND_CODE = 404

# Where each operation keeps what it returned.
RESULTS_KEY = "results"
STATUS_KEY = "status"
THREAD_KEY = "thread"
REPLIES_KEY = "replies"
USER_KEY = "user"
CURSOR_KEY = "cursor"
BOTTOM_KEY = "bottom"

# Every other key these payloads publish that this module reads, under the
# operator's own names. A status first.
ID_KEY = "id"
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

# Then a profile.
NAME_KEY = "name"
DESCRIPTION_KEY = "description"
JOINED_KEY = "joined"
LOCATION_KEY = "location"
PROTECTED_KEY = "protected"
WEBSITE_KEY = "website"
VERIFICATION_KEY = "verification"
VERIFIED_KEY = "verified"
TYPE_KEY = "type"

# The counts a status states, under this operator's own names for them. Every
# one is an exact integer where it is stated at all: `views` is `null` on a
# status nobody has viewed a reported number of times, and a null is a count
# nobody reported rather than a zero this module wrote.
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

# The counts a profile states, likewise.
FOLLOWERS_METRIC = "followers"
FOLLOWING_METRIC = "following"
MEDIA_COUNT_METRIC = "media_count"
STATUSES_METRIC = "statuses"
PROFILE_METRICS = (
    FOLLOWERS_METRIC,
    FOLLOWING_METRIC,
    LIKES_METRIC,
    MEDIA_COUNT_METRIC,
    STATUSES_METRIC,
)

# The facts each kind of row carries into `attributes`, in the order they are
# carried, each under the name the payload publishes it at and as the exact
# text the payload gave. A name absent from a row is absent from its record.
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
PROFILE_ATTRIBUTES = (LOCATION_KEY, JOINED_KEY, PROTECTED_KEY)
# Three facts carried under the key path the payload publishes them at, because
# each is nested and a bare last segment would name something else on the
# record.
AUTHOR_ID_ATTRIBUTE = "author.id"
REPLYING_TO_URL_ATTRIBUTE = "replying_to.url"
WEBSITE_URL_ATTRIBUTE = "website.url"
VERIFICATION_VERIFIED_ATTRIBUTE = "verification.verified"
VERIFICATION_TYPE_ATTRIBUTE = "verification.type"

# What each kind of row promises, so a record short of it says so. The
# measurement records what these operations answer and what a row carries; the
# row sets are this adapter's own declaration. An id is absent from both: a row
# without one is not a row of that kind at all.
STATUS_ROW_KEYS = (ID_KEY, TEXT_KEY, SCREEN_NAME_KEY, CREATED_TIMESTAMP_KEY)
PROFILE_ROW_KEYS = (ID_KEY, SCREEN_NAME_KEY, NAME_KEY, JOINED_KEY)

# The stamps this operator writes, and the one an artifact record holds. A
# status states an exact epoch second; a profile states only the platform's
# own English spelling of the moment it joined.
#
# The month is numbered before the spelling is read, because `%a` and `%b`
# read their names out of `LC_TIME`: a process that set a locale would stop
# reading this route's own English stamp and lose the time on every profile,
# for a reason that has nothing to do with the origin. The weekday is dropped
# rather than checked — it is derivable from the date, and auditing the
# origin's arithmetic is not this parser's job.
ROUTE_MONTHS = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)
ROUTE_INSTANT_FORMAT = "%m %d %H:%M:%S %z %Y"
RECORD_INSTANT_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
ROUTE_STAMP_PARTS = 6

HTTP_STATUS = "http_status"
MALFORMED_JSON = "malformed_json"
SCHEMA_DRIFT = "schema_drift"
FIELD_OMITTED = "field_omitted"


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


def _month_numbered(stamp: str) -> str:
    """This platform's stamp with its month name replaced by the month's number."""

    parts = stamp.split()
    if len(parts) != ROUTE_STAMP_PARTS or parts[1] not in ROUTE_MONTHS:
        return stamp
    return " ".join((str(ROUTE_MONTHS.index(parts[1]) + 1),) + tuple(parts[2:]))


def route_instant_to_utc_iso(stamped: Any) -> str:
    """A profile's ``joined`` stamp as the artifact's instant, or nothing.

    ``Thu Apr 23 21:53:30 +0000 2009`` is the shape the platform writes. A
    stamp stating an offset states an instant, so it is converted rather than
    relabelled; a spelling this format does not read is a missing time rather
    than an approximated one.
    """

    if not isinstance(stamped, str) or not stamped.strip():
        return ""
    try:
        moment = datetime.strptime(_month_numbered(stamped.strip()), ROUTE_INSTANT_FORMAT)
    except ValueError:
        return ""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).strftime(RECORD_INSTANT_FORMAT)


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


def _profile_record(position: int, user: Mapping[str, Any]) -> NativeRecord:
    """One account as this operator described it."""

    row = {
        ID_KEY: id_text(user.get(ID_KEY)),
        SCREEN_NAME_KEY: _text(user.get(SCREEN_NAME_KEY)),
        NAME_KEY: _text(user.get(NAME_KEY)),
        JOINED_KEY: route_instant_to_utc_iso(user.get(JOINED_KEY)),
    }
    named = _attributes(user, PROFILE_ATTRIBUTES)
    for name, value in (
        (WEBSITE_URL_ATTRIBUTE, scalar_text(_nested(user, WEBSITE_KEY, URL_KEY))),
        (
            VERIFICATION_VERIFIED_ATTRIBUTE,
            scalar_text(_nested(user, VERIFICATION_KEY, VERIFIED_KEY)),
        ),
        (VERIFICATION_TYPE_ATTRIBUTE, scalar_text(_nested(user, VERIFICATION_KEY, TYPE_KEY))),
    ):
        if value:
            named.append((name, value))
    return NativeRecord(
        canonical_content_kind=PROFILE_KIND,
        canonical_locator=_text(user.get(URL_KEY)),
        native_item_id=row[ID_KEY],
        title=row[NAME_KEY],
        body=_text(user.get(DESCRIPTION_KEY)),
        author=row[SCREEN_NAME_KEY],
        # When the account joined, which is the only moment a profile states.
        published_at=row[JOINED_KEY],
        engagement=_engagement(user, PROFILE_METRICS),
        attributes=tuple(named),
        native_position=position,
        loss=_record_loss(row, PROFILE_ROW_KEYS),
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


def _profile_records(rows: Sequence[Any]) -> Tuple[List[NativeRecord], int]:
    records: List[NativeRecord] = []
    unidentified = 0
    for user in rows:
        if not isinstance(user, Mapping) or not id_text(user.get(ID_KEY)):
            unidentified += 1
            continue
        records.append(_profile_record(len(records), user))
    return (records, unidentified)


RECORD_BUILDERS = {
    SEARCH_OPERATION: _status_records,
    SEARCH_TOP_OPERATION: _status_records,
    TIMELINE_OPERATION: _status_records,
    USER_OPERATION: _profile_records,
    CONVERSATION_OPERATION: _status_records,
}

# What each operation's rows are called where the answer keeps them, for the
# sentence a typed drift or a typed absence says out loud.
OPERATION_CONTAINERS = {
    SEARCH_OPERATION: RESULTS_KEY,
    SEARCH_TOP_OPERATION: RESULTS_KEY,
    TIMELINE_OPERATION: RESULTS_KEY,
    USER_OPERATION: USER_KEY,
    CONVERSATION_OPERATION: STATUS_KEY,
}

# The operations whose answer states a continuation this module proved: both
# search rankings and the timeline. The conversation states one too and it is
# not here, because the name it takes is not the one the others take and no
# read proved which.
PAGING_OPERATIONS = (SEARCH_OPERATION, SEARCH_TOP_OPERATION, TIMELINE_OPERATION)


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


def _rows_of(payload: Any, operation: str) -> Optional[Sequence[Any]]:
    """The rows this answer carries, or None when its container is not there.

    Three shapes across five operations, each read where its own endpoint puts
    it rather than found by looking for something list-shaped. A conversation
    is the root and then the replies under it, in the order the payload lays
    them out — and the root is read from ``thread`` when there is one, because
    a ``thread`` is the root's own self-thread and the measured payload puts
    the root itself at the head of it. Reading both would carry that root
    twice under one id, which is a duplicate this adapter would have made.
    ``status`` is the declared container either way: a payload without it is a
    payload this module no longer reads.
    """

    if not isinstance(payload, Mapping):
        return None
    if operation == USER_OPERATION:
        user = payload.get(USER_KEY)
        return (user,) if isinstance(user, Mapping) else None
    if operation == CONVERSATION_OPERATION:
        root = payload.get(STATUS_KEY)
        if not isinstance(root, Mapping):
            return None
        thread = payload.get(THREAD_KEY)
        rows: List[Any] = list(thread) if isinstance(thread, list) and thread else [root]
        replies = payload.get(REPLIES_KEY)
        if isinstance(replies, list):
            rows.extend(replies)
        return rows
    results = payload.get(RESULTS_KEY)
    return results if isinstance(results, list) else None


def next_cursor(payload: Any, operation: str) -> str:
    """The token the core spends for the next page, on the operations that proved one.

    The origin states it under ``cursor.bottom``. It is surfaced only where a
    read carrying rows came back, because this envelope states a token on
    every answer and states no "there is more" of its own: relaying one off an
    answer with nothing in it would be this module claiming a next page the
    origin never claimed.
    """

    if operation not in PAGING_OPERATIONS:
        return ""
    stated = _nested(payload, CURSOR_KEY, BOTTOM_KEY)
    return stated if isinstance(stated, str) else ""


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
            cursor_out=next_cursor(payload, operation),
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


def operation_for(request: AdapterRequest) -> Tuple[str, str]:
    """The operation this call performs, and the argument it performs it on.

    A caller names the operation, because one route answers five questions.
    Absent a name the step's own shape decides: a step naming only a query
    searches by recency, and a step naming a target reads that status's
    conversation, which is what freezing a hit from a search and asking for it
    again means. Nothing is inferred from the characters in an argument, so a
    query of digits stays a query and a handle written as a query stays one.
    """

    named = request.target_ids[0] if request.target_ids else request.query
    kind, separator, argument = named.partition(":")
    if separator and kind in FXTWITTER_OPERATIONS:
        return (kind, argument)
    return (CONVERSATION_OPERATION if request.target_ids else SEARCH_OPERATION, named)


def operation_params(operation: str, argument: str, cursor: str) -> Dict[str, str]:
    """The parameters one operation sends, in this route's and this operator's names.

    The endpoint and the subject are the route's own path segments, spent in
    the order the route declares them; the question and the ranking are
    ordinary query parameters. No window bound is sent: this operator publishes
    no term for one that this module could state without inventing a query
    syntax, so the core's own filter is the whole window.
    """

    params: Dict[str, str] = {}
    if operation in (SEARCH_OPERATION, SEARCH_TOP_OPERATION):
        params[ENDPOINT_PARAM] = SEARCH_ENDPOINT
        params[QUERY_PARAM] = argument
        params[FEED_PARAM] = TOP_FEED if operation == SEARCH_TOP_OPERATION else LATEST_FEED
    elif operation == CONVERSATION_OPERATION:
        params[ENDPOINT_PARAM] = CONVERSATION_ENDPOINT
        params[SUBJECT_PARAM] = argument
    else:
        params[ENDPOINT_PARAM] = PROFILE_ENDPOINT
        params[SUBJECT_PARAM] = argument
        if operation == TIMELINE_OPERATION:
            params[COLLECTION_PARAM] = STATUSES_COLLECTION
    if cursor and operation in PAGING_OPERATIONS:
        # The token the core froze, spent under the origin's own name. No next
        # one is derived here: the origin states it.
        params[CURSOR_PARAM] = cursor
    return params


def fetch_native_page(carrier: transport.Transport, request: AdapterRequest) -> NativePage:
    """Read one of the five declared operations and return exactly one NativePage.

    One call on one route. A search never also reads a profile, a conversation
    never also searches, and nothing here retries an answer it did not like —
    which matters on this origin more than on most, because it is measurably
    willing to answer 404 to a read it answered 200 to a second earlier.
    """

    operation, argument = operation_for(request)

    def parse(response: transport.TransportResponse) -> NativePage:
        return _page_from(response, operation, argument)

    return fetch_one_page(
        DESCRIPTOR,
        carrier,
        params=operation_params(operation, argument, request.cursor),
        parse=parse,
        native_order=NATIVE_ORDERS[operation],
    )
