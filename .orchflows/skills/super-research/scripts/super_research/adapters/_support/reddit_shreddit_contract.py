"""Static contracts and shared value grammar for the Reddit Shreddit adapter."""

from __future__ import annotations

import urllib.parse
from datetime import datetime, timezone
from typing import Any, Optional, Tuple

from ... import transport
from .. import AdapterDescriptor


REDDIT_ORIGIN = transport.REDDIT_SITE_ORIGIN
POST_FULLNAME_PREFIX = "t3_"
COMMENT_FULLNAME_PREFIX = "t1_"

DESCRIPTOR = AdapterDescriptor(
    adapter_id="reddit_shreddit",
    adapter_version="1",
    access_class="K2",
    route_id=transport.REDDIT_SHREDDIT_LISTING_ROUTE,
    platform="reddit",
    native_identity_namespace="reddit",
    representation_kind="native",
    operator_identity="reddit",
    min_interval_ms=1500,
    burst=10,
    comment_count_metric="comment-count",
    page_size=24,
)

SEARCH_DESCRIPTOR = AdapterDescriptor(
    adapter_id="reddit_shreddit",
    adapter_version="1",
    access_class="K2",
    route_id=transport.REDDIT_SHREDDIT_SEARCH_ROUTE,
    platform="reddit",
    native_identity_namespace="reddit",
    representation_kind="native",
    operator_identity="reddit",
    min_interval_ms=1500,
    burst=10,
    comment_count_metric="comment-count",
    page_size=7,
)

SUBREDDIT_SEARCH_DESCRIPTOR = AdapterDescriptor(
    adapter_id="reddit_shreddit",
    adapter_version="1",
    access_class="K2",
    route_id=transport.REDDIT_SHREDDIT_SUBREDDIT_SEARCH_ROUTE,
    platform="reddit",
    native_identity_namespace="reddit",
    representation_kind="native",
    operator_identity="reddit",
    min_interval_ms=1500,
    burst=10,
    comment_count_metric="comment-count",
    page_size=7,
)

COMMENTS_DESCRIPTOR = AdapterDescriptor(
    adapter_id="reddit_shreddit",
    adapter_version="1",
    access_class="K2",
    route_id=transport.REDDIT_SHREDDIT_COMMENTS_ROUTE,
    platform="reddit",
    native_identity_namespace="reddit",
    representation_kind="native",
    operator_identity="reddit",
    min_interval_ms=1500,
    burst=10,
    page_size=25,
)

SURFACE_DESCRIPTORS = (
    DESCRIPTOR,
    SEARCH_DESCRIPTOR,
    SUBREDDIT_SEARCH_DESCRIPTOR,
    COMMENTS_DESCRIPTOR,
)

LISTING_OPERATION = "listing"
SEARCH_OPERATION = "search"
COMMENTS_OPERATION = "comments"
SHREDDIT_OPERATIONS = (LISTING_OPERATION, SEARCH_OPERATION, COMMENTS_OPERATION)

NATIVE_ORDERS = {
    LISTING_OPERATION: "reddit_shreddit_listing_order",
    SEARCH_OPERATION: "reddit_shreddit_search_order",
    COMMENTS_OPERATION: "reddit_shreddit_comment_order",
}

LISTING_SORTS = ("new", "hot", "top", "rising")
SEARCH_SORTS = ("relevance", "new", "top", "comments")
COMMENT_SORTS = ("top", "new", "controversial", "old", "qa")
TIME_WINDOWS = ("hour", "day", "week", "month", "year", "all")
DEFAULT_LISTING_SORT = "new"
DEFAULT_SEARCH_SORT = "new"
DEFAULT_COMMENT_SORT = "top"
SUBREDDIT_SCOPE_PREFIX = "r/"

POST_TAG = "shreddit-post"
COMMENT_TAG = "shreddit-comment"
COMMENT_TREE_TAG = "shreddit-comment-tree"
TELEMETRY_TAG = "search-telemetry-tracker"
NUMBER_TAG = "faceplate-number"
TIMEAGO_TAG = "faceplate-timeago"
PARTIAL_TAG = "faceplate-partial"
ANCHOR_TAG = "a"
DIV_TAG = "div"

