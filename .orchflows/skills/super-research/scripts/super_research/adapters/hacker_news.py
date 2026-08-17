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
    # The 2026-08-10 probes record "no throttle observed" for HN and no latency for
    # either surface. An unmeasured ceiling is not one to spend, so all three
    # numbers stay the protocol's conservative defaults rather than a figure
    # this adapter would have had to invent.
    #
    # Firebase names a story's comment count `descendants`. Algolia names the
    # same quantity `num_comments`, and each surface declares the name its own
    # route reports — the two are never aliased into one.
    comment_count_metric="descendants",
)

# How many hits one search answer holds when the index has that many. Measured
# 2026-08-17: `search_by_date?query=spacex` answered 20 hits and stated
# `hitsPerPage: 20` with no size asked for, so this is the index's own default
# and the number a cap below it buys nothing against.
SEARCH_PAGE_SIZE = 20

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
    page_size=SEARCH_PAGE_SIZE,
)

# The Algolia items surface: the same origin as the search, a different
# endpoint shape, and so a route of its own with its own budget. It answers a
# story and its whole comment tree in one call where Firebase answers one node
# per call, and it is what makes hydrating an HN thread one read rather than
# a traversal the core has to schedule node by node. Nothing on it was measured
# refusing, so all three ceiling numbers stay the protocol's conservative
# defaults, as the other two surfaces' do; and no node it returns states a
# comment count, so neither ranking metric is declared.
ITEM_TREE_DESCRIPTOR = AdapterDescriptor(
    adapter_id="hacker_news",
    adapter_version="1",
    access_class="K0",
    route_id=transport.HN_ALGOLIA_ITEM_ROUTE,
    platform="hackernews",
    native_identity_namespace="hackernews",
    representation_kind="native",
    operator_identity="algolia",
)

# Every route this adapter can reach, one descriptor each. The core collects
# route budgets from here, because a route nothing declares a budget for is a
# route the scheduler refuses to pace.
SURFACE_DESCRIPTORS = (DESCRIPTOR, SEARCH_DESCRIPTOR, ITEM_TREE_DESCRIPTOR)

# The five operations, spelled once each. A caller names one with a prefix,
# because three surfaces answer different questions; absent a prefix the step's
# own shape decides, and never the characters in the argument.
ITEM_OPERATION = "item"
SEARCH_OPERATION = "search"
SEARCH_BY_DATE_OPERATION = "search_by_date"
COMMENT_SEARCH_OPERATION = "comments"
TREE_OPERATION = "tree"
HN_OPERATIONS = (
    ITEM_OPERATION,
    SEARCH_OPERATION,
    SEARCH_BY_DATE_OPERATION,
    COMMENT_SEARCH_OPERATION,
    TREE_OPERATION,
)

# Which endpoint each search operation asks, and under which tag. `search`
# ranks by relevance and `search_by_date` by recency; the tag selects rows
# rather than an endpoint, so it travels as a query parameter. The two story
# searches send no tag at all, which is the shape the evidence measured: the
# index then answers with every kind of item that matched, and each row is
# typed from its own tags rather than filtered here.
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
    TREE_OPERATION: "hn_algolia_tree_depth_first_order",
}

# Where each surface keeps what it returned, and what one row of it is.
# Declared, never searched for: the whole value of a typed drift is that it
# says the payload moved rather than that HN went quiet.
HITS_KEY = "hits"
PAGE_KEY = "page"
PAGE_COUNT_KEY = "nbPages"
TAGS_KEY = "_tags"
OBJECT_ID_KEY = "objectID"

# How a caller's window travels to the search index, in the index's own
# syntax: a comma-joined list of bounds on the epoch-second field every hit
# carries, and the page size beside it. Measured 2026-08-17 answering 200. The
# size is sent only beside a window: an unbounded search stays the request the
# 2026-08-10 measurement made, byte for byte, and a bounded one states its page
# explicitly rather than leaning on the index's default.
NUMERIC_FILTERS_PARAM = "numericFilters"
HITS_PER_PAGE_PARAM = "hitsPerPage"

