"""K1 YouTube reads through InnerTube, under the web key the site publishes.

Measured 2026-08-10 (YouTube): ``youtubei/v1/search``
answered 200 with 2.27 MB in 1.4 s, ``youtubei/v1/next`` 200 with 1.12 MB in
2.2 s carrying comment threads, and ``youtubei/v1/player`` 200 with 21 KB in
0.3 s carrying ``title``, ``viewCount`` and ``publishDate``. The key is
embedded in youtube.com's own page source; no account and no console project
is involved. The prior spec priced search and comments behind an API key.

**Captions do not work and this module must never say otherwise.** Across
``WEB``, ``MWEB``, ``TVHTML5``, ``ANDROID`` and ``IOS`` on three videos,
``captionTracks`` came back empty every time, and playability degraded to
``UNPLAYABLE`` after the first metadata call. The evidence names the cause:
PoToken/BotGuard attestation. So a response listing no caption track is
``attestation_required`` — the tracks were withheld from a client that could
not attest — and never "this video has no captions", which is a false claim
about the video rather than about the read. For the same reason a response the
origin declares unplayable is not mined for the metadata it happens to carry,
and the words "Sign in to confirm you're not a bot" in its body are not read as
a credential problem: only a status line may make this route ``auth_required``.

Retrieving captions is deferred by the spec with a named reopen condition, and
nothing here reaches toward it: the field a caption fetcher would need is
declared below and read nowhere, which is checkable from outside.

Three operations, one route, one budget, because the endpoint is a path
segment the route declares. The client version in the request body rotates with
each YouTube web release and is declared as this adapter's volatile identifier
with the way back to a current one; a request the origin refuses is typed
``stale_identifier``, never an empty result.
"""

from __future__ import annotations

import json
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

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

# The client this package presents. `WEB` is the client whose key the
# 2026-08-10 probes record, and the version rotates with each YouTube web
# release: it is the one thing in an InnerTube request that goes stale on
# the vendor's schedule.
CLIENT_NAME = "WEB"
CLIENT_VERSION = "2.20260808.00.00"

# The client the `player` operation presents, and the reason it is not the one
# above. Measured 2026-08-17: `WEB` still answers `UNPLAYABLE` — the 2026-08-10
# attestation, unchanged — while `ANDROID` at this version answered
# `playabilityStatus.status: "OK"` with `videoDetails` and a populated
# `captions.playerCaptionsTracklistRenderer.captionTracks`, keyless, with no
# header beyond the ones the transport already sends. That is what makes a
# transcript reachable at all, and it is why this module no longer says
# captions cannot be had. It rotates on the vendor's schedule like the web
# version beside it, and is declared as this adapter's second volatile
# identifier for the same reason.
PLAYER_CLIENT_NAME = "ANDROID"
PLAYER_CLIENT_VERSION = "20.10.38"
PLAYER_CLIENT_VERSION_RECOVERY = (
    "Rotates with the Android app's own releases. Recover a current one by"
    " hand from a published client table — yt-dlp's `_INNERTUBE_CLIENTS` and"
    " youtube-transcript-api both pin this client and this field — and replace"
    " PLAYER_CLIENT_VERSION here. This package fetches neither: recovery is a"
    " deliberate manual step, because a self-updating identifier would make a"
    " run's own provenance depend on an unrecorded read. A version the origin"
    " refuses answers 400, which is typed stale_identifier, and a version it"
    " serves without captions answers 200 with an empty track list."
)

CLIENT_VERSION_RECOVERY = (
    "Rotates with each YouTube web release. Recover a current one by hand:"
    " fetch youtube.com's own page source and read INNERTUBE_CLIENT_VERSION"
    " out of the ytcfg blob it embeds — the same blob that carries the web"
    " key — and replace CLIENT_VERSION here. This package never fetches that"
    " page: recovery is a deliberate manual step, because a self-updating"
    " identifier would make a run's own provenance depend on an unrecorded"
    " read. A version the origin refuses answers 400 rather than an empty"
    " result set, which is why a refused request is typed stale_identifier."
)

DESCRIPTOR = AdapterDescriptor(
    adapter_id="youtube_innertube",
    adapter_version="1",
    access_class="K1",
    route_id=transport.YOUTUBE_INNERTUBE_ROUTE,
    platform="youtube",
    native_identity_namespace="youtube",
    representation_kind="native",
    operator_identity="youtube",
    # The 2026-08-10 probes: 1.4 s for search, which is the roster row's declared
    # ceiling. `next` at 2.2 s and `player` at 0.3 s are those operations'
    # latencies and not second ceilings — one route, one budget. Nothing here
    # was measured refusing, so burst and cooldown keep the defaults.
    min_interval_ms=1400,
    volatile_identifiers=(
        VolatileIdentifier(
            name="InnerTube {0} client version {1}".format(CLIENT_NAME, CLIENT_VERSION),
            recovery=CLIENT_VERSION_RECOVERY,
        ),
        VolatileIdentifier(
            name="InnerTube {0} client version {1}".format(
                PLAYER_CLIENT_NAME, PLAYER_CLIENT_VERSION
            ),
            recovery=PLAYER_CLIENT_VERSION_RECOVERY,
        ),
    ),
    # A comment carries a count of its own replies. Nothing in these three
    # operations reports an exact count of comments on a video, so no comment
    # metric is declared: a name is never inferred, and the abbreviated vote
    # count a comment carries is a string rather than a number.
    reply_count_metric="replyCount",
)

# The second surface: the timed-text endpoint a caption track's own address
# names. It is a different route on the same origin — a different budget and a
# different window — the way the channel feed is, and its records are the one
# `transcript` representation this package produces.
TRANSCRIPT_DESCRIPTOR = AdapterDescriptor(
    adapter_id="youtube_innertube",
    adapter_version="1",
    access_class="K1",
    route_id=transport.YOUTUBE_TIMEDTEXT_ROUTE,
    platform="youtube",
    native_identity_namespace="youtube",
    representation_kind="transcript",
    operator_identity="youtube",
    # Measured 2026-08-17: 109 KB of `srv3` in well under a second, and the
    # same track as `json3`. No throttle was met, so this is the interval the
    # route beside it declares rather than a second measurement.
    min_interval_ms=1400,
    page_size=1,
)

SURFACE_DESCRIPTORS = (DESCRIPTOR, TRANSCRIPT_DESCRIPTOR)

NATIVE_ORDER = "youtube_innertube_route_order"
TRANSCRIPT_NATIVE_ORDER = "youtube_timedtext_cue_order"
VIDEO_KIND = "video"
COMMENT_KIND = "comment"

# The three operations this route serves, spelled once each. A caller names
# one, because one route serves three: inferring which from the characters in
# an argument would be a guess.
SEARCH_OPERATION = "search"
NEXT_OPERATION = "next"
PLAYER_OPERATION = "player"
# The fourth, and the only one that spans two routes: page one asks the player
# for the caption track list, page two reads the track off the timed-text
# endpoint the player itself named. It is a discovery step because it pages —
# the core spends the continuation page one publishes — and a hydration step
# authorizes one call per hit and no continuation at all.
TRANSCRIPT_OPERATION = "transcript"
INNERTUBE_OPERATIONS = (
    SEARCH_OPERATION,
    NEXT_OPERATION,
    PLAYER_OPERATION,
    TRANSCRIPT_OPERATION,
)

