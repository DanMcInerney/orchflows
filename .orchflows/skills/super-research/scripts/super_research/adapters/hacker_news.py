"""K0 Hacker News over two surfaces: Algolia for search, Firebase for the tree.

Measured 2026-08-10 (findings.md §1, "Carry-over routes"):
``hn.algolia.com/api/v1/search_by_date`` answered 200 with full-text HN search,
``hn.algolia.com/api/v1/search?tags=comment`` answered 200 for comment search,
and ``hacker-news.firebaseio.com/v0/item/<id>`` answered 200 with ``by``,
``descendants`` and the ``kids`` tree. Reading Algolia beside Firebase is what
makes HN searchable at all: the prior spec's Firebase-only adapter could list
and hydrate and never search, and the evidence records the upgrade as strict.

**Two origins, two routes, two calls.** A search is one call to Algolia and an
item is one call to Firebase, and no call here is ever both — this module holds
one descriptor per surface and spends exactly one of them per call. Walking a
``kids`` tree is therefore one call per item with the core choosing the next
one, because an adapter that walked it would turn one bounded call into a crawl
whose size nobody declared.

**An absence is not a shape change, in either direction.** Firebase answers a
request for an item it does not have with 200 and the body ``null``, and
Algolia answers a query nothing matched with 200 and an empty ``hits`` list.
Both are the origin saying there is nothing there, so both are `empty` and say
so out loud; only a payload that no longer carries the container this module
declares is ``schema_drift``. Typing an absence as drift sends a reader hunting
a shape change over an ordinary answer, and typing drift as an absence reports
the platform as quiet while this package reads the wrong keys.

**Neither surface has an ``auth_required`` branch, deliberately.** Both are
documented keyless, so no status either returns is a statement that a
credential was needed: a refusal here is the origin declining this read, and it
is recorded as the status it is.
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

# Where an HN item lives. It is HN's own site and not either route's origin, so
# `transport.origin_locator` cannot resolve it — that function resolves against
# the route that answered, which here would name Algolia or Firebase. Neither
# payload publishes an item's address in any form, so it is composed from the
# id, the way the X syndication reader composes a post's address from a handle
# and an id: a host no route in this package reads is not a host the transport
# seam owns.
HN_ITEM_ORIGIN = "https://news.ycombinator.com"
HN_ITEM_PATH = "/item?id="

# The item types HN names, shared by both surfaces: Firebase states one in
# `type` and Algolia states one in `_tags`. A row naming none of them is not a
# row this adapter can type, and typing it anyway would be a guess about what
# HN meant.
ITEM_TYPES = ("story", "comment", "poll", "pollopt", "job")
STORY_TYPE = "story"
COMMENT_TYPE = "comment"
TEXT_TYPES = (COMMENT_TYPE, "pollopt")

# The Firebase item surface. It is this adapter's primary descriptor because a
# request naming a target hydrates one item, which is the call the core makes
# most and the one an unprefixed target id means.
DESCRIPTOR = AdapterDescriptor(
    adapter_id="hacker_news",
    adapter_version="1",
    access_class="K0",
    route_id=transport.HN_FIREBASE_ITEM_ROUTE,
    platform="hackernews",
    native_identity_namespace="hackernews",
    representation_kind="native",
    operator_identity="hacker-news",
    # findings.md §1 records "no throttle observed" for HN and no latency for
    # either surface. An unmeasured ceiling is not one to spend, so all three
    # numbers stay the protocol's conservative defaults rather than a figure
    # this adapter would have had to invent.
    #
    # Firebase names a story's comment count `descendants`. Algolia names the
    # same quantity `num_comments`, and each surface declares the name its own
    # route reports — the two are never aliased into one.
    comment_count_metric="descendants",
)

# The Algolia search surface: the same adapter, a different origin, and its own
# route budget because a ceiling belongs to the origin that sets it.
SEARCH_DESCRIPTOR = AdapterDescriptor(
    adapter_id="hacker_news",
    adapter_version="1",
    access_class="K0",
    route_id=transport.HN_ALGOLIA_SEARCH_ROUTE,
    platform="hackernews",
    native_identity_namespace="hackernews",
    representation_kind="native",
    # HN's own index of itself, operated by Algolia and published by HN. The
    # evidence classes it `K0` documented-keyless rather than `K3`, so nothing
    # read here carries `third_party_archive`: this is not an independent
    # mirror speaking for the platform.
    operator_identity="algolia",
    comment_count_metric="num_comments",
)

# Every route this adapter can reach, one descriptor each. The core collects
# route budgets from here, because a route nothing declares a budget for is a
# route the scheduler refuses to pace.
SURFACE_DESCRIPTORS = (DESCRIPTOR, SEARCH_DESCRIPTOR)

# The four operations, spelled once each. A caller names one with a prefix,
# because two surfaces answer different questions; absent a prefix the step's
# own shape decides, and never the characters in the argument.
ITEM_OPERATION = "item"
SEARCH_OPERATION = "search"
SEARCH_BY_DATE_OPERATION = "search_by_date"
COMMENT_SEARCH_OPERATION = "comments"
HN_OPERATIONS = (
    ITEM_OPERATION,
    SEARCH_OPERATION,
    SEARCH_BY_DATE_OPERATION,
    COMMENT_SEARCH_OPERATION,
)

# Which endpoint each search operation asks, and under which tag. `search`
# ranks by relevance and `search_by_date` by recency; the tag selects rows
# rather than an endpoint, so it travels as a query parameter.
SEARCH_ENDPOINTS = {
    SEARCH_OPERATION: (SEARCH_OPERATION, ""),
    SEARCH_BY_DATE_OPERATION: (SEARCH_BY_DATE_OPERATION, ""),
    COMMENT_SEARCH_OPERATION: (SEARCH_OPERATION, COMMENT_TYPE),
}

NATIVE_ORDERS = {
    SEARCH_OPERATION: "hn_algolia_relevance_order",
    SEARCH_BY_DATE_OPERATION: "hn_algolia_recency_order",
    COMMENT_SEARCH_OPERATION: "hn_algolia_relevance_order",
    ITEM_OPERATION: "hn_firebase_item_order",
}

# Where each surface keeps what it returned, and what one row of it is.
# Declared, never searched for: the whole value of a typed drift is that it
# says the payload moved rather than that HN went quiet.
HITS_KEY = "hits"
PAGE_KEY = "page"
PAGE_COUNT_KEY = "nbPages"
TAGS_KEY = "_tags"
OBJECT_ID_KEY = "objectID"

# Every other key these two payloads publish that this module reads, under
# their own names.
TITLE_KEY = "title"
URL_KEY = "url"
AUTHOR_KEY = "author"
CREATED_AT_KEY = "created_at"
STORY_TEXT_KEY = "story_text"
COMMENT_TEXT_KEY = "comment_text"
STORY_ID_KEY = "story_id"
PARENT_ID_KEY = "parent_id"
POINTS_METRIC = "points"
NUM_COMMENTS_METRIC = "num_comments"

ITEM_ID_KEY = "id"
ITEM_TYPE_KEY = "type"
BY_KEY = "by"
TIME_KEY = "time"
TEXT_KEY = "text"
PARENT_KEY = "parent"
KIDS_KEY = "kids"
SCORE_METRIC = "score"
DESCENDANTS_METRIC = "descendants"

# What each kind of row promises, so a record short of it says so. The evidence
# enumerates a field set for the item route only (`by`, `descendants`, `kids`);
# the search rows are this adapter's own declaration. An id is absent from all
# of them: a row without one is not a row of that kind at all.
HIT_ROW_KEYS = {
    COMMENT_TYPE: (OBJECT_ID_KEY, COMMENT_TEXT_KEY, AUTHOR_KEY, CREATED_AT_KEY),
}
DEFAULT_HIT_ROW_KEYS = (OBJECT_ID_KEY, TITLE_KEY, AUTHOR_KEY, CREATED_AT_KEY)
ITEM_ROW_KEYS = {
    COMMENT_TYPE: (ITEM_ID_KEY, ITEM_TYPE_KEY, BY_KEY, TIME_KEY, TEXT_KEY),
    "pollopt": (ITEM_ID_KEY, ITEM_TYPE_KEY, BY_KEY, TIME_KEY, TEXT_KEY),
}
DEFAULT_ITEM_ROW_KEYS = (ITEM_ID_KEY, ITEM_TYPE_KEY, BY_KEY, TIME_KEY, TITLE_KEY)

# The stamps these routes emit, and the one an artifact record holds. Algolia
# writes an ISO instant with milliseconds; Firebase writes epoch seconds.
ROUTE_INSTANT_FORMAT = "%Y-%m-%dT%H:%M:%S"
RECORD_INSTANT_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

SCHEMA_DRIFT = "schema_drift"
MALFORMED_JSON = "malformed_json"
HTTP_STATUS = "http_status"


def item_locator(item_id: str) -> str:
    """One item's address on HN's own site, or nothing without an id."""

    return HN_ITEM_ORIGIN + HN_ITEM_PATH + item_id if item_id else ""


def _text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def exact_count(value: Any) -> Optional[int]:
    """One count a surface published as an exact number, or nothing at all.

    A bool is not a count and a string is not one either: both surfaces publish
    their counts as json numbers, so anything else is a field this adapter was
    not given rather than one it can recover.
    """

    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def id_text(value: Any) -> str:
    """One HN id as its decimal spelling, which is the only form a record holds.

    Firebase publishes an id as a json number and Algolia publishes the same id
    as a string, so one of the two has to be written the other's way for a
    search hit and an item read to name the same thing. Nothing is rounded,
    formatted, or made here: an identifier's decimal digits are the identifier.
    """

    if isinstance(value, bool):
        return ""
    if isinstance(value, int):
        return str(value)
    return value if isinstance(value, str) else ""


def route_instant_to_utc_iso(created_at: Any) -> str:
    """Algolia's stamp as the artifact's instant, or nothing.

    Milliseconds and a trailing ``Z`` are the shape this index writes.
    Anything else is a missing time rather than an approximated one.
    """

    if not isinstance(created_at, str) or not created_at.strip():
        return ""
    text = created_at.strip()
    if text.endswith("Z"):
        text = text[:-1]
    text = text.split(".")[0]
    try:
        moment = datetime.strptime(text, ROUTE_INSTANT_FORMAT)
    except ValueError:
        return ""
    return moment.replace(tzinfo=timezone.utc).strftime(RECORD_INSTANT_FORMAT)


def epoch_to_utc_iso(seconds: Any) -> str:
    """Firebase's stamp as the artifact's instant, or nothing.

    Epoch seconds are an exact instant, so this loses no precision and states
    none it was not given: a value that is not a whole number of seconds is a
    missing time.
    """

    if isinstance(seconds, bool) or not isinstance(seconds, int):
        return ""
    return datetime.fromtimestamp(seconds, tz=timezone.utc).strftime(RECORD_INSTANT_FORMAT)


def _missing(row: Mapping[str, Any], keys: Sequence[str]) -> Tuple[str, ...]:
    """Which of this row's declared fields the payload did not report.

    Absence, never falsehood: a story nobody has voted on reports zero points,
    and zero is a count. Marking it omitted would erase the one distinction
    `field_omitted` exists to make.
    """

    return tuple(key for key in keys if row.get(key) is None or row.get(key) == "")


def _engagement(pairs: Sequence[Tuple[str, Any]]) -> Tuple[Tuple[str, int], ...]:
    counted = []
    for name, value in pairs:
        exact = exact_count(value)
        if exact is not None:
            counted.append((name, exact))
    return tuple(counted)


def hit_kind(hit: Mapping[str, Any]) -> str:
    """The item type this index row states, or nothing when it states none.

    Algolia writes the type as the first of the row's own `_tags`, beside tags
    for the author and the story. The tag is read rather than guessed at from
    the fields present: a row with a `comment_text` is a comment because HN
    says so, not because this module recognized a shape.
    """

    tags = hit.get(TAGS_KEY)
    for tag in tags if isinstance(tags, list) else ():
        if tag in ITEM_TYPES:
            return tag
    return ""


def _hit_record(position: int, hit: Mapping[str, Any], kind: str) -> NativeRecord:
    """One index row as Algolia listed it."""

    item_id = id_text(hit.get(OBJECT_ID_KEY))
    row = {
        OBJECT_ID_KEY: item_id,
        TITLE_KEY: _text(hit.get(TITLE_KEY)),
        AUTHOR_KEY: _text(hit.get(AUTHOR_KEY)),
        CREATED_AT_KEY: route_instant_to_utc_iso(hit.get(CREATED_AT_KEY)),
        COMMENT_TEXT_KEY: _text(hit.get(COMMENT_TEXT_KEY)),
    }
    # A comment's own text, or a story's own text where it has one. The parent
    # story's title travels on a comment row too, and is deliberately not read:
    # it is a fact about the story rather than about this row.
    body = row[COMMENT_TEXT_KEY] if kind in TEXT_TYPES else _text(hit.get(STORY_TEXT_KEY))
    named: List[Tuple[str, str]] = []
    link = _text(hit.get(URL_KEY))
    if link:
        named.append((URL_KEY, link))
    story_id = id_text(hit.get(STORY_ID_KEY))
    if story_id:
        # The root this row sits under, which `native_parent_id` does not mean:
        # a reply's parent is the comment it answers.
        named.append((STORY_ID_KEY, story_id))
    return NativeRecord(
        canonical_content_kind=kind,
        canonical_locator=item_locator(item_id),
        native_item_id=item_id,
        native_parent_id=id_text(hit.get(PARENT_ID_KEY)),
        title="" if kind in TEXT_TYPES else row[TITLE_KEY],
        body=body,
        author=row[AUTHOR_KEY],
        published_at=row[CREATED_AT_KEY],
        engagement=_engagement(
            ((POINTS_METRIC, hit.get(POINTS_METRIC)),
             (NUM_COMMENTS_METRIC, hit.get(NUM_COMMENTS_METRIC)))
        ),
        attributes=tuple(named),
        native_position=position,
        loss=("field_omitted",)
        if _missing(row, HIT_ROW_KEYS.get(kind, DEFAULT_HIT_ROW_KEYS))
        else (),
    )


def _item_record(item: Mapping[str, Any], kind: str) -> NativeRecord:
    """One item as Firebase holds it, with the ids of what hangs off it."""

    item_id = id_text(item.get(ITEM_ID_KEY))
    row = {
        ITEM_ID_KEY: item_id,
        ITEM_TYPE_KEY: kind,
        BY_KEY: _text(item.get(BY_KEY)),
        TIME_KEY: epoch_to_utc_iso(item.get(TIME_KEY)),
        TITLE_KEY: _text(item.get(TITLE_KEY)),
        TEXT_KEY: _text(item.get(TEXT_KEY)),
    }
    named: List[Tuple[str, str]] = []
    link = _text(item.get(URL_KEY))
    if link:
        named.append((URL_KEY, link))
    kids = item.get(KIDS_KEY)
    for kid in kids if isinstance(kids, list) else ():
        # The tree, one id at a time, in the order HN listed them. They travel
        # as ids rather than as a walked tree because walking one here would
        # make a bounded call a crawl: the core spends these as its next calls.
        kid_id = id_text(kid)
        if kid_id:
            named.append((KIDS_KEY, kid_id))
    return NativeRecord(
        canonical_content_kind=kind,
        canonical_locator=item_locator(item_id),
        native_item_id=item_id,
        native_parent_id=id_text(item.get(PARENT_KEY)),
        title=row[TITLE_KEY],
        body=row[TEXT_KEY],
        author=row[BY_KEY],
        published_at=row[TIME_KEY],
        # A comment carries neither of these and a story carries both. An
        # absent count is left absent rather than reported as a zero nobody
        # published.
        engagement=_engagement(
            ((SCORE_METRIC, item.get(SCORE_METRIC)),
             (DESCENDANTS_METRIC, item.get(DESCENDANTS_METRIC)))
        ),
        attributes=tuple(named),
        native_position=0,
        loss=("field_omitted",)
        if _missing(row, ITEM_ROW_KEYS.get(kind, DEFAULT_ITEM_ROW_KEYS))
        else (),
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
        descriptor,
        response,
        native_order,
        outcome="failed",
        warnings=(warning,),
        loss=(loss,),
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


def _search_page(
    response: transport.TransportResponse, payload: Any, operation: str
) -> NativePage:
    native_order = NATIVE_ORDERS[operation]
    hits = payload.get(HITS_KEY) if isinstance(payload, Mapping) else None
    if not isinstance(hits, list):
        return _failed(
            SEARCH_DESCRIPTOR,
            response,
            native_order,
            SCHEMA_DRIFT,
            "{0} answered 200 with no {1} list: the payload this adapter reads has"
            " changed shape".format(operation, HITS_KEY),
        )

    records: List[NativeRecord] = []
    untyped = 0
    for hit in hits:
        if not isinstance(hit, Mapping):
            untyped += 1
            continue
        kind = hit_kind(hit)
        if not kind or not id_text(hit.get(OBJECT_ID_KEY)):
            # A row this index did not type, or did not identify, is not a row:
            # a record naming nothing groups with nothing and addresses nothing.
            untyped += 1
            continue
        records.append(_hit_record(len(records), hit, kind))

    warnings: List[str] = []
    if untyped:
        warnings.append(
            "{0} answered 200 with {1} hit(s) carrying no item type in {2} or no"
            " {3}: they are not rows this adapter can identify".format(
                operation, untyped, TAGS_KEY, OBJECT_ID_KEY
            )
        )
    if not records:
        warnings.append(
            "{0} answered 200 with a {1} list holding nothing this adapter could"
            " read: this query matched nothing".format(operation, HITS_KEY)
        )
    return _answered(
        SEARCH_DESCRIPTOR,
        response,
        native_order,
        records=tuple(records),
        outcome="ok" if records else "empty",
        cursor_out=next_page_of(payload),
        warnings=tuple(warnings),
    )


def next_page_of(payload: Any) -> str:
    """The page after this one, as the index itself counts them.

    Both numbers are Algolia's: it states which page answered and how many it
    holds. Deriving one from the number of rows returned would make this
    adapter the thing that decides there is more.
    """

    if not isinstance(payload, Mapping):
        return ""
    page = exact_count(payload.get(PAGE_KEY))
    pages = exact_count(payload.get(PAGE_COUNT_KEY))
    if page is None or pages is None or page + 1 >= pages:
        return ""
    return str(page + 1)


def _item_page(
    response: transport.TransportResponse, payload: Any, item_id: str
) -> NativePage:
    native_order = NATIVE_ORDERS[ITEM_OPERATION]
    if payload is None:
        # Firebase's own way of saying it holds no such item. An answer, not a
        # failure, and never the payload having moved.
        return _answered(
            DESCRIPTOR,
            response,
            native_order,
            outcome="empty",
            warnings=(
                "{0} answered 200 with null: HN holds no item {1}".format(
                    ITEM_OPERATION, item_id
                ),
            ),
        )
    kind = _text(payload.get(ITEM_TYPE_KEY)) if isinstance(payload, Mapping) else ""
    if kind not in ITEM_TYPES or not id_text(payload.get(ITEM_ID_KEY)):
        return _failed(
            DESCRIPTOR,
            response,
            native_order,
            SCHEMA_DRIFT,
            "{0} answered 200 with a body stating no {1} this adapter knows and no"
            " {2}: the payload this adapter reads has changed shape".format(
                ITEM_OPERATION, ITEM_TYPE_KEY, ITEM_ID_KEY
            ),
        )
    return _answered(
        DESCRIPTOR, response, native_order, records=(_item_record(payload, kind),)
    )


def operation_for(request: AdapterRequest) -> Tuple[str, str]:
    """The operation this call performs, and the argument it performs it on.

    A caller names the operation, because two surfaces answer two different
    questions. Absent a name, the step's own shape decides: a step naming a
    target hydrates that item, and a step naming only a query searches by date,
    which is the surface the evidence records as making HN searchable. Neither
    is inferred from the characters in the argument, so a query that happens to
    look like an id stays a query.
    """

    named = request.target_ids[0] if request.target_ids else request.query
    kind, separator, argument = named.partition(":")
    if separator and kind in HN_OPERATIONS:
        return (kind, argument)
    return (
        ITEM_OPERATION if request.target_ids else SEARCH_BY_DATE_OPERATION,
        named,
    )


def fetch_native_page(carrier: transport.Transport, request: AdapterRequest) -> NativePage:
    """Read one surface once and return exactly one NativePage.

    One call, one origin: an item read never also searches, and a search never
    also reads an item. The two are separate calls on separate routes with
    separate budgets, and which one to make next is the core's decision.
    """

    operation, argument = operation_for(request)
    if operation == ITEM_OPERATION:
        return _fetch_item(carrier, argument)
    return _fetch_search(carrier, operation, argument, request.cursor)


def _fetch_item(carrier: transport.Transport, item_id: str) -> NativePage:
    native_order = NATIVE_ORDERS[ITEM_OPERATION]

    def parse(response: transport.TransportResponse) -> NativePage:
        payload, refused = _payload_of(DESCRIPTOR, response, native_order, ITEM_OPERATION)
        return refused if refused is not None else _item_page(response, payload, item_id)

    return fetch_one_page(
        DESCRIPTOR,
        carrier,
        params={"item_id": item_id},
        parse=parse,
        native_order=native_order,
    )


def _fetch_search(
    carrier: transport.Transport, operation: str, query: str, cursor: str
) -> NativePage:
    endpoint, tag = SEARCH_ENDPOINTS[operation]
    native_order = NATIVE_ORDERS[operation]
    params: Dict[str, str] = {"endpoint": endpoint, "query": query}
    if tag:
        params["tags"] = tag
    if cursor:
        # The page the core froze, spent as the index's own page number. No
        # next offset is derived here: the index states how many pages it has.
        params[PAGE_KEY] = cursor

    def parse(response: transport.TransportResponse) -> NativePage:
        payload, refused = _payload_of(SEARCH_DESCRIPTOR, response, native_order, operation)
        return refused if refused is not None else _search_page(response, payload, operation)

    return fetch_one_page(
        SEARCH_DESCRIPTOR,
        carrier,
        params=params,
        parse=parse,
        native_order=native_order,
    )
