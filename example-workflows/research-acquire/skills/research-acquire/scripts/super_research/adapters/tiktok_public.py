"""K2 TikTok public pages: the web client's own rehydration JSON, no script run.

Measured from this host, with no cookie, no script run, and this
package's own honest `User-Agent` (never a browser's) — the identity every
other route in the roster is read under too. A video page
(``/@<handle>/video/<id>``) answered 200 in ~406 KB carrying a
``<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">``
whose ``__DEFAULT_SCOPE__["webapp.video-detail"].itemInfo.itemStruct`` holds
``id``, ``createTime`` (a decimal-string count of epoch seconds), ``desc``,
``statsV2`` (every count as a decimal string), ``stats`` (mostly ``int``, one
key not), an ``author`` and a ``textExtra`` hashtag list. A profile page
(``/@<handle>``) answered 200 the same way, at
``__DEFAULT_SCOPE__["webapp.user-detail"].userInfo``, with ``user``, ``stats``
and an **empty** ``itemList`` — the recent-video list is fetched by a signed
client-side call this package does not perform, so a profile page carries the
account alone. Both addresses were also proved to accept a `%40`-encoded `@`
segment, which is what ``transport.path_segments`` sends: nothing
about the pre-wired route shape needed correcting.

**The one branch this module cannot measure.** Neither read encountered a
login or verification wall, so the ``auth_required`` branch below rests on
TikTok's publicly documented anti-bot container ids rather than on a captured
example — chosen because none of them appears anywhere in an ordinary
answered page, including its own ``webapp.i18n-translation`` dictionary,
which repeats the literal text "Log in" dozens of times on every healthy
page and is therefore useless as a signal by itself.

Counts travel under TikTok's own key names — ``diggCount`` stays
``diggCount`` — for the same reason ``instagram_public`` keeps
``edge_liked_by.count`` rather than a cross-platform ``like_count``: an
adapter that renamed them would be inventing a vocabulary.
"""

from __future__ import annotations

import json
from html.parser import HTMLParser
from typing import Any, Mapping, Optional, Sequence, Tuple, List

from .. import transport, schema
from . import (
    AdapterDescriptor,
    AdapterRequest,
    NativePage,
    NativeRecord,
    build_native_page,
    fetch_one_page,
)
from datetime import datetime, timezone


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

# In the descriptor's own order: `diggCount`, `commentCount`, `playCount`,
# then `shareCount`, `collectCount`, `repostCount` complete the set the
# measurement recorded `statsV2` publishing.
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

# The roster row's own fields, plus the two identity fields every roster row
# is held to. A record missing one says so, because a
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

RECORD_INSTANT_FORMAT = schema.INSTANT_FORMAT


