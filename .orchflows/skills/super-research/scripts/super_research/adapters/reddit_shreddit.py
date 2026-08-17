"""K2 Reddit through the `/svc/shreddit/` partials its own web client loads.

Measured 2026-08-17 (Reddit, shreddit partials). Reddit's `.json` surfaces
answer 403 to every identity and its `.rss` surface answers one read per
minute, which is why the roster held a freshness probe and no search at all.
These partials are a different bucket entirely — `x-ratelimit-remaining: 199.0`
after the first read, against `0.0` on the feed — and they carry the platform's
own counts:

- `community-more-posts/<sort>/?name=<sub>` answered 200 with 24
  ``<shreddit-post>`` elements stating ``score``, ``comment-count``,
  ``post-title``, ``author``, ``created-timestamp``, ``permalink`` and
  ``subreddit-prefixed-name``, and a ``<faceplate-partial>`` naming the next
  page's ``after`` cursor.
- ``search?q=&type=posts`` and ``r/<sub>/search?q=`` answered 200 with seven
  posts per page, each a ``<search-telemetry-tracker>`` whose
  ``data-faceplate-tracking-context`` is the row's own JSON — id, title,
  author, subreddit — beside a ``<faceplate-timeago>`` and two
  ``<faceplate-number>`` elements, and a ``<faceplate-partial>`` naming the
  next page's cursor. **This is the one keyless Reddit search in the roster.**
- ``comments/r/<sub>/<t3_id>`` answered 200 with 25 ``<shreddit-comment>``
  elements stating ``score``, ``depth``, ``author``, ``created``,
  ``permalink``, ``thingid``, ``parentid`` and ``postid``, each body in a
  ``<div id="<thingid>-post-rtjson-content">``, under a
  ``<shreddit-comment-tree>`` stating ``totalcomments``. **This is the one
  keyless Reddit comment surface in the roster**, and comment-level sentiment
  was unreachable without it.

**The two numbers on a search row are named from a measurement, not a guess.**
The markup names neither: a row carries two bare ``<faceplate-number>``
elements. For `t3_1vpgr1i` the pair read 567 and 299 on 2026-08-17, and that
post's own comment tree answered ``totalcomments="299"`` — so the second is the
comment count and the first is the score, and they are carried under the names
the sibling listing surface spells for the same two quantities. Anything the
markup did name is carried under the name it used.

**What is not here.** The comment partial's own ``more-comments`` continuation
declares ``method="post"``, and a GET of it answered 200 carrying no comment,
so replies past the depth one page reaches are behind a verb this package does
not admit. No route is declared for it, the page states the cap it hit, and
`protocol.md` records the deferral. Nothing here retries, and nothing pages the
comment surface.
"""

from __future__ import annotations

import json
import urllib.parse
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

# Where a Reddit item lives. It is this route's own origin, and it is spelled
# through the transport's constant rather than here: a permalink these partials
# publish is relative to the site they are served from.
REDDIT_ORIGIN = transport.REDDIT_SITE_ORIGIN

# Reddit's fullname prefixes. A bare base-36 id is not an identity — wrong-merge
# rule 6 makes the prefix part of it — so every id this module emits carries one.
POST_FULLNAME_PREFIX = "t3_"
COMMENT_FULLNAME_PREFIX = "t1_"

# The listing surface, and this adapter's primary: a step naming a subreddit and
# no operation is asking for that subreddit's posts.
DESCRIPTOR = AdapterDescriptor(
    adapter_id="reddit_shreddit",
    adapter_version="1",
    access_class="K2",
    route_id=transport.REDDIT_SHREDDIT_LISTING_ROUTE,
    platform="reddit",
    native_identity_namespace="reddit",
    representation_kind="native",
    operator_identity="reddit",
    # Measured 2026-08-17: the bucket answered 200 with `x-ratelimit-remaining`
    # falling from 199 by one per read, against a window `x-ratelimit-reset`
    # stated as a few hundred seconds. That is two hundred reads per window and
    # this package spends far fewer; one and a half seconds apart, ten at once,
    # is well inside it and is not a number anyone has been refused at.
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
    # A comment carries its own score and no count of anything else: it states
    # no reply count, and the tree's `totalcomments` is the post's rather than
    # any comment's. So neither counted order has a metric here, which is a
    # stated absence rather than a zero nobody reported.
    page_size=25,
)

