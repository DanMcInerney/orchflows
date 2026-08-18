"""K0 Bluesky's public AppView over two surfaces: post search, and one actor's feed.

Measured 2026-08-17 (Bluesky), keyless on both and answering two different
ways on *this host*:

- ``getAuthorFeed?actor=bsky.app&limit=100`` answered 200 with
  ``{"feed", "cursor"}`` — 100 entries, each a ``{"post": {...}}`` and
  sometimes a sibling ``reply`` or ``reason`` — and ``limit=3`` answered
  exactly three, so the page a call reads is the size it asked for.
- ``searchPosts`` answered **403 with an HTML body from the CDN in front of
  it** to every read tried, windowed and unwindowed alike, while
  ``getProfile`` and ``getAuthorFeed`` on the same origin answered 200 in the
  same minute. That is a per-host administrative block on one method, not a
  platform gap and not a credential this package is missing — the method is
  documented keyless and the roster's own liveness read is what decides. The
  smoke decides liveness per host: another host may well be served, and this
  module is written against the shape the method documents and returns.

The search payload's shape is read off the corpus this package holds:
``{"posts", "cursor", "hitsTotal"}``, where every post carries the same
``uri``/``cid``/``author``/``record`` object the author feed carries under
``post``. One parser reads both, because both surfaces answer with the same
post view.

**A refusal about who is asking is typed as one.** 401 and 403 are
`auth_required` — "the origin refused over who is asking" — and the warning
carries the refusing body's own first readable sentence, so an operator reads
the CDN's words rather than this module's guess at them. Every other non-200
is the status it is. Nothing here retries, rotates an identity, or reaches a
second route when the first refuses.

**An absence is not a shape change.** An empty ``posts`` or ``feed`` list is
the origin saying there is nothing, so it is `empty`; a payload with no such
key at all is `schema_drift`, and so is a feed carrying rows where not one of
them names a post. Typing the second as the first would report Bluesky as
quiet while this package reads keys the AppView no longer publishes.

**A count nobody reported is not zero.** Every count is carried only where
the payload stated an exact integer, under the AppView's own name for it.
"""

from __future__ import annotations

import json
from html.parser import HTMLParser
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
from ._support import bluesky_extract as _extract

URI_KEY = _extract.URI_KEY
FIELD_OMITTED = "field_omitted"
exact_count = _extract.exact_count
_text = _extract._text


def _post_record(position: int, post: Mapping[str, Any]) -> NativeRecord:
    return _extract._post_record(position, post, FIELD_OMITTED)

# The search surface, and this adapter's primary: a step naming a query and no
# operation is asking Bluesky to search.
DESCRIPTOR = AdapterDescriptor(
    adapter_id="bluesky",
    adapter_version="1",
    access_class="K0",
    route_id=transport.BLUESKY_SEARCH_POSTS_ROUTE,
    platform="bluesky",
    native_identity_namespace="bluesky",
    representation_kind="native",
    operator_identity="bluesky",
    # The 2026-08-17 probes met no throttle on the surface that answered — the
    # one that refused did so on identity and not on rate, and a 403 about who
    # is asking states no interval to respect. An unmeasured ceiling is not one
    # to spend, so one read a second with a burst of five rather than a figure
    # this adapter would have had to invent.
    min_interval_ms=1000,
    burst=5,
    # A post states an exact count of its own replies. It states no count of
    # anything called a comment, and neither name is inferred.
    reply_count_metric="replyCount",
    # The most either method serves per read, and what this module asks for:
    # `limit=100` answered 100 rows and `limit=3` answered three, so the page
    # is the stated size rather than the origin's default of the day.
    page_size=100,
)

# One actor's own feed: the same origin, a different method, and its own route
# budget because a ceiling belongs to the route that sets it.
AUTHOR_FEED_DESCRIPTOR = AdapterDescriptor(
    adapter_id="bluesky",
    adapter_version="1",
    access_class="K0",
    route_id=transport.BLUESKY_AUTHOR_FEED_ROUTE,
    platform="bluesky",
    native_identity_namespace="bluesky",
    representation_kind="native",
    operator_identity="bluesky",
    min_interval_ms=1000,
    burst=5,
    reply_count_metric="replyCount",
    page_size=100,
)