# Where each answer keeps what it returned. Declared, never searched for: a
# parser that hunts for a familiar-looking list is inferring by similarity, and
# the whole point of a typed drift is to say the payload moved rather than that
# the platform went quiet.
SEARCH_RESULTS_PATH = (
    "contents",
    "twoColumnSearchResultsRenderer",
    "primaryContents",
    "sectionListRenderer",
    "contents",
)
WATCH_NEXT_PATH = ("contents", "twoColumnWatchNextResults", "results", "results", "contents")
RECEIVED_ENDPOINTS_KEY = "onResponseReceivedEndpoints"
# Where a *search* continuation keeps its rows. `SEARCH_RESULTS_PATH` above is
# the first answer's container and only ever the first answer's: a call
# spending a search token comes back with no `twoColumnSearchResultsRenderer`
# at all, and its sections ride here instead. Declared separately from
# `RECEIVED_ENDPOINTS_KEY` because the two routes name the container
# differently — `search` says Commands, `next` says Endpoints — and reading one
# container for the other is how a live route reports drift it did not have.
RECEIVED_COMMANDS_KEY = "onResponseReceivedCommands"
# And the names either container keeps its rows under. One tuple for both
# routes, because the suffix is not a per-route fact: each spells its append
# `appendContinuationItemsAction` and its reload
# `reloadContinuationItemsCommand`. The container above is what differs.
#
# Measured 2026-08-17, twice, and the second reading is why this is one tuple.
# Page two of `search:bitcoin price prediction` carried
# `onResponseReceivedCommands[0].appendContinuationItemsAction.continuationItems`
# holding 20 more `videoRenderer` rows, while the adapter read only the
# first-page path and typed the whole page `schema_drift`. Page three of
# `next:__tEElLKowI` answered 200 carrying
# `onResponseReceivedEndpoints[0].appendContinuationItemsAction` and nothing
# else — the third page of a video whose second had already returned 20
# threads — while `comment_items` scanned for `appendContinuationItemsCommand`,
# a spelling no route was ever measured sending, found no list, and typed that
# working page `schema_drift` too. A per-route tuple is the shape that let one
# route's correction leave the other broken, so there is one.
CONTINUATION_ACTIONS = (
    "appendContinuationItemsAction",
    "reloadContinuationItemsCommand",
)
CONTINUATION_ITEMS_KEY = "continuationItems"
CONTINUATION_ITEM_KEY = "continuationItemRenderer"
CONTINUATION_TOKEN_PATH = ("continuationEndpoint", "continuationCommand", "token")
ITEM_SECTION_KEY = "itemSectionRenderer"
SECTION_IDENTIFIER_KEY = "sectionIdentifier"
COMMENT_SECTION_IDENTIFIER = "comment-item-section"
CONTENTS_KEY = "contents"
VIDEO_RENDERER_KEY = "videoRenderer"
COMMENT_THREAD_KEY = "commentThreadRenderer"
COMMENT_PATH = ("comment", "commentRenderer")

# The second shape a thread arrives in, and the store its fields moved to.
# Measured 2026-08-17 on `next:4jZjM0Zs_LY`, page two: 13 threads, **zero** of
# them carrying `comment.commentRenderer`, so the path above read nothing and a
# video with 1,292 comments came back empty. The thread now carries a view model
# — nested under its own name twice, which is the platform's spelling and not a
# typo here — holding keys and no fields; `commentKey` addresses that thread's
# own `commentEntityPayload` among the answer's entity mutations, and the fields
# are on it. Both shapes are read, because both are served.
COMMENT_VIEW_MODEL_PATH = ("commentViewModel", "commentViewModel")
COMMENT_KEY_FIELD = "commentKey"
ENTITY_MUTATIONS_PATH = ("frameworkUpdates", "entityBatchUpdate", "mutations")
ENTITY_KEY_FIELD = "entityKey"
ENTITY_PAYLOAD_KEY = "payload"
# The one payload kind that carries a comment's fields. The same batch carried
# five other kinds on 13 threads — surface, tri-state button, toolbar surface,
# toolbar state, shared — and the kind is what selects, never the position: the
# toolbar-state mutations arrive interleaved with the comment ones.
COMMENT_ENTITY_KEY = "commentEntityPayload"
ENTITY_AUTHOR_KEY = "author"
ENTITY_AUTHOR_NAME_KEY = "displayName"
ENTITY_PROPERTIES_KEY = "properties"
ENTITY_CONTENT_KEY = "content"
# The body, and the reason it is not read through `route_text`: this one is a
# plain string under a key of its own name, not a `runs`/`simpleText` holder,
# and the label reader returns "" on it.
ENTITY_CONTENT_PATH = (ENTITY_CONTENT_KEY, ENTITY_CONTENT_KEY)
ENTITY_TOOLBAR_KEY = "toolbar"
PUBLISHED_TIME_KEY = "publishedTime"
# The like count a signed-out reader is shown. Beside it the same toolbar
# carries `likeCountLiked`, which is this count *if you liked it* — measured at
# exactly one more on all thirteen rows, 28/29, 6/7, 1/2 — so reading that one
# would inflate every count in the artifact by one and give a comment nobody
# liked a like. It is a string either way and rides in `attributes` verbatim:
# a comment with no likes reads `" "`, one space, which is a label and not a
# zero, and the count the origin published for it is no count at all.
LIKE_COUNT_NOTLIKED_KEY = "likeCountNotliked"
COMMENT_ENTITY_TEXT_FACTS = (LIKE_COUNT_NOTLIKED_KEY, PUBLISHED_TIME_KEY)

# Where a player answer keeps the three fields the roster row names, and what
# it says about whether it is answering at all.
PLAYABILITY_KEY = "playabilityStatus"
PLAYABILITY_STATUS_KEY = "status"
PLAYABILITY_REASON_KEY = "reason"
PLAYABLE_STATUS = "OK"
VIDEO_DETAILS_KEY = "videoDetails"
MICROFORMAT_PATH = ("microformat", "playerMicroformatRenderer")
PUBLISH_DATE_KEY = "publishDate"
EMBED_URL_PATH = ("embed", "iframeUrl")

# The statuses the 2026-08-10 probes recorded a degraded player answering with, and
# the cause it names for them. Both words mean the same thing here: this client
# was not served, and it was not served because it cannot attest.
ATTESTED_PLAYABILITY = ("UNPLAYABLE", "ERROR")

# The statuses that are YouTube refusing on its own account rather than this
# client failing to attest. protocol.md reserves `attestation_required` for a
# payload withheld behind an attestation this package does not perform, and
# names `auth_required` for the origin's own refusal; a private video is the
# second, and typing it as the first would file a video nobody may watch under
# a capability that is merely deferred.
CREDENTIAL_PLAYABILITY = ("LOGIN_REQUIRED", "AGE_VERIFICATION_REQUIRED")