SURFACE_DESCRIPTORS = (
    DESCRIPTOR,
    SEARCH_DESCRIPTOR,
    SUBREDDIT_SEARCH_DESCRIPTOR,
    COMMENTS_DESCRIPTOR,
)

# The operations, spelled once each. A caller names one with a prefix, because
# four surfaces answer four questions; absent a prefix the step's own shape
# decides, and never the characters in the argument.
LISTING_OPERATION = "listing"
SEARCH_OPERATION = "search"
COMMENTS_OPERATION = "comments"
SHREDDIT_OPERATIONS = (LISTING_OPERATION, SEARCH_OPERATION, COMMENTS_OPERATION)

# What each surface's rows arrive in.
NATIVE_ORDERS = {
    LISTING_OPERATION: "reddit_shreddit_listing_order",
    SEARCH_OPERATION: "reddit_shreddit_search_order",
    COMMENTS_OPERATION: "reddit_shreddit_comment_order",
}

# The sorts each surface admits, spelled out so a caller's word is checked
# against the route's own vocabulary rather than passed through. A sort this
# table does not name is refused before any call.
LISTING_SORTS = ("new", "hot", "top", "rising")
SEARCH_SORTS = ("relevance", "new", "top", "comments")
COMMENT_SORTS = ("top", "new", "controversial", "old", "qa")
# The windows the listing and search surfaces take, in the origin's own words.
TIME_WINDOWS = ("hour", "day", "week", "month", "year", "all")
DEFAULT_LISTING_SORT = "new"
DEFAULT_SEARCH_SORT = "new"
DEFAULT_COMMENT_SORT = "top"

# The subreddit scope a search may carry, in the grammar a caller writes it in.
SUBREDDIT_SCOPE_PREFIX = "r/"

# The markup this module reads. Every name is declared, never searched for: a
# parser that hunted for something list-shaped would report a rotated class as
# an empty subreddit, and the whole value of a typed drift is saying which.
POST_TAG = "shreddit-post"
COMMENT_TAG = "shreddit-comment"
COMMENT_TREE_TAG = "shreddit-comment-tree"
TELEMETRY_TAG = "search-telemetry-tracker"
NUMBER_TAG = "faceplate-number"
TIMEAGO_TAG = "faceplate-timeago"
PARTIAL_TAG = "faceplate-partial"
ANCHOR_TAG = "a"
DIV_TAG = "div"

# The attributes those tags carry, as `html.parser` reports them — lowercased,
# which is what HTML itself says an attribute name is.
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
# What a comment's body div is called: the thing's own fullname, then this.
COMMENT_BODY_SUFFIX = "-post-rtjson-content"

# The two metric names this adapter emits. They are the listing surface's own
# attribute names, and the search surface's unnamed pair is carried under them
# because the measurement in the module docstring says they are the same two
# quantities.
SCORE_METRIC = "score"
COMMENT_COUNT_METRIC = "comment-count"

# The cursor parameters each paging surface names, read back off the
# continuation the page itself published.
AFTER_PARAM = "after"
CURSOR_PARAM = "cursor"

# The instant these partials write, and the one a record holds. Reddit writes
# microseconds and a numeric offset; every stamp measured was `+0000`.
ROUTE_INSTANT_LENGTH = 19
RECORD_INSTANT_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
UTC_OFFSETS = ("+0000", "+00:00", "Z")

HTTP_STATUS = "http_status"
SCHEMA_DRIFT = "schema_drift"
FIELD_OMITTED = "field_omitted"
UNSELECTED_TARGET = "unselected_target"