def _text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def id_text(value: Any) -> str:
    """One TikTok id in the form a record holds it.

    Measured: `itemStruct.id` and `author.id` are both already
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

    Measured: `createTime` is a decimal-string count of seconds
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

    Measured: `textExtra` also carries a mention (`@handle`) as an
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


def video_record(position: int, item: Mapping[str, Any], origin: str) -> NativeRecord:
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
        loss=(FIELD_OMITTED,) if _missing(row, VIDEO_ROSTER_KEYS) else (),
    )


def profile_record(user: Mapping[str, Any], stats: Mapping[str, Any], origin: str) -> NativeRecord:
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
        loss=(FIELD_OMITTED,) if _missing(row, PROFILE_ROSTER_KEYS) else (),
    )


DESCRIPTOR = AdapterDescriptor(
    adapter_id="tiktok_public",
    adapter_version="1",
    access_class="K2",
    route_id=transport.TIKTOK_VIDEO_PAGE_ROUTE,
    platform="tiktok",
    native_identity_namespace="tiktok",
    representation_kind="native",
    operator_identity="tiktok",
    # Nothing on either route was measured refusing at any rate, so these stay
    # a conservative guess rather than a ceiling this module has proved.
    min_interval_ms=2000,
    burst=1,
    # TikTok reports a count of comments on a video and nothing named for
    # replies. Declaring the one under both names would make `most_commented`
    # and `most_replied` silently identical on a number reported once.
    comment_count_metric="commentCount",
)

PROFILE_DESCRIPTOR = AdapterDescriptor(
    adapter_id="tiktok_public",
    adapter_version="1",
    access_class="K2",
    route_id=transport.TIKTOK_PROFILE_PAGE_ROUTE,
    platform="tiktok",
    native_identity_namespace="tiktok",
    representation_kind="native",
    operator_identity="tiktok",
    min_interval_ms=2000,
    burst=1,
)

SURFACE_DESCRIPTORS = (DESCRIPTOR, PROFILE_DESCRIPTOR)

VIDEO_OPERATION = "video"
PROFILE_OPERATION = "profile"
TIKTOK_OPERATIONS = (VIDEO_OPERATION, PROFILE_OPERATION)

VIDEO_NATIVE_ORDER = "tiktok_video_order"
PROFILE_NATIVE_ORDER = "tiktok_profile_order"

VIDEO_RESOURCE = "video"

# Where this page keeps its answer. Declared, never searched for: a parser
# that went hunting for a familiar-looking object would eventually report a
# video or a profile assembled from whatever else the payload happened to
# carry.
SCRIPT_ID = "__UNIVERSAL_DATA_FOR_REHYDRATION__"
DEFAULT_SCOPE_KEY = "__DEFAULT_SCOPE__"
VIDEO_SCOPE_KEY = "webapp.video-detail"
PROFILE_SCOPE_KEY = "webapp.user-detail"
ITEM_INFO_KEY = "itemInfo"
ITEM_STRUCT_KEY = "itemStruct"
USER_INFO_KEY = "userInfo"
ITEM_LIST_KEY = "itemList"

VIDEO_ITEM_PATH = (DEFAULT_SCOPE_KEY, VIDEO_SCOPE_KEY, ITEM_INFO_KEY, ITEM_STRUCT_KEY)
PROFILE_USER_INFO_PATH = (DEFAULT_SCOPE_KEY, PROFILE_SCOPE_KEY, USER_INFO_KEY)

HTTP_STATUS = "http_status"
AUTH_REQUIRED = "auth_required"
SCHEMA_DRIFT = "schema_drift"
MALFORMED_JSON = "malformed_json"
FIELD_OMITTED = "field_omitted"
UNSELECTED_TARGET = "unselected_target"

# TikTok's own documented anti-bot interstitial container ids/classes — never
# observed live by this module (see the module docstring). Structural markup
# rather than page text, on purpose: the i18n dictionary embedded in every
# ordinary page already repeats "Log in" as translated text, which a
# substring match on that phrase would false-positive on constantly.
CHALLENGE_MARKERS = (
    'id="captcha_container"',
    'id="captcha-verify-container"',
    'class="captcha-verify-container"',
    'id="verify-bar-content"',
    'id="login-modal"',
    "secsdk-captcha",
)


class _RehydrationParser(HTMLParser):
    """Collect the one embedded script this surface keeps its payload in."""

    def __init__(self) -> None:
        HTMLParser.__init__(self, convert_charrefs=True)
        self.payload = ""
        self._capturing = False

    def handle_starttag(self, tag, attrs):
        if tag == "script" and dict(attrs).get("id") == SCRIPT_ID:
            self._capturing = True

    def handle_endtag(self, tag):
        if tag == "script":
            self._capturing = False

    def handle_data(self, data):
        if self._capturing:
            self.payload += data


def embedded_payload(body: str) -> str:
    """The page's rehydration script, or an empty string when it has none."""

    parser = _RehydrationParser()
    parser.feed(body)
    parser.close()
    return parser.payload


def _dig(payload: Any, path: Sequence[str]) -> Any:
    """Follow one declared path of mapping keys, or return None at the first gap."""

    found = payload
    for key in path:
        if not isinstance(found, Mapping):
            return None
        found = found.get(key)
    return found


def _looks_like_a_challenge(body: str) -> bool:
    return any(marker in body for marker in CHALLENGE_MARKERS)


