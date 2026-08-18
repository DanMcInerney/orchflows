"""K0 Hacker News over three surfaces: Algolia for search and for a whole tree, Firebase for one item.

Measured 2026-08-10 (Carry-over routes):
``hn.algolia.com/api/v1/search_by_date`` answered 200 with full-text HN search,
``hn.algolia.com/api/v1/search?tags=comment`` answered 200 for comment search,
and ``hacker-news.firebaseio.com/v0/item/<id>`` answered 200 with ``by``,
``descendants`` and the ``kids`` tree. Reading Algolia beside Firebase is what
makes HN searchable at all: the prior spec's Firebase-only adapter could list
and hydrate and never search, and the evidence records the upgrade as strict.

Measured 2026-08-17: ``hn.algolia.com/api/v1/items/<id>`` answered 200 in
0.94 s with 135 KB — one story and its whole comment tree, 259 nodes, each a
``{id, created_at, created_at_i, type, author, title, url, text, points,
parent_id, story_id, children, options}`` object nesting its own children.
``points`` was an integer on the story and ``null`` on every comment; a
comment id answered 200 with the subtree under that comment; an id the index
holds nothing under answered 404 with ``{"error":"Not Found","status":404}``.
The same day ``search_by_date?query=spacex`` answered 20 hits with
``hitsPerPage: 20`` and no size asked for, and adding
``numericFilters=created_at_i>=<epoch>,created_at_i<=<epoch>&hitsPerPage=20``
answered 200 with hits inside the bounds — which is how a caller's window
travels to this index in the index's own terms.

**Two origins, three routes, and still one call each.** A search is one call to
Algolia's search endpoint, an item is one call to Firebase, and a tree is one
call to Algolia's items endpoint; no call here is ever two of them — this
module holds one descriptor per surface and spends exactly one of them per
call. Walking a Firebase ``kids`` list is one call per item with the core
choosing the next one, because an adapter that walked it would turn one bounded
call into a crawl whose size nobody declared. The tree surface is the same
bound met differently: the origin itself answers the whole tree in one payload,
so flattening what one call returned is reading, not crawling, and this module
still makes no second call to fill anything in.

**A comment never carries the story's points.** The tree states ``points`` on
every node and states ``null`` on every comment, and that null is left absent:
a comment record carries no engagement rather than its root's, which is the one
way a per-comment ranking could be quietly wrong on every row.

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

from ._support.hacker_news_config import (
    AUTHOR_KEY,
    BY_KEY,
    CHILDREN_KEY,
    COMMENT_SEARCH_OPERATION,
    COMMENT_TEXT_KEY,
    COMMENT_TYPE,
    CREATED_AT_I_KEY,
    CREATED_AT_KEY,
    DEFAULT_HIT_ROW_KEYS,
    DEFAULT_ITEM_ROW_KEYS,
    DEFAULT_TREE_ROW_KEYS,
    DEPTH_ATTRIBUTE,
    DESCENDANTS_METRIC,
    DESCRIPTOR,
    FILTER_SEPARATOR,
    HITS_KEY,
    HITS_PER_PAGE_PARAM,
    HIT_ROW_KEYS,
    HN_ITEM_ORIGIN,
    HN_ITEM_PATH,
    HN_OPERATIONS,
    HTTP_STATUS,
    ITEM_ID_KEY,
    ITEM_OPERATION,
    ITEM_ROW_KEYS,
    ITEM_TREE_DESCRIPTOR,
    ITEM_TYPE_KEY,
    ITEM_TYPES,
    KIDS_KEY,
    MALFORMED_JSON,
    NATIVE_ORDERS,
    NUMERIC_FILTERS_PARAM,
    NUM_COMMENTS_METRIC,
    OBJECT_ID_KEY,
    PAGE_COUNT_KEY,
    PAGE_KEY,
    PARENT_ID_KEY,
    PARENT_KEY,
    POINTS_METRIC,
    RECORD_INSTANT_FORMAT,
    ROUTE_INSTANT_FORMAT,
    SCHEMA_DRIFT,
    SCORE_METRIC,
    SEARCH_BY_DATE_OPERATION,
    SEARCH_DESCRIPTOR,
    SEARCH_ENDPOINTS,
    SEARCH_OPERATION,
    SEARCH_PAGE_SIZE,
    STORY_ID_KEY,
    STORY_TEXT_KEY,
    SURFACE_DESCRIPTORS,
    TAGS_KEY,
    TEXT_KEY,
    TEXT_TYPES,
    TIME_KEY,
    TITLE_KEY,
    TREE_OPERATION,
    TREE_ROW_KEYS,
    TYPO_TOLERANCE_OFF,
    TYPO_TOLERANCE_PARAM,
    URL_KEY,
    WINDOW_END_FILTER,
    WINDOW_START_FILTER,
)
from ._support import hacker_news_mapping as _mapping
from ._support.hacker_news_mapping import (
    _engagement,
    _flatten_tree,
    _hit_record,
    _item_record,
    _missing,
    _text,
    _tree_record,
    epoch_to_utc_iso,
    exact_count,
    hit_kind,
    id_text,
    instant_to_epoch_text,
    item_locator,
    route_instant_to_utc_iso,
    window_filters,
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
    if not records and not untyped:
        # Said out loud, and only when it is true: an index that returned rows
        # this adapter cannot read matched something, and calling that "nothing
        # matched" would hide a shape this package does not handle behind an
        # ordinary empty answer. The warning above is what that case gets.
        warnings.append(
            "{0} answered 200 with an empty {1} list: this query matched"
            " nothing".format(operation, HITS_KEY)
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


def _tree_page(
    response: transport.TransportResponse, payload: Any, item_id: str
) -> NativePage:
    """One whole tree as the index answered it, flattened, or the typed reason not."""

    native_order = NATIVE_ORDERS[TREE_OPERATION]
    kind = _text(payload.get(ITEM_TYPE_KEY)) if isinstance(payload, Mapping) else ""
    if kind not in ITEM_TYPES or not id_text(payload.get(ITEM_ID_KEY)):
        # The root is where the tree keeps itself. A body that is not a node
        # this adapter knows is the payload having moved, and never a tree with
        # nothing in it: an id the index holds nothing under answers 404, which
        # `_payload_of` has already recorded as the status it is.
        return _failed(
            ITEM_TREE_DESCRIPTOR,
            response,
            native_order,
            SCHEMA_DRIFT,
            "{0} answered 200 with a root stating no {1} this adapter knows and no"
            " {2}: the payload this adapter reads has changed shape".format(
                TREE_OPERATION, ITEM_TYPE_KEY, ITEM_ID_KEY
            ),
        )
    records, untyped = _flatten_tree(payload)
    warnings: List[str] = []
    if untyped:
        warnings.append(
            "{0} answered 200 for item {1} with {2} node(s) carrying no item type in"
            " {3} or no {4}: they are not rows this adapter can identify".format(
                TREE_OPERATION, item_id, untyped, ITEM_TYPE_KEY, ITEM_ID_KEY
            )
        )
    return _answered(
        ITEM_TREE_DESCRIPTOR,
        response,
        native_order,
        records=records,
        warnings=tuple(warnings),
    )


def operation_for(request: AdapterRequest) -> Tuple[str, str]:
    """The operation this call performs, and the argument it performs it on.

    A caller names the operation, because three surfaces answer different
    questions. Absent a name, the step's own shape decides: a step naming a
    target hydrates that item, and a step naming only a query searches by date,
    which is the surface the evidence records as making HN searchable. Neither
    is inferred from the characters in the argument, so a query that happens to
    look like an id stays a query. `tree:` is answered from either shape, since
    one whole thread is as much a thing to discover as to hydrate.
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

    _mapping._tree_record = _tree_record
    operation, argument = operation_for(request)
    if operation == ITEM_OPERATION:
        return _fetch_item(carrier, argument)
    if operation == TREE_OPERATION:
        return _fetch_tree(carrier, argument)
    return _fetch_search(
        carrier, operation, argument, request.cursor, request.window_start, request.window_end
    )


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