# Every route this adapter can reach, one descriptor each. The core collects
# route budgets from here, because a route nothing declares a budget for is a
# route the scheduler refuses to pace.
SURFACE_DESCRIPTORS = (DESCRIPTOR, AUTHOR_FEED_DESCRIPTOR)

# The two operations, spelled once each. A caller names one with a prefix;
# absent a prefix both a query and a target ask this adapter to search, because
# a search is what a bare argument means here and an actor is not inferable
# from the characters in one. A caller who wants an actor's feed says so, and
# a decentralised identifier — `did:plc:...` — is written after the prefix
# exactly as the network spells it.
SEARCH_OPERATION = "search"
AUTHOR_OPERATION = "author"
BLUESKY_OPERATIONS = (SEARCH_OPERATION, AUTHOR_OPERATION)

OPERATION_SURFACES = {
    SEARCH_OPERATION: DESCRIPTOR,
    AUTHOR_OPERATION: AUTHOR_FEED_DESCRIPTOR,
}

NATIVE_ORDERS = {
    SEARCH_OPERATION: "bluesky_search_latest_order",
    AUTHOR_OPERATION: "bluesky_author_feed_order",
}

# The names the AppView gives what this module sends it: the question, the
# actor, the sort, the window, the page, and the continuation.
QUERY_PARAM = "q"
ACTOR_PARAM = "actor"
SORT_PARAM = "sort"
SINCE_PARAM = "since"
UNTIL_PARAM = "until"
LIMIT_PARAM = "limit"
CURSOR_PARAM = "cursor"

# The sort this module asks for, always. A search is a recency read here: the
# core's window is a bound on time, and ranking by the AppView's own relevance
# would hand it rows outside the window ahead of rows inside it.
LATEST_SORT = "latest"
PAGE_LIMIT = "100"

# Where each surface keeps what it returned, and where a feed entry keeps its
# post. Declared, never searched for: the whole value of a typed drift is that
# it says the payload moved rather than that Bluesky went quiet.
POSTS_KEY = "posts"
FEED_KEY = "feed"
POST_KEY = "post"
CURSOR_KEY = "cursor"

# How much of a refusing body's own words ride into a warning. A refusal page
# is a page, and a warning is a sentence.
REFUSAL_SENTENCE_LIMIT = 200
# What a refusal body says nothing in, so nothing is read out of it.
UNREADABLE_TAGS = ("script", "style")
# The key an AppView error body states its own sentence under.
MESSAGE_KEY = "message"

# The two statuses that are the origin declining over who is asking rather
# than over what was asked for.
REFUSING_STATUSES = (401, 403)

HTTP_STATUS = "http_status"
MALFORMED_JSON = "malformed_json"
SCHEMA_DRIFT = "schema_drift"
AUTH_REQUIRED = "auth_required"


class _ReadableTextParser(HTMLParser):
    """Every run of readable text in one document, in the order it was written.

    A refusing body is whatever the party in front of the origin chose to send,
    so nothing is looked for by name: the text is collected and the first run
    with anything in it is the sentence. Script and style hold instructions to
    a browser rather than words to a reader, and are skipped.
    """

    def __init__(self) -> None:
        HTMLParser.__init__(self, convert_charrefs=True)
        self.runs: List[str] = []
        self._silent = 0

    def handle_starttag(self, tag, attrs):
        if tag in UNREADABLE_TAGS:
            self._silent += 1

    def handle_endtag(self, tag):
        if tag in UNREADABLE_TAGS and self._silent:
            self._silent -= 1

    def handle_data(self, data):
        if self._silent:
            return
        held = " ".join(data.split())
        if held:
            self.runs.append(held)