# What each kind of row promises, so a record short of it says so.
POST_ROW_KEYS = ("native_item_id", "title", "author", "published_at")
COMMENT_ROW_KEYS = ("native_item_id", "body", "author", "published_at")


class ShredditError(ValueError):
    """A caller asked this adapter for something the route does not serve."""


def route_instant_to_utc_iso(stamp: Any) -> str:
    """One partial's stamp as the artifact's instant, or nothing.

    ``2026-08-17T14:23:02.287000+0000`` is the shape these partials write.
    The fraction is dropped rather than rounded and the offset is required to
    be UTC: a stamp in another zone would be an instant this module shifted,
    and shifting one is inventing a moment the origin did not state.
    """

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
    """One count the markup published as an exact decimal, or nothing.

    An attribute is a string, so a count is its digits and nothing else: a
    value carrying a separator, a suffix, or a sign is a number formatted for
    a reader rather than the one the platform holds.
    """

    if not isinstance(value, str):
        return None
    held = value.strip()
    if not held or not held.isdigit():
        return None
    return int(held)


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


def fullname(prefix: str, value: str) -> str:
    """One id under Reddit's own fullname prefix, whichever form it arrived in."""

    held = (value or "").strip()
    if not held:
        return ""
    return held if held.startswith(prefix) else prefix + held


def bare_id(value: str) -> str:
    """One fullname's base-36 id, for the surfaces that take it that way."""

    held = (value or "").strip()
    for prefix in (POST_FULLNAME_PREFIX, COMMENT_FULLNAME_PREFIX):
        if held.startswith(prefix):
            return held[len(prefix) :]
    return held


def subreddit_of(prefixed: str) -> str:
    """A subreddit's bare name, from either spelling these partials use."""

    held = (prefixed or "").strip()
    return held[len(SUBREDDIT_SCOPE_PREFIX) :] if held.startswith(SUBREDDIT_SCOPE_PREFIX) else held


def post_locator(permalink: str) -> str:
    return REDDIT_ORIGIN + permalink if permalink.startswith("/") else permalink


def cursor_in(source: str, name: str) -> str:
    """One continuation parameter off the address a partial published.

    The page states where its next one is; this reads the one parameter that
    names it and nothing else, so a continuation is the origin's own and never
    a next offset this module derived.
    """

    if not source:
        return ""
    query = urllib.parse.urlsplit(source).query
    for key, value in urllib.parse.parse_qsl(query, keep_blank_values=True):
        if key == name and value:
            return value
    return ""


