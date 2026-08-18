"""K2 Reddit through the `/svc/shreddit/` partials its own web client loads.

Measured 2026-08-17, these partials provide keyless read-only subreddit
listing, global and subreddit search, and one post's comments. Listing rows
state score and comment count directly. Search rows carry two unnamed numbers;
measurement against the same post's comment tree identifies them as score then
comment count. Comments state their own score, depth, parent and body.

The comment partial's `more-comments` continuation declares POST, so this
read-only adapter reports the page's stated cap and never follows it. Nothing
here retries or paginates: the core owns both decisions.
"""

from __future__ import annotations

import urllib.parse
from typing import Dict, List, Tuple

from .. import transport
from . import AdapterRequest, NativePage, build_native_page, fetch_one_page
from ._support.reddit_shreddit_contract import (
    AFTER_PARAM,
    ANCHOR_TAG,
    AUTHOR_ATTRIBUTE,
    AWARD_COUNT_ATTRIBUTE,
    COMMENT_BODY_SUFFIX,
    COMMENT_COUNT_ATTRIBUTE,
    COMMENT_COUNT_METRIC,
    COMMENT_FULLNAME_PREFIX,
    COMMENT_ROW_KEYS,
    COMMENT_SORTS,
    COMMENT_TAG,
    COMMENT_TREE_TAG,
    COMMENTS_DESCRIPTOR,
    COMMENTS_OPERATION,
    CONTENT_HREF_ATTRIBUTE,
    CREATED_ATTRIBUTE,
    CREATED_TIMESTAMP_ATTRIBUTE,
    CURSOR_PARAM,
    DEFAULT_COMMENT_SORT,
    DEFAULT_LISTING_SORT,
    DEFAULT_SEARCH_SORT,
    DEPTH_ATTRIBUTE,
    DESCRIPTOR,
    DIV_TAG,
    DOMAIN_ATTRIBUTE,
    FIELD_OMITTED,
    HREF_ATTRIBUTE,
    HTTP_STATUS,
    ID_ATTRIBUTE,
    LISTING_OPERATION,
    LISTING_SORTS,
    NATIVE_ORDERS,
    NUMBER_ATTRIBUTE,
    NUMBER_TAG,
    PARENT_ID_ATTRIBUTE,
    PARTIAL_TAG,
    PERMALINK_ATTRIBUTE,
    POST_FULLNAME_PREFIX,
    POST_ID_ATTRIBUTE,
    POST_ROW_KEYS,
    POST_TAG,
    POST_TITLE_ATTRIBUTE,
    POST_TITLE_TEST_ID,
    POST_TYPE_ATTRIBUTE,
    RECORD_INSTANT_FORMAT,
    REDDIT_ORIGIN,
    ROUTE_INSTANT_LENGTH,
    SCHEMA_DRIFT,
    SCORE_ATTRIBUTE,
    SCORE_METRIC,
    SEARCH_DESCRIPTOR,
    SEARCH_OPERATION,
    SEARCH_POST_TEST_ID,
    SEARCH_SORTS,
    SHREDDIT_OPERATIONS,
    SOURCE_ATTRIBUTE,
    SUBREDDIT_NAME_ATTRIBUTE,
    SUBREDDIT_PREFIXED_ATTRIBUTE,
    SUBREDDIT_SCOPE_PREFIX,
    SUBREDDIT_SEARCH_DESCRIPTOR,
    SURFACE_DESCRIPTORS,
    TELEMETRY_TAG,
    TEST_ID_ATTRIBUTE,
    THING_ID_ATTRIBUTE,
    THING_ID_DATA_ATTRIBUTE,
    TIMEAGO_TAG,
    TIMESTAMP_ATTRIBUTE,
    TIME_WINDOWS,
    TOTAL_COMMENTS_ATTRIBUTE,
    TRACKING_CONTEXT_ATTRIBUTE,
    UNSELECTED_TARGET,
    UPVOTE_RATIO_ATTRIBUTE,
    UTC_OFFSETS,
    ShredditError,
    bare_id,
    cursor_in,
    exact_count,
    fullname,
    post_locator,
    route_instant_to_utc_iso,
    subreddit_of,
)
from ._support.reddit_shreddit_extract import (
    _CommentParser,
    _ListingParser,
    _SearchParser,
    _comment_record,
    _engagement,
    _listing_record,
    _missing,
    _named,
    _search_record,
    _tracking_context,
    collapsed,
)
from ._support import reddit_shreddit_pages as _pages
from ._support.reddit_shreddit_pages import (
    _comments_page,
    _drifted,
    _failed,
    _listing_page,
    _search_page,
    _status_refused,
)


def _split(argument: str) -> List[str]:
    return [part for part in argument.split(":") if part != ""]


def listing_target(argument: str) -> Tuple[str, str, str]:
    """``<subreddit>[:<sort>[:<window>]]`` in the route's vocabulary."""

    parts = _split(argument)
    if not parts:
        raise ShredditError("a listing step names a subreddit: listing:<subreddit>")
    subreddit = subreddit_of(parts[0])
    sort = parts[1] if len(parts) > 1 else DEFAULT_LISTING_SORT
    window = parts[2] if len(parts) > 2 else ""
    if sort not in LISTING_SORTS:
        raise ShredditError(
            "listing sort {0!r} is not one this route serves: {1}".format(
                sort, ", ".join(LISTING_SORTS)
            )
        )
    if window and window not in TIME_WINDOWS:
        raise ShredditError(
            "listing window {0!r} is not one this route serves: {1}".format(
                window, ", ".join(TIME_WINDOWS)
            )
        )
    return (subreddit, sort, window)