def refusal_sentence(body: str) -> str:
    """The refusing party's own first readable sentence, whatever it sent.

    An AppView error is JSON and states its sentence under ``message``; the
    CDN in front of it answers in HTML and states one in the markup. Both are
    the origin's own words, and a warning that carried this module's guess at
    them instead would tell an operator nothing about which party refused.
    """

    if not body:
        return ""
    try:
        payload = json.loads(body)
    except ValueError:
        payload = None
    if isinstance(payload, Mapping):
        stated = payload.get(MESSAGE_KEY)
        if isinstance(stated, str) and stated.strip():
            return " ".join(stated.split())[:REFUSAL_SENTENCE_LIMIT]
        return ""
    parser = _ReadableTextParser()
    parser.feed(body)
    parser.close()
    return parser.runs[0][:REFUSAL_SENTENCE_LIMIT] if parser.runs else ""


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
    warnings: Tuple[str, ...],
) -> NativePage:
    return _answered(
        descriptor, response, native_order, outcome="failed", warnings=warnings, loss=(loss,)
    )


def _status_refused(
    descriptor: AdapterDescriptor,
    response: transport.TransportResponse,
    native_order: str,
) -> Optional[NativePage]:
    """The typed page for an answer that was not a 200, or None for one that was.

    Two kinds, told apart by the status line alone and never by the body: 401
    and 403 are the origin refusing over who is asking, and everything else is
    the status it is. What the body says rides along as the refusing party's
    own sentence, and decides nothing — a body that argued its way into a
    different loss code is how a local block gets recorded as a platform gap.
    """

    if response.status == 200:
        return None
    stated = refusal_sentence(response.body)
    if response.status in REFUSING_STATUSES:
        warnings = (
            "route {0} refused this read over who is asking: http status {1}".format(
                descriptor.route_id, response.status
            ),
        )
        if stated:
            warnings = warnings + ("the refusing body says: " + stated,)
        return _failed(descriptor, response, native_order, AUTH_REQUIRED, warnings)
    warnings = ("http status {0} from {1}".format(response.status, descriptor.route_id),)
    if stated:
        warnings = warnings + ("the answering body says: " + stated,)
    return _failed(descriptor, response, native_order, HTTP_STATUS, warnings)


def _payload_of(
    descriptor: AdapterDescriptor,
    response: transport.TransportResponse,
    native_order: str,
    operation: str,
) -> Tuple[Any, Optional[NativePage]]:
    """One answer's json, or the typed page that says why there is none."""

    refused = _status_refused(descriptor, response, native_order)
    if refused is not None:
        return (None, refused)
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
                ("{0} answered 200 with no json body".format(operation),),
            ),
        )


def next_cursor(payload: Any) -> str:
    """The continuation the AppView itself published, or nothing.

    The origin states it; nothing is derived from how many rows came back.
    An adapter that derived one would be the thing deciding there is more.
    """

    stated = payload.get(CURSOR_KEY) if isinstance(payload, Mapping) else None
    return stated if isinstance(stated, str) else ""


def _posts_of(payload: Any, operation: str) -> Optional[List[Any]]:
    """The post views this answer carries, or None when its container is not there.

    The search method answers with posts and the author feed answers with feed
    entries wrapping them, and each is read where its own method puts it rather
    than found by looking for something list-shaped. An entry carrying no
    ``post`` contributes nothing and is counted as unidentified by the caller.
    """

    if not isinstance(payload, Mapping):
        return None
    if operation == AUTHOR_OPERATION:
        feed = payload.get(FEED_KEY)
        if not isinstance(feed, list):
            return None
        return [entry.get(POST_KEY) if isinstance(entry, Mapping) else None for entry in feed]
    posts = payload.get(POSTS_KEY)
    return posts if isinstance(posts, list) else None