# Algolia guesses at spellings unless told not to, and on this index the guess
# is not a near miss: measured 2026-08-17, `query=SpaceX` answered **849,432**
# hits whose top rows were about Go release notes and "Apple's space", because
# typo tolerance reaches `space` from `SpaceX`. The same query with this
# parameter off answered 67,207, and its top rows are about SpaceX. A row count
# on an entity query is only a measure of topic volume if the index matched the
# entity, so this package asks the index not to guess — on every search, not as
# an option — and a caller who wants a phrase quotes it, which Algolia's own
# advanced syntax reads. It is the same law `engagement` follows: what a route
# reported, never what it might have meant.
TYPO_TOLERANCE_PARAM = "typoTolerance"
TYPO_TOLERANCE_OFF = "false"
CREATED_AT_I_KEY = "created_at_i"
WINDOW_START_FILTER = CREATED_AT_I_KEY + ">="
WINDOW_END_FILTER = CREATED_AT_I_KEY + "<="
FILTER_SEPARATOR = ","

# The tree surface's own keys, beside the ones it shares with the search hits
# (`id`, `type`, `author`, `title`, `url`, `text`, `created_at`, `parent_id`,
# `story_id`, `points`). `children` is where a node keeps the nodes under it,
# and `depth` is not the payload's at all: it is how far from the root this
# module found a node while flattening, and it travels as an attribute under
# that name because no record field means it.
CHILDREN_KEY = "children"
DEPTH_ATTRIBUTE = "depth"

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
# A tree node names its author `author` and its time `created_at`, the way a
# search hit does, and its type and text the way a Firebase item does. Its
# roster is this adapter's own declaration, as the hit rosters are.
TREE_ROW_KEYS = {
    COMMENT_TYPE: (ITEM_ID_KEY, ITEM_TYPE_KEY, AUTHOR_KEY, CREATED_AT_KEY, TEXT_KEY),
    "pollopt": (ITEM_ID_KEY, ITEM_TYPE_KEY, AUTHOR_KEY, CREATED_AT_KEY, TEXT_KEY),
}
DEFAULT_TREE_ROW_KEYS = (ITEM_ID_KEY, ITEM_TYPE_KEY, AUTHOR_KEY, CREATED_AT_KEY, TITLE_KEY)

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
    missing time, and so is one no clock can represent. A payload that moved
    must arrive as a typed answer rather than as an exception — an adapter that
    raised would cost the core the one page it is owed.
    """

    if isinstance(seconds, bool) or not isinstance(seconds, int):
        return ""
    try:
        moment = datetime.fromtimestamp(seconds, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return ""
    return moment.strftime(RECORD_INSTANT_FORMAT)


def instant_to_epoch_text(instant: str) -> str:
    """One manifest instant as the epoch seconds the search index filters on, or nothing.

    The other direction of :func:`epoch_to_utc_iso`, for the one place this
    module sends a time rather than reads one. A bound this function cannot
    read is a bound not sent — the core's own window filter still holds on
    every row that comes back — rather than a bound sent wrong, which would
    narrow the index's answer to a range nobody asked for.
    """

    if not isinstance(instant, str) or not instant.strip():
        return ""
    try:
        moment = datetime.strptime(instant.strip(), RECORD_INSTANT_FORMAT)
    except ValueError:
        return ""
    return str(int(moment.replace(tzinfo=timezone.utc).timestamp()))


def window_filters(window_start: str, window_end: str) -> str:
    """A caller's window in Algolia's own `numericFilters` syntax, or nothing.

    Either bound alone is a filter; both together are two, comma-joined, on the
    same field. Rows are never dropped here on either: the index applies what
    it is sent and the core counts what falls outside.
    """

    bounds = []
    start = instant_to_epoch_text(window_start)
    if start:
        bounds.append(WINDOW_START_FILTER + start)
    end = instant_to_epoch_text(window_end)
    if end:
        bounds.append(WINDOW_END_FILTER + end)
    return FILTER_SEPARATOR.join(bounds)


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

    Algolia lists a row's type among its own `_tags`, beside tags for the
    author and the story it belongs to, so the first tag naming an item type is
    the row's kind. The tag is read rather than guessed at from the fields
    present: a row is a comment because HN says so, not because this module
    recognized a shape with a `comment_text` in it.
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
    # A comment's own text, or a story's own text where it has one. A comment
    # row also carries the title of the story it sits under, and that is
    # deliberately read nowhere here: it is a fact about the story, and a
    # comment titled with its story's title is a record that claims to be one.
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
        title=row[TITLE_KEY],
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


def _tree_record(
    position: int, node: Mapping[str, Any], kind: str, depth: int
) -> NativeRecord:
    """One node of the tree as Algolia listed it, and how deep it sat."""

    item_id = id_text(node.get(ITEM_ID_KEY))
    row = {
        ITEM_ID_KEY: item_id,
        ITEM_TYPE_KEY: kind,
        AUTHOR_KEY: _text(node.get(AUTHOR_KEY)),
        CREATED_AT_KEY: route_instant_to_utc_iso(node.get(CREATED_AT_KEY)),
        TITLE_KEY: _text(node.get(TITLE_KEY)),
        TEXT_KEY: _text(node.get(TEXT_KEY)),
    }
    named: List[Tuple[str, str]] = []
    link = _text(node.get(URL_KEY))
    if link:
        named.append((URL_KEY, link))
    story_id = id_text(node.get(STORY_ID_KEY))
    if story_id:
        # The root this node sits under, which `native_parent_id` does not
        # mean: a reply's parent is the comment it answers.
        named.append((STORY_ID_KEY, story_id))
    named.append((DEPTH_ATTRIBUTE, str(depth)))
    return NativeRecord(
        canonical_content_kind=kind,
        canonical_locator=item_locator(item_id),
        native_item_id=item_id,
        native_parent_id=id_text(node.get(PARENT_ID_KEY)),
        title=row[TITLE_KEY],
        body=row[TEXT_KEY],
        author=row[AUTHOR_KEY],
        published_at=row[CREATED_AT_KEY],
        # This node's own points and only its own: the tree states `null` on
        # every comment, and an absent count is left absent rather than filled
        # from the story above it.
        engagement=_engagement(((POINTS_METRIC, node.get(POINTS_METRIC)),)),
        attributes=tuple(named),
        native_position=position,
        loss=("field_omitted",)
        if _missing(row, TREE_ROW_KEYS.get(kind, DEFAULT_TREE_ROW_KEYS))
        else (),
    )


def _flatten_tree(
    root: Mapping[str, Any]
) -> Tuple[Tuple[NativeRecord, ...], int]:
    """Every node of one tree, depth first, root first, children in listed order.

    Also how many nodes were passed over: a node stating no type this adapter
    knows, or no id, is not a row — it can be neither typed nor addressed —
    and it is counted so the page can say the tree held more than it read.
    Its children are still walked, because a hole in a thread is not the end
    of it. Iterative rather than recursive on purpose: a thread is as deep as
    HN let it get, and a payload must never turn into a recursion error.
    """

    records: List[NativeRecord] = []
    untyped = 0
    pending: List[Tuple[Any, int]] = [(root, 0)]
    while pending:
        node, depth = pending.pop()
        if not isinstance(node, Mapping):
            untyped += 1
            continue
        kind = _text(node.get(ITEM_TYPE_KEY))
        if kind in ITEM_TYPES and id_text(node.get(ITEM_ID_KEY)):
            records.append(_tree_record(len(records), node, kind, depth))
        else:
            untyped += 1
        children = node.get(CHILDREN_KEY)
        if isinstance(children, list):
            # Pushed in reverse so the first-listed child is the next popped:
            # the order HN listed them is the order the records hold.
            for child in reversed(children):
                pending.append((child, depth + 1))
    return (tuple(records), untyped)


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