# Where the caption tracks are listed, and the field the transcript operation
# spends. Both are read now: the 2026-08-10 deferral held because every client
# then measured answered with an empty list, and the `ANDROID` client above
# answers with a populated one.
CAPTION_TRACKS_PATH = ("captions", "playerCaptionsTracklistRenderer", "captionTracks")
CAPTION_FETCH_FIELD = "baseUrl"
CAPTION_LANGUAGE_FIELD = "languageCode"
CAPTION_KIND_FIELD = "kind"
# What the origin calls a track it generated itself. A caller asking for a
# language gets that language whichever kind it is; a caller asking for none
# gets a human-written track over a generated one, because the first is what
# the publisher meant to say.
CAPTION_ASR_KIND = "asr"

# The timed-text format this package asks for, and the shape it answers in.
# `json3` rather than the `srv3` the track's own address names: both answered
# 200 on 2026-08-17 and only one of them is JSON, which is a payload this
# package can read without a parser it does not have.
TIMEDTEXT_FORMAT_PARAM = "fmt"
TIMEDTEXT_FORMAT = "json3"
TIMEDTEXT_EVENTS_KEY = "events"
TIMEDTEXT_SEGMENTS_KEY = "segs"
TIMEDTEXT_TEXT_KEY = "utf8"
TIMEDTEXT_START_KEY = "tStartMs"
TIMEDTEXT_DURATION_KEY = "dDurationMs"

# Every other key this module reads, under the payload's own names.
VIDEO_ID_KEY = "videoId"
TITLE_KEY = "title"
OWNER_TEXT_KEY = "ownerText"
AUTHOR_KEY = "author"
DESCRIPTION_KEY = "shortDescription"
COMMENT_ID_KEY = "commentId"
AUTHOR_TEXT_KEY = "authorText"
CONTENT_TEXT_KEY = "contentText"
NAVIGATION_URL_PATH = ("navigationEndpoint", "commandMetadata", "webCommandMetadata", "url")
RUNS_KEY = "runs"
SIMPLE_TEXT_KEY = "simpleText"
TEXT_KEY = "text"

# The counts these operations publish as exact numbers, and the labels they
# publish as text formatted for a reader. A label is carried verbatim under the
# route's own name and never parsed: "1,284,553 views" is locale-shaped, "1.2K"
# is rounded, and "2 weeks ago" is only an instant to something holding a clock.
VIEW_COUNT_METRIC = "viewCount"
REPLY_COUNT_METRIC = "replyCount"
VIEW_COUNT_TEXT_KEY = "viewCountText"
PUBLISHED_TIME_TEXT_KEY = "publishedTimeText"
VOTE_COUNT_TEXT_KEY = "voteCount"
SEARCH_TEXT_FACTS = (VIEW_COUNT_TEXT_KEY, PUBLISHED_TIME_TEXT_KEY)
COMMENT_TEXT_FACTS = (VOTE_COUNT_TEXT_KEY, PUBLISHED_TIME_TEXT_KEY)

# What each kind of row promises, so a record short of it says so. The
# evidence enumerates a field set for `player` only, which is why the other two
# are this adapter's own declaration rather than a measured list. An id is
# absent from all three: a row without one is not a row of that kind at all.
SEARCH_ROW_KEYS = (TITLE_KEY, OWNER_TEXT_KEY)
PLAYER_ROW_KEYS = (TITLE_KEY, VIEW_COUNT_METRIC, PUBLISH_DATE_KEY)
COMMENT_ROW_KEYS = (COMMENT_ID_KEY, CONTENT_TEXT_KEY, AUTHOR_TEXT_KEY)
# The same three fields under the entity store's own names, which is what a
# thread in the second shape promises. A thread whose key resolves to no entity
# is short of all three at once, and says so rather than disappearing.
COMMENT_ENTITY_ROW_KEYS = (COMMENT_ID_KEY, ENTITY_CONTENT_KEY, ENTITY_AUTHOR_NAME_KEY)

ROUTE_DATE_FORMAT = "%Y-%m-%d"
ROUTE_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S%z"
RECORD_INSTANT_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
DATE_PRECISION_ONLY = "date_precision_only"

# The statuses that separate a rotated client version from a refusal.
STALE_IDENTIFIER_STATUS = 400
AUTHORIZATION_STATUSES = (401, 403)
STALE_IDENTIFIER = "stale_identifier"
ATTESTATION_REQUIRED = "attestation_required"
AUTH_REQUIRED = "auth_required"
# A refusal this evidence has nothing to say about: the origin declined to
# serve the payload and this package knows only that. It is the retained
# vocabulary's word for exactly that much, and it claims no cause.
WITHHELD = "withheld"
# The three the timed-text route can fail by, spelled as every sibling adapter
# spells them. A signed caption address expires and a payload shape is read
# rather than promised, so all three are ordinary weather on that route — and
# a code the core cannot recognise would report as little as a raise does.
HTTP_STATUS = "http_status"
MALFORMED_JSON = "malformed_json"
SCHEMA_DRIFT = "schema_drift"


def dig(payload: Any, path: Sequence[str]) -> Any:
    """Follow one declared path of mapping keys, or return None at the first gap."""

    found = payload
    for key in path:
        if not isinstance(found, Mapping):
            return None
        found = found.get(key)
    return found


def route_text(value: Any) -> str:
    """One label as the route wrote it: a simple string, or its runs joined back.

    The runs are one text the route split at its own formatting, so joining
    them restores what it said. Keeping them apart would make one sentence read
    as a list of fragments.
    """

    if not isinstance(value, Mapping):
        return ""
    simple = value.get(SIMPLE_TEXT_KEY)
    if isinstance(simple, str):
        return simple
    runs = value.get(RUNS_KEY)
    if not isinstance(runs, list):
        return ""
    parts = []
    for run in runs:
        text = run.get(TEXT_KEY) if isinstance(run, Mapping) else None
        if isinstance(text, str):
            parts.append(text)
    return "".join(parts)


def exact_count(value: Any) -> Optional[int]:
    """One count the route published as an exact number, or nothing.

    A string of digits is the number the route reported in the route's own
    encoding, so it is read. A count formatted for a reader is not one: it is
    rounded, separated, or suffixed, and a number recovered from it would be a
    number nobody published.
    """

    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def route_date_to_utc_iso(published: Any) -> Tuple[str, bool]:
    """This route's publish date as the artifact's instant, and how precise it is.

    Two shapes, because the route emits both: a bare day, which becomes
    midnight UTC and says so, and a full offset instant, which is carried
    exactly. Anything else is a missing time rather than an approximated one.
    """

    if not isinstance(published, str) or not published:
        return ("", False)
    text = published.strip()
    try:
        day = datetime.strptime(text, ROUTE_DATE_FORMAT)
    except ValueError:
        pass
    else:
        return (day.replace(tzinfo=timezone.utc).strftime(RECORD_INSTANT_FORMAT), True)
    try:
        moment = datetime.strptime(text, ROUTE_DATETIME_FORMAT)
    except ValueError:
        return ("", False)
    return (moment.astimezone(timezone.utc).strftime(RECORD_INSTANT_FORMAT), False)


def caption_tracks(payload: Mapping[str, Any]) -> Tuple[Mapping[str, Any], ...]:
    """Every caption track this answer listed, in the order it listed them."""

    tracks = dig(payload, CAPTION_TRACKS_PATH)
    if not isinstance(tracks, list):
        return ()
    return tuple(track for track in tracks if isinstance(track, Mapping))