ID_ATTRIBUTE = "id"
PERMALINK_ATTRIBUTE = "permalink"
SCORE_ATTRIBUTE = "score"
COMMENT_COUNT_ATTRIBUTE = "comment-count"
POST_TITLE_ATTRIBUTE = "post-title"
AUTHOR_ATTRIBUTE = "author"
CREATED_TIMESTAMP_ATTRIBUTE = "created-timestamp"
CREATED_ATTRIBUTE = "created"
SUBREDDIT_PREFIXED_ATTRIBUTE = "subreddit-prefixed-name"
SUBREDDIT_NAME_ATTRIBUTE = "subreddit-name"
POST_TYPE_ATTRIBUTE = "post-type"
DOMAIN_ATTRIBUTE = "domain"
UPVOTE_RATIO_ATTRIBUTE = "upvote-ratio"
AWARD_COUNT_ATTRIBUTE = "award-count"
CONTENT_HREF_ATTRIBUTE = "content-href"
THING_ID_ATTRIBUTE = "thingid"
PARENT_ID_ATTRIBUTE = "parentid"
POST_ID_ATTRIBUTE = "postid"
DEPTH_ATTRIBUTE = "depth"
TOTAL_COMMENTS_ATTRIBUTE = "totalcomments"
NUMBER_ATTRIBUTE = "number"
TIMESTAMP_ATTRIBUTE = "ts"
SOURCE_ATTRIBUTE = "src"
TEST_ID_ATTRIBUTE = "data-testid"
THING_ID_DATA_ATTRIBUTE = "data-thingid"
TRACKING_CONTEXT_ATTRIBUTE = "data-faceplate-tracking-context"
HREF_ATTRIBUTE = "href"
SEARCH_POST_TEST_ID = "search-sdui-post"
POST_TITLE_TEST_ID = "post-title"
COMMENT_BODY_SUFFIX = "-post-rtjson-content"

SCORE_METRIC = "score"
COMMENT_COUNT_METRIC = "comment-count"
AFTER_PARAM = "after"
CURSOR_PARAM = "cursor"

ROUTE_INSTANT_LENGTH = 19
RECORD_INSTANT_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
UTC_OFFSETS = ("+0000", "+00:00", "Z")

HTTP_STATUS = "http_status"
SCHEMA_DRIFT = "schema_drift"
FIELD_OMITTED = "field_omitted"
UNSELECTED_TARGET = "unselected_target"
POST_ROW_KEYS = ("native_item_id", "title", "author", "published_at")
COMMENT_ROW_KEYS = ("native_item_id", "body", "author", "published_at")


class ShredditError(ValueError):
    """A caller asked this adapter for something the route does not serve."""


def route_instant_to_utc_iso(stamp: Any) -> str:
    """One partial's UTC stamp as the artifact's instant, or nothing."""

    if not isinstance(stamp, str) or len(stamp) < ROUTE_INSTANT_LENGTH:
        return ""
    text = stamp.strip()
    if not any(text.endswith(offset) for offset in UTC_OFFSETS):
        return ""
    head = text[:ROUTE_INSTANT_LENGTH]
    if head[4] != "-" or head[7] != "-" or head[10] != "T":
        return ""
    for position in (0, 1, 2, 3, 5, 6, 8, 9, 11, 12, 14, 15, 17, 18):
        if not head[position].isdigit():
            return ""
    return head + "Z"


def exact_count(value: Any) -> Optional[int]:
    """One exact decimal count, or nothing for a display-formatted value."""

    if not isinstance(value, str):
        return None
    held = value.strip()
    if not held or not held.isdigit():
        return None
    return int(held)


def fullname(prefix: str, value: str) -> str:
    """One id under Reddit's own fullname prefix, whichever form arrived."""

    held = (value or "").strip()
    if not held:
        return ""
    return held if held.startswith(prefix) else prefix + held


