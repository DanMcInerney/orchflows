"""K2 Reddit through the `/svc/shreddit/` partials its own web client loads.

Measured, these partials provide keyless read-only subreddit
listing, global and subreddit search, and one post's comments. Listing rows
state score and comment count directly. Search rows carry two unnamed numbers;
measurement against the same post's comment tree identifies them as score then
comment count. Comments state their own score, depth, parent and body.

The comment partial's `more-comments` continuation declares POST, so this
read-only adapter reports the page's stated cap and never follows it. Nothing
here retries or paginates: the core owns both decisions.
"""

from __future__ import annotations

import urllib.parse, json
from typing import Dict, List, Tuple, Any, Optional, Mapping

from .. import transport, schema
from . import (
    AdapterRequest,
    NativePage,
    build_native_page,
    fetch_one_page,
    AdapterDescriptor,
    NativeRecord,
)
from datetime import datetime, timezone
from html.parser import HTMLParser


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
RECORD_INSTANT_FORMAT = schema.INSTANT_FORMAT
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

    A local parser rather than a shared one: each origin-adjacent adapter
    owns its own tiny parser rather than reaching into `ordering`, which
    stays a core-only import.
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
    newer than ``window_end`` — which is lawful (`runner.in_window` still
    trims what a caller keeps) but is exactly why
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


class _ListingParser(HTMLParser):
    """Every ``<shreddit-post>`` on one listing page and its next cursor."""

    def __init__(self) -> None:
        HTMLParser.__init__(self, convert_charrefs=True)
        self.posts: List[Dict[str, str]] = []
        self.next_cursor = ""
        self.partials = 0

    def handle_starttag(self, tag, attrs):
        attributes = {name: (value or "") for name, value in attrs}
        if tag == POST_TAG:
            self.posts.append(attributes)
        elif tag == PARTIAL_TAG:
            self.partials += 1
            found = cursor_in(attributes.get(SOURCE_ATTRIBUTE, ""), AFTER_PARAM)
            if found:
                self.next_cursor = found


class _SearchParser(HTMLParser):
    """Every search row on one page, in the order the page laid them out."""

    def __init__(self) -> None:
        HTMLParser.__init__(self, convert_charrefs=True)
        self.rows: List[Dict[str, Any]] = []
        self.next_cursor = ""
        self.trackers = 0

    def handle_starttag(self, tag, attrs):
        attributes = {name: (value or "") for name, value in attrs}
        if tag == TELEMETRY_TAG and attributes.get(TEST_ID_ATTRIBUTE) == SEARCH_POST_TEST_ID:
            self.trackers += 1
            self.rows.append(
                {
                    "thing_id": attributes.get(THING_ID_DATA_ATTRIBUTE, ""),
                    "context": attributes.get(TRACKING_CONTEXT_ATTRIBUTE, ""),
                    "permalink": "",
                    "title": "",
                    "published_at": "",
                    "numbers": [],
                }
            )
        elif not self.rows:
            return
        elif tag == ANCHOR_TAG and attributes.get(TEST_ID_ATTRIBUTE) == POST_TITLE_TEST_ID:
            row = self.rows[-1]
            row["permalink"] = attributes.get(HREF_ATTRIBUTE, "")
            row["title"] = attributes.get("aria-label", "")
        elif tag == TIMEAGO_TAG:
            self.rows[-1]["published_at"] = attributes.get(TIMESTAMP_ATTRIBUTE, "")
        elif tag == NUMBER_TAG:
            self.rows[-1]["numbers"].append(attributes.get(NUMBER_ATTRIBUTE, ""))
        elif tag == PARTIAL_TAG:
            found = cursor_in(attributes.get(SOURCE_ATTRIBUTE, ""), CURSOR_PARAM)
            if found:
                self.next_cursor = found


class _CommentParser(HTMLParser):
    """Every comment on one page, each with the body div it owns."""

    def __init__(self) -> None:
        HTMLParser.__init__(self, convert_charrefs=True)
        self.comments: List[Dict[str, str]] = []
        self.bodies: Dict[str, List[str]] = {}
        self.total_comments = ""
        self.trees = 0
        self._body_of = ""
        self._depth = 0

    def handle_starttag(self, tag, attrs):
        attributes = {name: (value or "") for name, value in attrs}
        if tag == COMMENT_TAG:
            self.comments.append(attributes)
        elif tag == COMMENT_TREE_TAG:
            self.trees += 1
            self.total_comments = attributes.get(TOTAL_COMMENTS_ATTRIBUTE, "")
        elif tag == DIV_TAG:
            if self._body_of:
                self._depth += 1
                return
            named = attributes.get(ID_ATTRIBUTE, "")
            if named.endswith(COMMENT_BODY_SUFFIX):
                self._body_of = named[: -len(COMMENT_BODY_SUFFIX)]
                self._depth = 1
                self.bodies.setdefault(self._body_of, [])

    def handle_endtag(self, tag):
        if tag == DIV_TAG and self._body_of:
            self._depth -= 1
            if self._depth <= 0:
                self._body_of = ""

    def handle_data(self, data):
        if self._body_of:
            self.bodies[self._body_of].append(data)


