"""K1 X reads authorized by an anonymous guest token.

Measured 2026-08-10 (findings.md §1, "X"): the activation route issues a
guest token freely, and with it ``TweetResultByRestId`` and
``UserByScreenName`` answered 200 in 0.5 s and ``UserTweets`` in 2.3 s,
cursor-paginated. No account, no console project, no cost.

``SearchTimeline`` and ``TweetDetail`` answered 404 in the same probe run,
and the evidence is explicit that this was a **stale query id and not an
authorization failure**: a guest-blocked operation answers 403 or 401, and
the three operations whose ids were current answered 200. X puts the query
id in the request path, so a rotated id names an endpoint that does not
exist. That is the whole reason this module exists in the shape it does — a
404 here is `stale_identifier`, with the recovery procedure attached, and it
is never an empty result and never `auth_required`.

The token itself is minted and held by ``transport``: activation is a route
and a credential, and this adapter performs exactly one read like every
other one.
"""

from __future__ import annotations

import json
from typing import Any, Mapping, Optional, Sequence, Tuple

from .. import transport
from . import (
    AdapterDescriptor,
    AdapterRequest,
    NativePage,
    NativeRecord,
    VolatileIdentifier,
    build_native_page,
    fetch_one_page,
)

# The three operations a guest token authorizes, spelled once each. X names
# them, so these strings are the platform's and go on the wire verbatim.
TWEET_OPERATION = "TweetResultByRestId"
USER_OPERATION = "UserByScreenName"
TIMELINE_OPERATION = "UserTweets"

# The rotating half of every url this adapter builds. findings.md §1 records
# these three operations answering 200 with a current id at probe time; it does
# not record the literal ids, so the values below are the ones this package
# last held and are unproven until criterion 12's live smoke. That is the
# steady state a volatile identifier is declared for rather than a defect: a
# wrong one answers 404, which this module types `stale_identifier` and hands
# back with the procedure below, never as an empty result.
GUEST_QUERY_IDS = {
    TWEET_OPERATION: "0hWvDhmW8YQ-S_ib3azIrw",
    USER_OPERATION: "G3KGOASz96M-Qu0nwmGXNg",
    TIMELINE_OPERATION: "V7H0Ap3_Hh2FyS75OCDO3Q",
}

# findings.md §1 (X) recorded the shape of the way back, having walked into it:
# X moved its bundles from the responsive-web layout to an x-web layout whose
# logged-out entry bundle hides the chunk graph behind ESM dynamic imports, so
# a naive regex over one file no longer finds anything.
GUEST_QUERY_ID_RECOVERY = (
    "Rotates per X web release. Recover a current id by hand: fetch the"
    " logged-out entry bundle under abs.twimg.com/x-web/x-web/, walk the ESM"
    " import map it declares to the chunk urls it names, and scan those chunks"
    " for adjacent operationName and queryId pairs; take the pair whose"
    " operationName matches this operation and replace the id in"
    " GUEST_QUERY_IDS. The older responsive-web/client-web layout no longer"
    " carries them. This package never fetches that bundle: recovery is a"
    " deliberate manual step, because a self-updating identifier would make"
    " the run's own provenance depend on an unrecorded read."
)

DESCRIPTOR = AdapterDescriptor(
    adapter_id="x_guest",
    adapter_version="1",
    access_class="K1",
    route_id=transport.X_GUEST_GRAPHQL_ROUTE,
    platform="x",
    native_identity_namespace="x",
    representation_kind="native",
    operator_identity="x",
    # findings.md §1: 0.5 s per request for the two single-object operations.
    # `UserTweets` answered in 2.3 s, which is that operation's latency and not
    # a second ceiling: one route, one budget. Nothing here was measured
    # refusing, so burst and cooldown keep the conservative defaults.
    min_interval_ms=500,
    volatile_identifiers=tuple(
        VolatileIdentifier(
            name="{0} query id {1}".format(operation, query_id),
            recovery=GUEST_QUERY_ID_RECOVERY,
        )
        for operation, query_id in sorted(GUEST_QUERY_IDS.items())
    ),
    # X reports one metric for replies and none named for comments. Declaring
    # this number under both names would make `most_commented` and
    # `most_replied` silently identical on a count the platform reported once.
    reply_count_metric="reply_count",
)

