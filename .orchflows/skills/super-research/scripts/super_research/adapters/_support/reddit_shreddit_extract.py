"""Typed HTML extraction for Reddit Shreddit partials."""

from __future__ import annotations

import json
from html.parser import HTMLParser
from typing import Any, Dict, List, Mapping, Tuple

from .. import NativeRecord
from .reddit_shreddit_contract import (
    AFTER_PARAM,
    ANCHOR_TAG,
    AUTHOR_ATTRIBUTE,
    AWARD_COUNT_ATTRIBUTE,
    COMMENT_BODY_SUFFIX,
    COMMENT_COUNT_ATTRIBUTE,
    COMMENT_COUNT_METRIC,
    COMMENT_ROW_KEYS,
    COMMENT_TAG,
    COMMENT_TREE_TAG,
    CONTENT_HREF_ATTRIBUTE,
    CREATED_ATTRIBUTE,
    CREATED_TIMESTAMP_ATTRIBUTE,
    CURSOR_PARAM,
    DEPTH_ATTRIBUTE,
    DIV_TAG,
    DOMAIN_ATTRIBUTE,
    FIELD_OMITTED,
    HREF_ATTRIBUTE,
    ID_ATTRIBUTE,
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
    SCORE_ATTRIBUTE,
    SCORE_METRIC,
    SEARCH_POST_TEST_ID,
    SOURCE_ATTRIBUTE,
    SUBREDDIT_NAME_ATTRIBUTE,
    SUBREDDIT_PREFIXED_ATTRIBUTE,
    TELEMETRY_TAG,
    TEST_ID_ATTRIBUTE,
    THING_ID_ATTRIBUTE,
    THING_ID_DATA_ATTRIBUTE,
    TIMEAGO_TAG,
    TIMESTAMP_ATTRIBUTE,
    TOTAL_COMMENTS_ATTRIBUTE,
    TRACKING_CONTEXT_ATTRIBUTE,
    UPVOTE_RATIO_ATTRIBUTE,
    cursor_in,
    exact_count,
    fullname,
    post_locator,
    route_instant_to_utc_iso,
    subreddit_of,
)


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