def collapsed(parts: List[str]) -> str:
    """One body's text with the markup's own whitespace collapsed."""

    return " ".join("".join(parts).split())


def _named(pairs: List[Tuple[str, str]], name: str, value: Any) -> None:
    if isinstance(value, str) and value:
        pairs.append((name, value))


def _engagement(pairs: Tuple[Tuple[str, Any], ...]) -> Tuple[Tuple[str, int], ...]:
    counted = []
    for name, value in pairs:
        exact = exact_count(value)
        if exact is not None:
            counted.append((name, exact))
    return tuple(counted)


def _missing(row: Mapping[str, str], keys: Tuple[str, ...]) -> Tuple[str, ...]:
    return tuple(key for key in keys if not row.get(key))


def _listing_record(position: int, post: Mapping[str, str]) -> NativeRecord:
    item_id = fullname(POST_FULLNAME_PREFIX, post.get(ID_ATTRIBUTE, ""))
    permalink = post.get(PERMALINK_ATTRIBUTE, "")
    community = subreddit_of(
        post.get(SUBREDDIT_PREFIXED_ATTRIBUTE) or post.get(SUBREDDIT_NAME_ATTRIBUTE, "")
    )
    row = {
        "native_item_id": item_id,
        "title": post.get(POST_TITLE_ATTRIBUTE, ""),
        "author": post.get(AUTHOR_ATTRIBUTE, ""),
        "published_at": route_instant_to_utc_iso(post.get(CREATED_TIMESTAMP_ATTRIBUTE)),
    }
    named: List[Tuple[str, str]] = []
    _named(named, POST_TYPE_ATTRIBUTE, post.get(POST_TYPE_ATTRIBUTE))
    _named(named, DOMAIN_ATTRIBUTE, post.get(DOMAIN_ATTRIBUTE))
    _named(named, UPVOTE_RATIO_ATTRIBUTE, post.get(UPVOTE_RATIO_ATTRIBUTE))
    _named(named, AWARD_COUNT_ATTRIBUTE, post.get(AWARD_COUNT_ATTRIBUTE))
    _named(named, CONTENT_HREF_ATTRIBUTE, post.get(CONTENT_HREF_ATTRIBUTE))
    return NativeRecord(
        canonical_content_kind="post",
        canonical_locator=post_locator(permalink),
        native_item_id=item_id,
        title=row["title"],
        author=row["author"],
        community=community,
        published_at=row["published_at"],
        engagement=_engagement(
            (
                (SCORE_METRIC, post.get(SCORE_ATTRIBUTE)),
                (COMMENT_COUNT_METRIC, post.get(COMMENT_COUNT_ATTRIBUTE)),
            )
        ),
        attributes=tuple(named),
        native_position=position,
        loss=(FIELD_OMITTED,) if _missing(row, POST_ROW_KEYS) else (),
    )


def _tracking_context(raw: str) -> Mapping[str, Any]:
    if not raw:
        return {}
    try:
        found = json.loads(raw)
    except ValueError:
        return {}
    return found if isinstance(found, Mapping) else {}


def _search_record(position: int, row: Mapping[str, Any]) -> NativeRecord:
    context = _tracking_context(row.get("context", ""))
    post = context.get("post") if isinstance(context.get("post"), Mapping) else {}
    profile = context.get("profile") if isinstance(context.get("profile"), Mapping) else {}
    subreddit = context.get("subreddit") if isinstance(context.get("subreddit"), Mapping) else {}
    item_id = fullname(
        POST_FULLNAME_PREFIX, row.get("thing_id", "") or str(post.get("id", "") or "")
    )
    title = post.get("title") if isinstance(post.get("title"), str) else ""
    numbers = row.get("numbers") or []
    published_at = route_instant_to_utc_iso(row.get("published_at"))
    return NativeRecord(
        canonical_content_kind="post",
        canonical_locator=post_locator(row.get("permalink", "")),
        native_item_id=item_id,
        title=title or row.get("title", ""),
        author=profile.get("name") if isinstance(profile.get("name"), str) else "",
        community=subreddit.get("name") if isinstance(subreddit.get("name"), str) else "",
        published_at=published_at,
        engagement=_engagement(tuple(zip((SCORE_METRIC, COMMENT_COUNT_METRIC), tuple(numbers)[:2]))),
        native_position=position,
        loss=(FIELD_OMITTED,)
        if _missing(
            {
                "native_item_id": item_id,
                "title": title or row.get("title", ""),
                "author": profile.get("name") or "",
                "published_at": published_at,
            },
            POST_ROW_KEYS,
        )
        else (),
    )