# The activation the reads above are authorized by, declared so the scheduler
# can pace it. A budget belongs to whoever sets it, and until this row existed
# the mint was the one request in the package that left under no ceiling at
# all — the governor refuses to pace a route no adapter declares.
#
# Same three numbers as the read: findings.md §1 measured this origin at 0.5 s
# per request and the activation is a request to it. Nothing here was measured
# refusing, so burst and cooldown keep the conservative defaults, exactly as
# the read's do.
#
# It is a surface with a budget and not a surface a caller reads: no record
# ever comes back from an activation, which is why `descriptor_for` still
# names the GraphQL route alone and this one is reachable only through
# `SURFACE_DESCRIPTORS`.
ACTIVATION_DESCRIPTOR = AdapterDescriptor(
    adapter_id="x_guest",
    adapter_version="1",
    access_class="K1",
    route_id=transport.X_GUEST_ACTIVATE_ROUTE,
    platform="x",
    native_identity_namespace="x",
    representation_kind="native",
    operator_identity="x",
    min_interval_ms=500,
)

SURFACE_DESCRIPTORS = (DESCRIPTOR, ACTIVATION_DESCRIPTOR)

NATIVE_ORDER = "x_guest_route_order"
X_ORIGIN = "https://x.com"
POST_KIND = "post"
PROFILE_KIND = "profile"

# Which operation a target id names, the variable that operation takes, and
# where its answer keeps the result. A caller names the operation because one
# route serves three of them: inferring which from the characters in an
# argument would be a guess, and a bare id is the roster's primary operation
# rather than a shape this module recognized.
TWEET_TARGET_KIND = "tweet"
GUEST_OPERATIONS = {
    TWEET_TARGET_KIND: (TWEET_OPERATION, "tweetId"),
    "user": (USER_OPERATION, "screen_name"),
    "user_tweets": (TIMELINE_OPERATION, "userId"),
}
RESULT_PATHS = {
    TWEET_OPERATION: ("data", "tweetResult", "result"),
    USER_OPERATION: ("data", "user", "result"),
    TIMELINE_OPERATION: ("data", "user", "result", "timeline_v2", "timeline", "instructions"),
}

# One timeline instruction's shape, and the two kinds of entry it holds.
ADD_ENTRIES_INSTRUCTION = "TimelineAddEntries"
TWEET_ITEM_PATH = ("content", "itemContent", "tweet_results", "result")
CURSOR_ENTRY_TYPE = "TimelineTimelineCursor"
BOTTOM_CURSOR = "Bottom"

ENGAGEMENT_FIELDS = ("favorite_count", "retweet_count", "reply_count", "quote_count")
FOLLOWERS_FIELD = "followers_count"
# What the route calls a row it is returning. A result that holds no row still
# names its own kind, which is the difference between a suspended account and
# an answer nobody can account for.
TYPENAME_FIELD = "__typename"

# The statuses that separate a rotated identifier from a refusal. findings.md
# §1 measured both: the stale ids answered 404, and the evidence states that a
# guest-blocked operation answers 403 or 401.
STALE_IDENTIFIER_STATUS = 404
AUTHORIZATION_STATUSES = (401, 403)
STALE_IDENTIFIER = "stale_identifier"
AUTH_REQUIRED = "auth_required"

# The stamp this route emits: "Sun Aug 09 07:00:00 +0000 2026". The month is
# read from this table rather than through `strptime`, whose `%a` and `%b` read
# the process locale — a timeline that parsed under one language and silently
# lost every time under another would be the worst kind of gap.
ROUTE_MONTHS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}
UTC_OFFSET = "+0000"
RECORD_INSTANT = "{0}-{1:02d}-{2:02d}T{3}Z"


def dig(payload: Any, path: Sequence[str]) -> Any:
    """Follow one declared path of mapping keys, or return None at the first gap."""

    found = payload
    for key in path:
        if not isinstance(found, Mapping):
            return None
        found = found.get(key)
    return found


