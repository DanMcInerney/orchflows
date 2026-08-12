"""K1 Instagram public profiles under a vendor-published web app id.

Measured 2026-08-10 (findings.md §1, "Instagram"): one request to
``api/v1/users/web_profile_info/?username=`` carrying ``x-ig-app-id`` answered
200 in 2.9 s with 455 KB — ``username``, ``biography``, a follower count, a
post count, and **12 recent posts** each with ``shortcode``,
``taken_at_timestamp``, a like count and a comment count. The prior synthesis
listed this platform as a flat gap; measured, it is a profile, its recent
posts, and the platform's own engagement, at zero cost and with no account.

The app id is not a user secret and this module never sees it:
``transport.py`` owns it as a route constant and attaches it at send time, so
nothing recorded here can carry it.

Two things this module must not do. It must not read a wall off a body — this
route's origin also serves a logged-out page that says "Log in" in plain words,
and only the origin's own status line may make this route ``auth_required``,
which is the finding the LinkedIn measurement established and the same finding
here. And it must not report a payload that moved as an account with nothing in
it: a `K1` payload is a shape the vendor may reshape without notice, so a
missing container is ``schema_drift`` while a container holding ``null`` is the
origin stating that nobody holds the name.

Counts travel under the exact key paths Instagram publishes them at. Spelling
them ``like_count`` and ``comment_count`` would be this package inventing a
cross-platform vocabulary, which is the aliasing the descriptor's own metric
law forbids and a non-goal of the spec besides.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Mapping, Optional, Sequence, Tuple

from .. import transport
from . import (
    AdapterDescriptor,
    AdapterRequest,
    NativePage,
    NativeRecord,
    build_native_page,
    fetch_one_page,
)

# Every count this payload publishes, under the container it publishes it in
# and the exact name a record carries it by. Both halves are spelled in full
# rather than assembled, so an exact search for either finds every use.
FOLLOWERS_KEY = "edge_followed_by"
FOLLOWERS_METRIC = "edge_followed_by.count"
MEDIA_KEY = "edge_owner_to_timeline_media"
POST_COUNT_METRIC = "edge_owner_to_timeline_media.count"
LIKE_KEY = "edge_liked_by"
LIKE_METRIC = "edge_liked_by.count"
COMMENT_KEY = "edge_media_to_comment"
COMMENT_METRIC = "edge_media_to_comment.count"

DESCRIPTOR = AdapterDescriptor(
    adapter_id="instagram_public",
    adapter_version="1",
    access_class="K1",
    route_id=transport.INSTAGRAM_WEB_PROFILE_ROUTE,
    platform="instagram",
    native_identity_namespace="instagram",
    representation_kind="native",
    operator_identity="instagram",
    # findings.md §1: 2.9 s per request, the slowest read in the roster.
    # Nothing here was measured refusing, so `burst` and `cooldown_ms` keep the
    # protocol's conservative defaults rather than a ceiling nobody observed.
    min_interval_ms=2900,
    # Instagram reports a count of comments on a post and nothing named for
    # replies. Declaring the one under both names would make `most_commented`
    # and `most_replied` silently identical on a number reported once.
    comment_count_metric=COMMENT_METRIC,
)

NATIVE_ORDER = "instagram_web_profile_order"
PROFILE_KIND = "profile"
POST_KIND = "post"

# Where this payload keeps its answer. Declared, never searched for: a parser
# that went hunting for a familiar-looking object would eventually report a
# profile assembled from whatever else the payload happened to carry.
PROFILE_PATH = ("data", "user")

# Every other key this module reads, under the payload's own names.
USERNAME_KEY = "username"
FULL_NAME_KEY = "full_name"
BIOGRAPHY_KEY = "biography"
IDENTITY_KEY = "id"
EDGES_KEY = "edges"
NODE_KEY = "node"
COUNT_KEY = "count"
SHORTCODE_KEY = "shortcode"
TAKEN_AT_KEY = "taken_at_timestamp"
CAPTION_KEY = "edge_media_to_caption"
CAPTION_TEXT_KEY = "text"

# The addresses Instagram gives a profile and a post. The payload publishes
# neither — a post is addressed by the shortcode it carries — so the path is
# named here and resolved by `transport.origin_locator`, which is where a host
# is spelled.
PROFILE_LOCATOR_PATH = "/{0}/"
POST_LOCATOR_PATH = "/p/{0}/"

# What the roster row names, per kind. A record missing one says so, because a
# caller needs to know which rows were incomplete rather than which were zero.
PROFILE_ROSTER_KEYS = (USERNAME_KEY, BIOGRAPHY_KEY, FOLLOWERS_METRIC, POST_COUNT_METRIC)
POST_ROSTER_KEYS = (SHORTCODE_KEY, TAKEN_AT_KEY, LIKE_METRIC, COMMENT_METRIC)

RECORD_INSTANT_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

# The statuses that separate the origin refusing from the payload changing.
AUTHORIZATION_STATUSES = (401, 403)
AUTH_REQUIRED = "auth_required"


def profile_in(payload: Any) -> Tuple[bool, Any]:
    """This payload's place for a profile, and what is in it.

    Three facts a caller needs apart, and the reason this returns a pair. A
    payload with no place for a profile has changed shape. A place holding
    ``null`` is the origin stating that nobody holds the name. A place holding
    an object is an answer.
    """

    held = payload
    for key in PROFILE_PATH[:-1]:
        if not isinstance(held, Mapping):
            return (False, None)
        held = held.get(key)
    if not isinstance(held, Mapping) or PROFILE_PATH[-1] not in held:
        return (False, None)
    return (True, held[PROFILE_PATH[-1]])


def counted(source: Mapping[str, Any], key: str) -> Optional[int]:
    """One count the payload publishes at ``<key>.count``, or nothing.

    Only an exact native integer is admitted, which is the same bar an
    engagement snapshot is held to everywhere else: a count this package
    derived would be a number Instagram never reported.
    """

    held = source.get(key)
    if not isinstance(held, Mapping):
        return None
    value = held.get(COUNT_KEY)
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _snapshots(
    source: Mapping[str, Any], counts: Sequence[Tuple[str, str]]
) -> Tuple[Tuple[str, int], ...]:
    found = []
    for key, metric_name in counts:
        value = counted(source, key)
        if value is not None:
            found.append((metric_name, value))
    return tuple(found)


def route_instant_to_utc_iso(taken_at: Any) -> str:
    """This payload's epoch second as the artifact's instant, or nothing.

    Only an exact integer is read. Anything else is a missing time rather than
    an approximated one, and every ordering downstream is entitled to the
    difference.
    """

    if isinstance(taken_at, bool) or not isinstance(taken_at, int):
        return ""
    try:
        moment = datetime.fromtimestamp(taken_at, tz=timezone.utc)
    except (OSError, OverflowError, ValueError):
        return ""
    return moment.strftime(RECORD_INSTANT_FORMAT)


def caption_of(node: Mapping[str, Any]) -> str:
    """One post's own caption, as the payload nests it, or nothing."""

    held = node.get(CAPTION_KEY)
    if not isinstance(held, Mapping):
        return ""
    edges = held.get(EDGES_KEY)
    if not isinstance(edges, list) or not edges:
        return ""
    first = edges[0]
    inner = first.get(NODE_KEY) if isinstance(first, Mapping) else None
    if not isinstance(inner, Mapping):
        return ""
    text = inner.get(CAPTION_TEXT_KEY)
    return text if isinstance(text, str) else ""