def captions_withheld(payload: Mapping[str, Any]) -> bool:
    """Whether this answer listed no caption track at all.

    The 2026-08-10 probes recorded exactly that on five clients and three videos, and
    names the cause: PoToken/BotGuard attestation. So an empty list is a
    statement about this client and not about the video, and the one thing a
    caller must never read off it is that the video has no captions.

    That reading still holds for a client that cannot attest. It does not hold
    for the `ANDROID` client this module now asks `player` with, which answered
    with a populated list on 2026-08-17 — so an empty list from *that* client is
    reported as an empty list rather than as a withholding, and the transcript
    operation says the video lists no track.
    """

    return not caption_tracks(payload)


def chosen_track(
    tracks: Tuple[Mapping[str, Any], ...], language: str
) -> Optional[Mapping[str, Any]]:
    """The one track a transcript read spends, under a stated rule.

    A named language wins, exactly, whichever kind it is. Absent one: a track
    the publisher wrote beats one the platform generated, and among equals the
    order the origin listed them in decides. Nothing here prefers English —
    a video's own language is the one thing the origin did state.
    """

    if language:
        for track in tracks:
            if _text(track.get(CAPTION_LANGUAGE_FIELD)) == language:
                return track
        return None
    for track in tracks:
        if _text(track.get(CAPTION_KIND_FIELD)) != CAPTION_ASR_KIND:
            return track
    return tracks[0] if tracks else None


def _text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _named_facts(
    source: Mapping[str, Any], keys: Sequence[str]
) -> Tuple[Tuple[str, str], ...]:
    """Every label this row carried, verbatim, under the route's own names."""

    carried = []
    for key in keys:
        text = route_text(source.get(key))
        if text:
            carried.append((key, text))
    return tuple(carried)


def _missing(row: Mapping[str, Any], keys: Sequence[str]) -> Tuple[str, ...]:
    """Which of this row's declared fields the payload did not report.

    Absence, never falsehood: a video nobody has watched reports zero views,
    and zero is a count. Marking it omitted would erase the one distinction
    `field_omitted` exists to make.
    """

    return tuple(key for key in keys if row.get(key) is None or row.get(key) == "")


def continuation_in(entry: Any) -> str:
    """The token one continuation row carries, or nothing when it is not one."""

    if not isinstance(entry, Mapping):
        return ""
    holder = entry.get(CONTINUATION_ITEM_KEY)
    if not isinstance(holder, Mapping):
        return ""
    return _text(dig(holder, CONTINUATION_TOKEN_PATH))


def search_sections(payload: Any) -> Optional[list]:
    """The section list a search answer carries, in whichever of its two shapes.

    A first call comes back with the results container. A call spending a token
    comes back with no container at all and its sections under an append or
    reload command instead. Both are declared, and the rows inside them are the
    same shape either way — `itemSectionRenderer` holding `videoRenderer`s,
    beside a `continuationItemRenderer` carrying the next token — so the walk in
    :func:`search_rows` reads either without knowing which it got.

    None means neither shape is there, which is the payload having moved.
    Returning the first-page container even when empty keeps "matched nothing"
    distinct from "the container is gone", which is the distinction the whole
    typed-drift vocabulary exists to preserve.
    """

    sections = dig(payload, SEARCH_RESULTS_PATH)
    if isinstance(sections, list):
        return sections
    commands = payload.get(RECEIVED_COMMANDS_KEY) if isinstance(payload, Mapping) else None
    for command in commands if isinstance(commands, list) else ():
        if not isinstance(command, Mapping):
            continue
        for name in CONTINUATION_ACTIONS:
            held = command.get(name)
            items = held.get(CONTINUATION_ITEMS_KEY) if isinstance(held, Mapping) else None
            if isinstance(items, list):
                return items
    return None


def search_rows(payload: Any) -> Optional[Tuple[Tuple[Mapping[str, Any], ...], str]]:
    """Every video the results section listed, in order, and its continuation.

    None when the section itself is not there, which is drift rather than a
    search that matched nothing: a query with no matches still answers with the
    container.
    """

    sections = search_sections(payload)
    if sections is None:
        return None
    found = []
    cursor = ""
    for section in sections:
        if not isinstance(section, Mapping):
            continue
        cursor = cursor or continuation_in(section)
        item = section.get(ITEM_SECTION_KEY)
        rows = item.get(CONTENTS_KEY) if isinstance(item, Mapping) else None
        for entry in rows if isinstance(rows, list) else ():
            if not isinstance(entry, Mapping):
                continue
            cursor = cursor or continuation_in(entry)
            renderer = entry.get(VIDEO_RENDERER_KEY)
            # A row with no id can be neither identified nor addressed, so it
            # is not a result: keeping it would put a record in the artifact
            # that names nothing and groups with nothing.
            if isinstance(renderer, Mapping) and _text(renderer.get(VIDEO_ID_KEY)):
                found.append(renderer)
    return (tuple(found), cursor)


def comment_items(payload: Any) -> Optional[Sequence[Any]]:
    """The rows a `next` answer carries, in whichever of its two shapes it came.

    A call spending a token comes back with the threads themselves. A call
    naming a video comes back with the watch page, whose comment section holds
    the token and no thread yet. Both are declared; None means neither is
    there, which is the payload having moved.

    **Every command's rows, not the first command's.** One answer carries the
    comment section in more than one piece, and the pieces are not ranked: the
    header — the comment count and the sort control — is its own
    `reloadContinuationItemsCommand` and it arrives *before* the one holding
    the threads. Returning the first list found therefore returned a
    one-row header and typed a video with comments as having none. Measured
    2026-08-17 on `next:4jZjM0Zs_LY`: entry 0 held one `commentsHeaderRenderer`
    and entry 1 held fourteen `commentThreadRenderer`s. Concatenating is safe
    because the caller reads each row for a thread and skips what is not one,
    so a header row costs a loop iteration and never a record.
    """

    found = []
    endpoints = payload.get(RECEIVED_ENDPOINTS_KEY) if isinstance(payload, Mapping) else None
    for endpoint in endpoints if isinstance(endpoints, list) else ():
        if not isinstance(endpoint, Mapping):
            continue
        for command in CONTINUATION_ACTIONS:
            held = endpoint.get(command)
            items = held.get(CONTINUATION_ITEMS_KEY) if isinstance(held, Mapping) else None
            if isinstance(items, list):
                found.extend(items)
    if found:
        return found
    sections = dig(payload, WATCH_NEXT_PATH)
    for section in sections if isinstance(sections, list) else ():
        item = section.get(ITEM_SECTION_KEY) if isinstance(section, Mapping) else None
        if not isinstance(item, Mapping):
            continue
        if item.get(SECTION_IDENTIFIER_KEY) != COMMENT_SECTION_IDENTIFIER:
            continue
        rows = item.get(CONTENTS_KEY)
        if isinstance(rows, list):
            return rows
    return None


