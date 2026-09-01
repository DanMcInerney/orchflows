"""Record extraction for TikTok's own rehydration JSON: a video, a profile.

Both shapes are read under TikTok's own key names, never a cross-platform
vocabulary this package would be inventing: ``diggCount`` stays ``diggCount``
in ``engagement``, exactly as ``instagram_public`` keeps ``edge_liked_by.count``
its own name rather than becoming a generic ``like_count``.

TikTok publishes a video's counts twice — ``statsV2`` as decimal strings and
``stats`` as a mixed bag where most values are already ``int`` and one
(``collectCount``, measured 2026-09-01) is not. ``statsV2`` is read first
because it is the complete, consistently-spelled set; ``stats`` fills in only
a name ``statsV2`` did not carry at all. A ``statsV2`` string that is present
but not all digits is not a fallback case — a count that arrived corrupted is
a count nobody reported, not one this module goes hunting for a second
opinion on.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List, Mapping, Optional, Sequence, Tuple

from .. import NativeRecord

ID_KEY = "id"
CREATE_TIME_KEY = "createTime"
DESC_KEY = "desc"
AUTHOR_KEY = "author"
UNIQUE_ID_KEY = "uniqueId"
NICKNAME_KEY = "nickname"
SIGNATURE_KEY = "signature"
STATS_KEY = "stats"
STATS_V2_KEY = "statsV2"
TEXT_EXTRA_KEY = "textExtra"
HASHTAG_NAME_KEY = "hashtagName"
HASHTAG_TYPE_KEY = "type"
HASHTAG_TYPE_VALUE = 1
USER_KEY = "user"

VIDEO_KIND = "video"
PROFILE_KIND = "profile"

HASHTAG_ATTRIBUTE = "hashtag"
NICKNAME_ATTRIBUTE = "nickname"

# Named in this order because it is the order the descriptor and the smoke
# probe both spell it in: `diggCount`, `commentCount`, `playCount` are the
# three the probe pins, and `shareCount`, `collectCount`, `repostCount`
# complete the set the 2026-09-01 measurement recorded `statsV2` publishing.
VIDEO_METRIC_NAMES = (
    "diggCount",
    "commentCount",
    "playCount",
    "shareCount",
    "collectCount",
    "repostCount",
)
# What the profile roster row names, per the same measurement: a follower
# count, a like count and a video count. `friendCount` and `followingCount`
# are on the payload and unnamed by any roster row, so neither is read.
PROFILE_METRIC_NAMES = ("followerCount", "heartCount", "videoCount")

# What the smoke probe's own field set names, plus the two identity fields
# every roster row is held to. A record missing one says so, because a
# caller comparing videos needs to know which rows were incomplete rather
# than which reported a zero.
VIDEO_ROSTER_KEYS = (
    ID_KEY,
    DESC_KEY,
    AUTHOR_KEY,
    CREATE_TIME_KEY,
    "diggCount",
    "playCount",
    "commentCount",
)
PROFILE_ROSTER_KEYS = (
    UNIQUE_ID_KEY,
    NICKNAME_KEY,
    SIGNATURE_KEY,
    "followerCount",
    "heartCount",
    "videoCount",
)

RECORD_INSTANT_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def _text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def id_text(value: Any) -> str:
    """One TikTok id in the form a record holds it.

    Measured 2026-09-01: `itemStruct.id` and `author.id` are both already
    decimal strings; `int` is read anyway because a shape this large is
    exactly the kind a vendor reshapes without notice, and a record holding
    `""` for an id that arrived as a number would be a worse failure than one
    line of defense against it.
    """

    if isinstance(value, bool):
        return ""
    if isinstance(value, int):
        return str(value)
    return value if isinstance(value, str) else ""


def route_instant_to_utc_iso(value: Any) -> str:
    """`createTime` as the artifact's instant, or nothing.

    Measured 2026-09-01: `createTime` is a decimal-string count of seconds
    since the epoch, not a number. Only a value that is all digits is read —
    anything else is a missing time rather than a guessed one, and every
    ordering downstream is entitled to know the difference.
    """

    if not isinstance(value, str) or not value.isdigit():
        return ""
    try:
        moment = datetime.fromtimestamp(int(value), tz=timezone.utc)
    except (OSError, OverflowError, ValueError):
        return ""
    return moment.strftime(RECORD_INSTANT_FORMAT)


def exact_count(value: Any) -> Optional[int]:
    """One count TikTok published as an exact native integer, or nothing."""

    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def digit_string_count(value: Any) -> Optional[int]:
    """One count TikTok published as a decimal string, or nothing.

    A string that is not all digits is not read as a number: `statsV2`
    publishing something unparseable in a count's place is a count nobody
    reported, the same reading `route_instant_to_utc_iso` gives a `createTime`
    that fails the same test.
    """

    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def video_engagement(item: Mapping[str, Any]) -> Tuple[Tuple[str, int], ...]:
    """`statsV2` primary, `stats` filling in only a name `statsV2` never had."""

    stats_v2 = item.get(STATS_V2_KEY)
    stats_v2 = stats_v2 if isinstance(stats_v2, Mapping) else {}
    stats = item.get(STATS_KEY)
    stats = stats if isinstance(stats, Mapping) else {}
    found: List[Tuple[str, int]] = []
    for name in VIDEO_METRIC_NAMES:
        if name in stats_v2:
            value = digit_string_count(stats_v2.get(name))
        else:
            value = exact_count(stats.get(name))
        if value is not None:
            found.append((name, value))
    return tuple(found)


def profile_engagement(stats: Mapping[str, Any]) -> Tuple[Tuple[str, int], ...]:
    """The three counts the roster names, each an exact native integer or absent."""

    found: List[Tuple[str, int]] = []
    for name in PROFILE_METRIC_NAMES:
        value = exact_count(stats.get(name))
        if value is not None:
            found.append((name, value))
    return tuple(found)


def hashtags_of(item: Mapping[str, Any]) -> Tuple[str, ...]:
    """Every hashtag this video's `textExtra` named, in the order it named them.

    Measured 2026-09-01: `textExtra` also carries a mention (`@handle`) as an
    entry of a different `type` with an empty `hashtagName` — excluded by
    both tests, so a future entry shape that reuses the name for something
    else is not silently carried as a hashtag it never was.
    """

    entries = item.get(TEXT_EXTRA_KEY)
    found: List[str] = []
    for entry in entries if isinstance(entries, list) else ():
        if not isinstance(entry, Mapping):
            continue
        name = entry.get(HASHTAG_NAME_KEY)
        if isinstance(name, str) and name and entry.get(HASHTAG_TYPE_KEY) == HASHTAG_TYPE_VALUE:
            found.append(name)
    return tuple(found)


def _missing(row: Mapping[str, Any], keys: Sequence[str]) -> Tuple[str, ...]:
    """Which of this row's roster fields the payload did not report.

    Absence, never falsehood: a video nobody has liked reports zero, and zero
    is a count.
    """

    return tuple(key for key in keys if row.get(key) is None or row.get(key) == "")


def _video_locator(origin: str, unique_id: str, item_id: str) -> str:
    if not unique_id or not item_id:
        return ""
    return origin + "/@" + unique_id + "/video/" + item_id


def _profile_locator(origin: str, unique_id: str) -> str:
    if not unique_id:
        return ""
    return origin + "/@" + unique_id


def video_record(
    position: int, item: Mapping[str, Any], origin: str, missing_loss: str
) -> NativeRecord:
    """One video as `itemStruct` reported it."""

    author = item.get(AUTHOR_KEY)
    author = author if isinstance(author, Mapping) else {}
    unique_id = _text(author.get(UNIQUE_ID_KEY))
    nickname = _text(author.get(NICKNAME_KEY))
    item_id = id_text(item.get(ID_KEY))
    published_at = route_instant_to_utc_iso(item.get(CREATE_TIME_KEY))
    body = _text(item.get(DESC_KEY))
    engagement = video_engagement(item)

    row = dict(engagement)
    row[ID_KEY] = item_id
    row[DESC_KEY] = body
    row[AUTHOR_KEY] = unique_id
    row[CREATE_TIME_KEY] = published_at

    named: List[Tuple[str, str]] = [(HASHTAG_ATTRIBUTE, name) for name in hashtags_of(item)]
    if nickname:
        named.append((NICKNAME_ATTRIBUTE, nickname))

    return NativeRecord(
        canonical_content_kind=VIDEO_KIND,
        canonical_locator=_video_locator(origin, unique_id, item_id),
        native_item_id=item_id,
        body=body,
        author=unique_id,
        published_at=published_at,
        engagement=engagement,
        attributes=tuple(named),
        native_position=position,
        loss=(missing_loss,) if _missing(row, VIDEO_ROSTER_KEYS) else (),
    )


def profile_record(
    user: Mapping[str, Any], stats: Mapping[str, Any], origin: str, missing_loss: str
) -> NativeRecord:
    """The account as `userInfo` reported it, with no recent-video list.

    `native_item_id` is TikTok's own numeric id when the payload carries one
    and the handle otherwise — the handle is always the account's identity,
    the numeric id is the stronger one when it is there.
    """

    unique_id = _text(user.get(UNIQUE_ID_KEY))
    nickname = _text(user.get(NICKNAME_KEY))
    signature = _text(user.get(SIGNATURE_KEY))
    numeric_id = id_text(user.get(ID_KEY))
    engagement = profile_engagement(stats)

    row = dict(engagement)
    row[UNIQUE_ID_KEY] = unique_id
    row[NICKNAME_KEY] = nickname
    row[SIGNATURE_KEY] = signature

    return NativeRecord(
        canonical_content_kind=PROFILE_KIND,
        canonical_locator=_profile_locator(origin, unique_id),
        native_item_id=numeric_id or unique_id,
        title=nickname,
        body=signature,
        author=unique_id,
        engagement=engagement,
        native_position=0,
        loss=(missing_loss,) if _missing(row, PROFILE_ROSTER_KEYS) else (),
    )