class _ListingParser(HTMLParser):
    """Every ``<shreddit-post>`` on one listing page, and the next page's cursor."""

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
    """Every search row on one page, in the order the page laid them out.

    A row opens at a ``<search-telemetry-tracker>`` carrying this page's own
    JSON about it, and everything until the next one belongs to it: the title
    anchor, the timeago, and the two numbers the docstring's measurement names.
    """

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
    """Every ``<shreddit-comment>`` on one page, each with the body div it owns.

    A body is not the comment element's text: it is a ``<div>`` named after the
    comment's own fullname, so the text is collected between that div opening
    and its matching close. Nesting is counted rather than assumed, because a
    body holds markup of its own.
    """

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
    """One body's text as one string, with the markup's own whitespace collapsed."""

    return " ".join("".join(parts).split())


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
    # A ratio is a float and is never an engagement snapshot; it rides here as
    # the exact string the markup wrote.
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
    """One search row's own JSON about itself, or nothing this module can read."""

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
    return NativeRecord(
        canonical_content_kind="post",
        canonical_locator=post_locator(row.get("permalink", "")),
        native_item_id=item_id,
        title=title or row.get("title", ""),
        author=profile.get("name") if isinstance(profile.get("name"), str) else "",
        community=subreddit.get("name") if isinstance(subreddit.get("name"), str) else "",
        published_at=route_instant_to_utc_iso(row.get("published_at")),
        # The measured pair: score first, comment count second. A row that
        # carried fewer than two numbers contributes only what it carried.
        engagement=_engagement(
            tuple(
                zip((SCORE_METRIC, COMMENT_COUNT_METRIC), tuple(numbers)[:2])
            )
        ),
        native_position=position,
        loss=(FIELD_OMITTED,)
        if _missing(
            {
                "native_item_id": item_id,
                "title": title or row.get("title", ""),
                "author": profile.get("name") or "",
                "published_at": route_instant_to_utc_iso(row.get("published_at")),
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
    # A reply names the comment it answers; a top-level comment names the post,
    # which is what Reddit itself puts in `parent_id` for one.
    parent = comment.get(PARENT_ID_ATTRIBUTE) or comment.get(POST_ID_ATTRIBUTE, "")
    row = {
        "native_item_id": item_id,
        "body": body,
        "author": comment.get(AUTHOR_ATTRIBUTE, ""),
        "published_at": route_instant_to_utc_iso(comment.get(CREATED_ATTRIBUTE)),
    }
    named: List[Tuple[str, str]] = []
    _named(named, DEPTH_ATTRIBUTE, comment.get(DEPTH_ATTRIBUTE))
    # The thread this comment belongs to, under Reddit's own name for it. It is
    # never this record's engagement: a comment weighted by its parent thread's
    # counts is the attribution error the 2026-08-17 review measured.
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
    """The origin answered 200 and what it answered with is not this partial.

    Never `empty`: a subreddit with nothing in it and a partial whose custom
    elements were renamed arrive at the same door, and only the first is a
    statement about Reddit.
    """

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
            # The page's own account of what it did not carry. It is a warning
            # rather than `recall_window_partial`, which is the core's word for
            # a cap it enforced: this is the origin paging, and the rest of the
            # tree sits behind a `more-comments` POST no route here declares.
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
    """``<subreddit>[:<sort>[:<window>]]``, checked against the route's vocabulary."""

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
    """``[r/<subreddit>:]<query>[:sort=<sort>][:t=<window>]`` as the caller wrote it.

    The scope comes first because it decides which of two routes answers, and
    the query keeps every character the caller gave it that is not one of the
    two trailing options — a search text may contain a colon, and a rule that
    split on every one would silently truncate it.
    """

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
    """``<subreddit>/<post id>[:<sort>]``, or the permalink a discovery row carried.

    A permalink is what a discovery record's locator actually is, so a caller
    freezing a hit does not have to take it apart; both forms name the same two
    things this route needs.
    """

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
    """The operation this call performs, and the argument it performs it on.

    A caller names the operation, because four surfaces answer four questions.
    Absent a name the step's own shape decides: a step naming a target reads
    that post's comments, and a step naming only a query searches all of
    Reddit. Neither is inferred from the characters in the argument, so a query
    that happens to look like a permalink stays a query.
    """

    named = request.target_ids[0] if request.target_ids else request.query
    kind, separator, argument = named.partition(":")
    if separator and kind in SHREDDIT_OPERATIONS:
        return (kind, argument)
    return (COMMENTS_OPERATION if request.target_ids else SEARCH_OPERATION, named)


def fetch_native_page(carrier: transport.Transport, request: AdapterRequest) -> NativePage:
    """Read one shreddit partial once and return exactly one NativePage.

    One call, one surface. Which one to read next — a search row's comments, a
    listing's next page — is the core's decision, from the cursor a page
    published or from a hit a caller froze.
    """

    operation, argument = operation_for(request)
    try:
        if operation == LISTING_OPERATION:
            return _fetch_listing(carrier, argument, request.cursor)
        if operation == COMMENTS_OPERATION:
            return _fetch_comments(carrier, argument)
        return _fetch_search(carrier, argument, request.cursor)
    except ShredditError as error:
        # A target this route's grammar does not serve costs a page and no
        # read. Typed rather than raised, for the reason every other failure
        # here is: an adapter that raised would cost the core the one page it
        # is owed, and the caller would learn nothing about which rule it met.
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