def comment_entities(payload: Any) -> Optional[Dict[str, Mapping[str, Any]]]:
    """Every comment entity this answer carried, under the key that addresses it.

    None means the mutation list itself is not there, which is the payload
    having moved and not an answer whose threads happen to resolve to nothing:
    an answer serving view models states a store, and one that states none has
    put the fields somewhere this module has not been told about. An empty
    mapping is a store that arrived carrying no comment, which is a different
    piece of news and stays distinct from it.
    """

    mutations = dig(payload, ENTITY_MUTATIONS_PATH)
    if not isinstance(mutations, list):
        return None
    found = {}
    for mutation in mutations:
        if not isinstance(mutation, Mapping):
            continue
        key = _text(mutation.get(ENTITY_KEY_FIELD))
        entity = dig(mutation, (ENTITY_PAYLOAD_KEY, COMMENT_ENTITY_KEY))
        if key and isinstance(entity, Mapping):
            found[key] = entity
    return found


def _entity_facts(
    properties: Mapping[str, Any], toolbar: Mapping[str, Any]
) -> Tuple[Tuple[str, str], ...]:
    """The two non-integer facts this entity states, verbatim, under its names.

    Neither is a number and neither is made into one. The like count is a
    string the origin writes as `" "` where nobody has liked the comment, and
    the published time is an interval from a moment this package did not
    observe — the same reason the older shape's record states no instant.
    """

    carried = []
    for source, key in ((toolbar, LIKE_COUNT_NOTLIKED_KEY), (properties, PUBLISHED_TIME_KEY)):
        value = source.get(key)
        if isinstance(value, str) and value:
            carried.append((key, value))
    return tuple(carried)


def _view_model_record(
    position: int,
    entity: Optional[Mapping[str, Any]],
    video_id: str,
) -> NativeRecord:
    """One thread as the entity its key named reported it.

    ``entity`` is None for a key that addressed nothing in the store this
    answer carried. That is still a record: the platform listed the thread, and
    dropping it would report fewer comments than the video has. It carries
    `field_omitted` because the fields did not arrive — which is absence, and
    never a comment with no author and no body.
    """

    entity = entity if isinstance(entity, Mapping) else {}
    author = entity.get(ENTITY_AUTHOR_KEY)
    author = author if isinstance(author, Mapping) else {}
    properties = entity.get(ENTITY_PROPERTIES_KEY)
    properties = properties if isinstance(properties, Mapping) else {}
    toolbar = entity.get(ENTITY_TOOLBAR_KEY)
    toolbar = toolbar if isinstance(toolbar, Mapping) else {}
    row = {
        COMMENT_ID_KEY: _text(properties.get(COMMENT_ID_KEY)),
        # A plain string at this path, read as one. The label reader beside it
        # is for `runs`/`simpleText` holders and returns "" on this.
        ENTITY_CONTENT_KEY: _text(dig(properties, ENTITY_CONTENT_PATH)),
        ENTITY_AUTHOR_NAME_KEY: _text(author.get(ENTITY_AUTHOR_NAME_KEY)),
    }
    # Digits or nothing. This route writes `""` for a thread with no replies and
    # states the zero only in a sentence beside it, and a sentence is not a
    # count: reading zero off `""` would publish a number nobody sent.
    replies = exact_count(toolbar.get(REPLY_COUNT_METRIC))
    return NativeRecord(
        canonical_content_kind=COMMENT_KIND,
        canonical_locator="",
        native_item_id=row[COMMENT_ID_KEY],
        native_parent_id=video_id,
        body=row[ENTITY_CONTENT_KEY],
        author=row[ENTITY_AUTHOR_NAME_KEY],
        engagement=() if replies is None else ((REPLY_COUNT_METRIC, replies),),
        attributes=_entity_facts(properties, toolbar),
        native_position=position,
        loss=("field_omitted",) if _missing(row, COMMENT_ENTITY_ROW_KEYS) else (),
    )


def _search_record(position: int, renderer: Mapping[str, Any]) -> NativeRecord:
    """One search result as the section listed it."""

    row = {
        VIDEO_ID_KEY: _text(renderer.get(VIDEO_ID_KEY)),
        TITLE_KEY: route_text(renderer.get(TITLE_KEY)),
        OWNER_TEXT_KEY: route_text(renderer.get(OWNER_TEXT_KEY)),
    }
    return NativeRecord(
        canonical_content_kind=VIDEO_KIND,
        # The address the payload published, resolved against the origin that
        # published it. YouTube writes it relative to itself, and a route's
        # host belongs to `routes.py`.
        canonical_locator=transport.origin_locator(
            DESCRIPTOR.route_id, _text(dig(renderer, NAVIGATION_URL_PATH))
        ),
        native_item_id=row[VIDEO_ID_KEY],
        title=row[TITLE_KEY],
        author=row[OWNER_TEXT_KEY],
        attributes=_named_facts(renderer, SEARCH_TEXT_FACTS),
        native_position=position,
        loss=("field_omitted",) if _missing(row, SEARCH_ROW_KEYS) else (),
    )


def _comment_record(
    position: int, comment: Mapping[str, Any], video_id: str
) -> NativeRecord:
    """One comment as the thread reported it.

    ``published_at`` is left unset because this route states no instant: it
    says "3 days ago", which is an interval from a moment nobody here observed.
    ``canonical_locator`` is unset for the same kind of reason — the payload
    publishes no address for a comment, and composing one would be this package
    asserting a scheme rather than carrying what it was told.
    """

    row = {
        COMMENT_ID_KEY: _text(comment.get(COMMENT_ID_KEY)),
        CONTENT_TEXT_KEY: route_text(comment.get(CONTENT_TEXT_KEY)),
        AUTHOR_TEXT_KEY: route_text(comment.get(AUTHOR_TEXT_KEY)),
    }
    replies = exact_count(comment.get(REPLY_COUNT_METRIC))
    return NativeRecord(
        canonical_content_kind=COMMENT_KIND,
        canonical_locator="",
        native_item_id=row[COMMENT_ID_KEY],
        native_parent_id=video_id,
        body=row[CONTENT_TEXT_KEY],
        author=row[AUTHOR_TEXT_KEY],
        engagement=() if replies is None else ((REPLY_COUNT_METRIC, replies),),
        attributes=_named_facts(comment, COMMENT_TEXT_FACTS),
        native_position=position,
        loss=("field_omitted",) if _missing(row, COMMENT_ROW_KEYS) else (),
    )


def _player_record(payload: Mapping[str, Any], withheld: bool) -> NativeRecord:
    """One video's metadata as the player answer reported it."""

    details = payload.get(VIDEO_DETAILS_KEY)
    details = details if isinstance(details, Mapping) else {}
    microformat = dig(payload, MICROFORMAT_PATH)
    microformat = microformat if isinstance(microformat, Mapping) else {}
    views = exact_count(details.get(VIEW_COUNT_METRIC))
    published_at, day_only = route_date_to_utc_iso(microformat.get(PUBLISH_DATE_KEY))
    row = {
        TITLE_KEY: _text(details.get(TITLE_KEY)),
        VIEW_COUNT_METRIC: views,
        PUBLISH_DATE_KEY: published_at,
    }
    loss = (ATTESTATION_REQUIRED,) if withheld else ()
    if day_only:
        loss = loss + (DATE_PRECISION_ONLY,)
    if _missing(row, PLAYER_ROW_KEYS):
        loss = loss + ("field_omitted",)
    return NativeRecord(
        canonical_content_kind=VIDEO_KIND,
        # The one address this payload publishes for the video, already
        # absolute and carried as published.
        canonical_locator=transport.origin_locator(
            DESCRIPTOR.route_id, _text(dig(microformat, EMBED_URL_PATH))
        ),
        native_item_id=_text(details.get(VIDEO_ID_KEY)),
        title=row[TITLE_KEY],
        body=_text(details.get(DESCRIPTION_KEY)),
        author=_text(details.get(AUTHOR_KEY)),
        published_at=published_at,
        engagement=() if views is None else ((VIEW_COUNT_METRIC, views),),
        native_position=0,
        loss=loss,
    )