def _comment_record(
    position: int, comment: Mapping[str, str], body: str, community: str
) -> NativeRecord:
    item_id = comment.get(THING_ID_ATTRIBUTE, "")
    permalink = comment.get(PERMALINK_ATTRIBUTE, "")
    parent = comment.get(PARENT_ID_ATTRIBUTE) or comment.get(POST_ID_ATTRIBUTE, "")
    row = {
        "native_item_id": item_id,
        "body": body,
        "author": comment.get(AUTHOR_ATTRIBUTE, ""),
        "published_at": route_instant_to_utc_iso(comment.get(CREATED_ATTRIBUTE)),
    }
    named: List[Tuple[str, str]] = []
    _named(named, DEPTH_ATTRIBUTE, comment.get(DEPTH_ATTRIBUTE))
    _named(named, "link_id", comment.get(POST_ID_ATTRIBUTE))
    _named(named, AWARD_COUNT_ATTRIBUTE, comment.get(AWARD_COUNT_ATTRIBUTE))
    return NativeRecord(
        canonical_content_kind="comment",
        canonical_locator=post_locator(permalink),
        native_item_id=item_id,
        native_parent_id=parent,
        body=body,
        author=row["author"],
        community=community,
        published_at=row["published_at"],
        engagement=_engagement(((SCORE_METRIC, comment.get(SCORE_ATTRIBUTE)),)),
        attributes=tuple(named),
        native_position=position,
        loss=(FIELD_OMITTED,) if _missing(row, COMMENT_ROW_KEYS) else (),
    )


def _failed(
    descriptor: AdapterDescriptor,
    response: transport.TransportResponse,
    native_order: str,
    loss: str,
    warning: str,
) -> NativePage:
    return build_native_page(
        descriptor,
        (),
        observed_at=response.observed_at,
        native_order=native_order,
        warnings=(warning,),
        outcome="failed",
        loss=(loss,),
    )


def _drifted(
    descriptor: AdapterDescriptor,
    response: transport.TransportResponse,
    native_order: str,
    detail: str,
) -> NativePage:
    """Type a successful response whose custom-element shape has changed."""

    return _failed(
        descriptor,
        response,
        native_order,
        SCHEMA_DRIFT,
        "route {0} answered {1} and {2}: the partial this adapter reads has"
        " changed shape".format(descriptor.route_id, response.status, detail),
    )


def _status_refused(
    descriptor: AdapterDescriptor, response: transport.TransportResponse, native_order: str
) -> Optional[NativePage]:
    if response.status == 200:
        return None
    return _failed(
        descriptor,
        response,
        native_order,
        HTTP_STATUS,
        "http status {0} from {1}".format(response.status, descriptor.route_id),
    )


def _listing_page(response: transport.TransportResponse) -> NativePage:
    native_order = NATIVE_ORDERS[LISTING_OPERATION]
    refused = _status_refused(DESCRIPTOR, response, native_order)
    if refused is not None:
        return refused
    parser = _ListingParser()
    parser.feed(response.body)
    parser.close()
    records = tuple(
        _listing_record(position, post) for position, post in enumerate(parser.posts)
    )
    if not records and not parser.partials:
        return _drifted(
            DESCRIPTOR, response, native_order, "carried no <" + POST_TAG + "> and no partial"
        )
    return build_native_page(
        DESCRIPTOR,
        records,
        observed_at=response.observed_at,
        cursor_out=parser.next_cursor,
        native_order=native_order,
        outcome="ok" if records else "empty",
        warnings=()
        if records
        else (
            "route {0} answered 200 with no <{1}>: this listing holds no post".format(
                DESCRIPTOR.route_id, POST_TAG
            ),
        ),
    )


def _search_page(
    descriptor: AdapterDescriptor, response: transport.TransportResponse
) -> NativePage:
    native_order = NATIVE_ORDERS[SEARCH_OPERATION]
    refused = _status_refused(descriptor, response, native_order)
    if refused is not None:
        return refused
    parser = _SearchParser()
    parser.feed(response.body)
    parser.close()
    records = tuple(
        _search_record(position, row)
        for position, row in enumerate(parser.rows)
        if row.get("thing_id") or row.get("context")
    )
    if not records and parser.trackers:
        return _drifted(
            descriptor,
            response,
            native_order,
            "carried {0} <{1}> row(s) naming no identity".format(
                parser.trackers, TELEMETRY_TAG
            ),
        )
    return build_native_page(
        descriptor,
        records,
        observed_at=response.observed_at,
        cursor_out=parser.next_cursor,
        native_order=native_order,
        outcome="ok" if records else "empty",
        warnings=()
        if records
        else (
            "route {0} answered 200 with no <{1}> row: this query matched"
            " nothing".format(descriptor.route_id, TELEMETRY_TAG),
        ),
    )


