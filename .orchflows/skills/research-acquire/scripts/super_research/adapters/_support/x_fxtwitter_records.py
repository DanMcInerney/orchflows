"""Record extraction for the FxTwitter adapter facade."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List, Mapping, Optional, Sequence, Tuple

from ... import schema
from .. import NativeRecord

# The one standing fact every record from this route carries. An independent
# operator answered about X; the reader is entitled to know that on the record
# it is holding rather than on a page it would have to go find.
THIRD_PARTY_ARCHIVE = "third_party_archive"
STANDING_LOSS = (THIRD_PARTY_ARCHIVE,)

# Every other key these payloads publish that record extraction reads, under
# the operator's own names. A status first.
ID_KEY = "id"
STATUS_KEY = "status"
URL_KEY = "url"
TEXT_KEY = "text"
AUTHOR_KEY = "author"
SCREEN_NAME_KEY = "screen_name"
CREATED_AT_KEY = "created_at"
CREATED_TIMESTAMP_KEY = "created_timestamp"
LANG_KEY = "lang"
SOURCE_KEY = "source"
PROVIDER_KEY = "provider"
POSSIBLY_SENSITIVE_KEY = "possibly_sensitive"
IS_NOTE_TWEET_KEY = "is_note_tweet"
REPLYING_TO_KEY = "replying_to"

# Then a profile.
NAME_KEY = "name"
DESCRIPTION_KEY = "description"
JOINED_KEY = "joined"
LOCATION_KEY = "location"
PROTECTED_KEY = "protected"
WEBSITE_KEY = "website"
VERIFICATION_KEY = "verification"
VERIFIED_KEY = "verified"
TYPE_KEY = "type"

# The counts a status states, under this operator's own names for them. Every
# one is an exact integer where it is stated at all: `views` is `null` on a
# status nobody has viewed a reported number of times, and a null is a count
# nobody reported rather than a zero this module wrote.
LIKES_METRIC = "likes"
REPOSTS_METRIC = "reposts"
REPLIES_METRIC = "replies"
QUOTES_METRIC = "quotes"
BOOKMARKS_METRIC = "bookmarks"
VIEWS_METRIC = "views"
STATUS_METRICS = (
    LIKES_METRIC,
    REPOSTS_METRIC,
    REPLIES_METRIC,
    QUOTES_METRIC,
    BOOKMARKS_METRIC,
    VIEWS_METRIC,
)

# The counts a profile states, likewise.
FOLLOWERS_METRIC = "followers"
FOLLOWING_METRIC = "following"
MEDIA_COUNT_METRIC = "media_count"
STATUSES_METRIC = "statuses"
PROFILE_METRICS = (
    FOLLOWERS_METRIC,
    FOLLOWING_METRIC,
    LIKES_METRIC,
    MEDIA_COUNT_METRIC,
    STATUSES_METRIC,
)

# The facts each kind of row carries into `attributes`, in the order they are
# carried, each under the name the payload publishes it at and as the exact
# text the payload gave. A name absent from a row is absent from its record.
STATUS_ATTRIBUTES = (
    LANG_KEY,
    SOURCE_KEY,
    # The operator's own spelling of the moment, beside the exact epoch the
    # record's instant is read from. Two statements of one fact, and the
    # record keeps both because they are both the origin's.
    CREATED_AT_KEY,
    POSSIBLY_SENSITIVE_KEY,
    IS_NOTE_TWEET_KEY,
    PROVIDER_KEY,
)
PROFILE_ATTRIBUTES = (LOCATION_KEY, JOINED_KEY, PROTECTED_KEY)
# Three facts carried under the key path the payload publishes them at, because
# each is nested and a bare last segment would name something else on the
# record.
AUTHOR_ID_ATTRIBUTE = "author.id"
REPLYING_TO_URL_ATTRIBUTE = "replying_to.url"
WEBSITE_URL_ATTRIBUTE = "website.url"
VERIFICATION_VERIFIED_ATTRIBUTE = "verification.verified"
VERIFICATION_TYPE_ATTRIBUTE = "verification.type"

# What each kind of row promises, so a record short of it says so. The
# measurement records what these operations answer and what a row carries; the
# row sets are this adapter's own declaration. An id is absent from both: a row
# without one is not a row of that kind at all.
STATUS_ROW_KEYS = (ID_KEY, TEXT_KEY, SCREEN_NAME_KEY, CREATED_TIMESTAMP_KEY)
PROFILE_ROW_KEYS = (ID_KEY, SCREEN_NAME_KEY, NAME_KEY, JOINED_KEY)

# The stamps this operator writes, and the one an artifact record holds. A
# status states an exact epoch second; a profile states only the platform's
# own English spelling of the moment it joined.
#
# The month is numbered before the spelling is read, because `%a` and `%b`
# read their names out of `LC_TIME`: a process that set a locale would stop
# reading this route's own English stamp and lose the time on every profile,
# for a reason that has nothing to do with the origin. The weekday is dropped
# rather than checked — it is derivable from the date, and auditing the
# origin's arithmetic is not this parser's job.
ROUTE_MONTHS = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)
ROUTE_INSTANT_FORMAT = "%m %d %H:%M:%S %z %Y"
RECORD_INSTANT_FORMAT = schema.INSTANT_FORMAT
ROUTE_STAMP_PARTS = 6

FIELD_OMITTED = "field_omitted"
POST_KIND = "post"
PROFILE_KIND = "profile"


def _text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def exact_count(value: Any) -> Optional[int]:
    """One count this operator published as an exact number, or nothing at all.

    A bool is not a count and ``null`` is not one either: every count here
    arrives as a json integer, so anything else is a count this adapter was
    not given rather than one it can recover.
    """

    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def id_text(value: Any) -> str:
    """One identifier as its text, which is the only form a record holds.

    Every id this operator publishes is a string; a number here would be an
    origin that changed its mind, and its decimal digits are still the
    identifier.
    """

    if isinstance(value, bool):
        return ""
    if isinstance(value, int):
        return str(value)
    return value if isinstance(value, str) else ""


def scalar_text(value: Any) -> str:
    """One payload scalar as the exact text a record carries, or nothing.

    A string travels verbatim. A bool is spelled the way json spells one, and
    a number as its own decimal text. Nothing here is rounded, parsed, or
    compared: an attribute states a fact the origin stated.
    """

    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return ""


def epoch_to_utc_iso(seconds: Any) -> str:
    """A status's exact epoch second as the artifact's instant, or nothing.

    A value that is not a whole number is a missing time, and so is one no
    clock can represent — a payload that moved must arrive as a typed answer
    rather than as an exception.
    """

    if isinstance(seconds, bool) or not isinstance(seconds, int):
        return ""
    try:
        moment = datetime.fromtimestamp(seconds, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return ""
    return moment.strftime(RECORD_INSTANT_FORMAT)


def _month_numbered(stamp: str) -> str:
    """This platform's stamp with its month name replaced by the month's number."""

    parts = stamp.split()
    if len(parts) != ROUTE_STAMP_PARTS or parts[1] not in ROUTE_MONTHS:
        return stamp
    return " ".join((str(ROUTE_MONTHS.index(parts[1]) + 1),) + tuple(parts[2:]))


def route_instant_to_utc_iso(stamped: Any) -> str:
    """A profile's ``joined`` stamp as the artifact's instant, or nothing.

    ``Thu Apr 23 21:53:30 +0000 2009`` is the shape the platform writes. A
    stamp stating an offset states an instant, so it is converted rather than
    relabelled; a spelling this format does not read is a missing time rather
    than an approximated one.
    """

    if not isinstance(stamped, str) or not stamped.strip():
        return ""
    try:
        moment = datetime.strptime(_month_numbered(stamped.strip()), ROUTE_INSTANT_FORMAT)
    except ValueError:
        return ""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).strftime(RECORD_INSTANT_FORMAT)


def _nested(payload: Any, *keys: str) -> Any:
    """One value under a key path, or None the moment the path leaves a mapping."""

    held: Any = payload
    for key in keys:
        if not isinstance(held, Mapping):
            return None
        held = held.get(key)
    return held


def _missing(row: Mapping[str, Any], keys: Sequence[str]) -> Tuple[str, ...]:
    """Which of this row's declared fields the payload did not report."""

    return tuple(key for key in keys if not row.get(key))