def _answered(
    response: transport.TransportResponse,
    records: Tuple[NativeRecord, ...],
    outcome: str,
    cursor_out: str = "",
    warnings: Tuple[str, ...] = (),
    loss: Tuple[str, ...] = (),
) -> NativePage:
    return build_native_page(
        DESCRIPTOR,
        records,
        observed_at=response.observed_at,
        cursor_out=cursor_out,
        native_order=NATIVE_ORDER,
        warnings=warnings,
        outcome=outcome,
        loss=loss,
    )


def _failed(response: transport.TransportResponse, loss: str, warning: str) -> NativePage:
    return _answered(response, (), "failed", warnings=(warning,), loss=(loss,))


def _drifted(response: transport.TransportResponse, operation: str, detail: str) -> NativePage:
    return _failed(
        response,
        "schema_drift",
        "{0} answered 200 and {1}: the payload this adapter reads has changed"
        " shape".format(operation, detail),
    )


def _search_page(response: transport.TransportResponse, payload: Any) -> NativePage:
    found = search_rows(payload)
    if found is None:
        return _drifted(
            response, SEARCH_OPERATION, "kept no results at " + ".".join(SEARCH_RESULTS_PATH)
        )
    renderers, cursor = found
    records = tuple(
        _search_record(position, renderer) for position, renderer in enumerate(renderers)
    )
    return _answered(
        response,
        records,
        "ok" if records else "empty",
        cursor_out=cursor,
        warnings=()
        if records
        else ("{0} answered 200 with a results section holding no video".format(
            SEARCH_OPERATION
        ),),
    )


def _comments_page(
    response: transport.TransportResponse, payload: Any, video_id: str
) -> NativePage:
    items = comment_items(payload)
    if items is None:
        return _drifted(
            response,
            NEXT_OPERATION,
            "carried neither continuation items nor a {0}".format(
                COMMENT_SECTION_IDENTIFIER
            ),
        )
    records = []
    cursor = ""
    # Read once for the whole answer: the store is the answer's, not a thread's.
    entities = comment_entities(payload)
    for entry in items:
        thread = entry.get(COMMENT_THREAD_KEY) if isinstance(entry, Mapping) else None
        comment = dig(thread, COMMENT_PATH) if isinstance(thread, Mapping) else None
        if isinstance(comment, Mapping):
            records.append(_comment_record(len(records), comment, video_id))
            continue
        view_model = dig(thread, COMMENT_VIEW_MODEL_PATH) if isinstance(thread, Mapping) else None
        if isinstance(view_model, Mapping):
            if entities is None:
                # Threads arrived and the store they address did not. Reading
                # them as empty would report a video with comments as having
                # none, which is the one thing the typed vocabulary exists to
                # keep apart from the platform going quiet.
                return _drifted(
                    response,
                    NEXT_OPERATION,
                    "carried a {0} and no {1}".format(
                        COMMENT_VIEW_MODEL_PATH[-1], ".".join(ENTITY_MUTATIONS_PATH)
                    ),
                )
            records.append(
                _view_model_record(
                    len(records),
                    entities.get(_text(view_model.get(COMMENT_KEY_FIELD))),
                    video_id,
                )
            )
            continue
        cursor = cursor or continuation_in(entry)
    if records:
        return _answered(response, tuple(records), "ok", cursor_out=cursor)
    # Two empties this route can honestly answer with, and neither is silent:
    # the first call carries the token for the threads and no thread yet, and a
    # video with comments turned off carries neither. The token is surfaced for
    # the core to spend — following it here would make one call two reads.
    return _answered(
        response,
        (),
        "empty",
        cursor_out=cursor,
        warnings=(
            "{0} answered 200 with the {1} carrying {2} and no thread".format(
                NEXT_OPERATION,
                COMMENT_SECTION_IDENTIFIER,
                "a continuation token" if cursor else "no continuation token",
            ),
        ),
    )


def _playability_loss(status: str) -> str:
    """Which refusal a non-`OK` playability is, off the two declared lists.

    Three answers, because they are three different pieces of news. A status
    The 2026-08-10 probes recorded is attestation. A status naming the origin's own
    refusal is `auth_required`, which is what protocol.md reserves for it. A
    status on neither list is `withheld`: the origin declined and this package
    knows only that, and typing it as attestation would report a video that is
    private, deleted, or region-blocked as a capability merely deferred.
    """

    if status in ATTESTED_PLAYABILITY:
        return ATTESTATION_REQUIRED
    if status in CREDENTIAL_PLAYABILITY:
        return AUTH_REQUIRED
    return WITHHELD


def _playability_warning(playability: Mapping[str, Any]) -> str:
    """What the origin said, and the evidence for reading it that way — if any.

    The measured citation is attached only to the statuses it was measured on.
    Quoting five clients and three videos under a status the probe run never
    saw would make this module's own warning the evidence for its own typing.
    """

    status = _text(playability.get(PLAYABILITY_STATUS_KEY))
    said = "{0} answered 200 with playability {1} ({2}).".format(
        PLAYER_OPERATION,
        status or "unstated",
        _text(playability.get(PLAYABILITY_REASON_KEY)) or "no reason given",
    )
    if status in ATTESTED_PLAYABILITY:
        # Measured on videos that exist, so the code names the cause. The same
        # status is also how the origin answers for a video it no longer has,
        # which the reason above is the only thing that distinguishes.
        return said + (
            " The 2026-08-10 probes recorded this status across five clients and three"
            " videos and names the cause as PoToken/BotGuard attestation;"
            " caption retrieval and attestation are deferred by the spec. The"
            " origin's own reason is quoted above: this status is also what it"
            " answers for a video it no longer holds."
        )
    if status in CREDENTIAL_PLAYABILITY:
        return said + (
            " That is the origin refusing this read on its own account, not an"
            " attestation this package could perform: no credential makes a"
            " keyless route credentialed, and none is supplied."
        )
    return said + (
        " The 2026-08-10 probes did not record this status, so nothing here names a"
        " cause: the origin declined to serve the payload and the reason it"
        " gave is quoted above."
    )


