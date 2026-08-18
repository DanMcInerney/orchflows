"""Static contracts and shared value grammar for the Reddit Shreddit adapter."""

from __future__ import annotations

import urllib.parse
from typing import Any, Optional

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
