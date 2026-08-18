"""Private declarations for the Hacker News adapter surfaces."""

from __future__ import annotations

from ... import transport
from .. import AdapterDescriptor

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