def _player_page(response: transport.TransportResponse, payload: Any) -> NativePage:
    playability = payload.get(PLAYABILITY_KEY) if isinstance(payload, Mapping) else None
    if not isinstance(playability, Mapping):
        return _drifted(
            response, PLAYER_OPERATION, "stated no " + PLAYABILITY_KEY
        )

    status = _text(playability.get(PLAYABILITY_STATUS_KEY))
    if status != PLAYABLE_STATUS:
        # The origin declined to serve this client, and the answer is not mined
        # for the metadata it happens to carry: a degraded response is not a
        # successful read. Which refusal it is comes off the two declared lists
        # above rather than from "not OK", because the three cases are three
        # different pieces of news and only one of them is measured.
        return _failed(response, _playability_loss(status), _playability_warning(playability))

    details = payload.get(VIDEO_DETAILS_KEY)
    if not isinstance(details, Mapping):
        return _drifted(response, PLAYER_OPERATION, "stated no " + VIDEO_DETAILS_KEY)

    withheld = captions_withheld(payload)
    return _answered(
        response,
        (_player_record(payload, withheld),),
        "ok",
        warnings=(
            "{0} answered 200 listing no caption track at {1}. The 2026-08-10 probes"
            " measured that on every client and every video probed and names"
            " the cause as PoToken/BotGuard attestation: the tracks are"
            " withheld from a client that cannot attest, and this is not a"
            " statement that the video has none.".format(
                PLAYER_OPERATION, ".".join(CAPTION_TRACKS_PATH)
            ),
        )
        if withheld
        else (),
        loss=(ATTESTATION_REQUIRED,) if withheld else (),
    )