def search_target(argument: str) -> Tuple[str, str, str, str]:
    """``[r/<subreddit>:]<query>[:sort=<sort>][:t=<window>]``."""

    subreddit = ""
    held = argument
    if held.startswith(SUBREDDIT_SCOPE_PREFIX):
        scope, separator, rest = held.partition(":")
        if not separator:
            raise ShredditError(
                "a scoped search names a query too: search:r/<subreddit>:<query>"
            )
        subreddit = subreddit_of(scope)
        held = rest
    sort = DEFAULT_SEARCH_SORT
    window = ""
    for option in ("t=", "sort="):
        head, separator, tail = held.rpartition(":")
        if separator and tail.startswith(option):
            value = tail[len(option) :]
            if option == "sort=":
                if value not in SEARCH_SORTS:
                    raise ShredditError(
                        "search sort {0!r} is not one this route serves: {1}".format(
                            value, ", ".join(SEARCH_SORTS)
                        )
                    )
                sort = value
            else:
                if value not in TIME_WINDOWS:
                    raise ShredditError(
                        "search window {0!r} is not one this route serves: {1}".format(
                            value, ", ".join(TIME_WINDOWS)
                        )
                    )
                window = value
            held = head
    if not held:
        raise ShredditError("a search step names a query: search:<query>")
    return (subreddit, held, sort, window)


def comments_target(argument: str) -> Tuple[str, str, str]:
    """``<subreddit>/<post id>[:<sort>]`` or a discovery permalink."""

    held = argument
    sort = DEFAULT_COMMENT_SORT
    for candidate in COMMENT_SORTS:
        if held.endswith(":" + candidate):
            sort = candidate
            held = held[: -len(candidate) - 1]
            break
    subreddit = ""
    post_id = ""
    if "/comments/" in held:
        path = urllib.parse.urlsplit(held).path or held
        parts = [part for part in path.split("/") if part]
        if "r" in parts:
            index = parts.index("r")
            if len(parts) > index + 3 and parts[index + 2] == "comments":
                subreddit = parts[index + 1]
                post_id = parts[index + 3]
    elif "/" in held:
        subreddit, _, post_id = held.partition("/")
        subreddit = subreddit_of(subreddit)
    if not subreddit or not post_id:
        raise ShredditError(
            "a comments step names a subreddit and a post:"
            " comments:<subreddit>/<post id>, or the permalink a row carried"
        )
    return (subreddit, fullname(POST_FULLNAME_PREFIX, bare_id(post_id)), sort)


def operation_for(request: AdapterRequest) -> Tuple[str, str]:
    """The explicitly named operation, or the request-shape default."""

    named = request.target_ids[0] if request.target_ids else request.query
    kind, separator, argument = named.partition(":")
    if separator and kind in SHREDDIT_OPERATIONS:
        return (kind, argument)
    return (COMMENTS_OPERATION if request.target_ids else SEARCH_OPERATION, named)


def fetch_native_page(carrier: transport.Transport, request: AdapterRequest) -> NativePage:
    """Read one Shreddit partial once and return exactly one NativePage."""

    _pages.DESCRIPTOR = DESCRIPTOR
    _pages._listing_record = _listing_record
    _pages._search_record = _search_record
    operation, argument = operation_for(request)
    try:
        if operation == LISTING_OPERATION:
            return _fetch_listing(carrier, argument, request.cursor)
        if operation == COMMENTS_OPERATION:
            return _fetch_comments(carrier, argument)
        return _fetch_search(carrier, argument, request.cursor)
    except ShredditError as error:
        return build_native_page(
            DESCRIPTOR,
            (),
            native_order=NATIVE_ORDERS.get(operation, NATIVE_ORDERS[SEARCH_OPERATION]),
            warnings=(str(error),),
            outcome="refused",
            loss=(UNSELECTED_TARGET,),
        )


def _fetch_listing(
    carrier: transport.Transport, argument: str, cursor: str
) -> NativePage:
    subreddit, sort, window = listing_target(argument)
    params: Dict[str, str] = {"sort": sort, "name": subreddit}
    if window:
        params["t"] = window
    if cursor:
        params[AFTER_PARAM] = cursor
    return fetch_one_page(
        DESCRIPTOR,
        carrier,
        params=params,
        parse=_listing_page,
        native_order=NATIVE_ORDERS[LISTING_OPERATION],
    )


def _fetch_search(carrier: transport.Transport, argument: str, cursor: str) -> NativePage:
    subreddit, query, sort, window = search_target(argument)
    descriptor = SUBREDDIT_SEARCH_DESCRIPTOR if subreddit else SEARCH_DESCRIPTOR
    params: Dict[str, str] = {"q": query, "type": "posts", "sort": sort}
    if subreddit:
        params["subreddit"] = subreddit
    if window:
        params["t"] = window
    if cursor:
        params[CURSOR_PARAM] = cursor

    def parse(response: transport.TransportResponse) -> NativePage:
        return _search_page(descriptor, response)

    return fetch_one_page(
        descriptor,
        carrier,
        params=params,
        parse=parse,
        native_order=NATIVE_ORDERS[SEARCH_OPERATION],
    )


def _fetch_comments(carrier: transport.Transport, argument: str) -> NativePage:
    subreddit, post_fullname, sort = comments_target(argument)

    def parse(response: transport.TransportResponse) -> NativePage:
        return _comments_page(response, subreddit)

    return fetch_one_page(
        COMMENTS_DESCRIPTOR,
        carrier,
        params={"subreddit": subreddit, "post_fullname": post_fullname, "sort": sort},
        parse=parse,
        native_order=NATIVE_ORDERS[COMMENTS_OPERATION],
    )