def _text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _missing(row: Mapping[str, Any], keys: Sequence[str]) -> Tuple[str, ...]:
    """Which of this row's roster fields the payload did not report.

    Absence, never falsehood: a post nobody has commented on reports zero, and
    zero is a count. Marking it omitted would erase the one distinction
    `field_omitted` exists to make.
    """

    return tuple(key for key in keys if row.get(key) is None or row.get(key) == "")


def _profile_record(user: Mapping[str, Any]) -> NativeRecord:
    """The account as the payload reported it.

    ``published_at`` is left unset because a profile states no publication
    time. An unset one becomes `unknown` time confidence and sorts last under
    the time orders, which is what a caller should see; the moment the payload
    was read is already on the record as ``observed_at``.
    """

    username = _text(user.get(USERNAME_KEY))
    snapshots = _snapshots(
        user, ((FOLLOWERS_KEY, FOLLOWERS_METRIC), (MEDIA_KEY, POST_COUNT_METRIC))
    )
    row = dict(snapshots)
    row[USERNAME_KEY] = username
    row[BIOGRAPHY_KEY] = _text(user.get(BIOGRAPHY_KEY))
    return NativeRecord(
        canonical_content_kind=PROFILE_KIND,
        canonical_locator=(
            transport.origin_locator(
                DESCRIPTOR.route_id, PROFILE_LOCATOR_PATH.format(username)
            )
            if username
            else ""
        ),
        # Instagram's own numeric id, which is what a post names as its owner
        # and what survives a rename; the username is the public handle.
        native_item_id=_text(user.get(IDENTITY_KEY)),
        title=_text(user.get(FULL_NAME_KEY)),
        body=row[BIOGRAPHY_KEY],
        author=username,
        engagement=snapshots,
        native_position=0,
        loss=("field_omitted",) if _missing(row, PROFILE_ROSTER_KEYS) else (),
    )