def _engagement(row: Mapping[str, Any], names: Sequence[str]) -> Tuple[Tuple[str, int], ...]:
    counted: List[Tuple[str, int]] = []
    for name in names:
        exact = exact_count(row.get(name))
        if exact is not None:
            counted.append((name, exact))
    return tuple(counted)


def _attributes(row: Mapping[str, Any], names: Sequence[str]) -> List[Tuple[str, str]]:
    """The facts a row carries under the names declared for it, as exact text."""

    named: List[Tuple[str, str]] = []
    for name in names:
        text = scalar_text(row.get(name))
        if text:
            named.append((name, text))
    return named


def _record_loss(row: Mapping[str, Any], keys: Sequence[str]) -> Tuple[str, ...]:
    """This record's standing loss, plus what the payload left out.

    The standing half is on every record without exception: it is the fact
    that an independent operator answered, and it does not depend on what the
    row carried.
    """

    return STANDING_LOSS + ((FIELD_OMITTED,) if _missing(row, keys) else ())


def _status_record(position: int, status: Mapping[str, Any]) -> NativeRecord:
    """One status as this operator described it."""

    screen_name = _text(_nested(status, AUTHOR_KEY, SCREEN_NAME_KEY))
    row = {
        ID_KEY: id_text(status.get(ID_KEY)),
        TEXT_KEY: _text(status.get(TEXT_KEY)),
        SCREEN_NAME_KEY: screen_name,
        CREATED_TIMESTAMP_KEY: epoch_to_utc_iso(status.get(CREATED_TIMESTAMP_KEY)),
    }
    named = _attributes(status, STATUS_ATTRIBUTES)
    for name, value in (
        (AUTHOR_ID_ATTRIBUTE, id_text(_nested(status, AUTHOR_KEY, ID_KEY))),
        (REPLYING_TO_URL_ATTRIBUTE, _text(_nested(status, REPLYING_TO_KEY, URL_KEY))),
    ):
        if value:
            named.append((name, value))
    return NativeRecord(
        canonical_content_kind=POST_KIND,
        # The address this operator published for it, which is the platform's
        # own and is carried as published: nothing is composed here.
        canonical_locator=_text(status.get(URL_KEY)),
        native_item_id=row[ID_KEY],
        # The status this one answers, when it answers one. A reply never
        # carries its parent's counts: the parent is named and nothing else of
        # it travels onto this record.
        native_parent_id=id_text(_nested(status, REPLYING_TO_KEY, STATUS_KEY)),
        body=row[TEXT_KEY],
        author=screen_name,
        published_at=row[CREATED_TIMESTAMP_KEY],
        engagement=_engagement(status, STATUS_METRICS),
        attributes=tuple(named),
        native_position=position,
        loss=_record_loss(row, STATUS_ROW_KEYS),
    )