def _comments_page(response: transport.TransportResponse, community: str) -> NativePage:
    native_order = NATIVE_ORDERS[COMMENTS_OPERATION]
    refused = _status_refused(COMMENTS_DESCRIPTOR, response, native_order)
    if refused is not None:
        return refused
    parser = _CommentParser()
    parser.feed(response.body)
    parser.close()
    records = tuple(
        _comment_record(
            position,
            comment,
            collapsed(parser.bodies.get(comment.get(THING_ID_ATTRIBUTE, ""), [])),
            community,
        )
        for position, comment in enumerate(parser.comments)
    )
    if not records and not parser.trees:
        return _drifted(
            COMMENTS_DESCRIPTOR,
            response,
            native_order,
            "carried no <" + COMMENT_TREE_TAG + "> and no <" + COMMENT_TAG + ">",
        )
    warnings: List[str] = []
    if not records:
        warnings.append(
            "route {0} answered 200 with a <{1}> holding no <{2}>: this post has"
            " no comment".format(
                COMMENTS_DESCRIPTOR.route_id, COMMENT_TREE_TAG, COMMENT_TAG
            )
        )
    else:
        stated = exact_count(parser.total_comments)
        if stated is not None and stated > len(records):
            warnings.append(
                "this post states {0} comments and this page carried {1}: the rest"
                " are behind the more-comments continuation, which declares a POST"
                " this package does not admit".format(stated, len(records))
            )
    return build_native_page(
        COMMENTS_DESCRIPTOR,
        records,
        observed_at=response.observed_at,
        native_order=native_order,
        outcome="ok" if records else "empty",
        warnings=tuple(warnings),
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

    operation, argument = operation_for(request)
    try:
        if operation == LISTING_OPERATION:
            return _fetch_listing(carrier, argument, request)
        if operation == COMMENTS_OPERATION:
            return _fetch_comments(carrier, argument)
        return _fetch_search(carrier, argument, request)
    except ShredditError as error:
        return build_native_page(
            DESCRIPTOR,
            (),
            native_order=NATIVE_ORDERS.get(operation, NATIVE_ORDERS[SEARCH_OPERATION]),
            warnings=(str(error),),
            outcome="refused",
            loss=(UNSELECTED_TARGET,),
        )


def _origin_window(argument_window: str, request: AdapterRequest) -> str:
    """The `t=` this call sends: the step's own window, or the query's.

    A windowed discovery step's `window_start`/`window_end` (`AdapterRequest`'s
    own fields, per its docstring "the step's own bounds") take the origin's
    `t=` over anything the caller's target string names — `origin_time_bucket`
    is the derivation. Absent that
    step-level window, the caller's own `:t=<window>`/embedded window keeps
    deciding exactly as it always has: an unwindowed step is byte-for-byte the
    request it always sent.
    """

    if request.window_start:
        return origin_time_bucket(request.window_start, request.window_end)
    return argument_window


def _fetch_listing(
    carrier: transport.Transport, argument: str, request: AdapterRequest
) -> NativePage:
    subreddit, sort, window = listing_target(argument)
    params: Dict[str, str] = {"sort": sort, "name": subreddit}
    origin_window = _origin_window(window, request)
    if origin_window:
        params["t"] = origin_window
    if request.cursor:
        params[AFTER_PARAM] = request.cursor
    return fetch_one_page(
        DESCRIPTOR,
        carrier,
        params=params,
        parse=_listing_page,
        native_order=NATIVE_ORDERS[LISTING_OPERATION],
    )


def _fetch_search(carrier: transport.Transport, argument: str, request: AdapterRequest) -> NativePage:
    subreddit, query, sort, window = search_target(argument)
    descriptor = SUBREDDIT_SEARCH_DESCRIPTOR if subreddit else SEARCH_DESCRIPTOR
    params: Dict[str, str] = {"q": query, "type": "posts", "sort": sort}
    if subreddit:
        params["subreddit"] = subreddit
    origin_window = _origin_window(window, request)
    if origin_window:
        params["t"] = origin_window
    if request.cursor:
        params[CURSOR_PARAM] = request.cursor

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