def _post_record(
    position: int, node: Mapping[str, Any], username: str, owner_id: str
) -> NativeRecord:
    """One recent post as the payload reported it."""

    shortcode = _text(node.get(SHORTCODE_KEY))
    snapshots = _snapshots(node, ((LIKE_KEY, LIKE_METRIC), (COMMENT_KEY, COMMENT_METRIC)))
    row = dict(snapshots)
    row[SHORTCODE_KEY] = shortcode
    row[TAKEN_AT_KEY] = route_instant_to_utc_iso(node.get(TAKEN_AT_KEY))
    return NativeRecord(
        canonical_content_kind=POST_KIND,
        canonical_locator=(
            transport.origin_locator(DESCRIPTOR.route_id, POST_LOCATOR_PATH.format(shortcode))
            if shortcode
            else ""
        ),
        # The shortcode is what Instagram addresses a post by, so it is this
        # record's own id; the numeric media id addresses nothing a caller can
        # reach and the roster row does not name it.
        native_item_id=shortcode,
        native_parent_id=owner_id,
        body=caption_of(node),
        author=username,
        published_at=row[TAKEN_AT_KEY],
        engagement=snapshots,
        native_position=position,
        loss=("field_omitted",) if _missing(row, POST_ROSTER_KEYS) else (),
    )


def recent_posts(user: Mapping[str, Any]) -> Tuple[Mapping[str, Any], ...]:
    """Every recent post the payload listed, in the order it listed them."""

    held = user.get(MEDIA_KEY)
    if not isinstance(held, Mapping):
        return ()
    edges = held.get(EDGES_KEY)
    if not isinstance(edges, list):
        return ()
    found = []
    for edge in edges:
        node = edge.get(NODE_KEY) if isinstance(edge, Mapping) else None
        if isinstance(node, Mapping):
            found.append(node)
    return tuple(found)


def _answered(
    response: transport.TransportResponse,
    records: Tuple[NativeRecord, ...],
    outcome: str,
    warnings: Tuple[str, ...] = (),
    loss: Tuple[str, ...] = (),
) -> NativePage:
    return build_native_page(
        DESCRIPTOR,
        records,
        observed_at=response.observed_at,
        native_order=NATIVE_ORDER,
        warnings=warnings,
        outcome=outcome,
        loss=loss,
    )


def _failed(response: transport.TransportResponse, loss: str, warning: str) -> NativePage:
    return _answered(response, (), "failed", warnings=(warning,), loss=(loss,))


def _page_from(response: transport.TransportResponse, username: str) -> NativePage:
    """Turn one response the origin itself sent into exactly one page."""

    if response.status in AUTHORIZATION_STATUSES:
        # The one lawful way this adapter says `auth_required`: the origin said
        # so. It is never read off a string in the body, which is the whole
        # difference between this branch and a login page served at 200.
        return _failed(
            response,
            AUTH_REQUIRED,
            "route {0} answered {1}: the origin refused this read".format(
                DESCRIPTOR.route_id, response.status
            ),
        )
    if response.status != 200:
        return _failed(
            response,
            "http_status",
            "http status {0} from {1}".format(response.status, DESCRIPTOR.route_id),
        )

    try:
        payload = json.loads(response.body)
    except ValueError:
        return _failed(
            response,
            "malformed_json",
            "route {0} answered 200 with a {1} body that is not json: this route"
            " stopped answering in json, which is not a credential the origin"
            " withheld".format(DESCRIPTOR.route_id, response.content_type),
        )

    has_place, user = profile_in(payload)
    if not has_place:
        return _failed(
            response,
            "schema_drift",
            "route {0} answered 200 with no {1} in its payload: the shape this"
            " adapter reads has changed".format(
                DESCRIPTOR.route_id, ".".join(PROFILE_PATH)
            ),
        )
    if user is None:
        # The one empty this route can legitimately answer with: the place is
        # there and holds nothing, which is the origin saying nobody holds the
        # name. It is still said out loud, because an empty nobody explained is
        # indistinguishable at a glance from the branches above.
        return _answered(
            response,
            (),
            "empty",
            warnings=(
                "route {0} answered 200 and nobody holds the name {1}".format(
                    DESCRIPTOR.route_id, username
                ),
            ),
        )
    if not isinstance(user, Mapping):
        return _failed(
            response,
            "schema_drift",
            "route {0} answered 200 with a {1} that is not a profile object:"
            " the shape this adapter reads has changed".format(
                DESCRIPTOR.route_id, ".".join(PROFILE_PATH)
            ),
        )

    profile = _profile_record(user)
    records = (profile,) + tuple(
        _post_record(position, node, profile.author, profile.native_item_id)
        for position, node in enumerate(recent_posts(user))
    )
    return _answered(response, records, "ok")


def username_of(request: AdapterRequest) -> str:
    """The account this route reads, in the one form its query takes.

    A hydration step names it in ``target_ids``; a discovery step names it in
    ``query``. A leading ``@`` is Instagram's display form rather than part of
    the handle.
    """

    named = request.target_ids[0] if request.target_ids else request.query
    return named[1:] if named.startswith("@") else named


def fetch_native_page(carrier: transport.Transport, request: AdapterRequest) -> NativePage:
    """Read one public profile and return exactly one NativePage."""

    username = username_of(request)

    def parse(response: transport.TransportResponse) -> NativePage:
        return _page_from(response, username)

    return fetch_one_page(
        DESCRIPTOR,
        carrier,
        params={"username": username},
        parse=parse,
        native_order=NATIVE_ORDER,
    )