def _profile_record(position: int, user: Mapping[str, Any]) -> NativeRecord:
    """One account as this operator described it."""

    row = {
        ID_KEY: id_text(user.get(ID_KEY)),
        SCREEN_NAME_KEY: _text(user.get(SCREEN_NAME_KEY)),
        NAME_KEY: _text(user.get(NAME_KEY)),
        JOINED_KEY: route_instant_to_utc_iso(user.get(JOINED_KEY)),
    }
    named = _attributes(user, PROFILE_ATTRIBUTES)
    for name, value in (
        (WEBSITE_URL_ATTRIBUTE, scalar_text(_nested(user, WEBSITE_KEY, URL_KEY))),
        (
            VERIFICATION_VERIFIED_ATTRIBUTE,
            scalar_text(_nested(user, VERIFICATION_KEY, VERIFIED_KEY)),
        ),
        (VERIFICATION_TYPE_ATTRIBUTE, scalar_text(_nested(user, VERIFICATION_KEY, TYPE_KEY))),
    ):
        if value:
            named.append((name, value))
    return NativeRecord(
        canonical_content_kind=PROFILE_KIND,
        canonical_locator=_text(user.get(URL_KEY)),
        native_item_id=row[ID_KEY],
        title=row[NAME_KEY],
        body=_text(user.get(DESCRIPTION_KEY)),
        author=row[SCREEN_NAME_KEY],
        # When the account joined, which is the only moment a profile states.
        published_at=row[JOINED_KEY],
        engagement=_engagement(user, PROFILE_METRICS),
        attributes=tuple(named),
        native_position=position,
        loss=_record_loss(row, PROFILE_ROW_KEYS),
    )


def _status_records(rows: Sequence[Any]) -> Tuple[List[NativeRecord], int]:
    records: List[NativeRecord] = []
    unidentified = 0
    for status in rows:
        if not isinstance(status, Mapping) or not id_text(status.get(ID_KEY)):
            unidentified += 1
            continue
        records.append(_status_record(len(records), status))
    return (records, unidentified)


def _profile_records(rows: Sequence[Any]) -> Tuple[List[NativeRecord], int]:
    records: List[NativeRecord] = []
    unidentified = 0
    for user in rows:
        if not isinstance(user, Mapping) or not id_text(user.get(ID_KEY)):
            unidentified += 1
            continue
        records.append(_profile_record(len(records), user))
    return (records, unidentified)