def _page_from(
    response: transport.TransportResponse, operation: str, argument: str
) -> NativePage:
    """Turn one response the origin itself sent into exactly one page."""

    if response.status == STALE_IDENTIFIER_STATUS:
        # The one thing in this request that rotates on the vendor's schedule
        # is the client version, and the origin refusing the request is how a
        # stale one shows. Reporting it as an empty result would turn a
        # scheduled rotation into a quiet nothing.
        return _failed(
            response,
            STALE_IDENTIFIER,
            "{0} answered {1}: the origin refused this request, whose one"
            " rotating part is {2} client version {3}. {4}".format(
                operation,
                response.status,
                CLIENT_NAME,
                CLIENT_VERSION,
                CLIENT_VERSION_RECOVERY,
            ),
        )
    if response.status in AUTHORIZATION_STATUSES:
        return _failed(
            response,
            AUTH_REQUIRED,
            "{0} answered {1}: the origin refused this read".format(
                operation, response.status
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
            response, "malformed_json", operation + " answered 200 with no json body"
        )

    if operation == SEARCH_OPERATION:
        return _search_page(response, payload)
    if operation == NEXT_OPERATION:
        return _comments_page(response, payload, argument)
    return _player_page(response, payload)


TRANSCRIPT_KIND = "transcript"

# What a transcript's first page hands its second. It is the track's own signed
# query, exactly as the origin wrote it, with the format this package reads
# asked for — a continuation is the origin's own statement of where the next
# read is, and this one is that statement verbatim.
CURSOR_VIDEO_FIELD = "sr_video"
CURSOR_LANGUAGE_FIELD = "sr_lang"
CURSOR_KIND_FIELD = "sr_kind"


def transcript_cursor(video_id: str, track: Mapping[str, Any]) -> str:
    """One caption track's own address, as the continuation page two spends.

    The track's `baseUrl` carries a signature and an expiry this package
    neither makes nor reads; it is carried whole. The three fields added
    alongside it are what the record needs and the address does not always
    say: which video it belongs to, and which track was chosen.
    """

    address = _text(track.get(CAPTION_FETCH_FIELD))
    if not address:
        return ""
    query = urllib.parse.urlsplit(address).query
    pairs = [
        (name, value)
        for name, value in urllib.parse.parse_qsl(query, keep_blank_values=True)
        if name != TIMEDTEXT_FORMAT_PARAM
    ]
    pairs.append((TIMEDTEXT_FORMAT_PARAM, TIMEDTEXT_FORMAT))
    pairs.append((CURSOR_VIDEO_FIELD, video_id))
    pairs.append((CURSOR_LANGUAGE_FIELD, _text(track.get(CAPTION_LANGUAGE_FIELD))))
    pairs.append((CURSOR_KIND_FIELD, _text(track.get(CAPTION_KIND_FIELD))))
    return urllib.parse.urlencode(pairs)


def transcript_params(cursor: str) -> Dict[str, str]:
    """The continuation, back as the parameters the timed-text route is asked with."""

    return dict(urllib.parse.parse_qsl(cursor, keep_blank_values=True))


def transcript_text(payload: Any) -> Tuple[str, int, int]:
    """One `json3` track as its own text, its cue count, and where it ends.

    Cues are joined in the order the origin listed them, one line each.
    A cue the origin sent as whitespace alone is dropped, because `json3`
    spaces its cues that way and a line of nothing is not a line the speaker
    said.
    """

    events = payload.get(TIMEDTEXT_EVENTS_KEY) if isinstance(payload, Mapping) else None
    if not isinstance(events, list):
        return ("", -1, 0)
    lines = []
    end_ms = 0
    for event in events:
        if not isinstance(event, Mapping):
            continue
        start = exact_count(event.get(TIMEDTEXT_START_KEY))
        duration = exact_count(event.get(TIMEDTEXT_DURATION_KEY))
        if start is not None:
            end_ms = max(end_ms, start + (duration or 0))
        segments = event.get(TIMEDTEXT_SEGMENTS_KEY)
        if not isinstance(segments, list):
            continue
        said = "".join(
            _text(segment.get(TIMEDTEXT_TEXT_KEY))
            for segment in segments
            if isinstance(segment, Mapping)
        )
        held = " ".join(said.split())
        if held:
            lines.append(held)
    return (chr(10).join(lines), len(lines), end_ms)


def operation_for(request: AdapterRequest) -> Tuple[str, str]:
    """The operation this call performs, and the argument it performs it on.

    A caller names the operation, because one route serves three. The name is a
    prefix off :data:`INNERTUBE_OPERATIONS` before the first colon and nothing
    else: a colon anywhere later in the text is text, so ``"ratio 16:9"`` is a
    search for those characters. Absent a name, the step's own shape decides —
    a step naming a target is hydrating one, a step naming only a query is
    searching — and nothing is inferred from the rest of the argument.

    The one thing a caller cannot express is a query whose own first word is
    ``search``, ``next`` or ``player`` followed immediately by a colon: that
    reads as the prefix, because the prefix is checked before the shape. The
    selector is a closed three-name list rather than a general escape, so
    stating the collision is the whole of the remedy.
    """

    named = request.target_ids[0] if request.target_ids else request.query
    kind, separator, argument = named.partition(":")
    if separator and kind in INNERTUBE_OPERATIONS:
        return (kind, argument)
    return (PLAYER_OPERATION if request.target_ids else SEARCH_OPERATION, named)


def _transcript_record(
    video_id, language, kind, text, cues, end_ms
):
    named = [
        (CAPTION_LANGUAGE_FIELD, language),
        (CAPTION_KIND_FIELD, kind or "published"),
        ("cue_count", str(cues)),
        ("duration_ms", str(end_ms)),
    ]
    return NativeRecord(
        canonical_content_kind=TRANSCRIPT_KIND,
        canonical_locator=transport.origin_locator(
            transport.YOUTUBE_INNERTUBE_ROUTE, "/watch?v=" + video_id
        ),
        # The video's own id: a transcript is a representation of that video,
        # which is what makes the two group by strong identity and never merge
        # — `representation_kind` partitions the key ahead of it.
        native_item_id=video_id,
        body=text,
        attributes=tuple(pair for pair in named if pair[1]),
        native_position=0,
    )


def _transcript_page(response, cursor):
    """Page two: one caption track, read at the address page one published."""

    asked = transcript_params(cursor)
    video_id = asked.get(CURSOR_VIDEO_FIELD, "")
    if response.status != 200:
        return build_native_page(
            TRANSCRIPT_DESCRIPTOR,
            (),
            observed_at=response.observed_at,
            native_order=TRANSCRIPT_NATIVE_ORDER,
            warnings=(
                "http status {0} from {1}".format(
                    response.status, TRANSCRIPT_DESCRIPTOR.route_id
                ),
            ),
            outcome="failed",
            loss=(HTTP_STATUS,),
        )
    try:
        payload = json.loads(response.body)
    except ValueError:
        return build_native_page(
            TRANSCRIPT_DESCRIPTOR,
            (),
            observed_at=response.observed_at,
            native_order=TRANSCRIPT_NATIVE_ORDER,
            warnings=(
                "{0} answered 200 with no json body: a signed caption address"
                " that has expired answers this way".format(TRANSCRIPT_OPERATION),
            ),
            outcome="failed",
            loss=(MALFORMED_JSON,),
        )
    text, cues, end_ms = transcript_text(payload)
    if cues < 0:
        return build_native_page(
            TRANSCRIPT_DESCRIPTOR,
            (),
            observed_at=response.observed_at,
            native_order=TRANSCRIPT_NATIVE_ORDER,
            warnings=(
                "{0} answered 200 with no {1} list: the timed-text payload this"
                " adapter reads has changed shape".format(
                    TRANSCRIPT_OPERATION, TIMEDTEXT_EVENTS_KEY
                ),
            ),
            outcome="failed",
            loss=(SCHEMA_DRIFT,),
        )
    if not text:
        return build_native_page(
            TRANSCRIPT_DESCRIPTOR,
            (),
            observed_at=response.observed_at,
            native_order=TRANSCRIPT_NATIVE_ORDER,
            warnings=(
                "{0} answered 200 with {1} cue(s) and no text in any of"
                " them".format(TRANSCRIPT_OPERATION, cues),
            ),
            outcome="empty",
        )
    return build_native_page(
        TRANSCRIPT_DESCRIPTOR,
        (
            _transcript_record(
                video_id,
                asked.get(CURSOR_LANGUAGE_FIELD, ""),
                asked.get(CURSOR_KIND_FIELD, ""),
                text,
                cues,
                end_ms,
            ),
        ),
        observed_at=response.observed_at,
        native_order=TRANSCRIPT_NATIVE_ORDER,
    )


def _with_continuation(page, response, cursor_out, extra_warning=""):
    """One player page carried forward, with what the next read needs."""

    return build_native_page(
        DESCRIPTOR,
        page.records,
        observed_at=response.observed_at,
        cursor_out=cursor_out,
        native_order=NATIVE_ORDER,
        warnings=page.warnings + ((extra_warning,) if extra_warning else ()),
        outcome=page.outcome,
        loss=page.loss,
    )


def _transcript_first_page(response, video_id, language):
    """Page one: the player answer, and the track the second page will read.

    The video's own record is what this page carries — a transcript read that
    stopped here still learned the title, the view count and which tracks
    exist — and the continuation is the chosen track's own address.
    """

    page = _page_from(response, PLAYER_OPERATION, video_id)
    if page.outcome != "ok":
        return page
    try:
        payload = json.loads(response.body)
    except ValueError:
        return page
    tracks = caption_tracks(payload if isinstance(payload, Mapping) else {})
    if not tracks:
        return _with_continuation(
            page,
            response,
            "",
            "{0} answered 200 listing no caption track for {1}: this client is"
            " served tracks where a video has them, so this is the video"
            " listing none rather than a payload withheld".format(
                PLAYER_OPERATION, video_id
            ),
        )
    track = chosen_track(tracks, language)
    if track is None:
        return _with_continuation(
            page,
            response,
            "",
            "{0} lists {1} caption track(s) for {2} and none in {3!r}; it"
            " lists {4}".format(
                PLAYER_OPERATION,
                len(tracks),
                video_id,
                language,
                ", ".join(_text(one.get(CAPTION_LANGUAGE_FIELD)) for one in tracks),
            ),
        )
    return _with_continuation(page, response, transcript_cursor(video_id, track))


def transcript_target(argument):
    """``<video id>[:<language>]`` — the id, and the track a caller asked for."""

    video_id, _, language = argument.partition(":")
    return (video_id.strip(), language.strip())


def fetch_native_page(carrier: transport.Transport, request: AdapterRequest) -> NativePage:
    """Read one InnerTube operation and return exactly one NativePage.

    Four operations over two routes. The transcript operation is the one that
    spans both: its first page asks `player` on the InnerTube route and its
    second reads the timed-text route at the address that answer named. That
    is why it is a discovery step — the core spends the continuation a page
    published, and a hydration step authorizes none.
    """

    operation, argument = operation_for(request)
    if operation == TRANSCRIPT_OPERATION:
        video_id, language = transcript_target(argument)
        if request.cursor:

            def read_track(response: transport.TransportResponse) -> NativePage:
                return _transcript_page(response, request.cursor)

            return fetch_one_page(
                TRANSCRIPT_DESCRIPTOR,
                carrier,
                params=transcript_params(request.cursor),
                parse=read_track,
                native_order=TRANSCRIPT_NATIVE_ORDER,
            )

        def read_player(response: transport.TransportResponse) -> NativePage:
            return _transcript_first_page(response, video_id, language)

        return fetch_one_page(
            DESCRIPTOR,
            carrier,
            params={
                "endpoint": PLAYER_OPERATION,
                "client_name": PLAYER_CLIENT_NAME,
                "client_version": PLAYER_CLIENT_VERSION,
                "video_id": video_id,
            },
            parse=read_player,
            native_order=NATIVE_ORDER,
        )

    params = {
        "endpoint": operation,
        # The player operation presents the client that is served caption
        # tracks; search and comments keep the web client whose key the route
        # carries and whose answers this module's parsers were built on.
        "client_name": PLAYER_CLIENT_NAME if operation == PLAYER_OPERATION else CLIENT_NAME,
        "client_version": (
            PLAYER_CLIENT_VERSION if operation == PLAYER_OPERATION else CLIENT_VERSION
        ),
    }
    if request.cursor:
        # A continuation replaces the argument in the body, which is the shape
        # the origin takes: the argument still names what the rows belong to.
        params["continuation"] = request.cursor
    elif operation == SEARCH_OPERATION:
        params["query"] = argument
    else:
        params["video_id"] = argument

    def parse(response: transport.TransportResponse) -> NativePage:
        return _page_from(response, operation, argument)

    return fetch_one_page(
        DESCRIPTOR, carrier, params=params, parse=parse, native_order=NATIVE_ORDER
    )
