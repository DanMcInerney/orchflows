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
from ._support.x_fxtwitter_records import (
    ID_KEY,
    STATUS_KEY,
    STANDING_LOSS,
    THIRD_PARTY_ARCHIVE,
    _nested,
    _profile_records,
    _status_records,
    epoch_to_utc_iso,
    exact_count,
    id_text,
    route_instant_to_utc_iso,
    scalar_text,
)

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

# The envelope every answer carries, and the two codes this module tells
# apart inside a 200. Declared, never searched for.
CODE_KEY = "code"
MESSAGE_KEY = "message"
OK_CODE = 200
NOT_FOUND_CODE = 404

# Where each operation keeps what it returned.
RESULTS_KEY = "results"
THREAD_KEY = "thread"
REPLIES_KEY = "replies"
USER_KEY = "user"
CURSOR_KEY = "cursor"
BOTTOM_KEY = "bottom"

HTTP_STATUS = "http_status"
MALFORMED_JSON = "malformed_json"
SCHEMA_DRIFT = "schema_drift"


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