def bare_id(value: str) -> str:
    """One fullname's base-36 id, for surfaces that take it that way."""

    held = (value or "").strip()
    for prefix in (POST_FULLNAME_PREFIX, COMMENT_FULLNAME_PREFIX):
        if held.startswith(prefix):
            return held[len(prefix) :]
    return held


def subreddit_of(prefixed: str) -> str:
    """A subreddit's bare name, from either spelling the partials use."""

    held = (prefixed or "").strip()
    return held[len(SUBREDDIT_SCOPE_PREFIX) :] if held.startswith(SUBREDDIT_SCOPE_PREFIX) else held


def post_locator(permalink: str) -> str:
    return REDDIT_ORIGIN + permalink if permalink.startswith("/") else permalink


def cursor_in(source: str, name: str) -> str:
    """One continuation parameter off the address a partial published."""

    if not source:
        return ""
    query = urllib.parse.urlsplit(source).query
    for key, value in urllib.parse.parse_qsl(query, keep_blank_values=True):
        if key == name and value:
            return value
    return ""


_SECONDS_PER_HOUR = 3600
_SECONDS_PER_DAY = 24 * _SECONDS_PER_HOUR
_SECONDS_PER_WEEK = 7 * _SECONDS_PER_DAY
_SECONDS_PER_MONTH = 30 * _SECONDS_PER_DAY
_SECONDS_PER_YEAR = 365 * _SECONDS_PER_DAY

# The origin's own vocabulary (`TIME_WINDOWS`, minus `"all"`) paired with the
# span each bucket reaches back from *now*, ascending. `origin_time_bucket`
# below picks the first one wide enough to still cover `window_start`.
_T_BUCKET_SPANS: Tuple[Tuple[str, int], ...] = (
    ("hour", _SECONDS_PER_HOUR),
    ("day", _SECONDS_PER_DAY),
    ("week", _SECONDS_PER_WEEK),
    ("month", _SECONDS_PER_MONTH),
    ("year", _SECONDS_PER_YEAR),
)


def _instant_seconds(stamped: str) -> Optional[int]:
    """One manifest instant (``RECORD_INSTANT_FORMAT``) as whole UTC seconds.

    A local parser rather than a shared one: another origin-adjacent adapter
    module already reads the same manifest spelling this same way, and each
    owns its own tiny parser rather than reaching into `ordering`, which
    stays a core-only import (`test_dependency_boundary_cases`'s edge table
    names no adapter as one of its importers).
    """

    if not stamped:
        return None
    try:
        moment = datetime.strptime(stamped, RECORD_INSTANT_FORMAT).replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return int(moment.timestamp())


def origin_time_bucket(window_start: str, window_end: str) -> str:
    """The coarsest-covering native ``t=`` value for one step's window, or nothing.

    A pure function of the step's two instants, imitating this shape's
    exemplar's three properties: it lives beside this adapter, it returns the
    origin's own term, and it returns nothing when there is no bound to
    state, so an unwindowed step's request is unchanged.

    Reddit's own bucket is a span measured back from *now*, never from an
    explicit endpoint — `_fetch_listing`/`_fetch_search` send it as the
    route's only time parameter, and there is no second one to narrow the
    near edge. The smallest bucket that still reaches ``window_start`` is the
    one returned. A step whose ``window_end`` sits before now is therefore
    over-covered at the near edge — the origin also answers with records
    newer than ``window_end`` — which is lawful (`_support/runner_plan.py`'s
    `in_window` still trims what a caller keeps) but is exactly why
    ``window_end`` plays no part in the choice below: nothing this route
    accepts can pull the near edge in from "now", so a second instant could
    not narrow it. A step with no ``window_start`` needs no bucket at all:
    the unbounded answer already reaches back far enough, and the same filter
    trims the far edge.
    """

    del window_end  # Documented above: the near edge is fixed at "now" here.
    start_seconds = _instant_seconds(window_start)
    if start_seconds is None:
        return ""
    now_seconds = _instant_seconds(transport.utc_now_iso())
    if now_seconds is None:
        return ""
    age = now_seconds - start_seconds
    for bucket, span in _T_BUCKET_SPANS:
        if age <= span:
            return bucket
    return "all"