def operation_for(request: AdapterRequest) -> Tuple[str, str]:
    """The operation this call performs, and the argument it performs it on.

    A caller names the operation; absent a name, an unprefixed target reads a
    profile — the one surface this adapter's two ever agree could be meant by
    a bare handle. Neither operation is inferred from the argument's own
    shape: a query naming a slash stays whatever operation named it.
    """

    named = request.target_ids[0] if request.target_ids else request.query
    kind, separator, argument = named.partition(":")
    if separator and kind in TIKTOK_OPERATIONS:
        return (kind, argument)
    return (PROFILE_OPERATION, named)


def _bare_handle(value: str) -> str:
    """TikTok's display form is a leading `@`; the route wants it back on."""

    return value[1:] if value.startswith("@") else value


def video_target(argument: str) -> Tuple[str, str, str]:
    """`video:`'s argument split into its required pair, or why it is refused.

    Returns ``(handle, video_id, refusal)``. There is no reading of
    ``video:<id-only>``: an id with no handle names an address this route
    cannot build, so both halves are required together or neither is
    admitted — the same rule ``AdapterDescriptor.volatile_identifiers``
    already holds a declaration to.
    """

    handle, separator, video_id = argument.partition("/")
    if not separator or not handle or not video_id:
        return (
            "",
            "",
            "video: takes the pair handle/id and refuses {0!r}: neither a bare"
            " handle nor a bare id names an address this route can"
            " build".format(argument),
        )
    return (handle, video_id, "")