def route_instant_to_utc_iso(created_at: Any) -> str:
    """This route's stamp as the artifact's instant, or nothing.

    Only the exact form the route emits, at UTC, is read. Anything else is a
    missing time rather than an approximated one.
    """

    if not isinstance(created_at, str):
        return ""
    parts = created_at.split()
    if len(parts) != 6:
        return ""
    _, month, day, clock, offset, year = parts
    if month not in ROUTE_MONTHS or offset != UTC_OFFSET:
        return ""
    if not (day.isdigit() and year.isdigit() and len(clock) == 8):
        return ""
    return RECORD_INSTANT.format(year, ROUTE_MONTHS[month], int(day), clock)


def operation_for(target_id: str) -> Tuple[str, str, str]:
    """The operation one target id names, its variable name, and its argument."""

    kind, separator, argument = target_id.partition(":")
    if separator and kind in GUEST_OPERATIONS:
        return GUEST_OPERATIONS[kind] + (argument,)
    return GUEST_OPERATIONS[TWEET_TARGET_KIND] + (target_id,)


def _integers_of(
    source: Mapping[str, Any], names: Sequence[str]
) -> Tuple[Tuple[str, int], ...]:
    # Only exact native integers are admitted; anything else is not a snapshot.
    return tuple(
        (name, source[name])
        for name in names
        if isinstance(source.get(name), int) and not isinstance(source.get(name), bool)
    )


def _typename_of(result: Any) -> str:
    """What the route said this row is, for a page that holds no row at all."""

    if not isinstance(result, Mapping):
        return "no result object"
    return result.get(TYPENAME_FIELD) or "no " + TYPENAME_FIELD


def _screen_name_of(result: Mapping[str, Any]) -> str:
    author = dig(result, ("core", "user_results", "result", "legacy"))
    if not isinstance(author, Mapping):
        return ""
    return author.get("screen_name") or ""


def _record_from_tweet(position: int, result: Any) -> Optional[NativeRecord]:
    """One post as the route reported it, or None when the row is not one."""

    if not isinstance(result, Mapping):
        return None
    legacy = result.get("legacy")
    if not isinstance(legacy, Mapping):
        return None
    screen_name = _screen_name_of(result)
    tweet_id = legacy.get("id_str") or result.get("rest_id") or ""
    return NativeRecord(
        canonical_content_kind=POST_KIND,
        canonical_locator=(
            "{0}/{1}/status/{2}".format(X_ORIGIN, screen_name, tweet_id)
            if screen_name and tweet_id
            else ""
        ),
        native_item_id=tweet_id,
        # X names the thread a post belongs to `conversation_id_str`: its own
        # id for a root, the root it answers for a reply. Both are the
        # platform's own statement, and both are carried as reported.
        native_parent_id=legacy.get("conversation_id_str") or "",
        body=legacy.get("full_text") or "",
        author=screen_name,
        published_at=route_instant_to_utc_iso(legacy.get("created_at")),
        engagement=_integers_of(legacy, ENGAGEMENT_FIELDS),
        native_position=position,
    )


def _record_from_user(result: Any) -> Optional[NativeRecord]:
    """One profile as the route reported it, or None when the row is not one."""

    if not isinstance(result, Mapping):
        return None
    legacy = result.get("legacy")
    if not isinstance(legacy, Mapping):
        return None
    screen_name = legacy.get("screen_name") or ""
    return NativeRecord(
        canonical_content_kind=PROFILE_KIND,
        canonical_locator="{0}/{1}".format(X_ORIGIN, screen_name) if screen_name else "",
        native_item_id=result.get("rest_id") or "",
        title=legacy.get("name") or "",
        body=legacy.get("description") or "",
        author=screen_name,
        published_at=route_instant_to_utc_iso(legacy.get("created_at")),
        engagement=_integers_of(legacy, (FOLLOWERS_FIELD,)),
        native_position=0,
    )


def _timeline_rows(instructions: Sequence[Any]) -> Tuple[Tuple[NativeRecord, ...], str]:
    """This timeline's posts, in the order it listed them, and its bottom cursor.

    The cursor is surfaced and never followed: pagination is the core's to own,
    so what an adapter finds is something for the caller to decide on. Nothing
    in this release decides on it — ``runner.planned_calls`` sets no cursor —
    so this is the seam and not yet a behaviour.
    """

    records = []
    cursor = ""
    for instruction in instructions:
        if not isinstance(instruction, Mapping):
            continue
        if instruction.get("type") != ADD_ENTRIES_INSTRUCTION:
            continue
        for entry in instruction.get("entries") or ():
            if not isinstance(entry, Mapping):
                continue
            content = entry.get("content")
            if isinstance(content, Mapping) and content.get("entryType") == CURSOR_ENTRY_TYPE:
                if content.get("cursorType") == BOTTOM_CURSOR:
                    cursor = content.get("value") or ""
                continue
            record = _record_from_tweet(len(records), dig(entry, TWEET_ITEM_PATH))
            if record is not None:
                records.append(record)
    return (tuple(records), cursor)