def _fetch_tree(carrier: transport.Transport, item_id: str) -> NativePage:
    native_order = NATIVE_ORDERS[TREE_OPERATION]

    def parse(response: transport.TransportResponse) -> NativePage:
        payload, refused = _payload_of(
            ITEM_TREE_DESCRIPTOR, response, native_order, TREE_OPERATION
        )
        return refused if refused is not None else _tree_page(response, payload, item_id)

    return fetch_one_page(
        ITEM_TREE_DESCRIPTOR,
        carrier,
        params={"item_id": item_id},
        parse=parse,
        native_order=native_order,
    )


def _fetch_search(
    carrier: transport.Transport,
    operation: str,
    query: str,
    cursor: str,
    window_start: str = "",
    window_end: str = "",
) -> NativePage:
    endpoint, tag = SEARCH_ENDPOINTS[operation]
    native_order = NATIVE_ORDERS[operation]
    params: Dict[str, str] = {
        "endpoint": endpoint,
        "query": query,
        TYPO_TOLERANCE_PARAM: TYPO_TOLERANCE_OFF,
    }
    if tag:
        params["tags"] = tag
    if cursor:
        # The page the core froze, spent as the index's own page number. No
        # next offset is derived here: the index states how many pages it has.
        params[PAGE_KEY] = cursor
    filters = window_filters(window_start, window_end)
    if filters:
        # The caller's window, in the index's own terms, and the page size
        # stated beside it. Nothing is dropped here on either bound.
        params[NUMERIC_FILTERS_PARAM] = filters
        params[HITS_PER_PAGE_PARAM] = str(SEARCH_PAGE_SIZE)

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