def _refused(descriptor: AdapterDescriptor, native_order: str, reason: str) -> NativePage:
    """A target this adapter will not read, refused without touching the network."""

    return build_native_page(
        descriptor,
        (),
        native_order=native_order,
        warnings=(reason,),
        outcome="refused",
        loss=(UNSELECTED_TARGET,),
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


def _no_script(
    descriptor: AdapterDescriptor, response: transport.TransportResponse, native_order: str
) -> NativePage:
    """A 200 that carried no rehydration script: a wall, or a shape change.

    The one lawful way this adapter says `auth_required` off a body rather
    than a status: a marker TikTok's own challenge interstitial is documented
    to render. Everything else a 200-with-no-script could be is a payload
    that changed shape, not a credential this package is missing.
    """

    if _looks_like_a_challenge(response.body):
        return _failed(
            descriptor,
            response,
            native_order,
            AUTH_REQUIRED,
            "route {0} answered 200 with no {1} script and a challenge/login"
            " marker in the body: the origin refused this read".format(
                descriptor.route_id, SCRIPT_ID
            ),
        )
    return _failed(
        descriptor,
        response,
        native_order,
        SCHEMA_DRIFT,
        "route {0} answered 200 with no {1} script: the page this adapter"
        " reads has changed shape".format(descriptor.route_id, SCRIPT_ID),
    )


def _payload_of(
    descriptor: AdapterDescriptor, response: transport.TransportResponse, native_order: str
) -> Tuple[Optional[Any], Optional[NativePage]]:
    """The response's rehydration JSON, or the typed failure page it is instead."""

    if response.status != 200:
        return None, _failed(
            descriptor,
            response,
            native_order,
            HTTP_STATUS,
            "http status {0} from {1}".format(response.status, descriptor.route_id),
        )
    embedded = embedded_payload(response.body)
    if not embedded.strip():
        return None, _no_script(descriptor, response, native_order)
    try:
        payload = json.loads(embedded)
    except ValueError:
        return None, _failed(
            descriptor,
            response,
            native_order,
            MALFORMED_JSON,
            "{0} script on {1} did not parse as json".format(SCRIPT_ID, descriptor.route_id),
        )
    return payload, None


def _video_page_from(response: transport.TransportResponse) -> NativePage:
    """Turn one video-page response into exactly one NativePage."""

    payload, failure = _payload_of(DESCRIPTOR, response, VIDEO_NATIVE_ORDER)
    if failure is not None:
        return failure

    item = _dig(payload, VIDEO_ITEM_PATH)
    if not isinstance(item, Mapping) or not item.get(ID_KEY):
        return _failed(
            DESCRIPTOR,
            response,
            VIDEO_NATIVE_ORDER,
            SCHEMA_DRIFT,
            "route {0} answered 200 with no {1} at {2}: the payload has changed"
            " shape".format(DESCRIPTOR.route_id, ITEM_STRUCT_KEY, ".".join(VIDEO_ITEM_PATH)),
        )

    origin = transport.route_constant(DESCRIPTOR.route_id).origin
    record = video_record(0, item, origin)
    return build_native_page(
        DESCRIPTOR,
        (record,),
        observed_at=response.observed_at,
        native_order=VIDEO_NATIVE_ORDER,
        outcome="ok",
    )


def _profile_page_from(response: transport.TransportResponse) -> NativePage:
    """Turn one profile-page response into exactly one NativePage."""

    payload, failure = _payload_of(PROFILE_DESCRIPTOR, response, PROFILE_NATIVE_ORDER)
    if failure is not None:
        return failure

    user_info = _dig(payload, PROFILE_USER_INFO_PATH)
    user = user_info.get(USER_KEY) if isinstance(user_info, Mapping) else None
    if not isinstance(user, Mapping) or not user.get(UNIQUE_ID_KEY):
        return _failed(
            PROFILE_DESCRIPTOR,
            response,
            PROFILE_NATIVE_ORDER,
            SCHEMA_DRIFT,
            "route {0} answered 200 with no {1} at {2}: the payload has changed"
            " shape".format(
                PROFILE_DESCRIPTOR.route_id,
                USER_KEY,
                ".".join(PROFILE_USER_INFO_PATH),
            ),
        )

    stats = user_info.get(STATS_KEY)
    stats = stats if isinstance(stats, Mapping) else {}
    origin = transport.route_constant(PROFILE_DESCRIPTOR.route_id).origin
    profile = profile_record(user, stats, origin)

    item_list = user_info.get(ITEM_LIST_KEY)
    videos = tuple(
        entry for entry in (item_list if isinstance(item_list, list) else ()) if isinstance(entry, Mapping)
    )
    if videos:
        # The one case this surface was measured *not* to answer with
        # (`itemList` came back empty on every read): the list is
        # present and holds rows after all, so it is read as the video
        # records it names, and the standing warning about its absence does
        # not apply to this page.
        extra: Tuple[NativeRecord, ...] = tuple(
            video_record(position + 1, entry, origin)
            for position, entry in enumerate(videos)
        )
        return build_native_page(
            PROFILE_DESCRIPTOR,
            (profile,) + extra,
            observed_at=response.observed_at,
            native_order=PROFILE_NATIVE_ORDER,
            outcome="ok",
        )
    return build_native_page(
        PROFILE_DESCRIPTOR,
        (profile,),
        observed_at=response.observed_at,
        native_order=PROFILE_NATIVE_ORDER,
        outcome="ok",
        warnings=(
            "route {0} answered 200 with an empty {1}: TikTok's recent-video"
            " list on this surface is fetched by a signed client-side call"
            " this package does not perform, so this profile carries the"
            " account alone".format(PROFILE_DESCRIPTOR.route_id, ITEM_LIST_KEY),
        ),
    )


def fetch_native_page(carrier: transport.Transport, request: AdapterRequest) -> NativePage:
    """Read one of the two declared operations and return exactly one NativePage.

    One call on one route. `video:` refuses before any call is made when its
    argument does not name the required pair; `profile:` refuses the same way
    when it names no handle at all.
    """

    operation, argument = operation_for(request)
    if operation == VIDEO_OPERATION:
        handle, video_id, refusal = video_target(argument)
        if refusal:
            return _refused(DESCRIPTOR, VIDEO_NATIVE_ORDER, refusal)
        handle = _bare_handle(handle)
        params = {"handle": "@" + handle, "resource": VIDEO_RESOURCE, "video_id": video_id}
        return fetch_one_page(
            DESCRIPTOR,
            carrier,
            params=params,
            parse=_video_page_from,
            native_order=VIDEO_NATIVE_ORDER,
        )

    handle = _bare_handle(argument)
    if not handle:
        return _refused(
            PROFILE_DESCRIPTOR,
            PROFILE_NATIVE_ORDER,
            "profile: names no handle, and {0!r} names none either".format(argument),
        )
    return fetch_one_page(
        PROFILE_DESCRIPTOR,
        carrier,
        params={"handle": "@" + handle},
        parse=_profile_page_from,
        native_order=PROFILE_NATIVE_ORDER,
    )