def _failed(
    response: transport.TransportResponse, loss: str, warning: str
) -> NativePage:
    return build_native_page(
        DESCRIPTOR,
        (),
        observed_at=response.observed_at,
        native_order=NATIVE_ORDER,
        warnings=(warning,),
        outcome="failed",
        loss=(loss,),
    )


def _page_from(response: transport.TransportResponse, operation: str) -> NativePage:
    """Turn one response the origin itself sent into exactly one page."""

    if response.status == STALE_IDENTIFIER_STATUS:
        # The query id is in the path, so this status is about the endpoint and
        # not about the thing asked for. Reporting it as an empty result would
        # turn a scheduled rotation into a quiet nothing; reporting it as
        # `auth_required` would call a keyless route credentialed.
        return _failed(
            response,
            STALE_IDENTIFIER,
            "{0} answered {1}: query id {2} no longer names an endpoint. {3}".format(
                operation,
                response.status,
                GUEST_QUERY_IDS[operation],
                GUEST_QUERY_ID_RECOVERY,
            ),
        )
    if response.status in AUTHORIZATION_STATUSES:
        return _failed(
            response,
            AUTH_REQUIRED,
            "{0} answered {1}: the guest token does not authorize this"
            " operation".format(operation, response.status),
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
            response, "malformed_json", operation + " answered 200 with no json body"
        )

    result = dig(payload, RESULT_PATHS[operation])
    if result is None:
        return _failed(
            response,
            "schema_drift",
            "{0} answered 200 but kept no result at {1}".format(
                operation, ".".join(RESULT_PATHS[operation])
            ),
        )

    cursor = ""
    if operation == TIMELINE_OPERATION:
        if not isinstance(result, list):
            return _failed(
                response, "schema_drift", operation + " answered 200 with no instruction list"
            )
        records, cursor = _timeline_rows(result)
    elif operation == USER_OPERATION:
        records = tuple(record for record in (_record_from_user(result),) if record)
    else:
        records = tuple(record for record in (_record_from_tweet(0, result),) if record)

    if not records:
        # The one empty this route can legitimately answer with: the container
        # is there and holds no row, which is a suspended account or a timeline
        # with nothing in it. It is still said out loud, naming what was found,
        # because an empty nobody explained is indistinguishable at a glance
        # from the ones every branch above exists to keep apart from it.
        return build_native_page(
            DESCRIPTOR,
            (),
            observed_at=response.observed_at,
            cursor_out=cursor,
            native_order=NATIVE_ORDER,
            warnings=(
                "{0} answered 200 with no row this adapter could read: {1}".format(
                    operation, _typename_of(result)
                ),
            ),
            outcome="empty",
        )
    return build_native_page(
        DESCRIPTOR,
        records,
        observed_at=response.observed_at,
        cursor_out=cursor,
        native_order=NATIVE_ORDER,
        outcome="ok",
    )


def fetch_native_page(carrier: transport.Transport, request: AdapterRequest) -> NativePage:
    """Read one guest-authorized operation and return exactly one NativePage."""

    target_id = request.target_ids[0] if request.target_ids else request.query
    operation, variable, argument = operation_for(target_id)
    variables = {variable: argument}
    if request.cursor:
        variables["cursor"] = request.cursor

    def parse(response: transport.TransportResponse) -> NativePage:
        return _page_from(response, operation)

    return fetch_one_page(
        DESCRIPTOR,
        carrier,
        params={
            "query_id": GUEST_QUERY_IDS[operation],
            "operation_name": operation,
            "variables": json.dumps(variables, separators=(",", ":"), sort_keys=True),
        },
        parse=parse,
        native_order=NATIVE_ORDER,
    )
