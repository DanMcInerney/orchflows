"""Private extraction of native Bluesky post views."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List, Mapping, Optional, Sequence, Tuple

from .. import NativeRecord

# Where a Bluesky post lives for a reader. The AppView answers at an API host,
# while neither payload publishes a web locator for a post. Its ``at://`` URI
# is an identity, so the reader address is composed from the stated handle and
# record key.
BLUESKY_APP_ORIGIN = "https://bsky.app"
PROFILE_PATH = "/profile/"
POST_PATH = "/post/"

# Both surfaces answer with native post views.
POST_KIND = "post"

# The AppView's own names for fields carried into a native record.
URI_KEY = "uri"
CID_KEY = "cid"
AUTHOR_KEY = "author"
HANDLE_KEY = "handle"
DID_KEY = "did"
RECORD_KEY = "record"
TEXT_KEY = "text"
CREATED_AT_KEY = "createdAt"
INDEXED_AT_KEY = "indexedAt"
REPLY_KEY = "reply"
PARENT_KEY = "parent"
ROOT_KEY = "root"

LIKE_COUNT_METRIC = "likeCount"
REPOST_COUNT_METRIC = "repostCount"
REPLY_COUNT_METRIC = "replyCount"
QUOTE_COUNT_METRIC = "quoteCount"
POST_METRICS = (
    LIKE_COUNT_METRIC,
    REPOST_COUNT_METRIC,
    REPLY_COUNT_METRIC,
    QUOTE_COUNT_METRIC,
)

# A reply's thread root is separate from its native parent.
ROOT_URI_ATTRIBUTE = "root_uri"

# A row naming no URI is not a post; these other omissions are record loss.
POST_ROW_KEYS = (URI_KEY, TEXT_KEY, HANDLE_KEY, CREATED_AT_KEY)

ROUTE_INSTANT_FORMAT = "%Y-%m-%dT%H:%M:%S"
RECORD_INSTANT_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
FIELD_OMITTED = "field_omitted"


def record_key(uri: str) -> str:
    """One post's record key: the last segment of the ``at://`` URI naming it.

    An ``at://`` URI is an identity — an authority, a collection, and a key —
    and the key is the part a reader's address ends in. Nothing else is taken
    apart: the authority in the URI is a decentralised identifier and the
    address is built from the handle the payload states beside it.
    """

    held = (uri or "").strip()
    if not held or held.endswith("/"):
        return ""
    _, separator, last = held.rpartition("/")
    return last if separator else ""


def post_locator(handle: str, uri: str) -> str:
    """One post's address on Bluesky's own app, or nothing without both parts."""

    key = record_key(uri)
    if not handle or not key:
        return ""
    return BLUESKY_APP_ORIGIN + PROFILE_PATH + handle + POST_PATH + key


def _text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def exact_count(value: Any) -> Optional[int]:
    """One exact integer the AppView published, or nothing at all."""

    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def route_instant_to_utc_iso(stamped: Any) -> str:
    """This payload's stamp as the artifact's instant, or nothing.

    The fraction is dropped rather than rounded, so nothing is stated that
    the origin did not; another spelling is a missing time, not an estimate.
    """

    if not isinstance(stamped, str) or not stamped.strip():
        return ""
    text = stamped.strip()
    if text.endswith("Z"):
        text = text[:-1]
    text = text.split(".")[0]
    try:
        moment = datetime.strptime(text, ROUTE_INSTANT_FORMAT)
    except ValueError:
        return ""
    return moment.replace(tzinfo=timezone.utc).strftime(RECORD_INSTANT_FORMAT)


def _nested(payload: Any, *keys: str) -> Any:
    """One value under a key path, or None once the path leaves a mapping."""

    held: Any = payload
    for key in keys:
        if not isinstance(held, Mapping):
            return None
        held = held.get(key)
    return held


def _missing(row: Mapping[str, Any], keys: Sequence[str]) -> Tuple[str, ...]:
    """Which of this row's declared fields the payload did not report."""

    return tuple(key for key in keys if not row.get(key))


def _engagement(post: Mapping[str, Any]) -> Tuple[Tuple[str, int], ...]:
    """The counts this post stated, in the declared order, and no others."""

    counted: List[Tuple[str, int]] = []
    for name in POST_METRICS:
        exact = exact_count(post.get(name))
        if exact is not None:
            counted.append((name, exact))
    return tuple(counted)


def reply_parents_of(post: Mapping[str, Any]) -> Tuple[str, str]:
    """The post this one answers, and the root of its thread.

    Both are empty for a post that answers nothing. The AppView states each on
    the record, so neither is derived and a root is never treated as a parent.
    """

    parent = _text(_nested(post, RECORD_KEY, REPLY_KEY, PARENT_KEY, URI_KEY))
    root = _text(_nested(post, RECORD_KEY, REPLY_KEY, ROOT_KEY, URI_KEY))
    return (parent, root)


def _post_record(position: int, post: Mapping[str, Any]) -> NativeRecord:
    """One post as either method's post view described it."""

    uri = _text(post.get(URI_KEY))
    handle = _text(_nested(post, AUTHOR_KEY, HANDLE_KEY))
    row = {
        URI_KEY: uri,
        TEXT_KEY: _text(_nested(post, RECORD_KEY, TEXT_KEY)),
        HANDLE_KEY: handle,
        CREATED_AT_KEY: route_instant_to_utc_iso(_nested(post, RECORD_KEY, CREATED_AT_KEY)),
    }
    parent, root = reply_parents_of(post)
    named: List[Tuple[str, str]] = []
    for name, value in (
        (DID_KEY, _text(_nested(post, AUTHOR_KEY, DID_KEY))),
        (CID_KEY, _text(post.get(CID_KEY))),
        (INDEXED_AT_KEY, _text(post.get(INDEXED_AT_KEY))),
        (ROOT_URI_ATTRIBUTE, root),
    ):
        if value:
            named.append((name, value))
    return NativeRecord(
        canonical_content_kind=POST_KIND,
        canonical_locator=post_locator(handle, uri),
        native_item_id=uri,
        native_parent_id=parent,
        body=row[TEXT_KEY],
        author=handle,
        published_at=row[CREATED_AT_KEY],
        engagement=_engagement(post),
        attributes=tuple(named),
        native_position=position,
        loss=(FIELD_OMITTED,) if _missing(row, POST_ROW_KEYS) else (),
    )