def _page_from(
    response: transport.TransportResponse, operation: str, argument: str
) -> NativePage:
    """Turn one answer the origin itself sent into exactly one page."""

    descriptor = OPERATION_SURFACES[operation]
    native_order = NATIVE_ORDERS[operation]
    container = POSTS_KEY if operation == SEARCH_OPERATION else FEED_KEY
    payload, refused = _payload_of(descriptor, response, native_order, operation)
    if refused is not None:
        return refused

    rows = _posts_of(payload, operation)
    if rows is None:
        return _failed(
            descriptor,
            response,
            native_order,
            SCHEMA_DRIFT,
            (
                "{0} answered 200 with no {1} list: the payload this adapter reads has"
                " changed shape".format(operation, container),
            ),
        )
    records: List[NativeRecord] = []
    unidentified = 0
    for post in rows:
        if not isinstance(post, Mapping) or not _text(post.get(URI_KEY)):
            # A row this AppView did not identify is not a row: a record naming
            # nothing groups with nothing and addresses nothing.
            unidentified += 1
            continue
        records.append(_post_record(len(records), post))
    if records:
        warnings = (
            (
                "{0} answered 200 with {1} row(s) naming no {2}: they are not rows"
                " this adapter can identify".format(operation, unidentified, URI_KEY),
            )
            if unidentified
            else ()
        )
        return _answered(
            descriptor,
            response,
            native_order,
            records=tuple(records),
            cursor_out=next_cursor(payload),
            warnings=warnings,
        )
    if rows:
        # The container is present and holds rows, and not one of them names a
        # post. That is the payload reshaping, not an answer with nothing in
        # it: reporting it as "there is nothing here" is the one thing a caller
        # cannot tell from a real absence.
        return _failed(
            descriptor,
            response,
            native_order,
            SCHEMA_DRIFT,
            (
                "{0} answered 200 with {1} row(s) and no {2} on any of them: the"
                " payload has changed shape".format(operation, len(rows), URI_KEY),
            ),
        )
    return _answered(
        descriptor,
        response,
        native_order,
        outcome="empty",
        cursor_out=next_cursor(payload),
        warnings=(
            "{0} answered 200 with an empty {1} list: {2} has nothing here".format(
                operation, container, argument or operation
            ),
        ),
    )


def operation_for(request: AdapterRequest) -> Tuple[str, str]:
    """The operation this call performs, and the argument it performs it on.

    A caller names the operation, because two methods answer two different
    questions. Absent a name both shapes of step search: a query is a query,
    and a target this adapter was handed without a prefix is asked about the
    same way, because an actor is a thing a caller names rather than a thing
    inferred from the characters in an argument. A handle, a decentralised
    identifier, and a query that happens to contain a colon all stay whatever
    the caller said they were.
    """

    named = request.target_ids[0] if request.target_ids else request.query
    kind, separator, argument = named.partition(":")
    if separator and kind in BLUESKY_OPERATIONS:
        return (kind, argument)
    return (SEARCH_OPERATION, named)


def operation_params(
    operation: str, argument: str, request: AdapterRequest
) -> Dict[str, str]:
    """The parameters one operation sends, in the AppView's own names.

    The step's window travels to the search method in that method's own terms
    — ``since`` and ``until`` take the manifest's instant spelling as it is
    written — so the origin bounds what it sends rather than this module
    dropping rows after the fact. The author feed takes no bound on time and
    is sent none; the core's own filter is the whole window there. No row is
    ever dropped here either way: dropping is the core's, so a drop is counted
    once and in one place.
    """

    if operation == AUTHOR_OPERATION:
        params: Dict[str, str] = {ACTOR_PARAM: argument, LIMIT_PARAM: PAGE_LIMIT}
    else:
        params = {
            QUERY_PARAM: argument,
            SORT_PARAM: LATEST_SORT,
            LIMIT_PARAM: PAGE_LIMIT,
        }
        if request.window_start:
            params[SINCE_PARAM] = request.window_start
        if request.window_end:
            params[UNTIL_PARAM] = request.window_end
    if request.cursor:
        # The continuation the core froze, spent under the origin's own name.
        # No next one is derived here: the origin states it.
        params[CURSOR_PARAM] = request.cursor
    return params


def fetch_native_page(carrier: transport.Transport, request: AdapterRequest) -> NativePage:
    """Read one AppView method once and return exactly one NativePage.

    One call, one method: a search never also reads a feed, and a feed read
    never also searches. Which page to read next is the core's, from the
    cursor this one publishes.
    """

    operation, argument = operation_for(request)
    descriptor = OPERATION_SURFACES[operation]

    def parse(response: transport.TransportResponse) -> NativePage:
        return _page_from(response, operation, argument)

    return fetch_one_page(
        descriptor,
        carrier,
        params=operation_params(operation, argument, request),
        parse=parse,
        native_order=NATIVE_ORDERS[operation],
    )
