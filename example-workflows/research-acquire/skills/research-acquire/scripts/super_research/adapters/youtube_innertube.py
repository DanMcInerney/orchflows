"""Keyless YouTube search, comments, player metadata, and transcripts.

Operation selection and the two-route transcript handoff sit at the bottom;
above them the platform's declared containers are parsed into native values,
rows, and pages.
"""

from __future__ import annotations

import json
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Mapping, Optional, Tuple, Dict, Sequence

from .. import transport, schema
from . import (
    AdapterRequest,
    NativePage,
    fetch_one_page,
    AdapterDescriptor,
    VolatileIdentifier,
    NativeRecord,
    build_native_page,
)


CLIENT_NAME = "WEB"
CLIENT_VERSION = "2.20260808.00.00"

# The client the transcript operation's player read presents, and the only
# read that presents it. Measured: `ANDROID` at this version
# answers playability `OK` with a populated caption track list, keyless,
# where `WEB` is served none. Measured: that same answer carries
# no `microformat` — a whole-body scan found no date field anywhere in it,
# on `IOS` and `ANDROID_VR` alike — while `WEB` still carries `publishDate`
# beside a complete `videoDetails`. So the `player` metadata operation
# presents the web client above, and this one exists for the caption listing
# alone.
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
    reply_count_metric="replyCount",
)
TRANSCRIPT_DESCRIPTOR = AdapterDescriptor(
    adapter_id="youtube_innertube",
    adapter_version="1",
    access_class="K1",
    route_id=transport.YOUTUBE_TIMEDTEXT_ROUTE,
    platform="youtube",
    native_identity_namespace="youtube",
    representation_kind="transcript",
    operator_identity="youtube",
    min_interval_ms=1400,
    page_size=1,
)
SURFACE_DESCRIPTORS = (DESCRIPTOR, TRANSCRIPT_DESCRIPTOR)

NATIVE_ORDER = "youtube_innertube_route_order"
TRANSCRIPT_NATIVE_ORDER = "youtube_timedtext_cue_order"
VIDEO_KIND = "video"
COMMENT_KIND = "comment"
TRANSCRIPT_KIND = "transcript"

SEARCH_OPERATION = "search"
NEXT_OPERATION = "next"
PLAYER_OPERATION = "player"
TRANSCRIPT_OPERATION = "transcript"
INNERTUBE_OPERATIONS = (
    SEARCH_OPERATION,
    NEXT_OPERATION,
    PLAYER_OPERATION,
    TRANSCRIPT_OPERATION,
)

SEARCH_RESULTS_PATH = (
    "contents",
    "twoColumnSearchResultsRenderer",
    "primaryContents",
    "sectionListRenderer",
    "contents",
)
WATCH_NEXT_PATH = (
    "contents",
    "twoColumnWatchNextResults",
    "results",
    "results",
    "contents",
)
RECEIVED_ENDPOINTS_KEY = "onResponseReceivedEndpoints"
RECEIVED_COMMANDS_KEY = "onResponseReceivedCommands"
CONTINUATION_ACTIONS = (
    "appendContinuationItemsAction",
    "reloadContinuationItemsCommand",
)
CONTINUATION_ITEMS_KEY = "continuationItems"
CONTINUATION_ITEM_KEY = "continuationItemRenderer"
CONTINUATION_TOKEN_PATH = (
    "continuationEndpoint",
    "continuationCommand",
    "token",
)
ITEM_SECTION_KEY = "itemSectionRenderer"
SECTION_IDENTIFIER_KEY = "sectionIdentifier"
COMMENT_SECTION_IDENTIFIER = "comment-item-section"
CONTENTS_KEY = "contents"
VIDEO_RENDERER_KEY = "videoRenderer"
COMMENT_THREAD_KEY = "commentThreadRenderer"
COMMENT_PATH = ("comment", "commentRenderer")

COMMENT_VIEW_MODEL_PATH = ("commentViewModel", "commentViewModel")
COMMENT_KEY_FIELD = "commentKey"
ENTITY_MUTATIONS_PATH = ("frameworkUpdates", "entityBatchUpdate", "mutations")
ENTITY_KEY_FIELD = "entityKey"
ENTITY_PAYLOAD_KEY = "payload"
COMMENT_ENTITY_KEY = "commentEntityPayload"
ENTITY_AUTHOR_KEY = "author"
ENTITY_AUTHOR_NAME_KEY = "displayName"
ENTITY_PROPERTIES_KEY = "properties"
ENTITY_CONTENT_KEY = "content"
ENTITY_CONTENT_PATH = (ENTITY_CONTENT_KEY, ENTITY_CONTENT_KEY)
ENTITY_TOOLBAR_KEY = "toolbar"
PUBLISHED_TIME_KEY = "publishedTime"
LIKE_COUNT_NOTLIKED_KEY = "likeCountNotliked"
COMMENT_ENTITY_TEXT_FACTS = (LIKE_COUNT_NOTLIKED_KEY, PUBLISHED_TIME_KEY)

PLAYABILITY_KEY = "playabilityStatus"
PLAYABILITY_STATUS_KEY = "status"
PLAYABILITY_REASON_KEY = "reason"
PLAYABLE_STATUS = "OK"
VIDEO_DETAILS_KEY = "videoDetails"
MICROFORMAT_PATH = ("microformat", "playerMicroformatRenderer")
PUBLISH_DATE_KEY = "publishDate"
EMBED_URL_PATH = ("embed", "iframeUrl")
ATTESTED_PLAYABILITY = ("UNPLAYABLE", "ERROR")
CREDENTIAL_PLAYABILITY = ("LOGIN_REQUIRED", "AGE_VERIFICATION_REQUIRED")

CAPTION_TRACKS_PATH = (
    "captions",
    "playerCaptionsTracklistRenderer",
    "captionTracks",
)
CAPTION_LANGUAGE_FIELD = "languageCode"
CAPTION_KIND_FIELD = "kind"
CAPTION_ASR_KIND = "asr"

TIMEDTEXT_FORMAT_PARAM = "fmt"
TIMEDTEXT_FORMAT = "json3"
TIMEDTEXT_EVENTS_KEY = "events"
TIMEDTEXT_SEGMENTS_KEY = "segs"
TIMEDTEXT_TEXT_KEY = "utf8"
TIMEDTEXT_START_KEY = "tStartMs"
TIMEDTEXT_DURATION_KEY = "dDurationMs"

VIDEO_ID_KEY = "videoId"
TITLE_KEY = "title"
OWNER_TEXT_KEY = "ownerText"
AUTHOR_KEY = "author"
DESCRIPTION_KEY = "shortDescription"
COMMENT_ID_KEY = "commentId"
AUTHOR_TEXT_KEY = "authorText"
CONTENT_TEXT_KEY = "contentText"
NAVIGATION_URL_PATH = (
    "navigationEndpoint",
    "commandMetadata",
    "webCommandMetadata",
    "url",
)
RUNS_KEY = "runs"
SIMPLE_TEXT_KEY = "simpleText"
TEXT_KEY = "text"

VIEW_COUNT_METRIC = "viewCount"
REPLY_COUNT_METRIC = "replyCount"
VIEW_COUNT_TEXT_KEY = "viewCountText"
PUBLISHED_TIME_TEXT_KEY = "publishedTimeText"
VOTE_COUNT_TEXT_KEY = "voteCount"
SEARCH_TEXT_FACTS = (VIEW_COUNT_TEXT_KEY, PUBLISHED_TIME_TEXT_KEY)
COMMENT_TEXT_FACTS = (VOTE_COUNT_TEXT_KEY, PUBLISHED_TIME_TEXT_KEY)

SEARCH_ROW_KEYS = (TITLE_KEY, OWNER_TEXT_KEY)
PLAYER_ROW_KEYS = (TITLE_KEY, VIEW_COUNT_METRIC, PUBLISH_DATE_KEY)
COMMENT_ROW_KEYS = (COMMENT_ID_KEY, CONTENT_TEXT_KEY, AUTHOR_TEXT_KEY)
COMMENT_ENTITY_ROW_KEYS = (
    COMMENT_ID_KEY,
    ENTITY_CONTENT_KEY,
    ENTITY_AUTHOR_NAME_KEY,
)

ROUTE_DATE_FORMAT = "%Y-%m-%d"
ROUTE_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S%z"
RECORD_INSTANT_FORMAT = schema.INSTANT_FORMAT
DATE_PRECISION_ONLY = "date_precision_only"

STALE_IDENTIFIER_STATUS = 400
AUTHORIZATION_STATUSES = (401, 403)
STALE_IDENTIFIER = "stale_identifier"
ATTESTATION_REQUIRED = "attestation_required"
AUTH_REQUIRED = "auth_required"
WITHHELD = "withheld"
HTTP_STATUS = "http_status"
MALFORMED_JSON = "malformed_json"
SCHEMA_DRIFT = "schema_drift"

CURSOR_VIDEO_FIELD = "sr_video"
CURSOR_LANGUAGE_FIELD = "sr_lang"
CURSOR_KIND_FIELD = "sr_kind"


def dig(payload: Any, path: Sequence[str]) -> Any:
    """Follow a declared mapping path, returning ``None`` at the first gap."""

    found = payload
    for key in path:
        if not isinstance(found, Mapping):
            return None
        found = found.get(key)
    return found


def route_text(value: Any) -> str:
    """Return one simple label or its formatting runs joined back together."""

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
    """Return an exact integer the route published, never a formatted label."""

    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def route_date_to_utc_iso(published: Any) -> Tuple[str, bool]:
    """Return a route date as UTC ISO text and whether it had day precision."""

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
    """Return caption tracks in the order the answer listed them."""

    tracks = dig(payload, CAPTION_TRACKS_PATH)
    if not isinstance(tracks, list):
        return ()
    return tuple(track for track in tracks if isinstance(track, Mapping))


def captions_withheld(payload: Mapping[str, Any]) -> bool:
    """Whether this answer listed no caption track for the presented client."""

    return not caption_tracks(payload)


def chosen_track(
    tracks: Tuple[Mapping[str, Any], ...], language: str
) -> Optional[Mapping[str, Any]]:
    """Choose the requested language, otherwise preferring a published track."""

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
    carried = []
    for key in keys:
        text = route_text(source.get(key))
        if text:
            carried.append((key, text))
    return tuple(carried)


def _missing(row: Mapping[str, Any], keys: Sequence[str]) -> Tuple[str, ...]:
    return tuple(key for key in keys if row.get(key) is None or row.get(key) == "")


def continuation_in(entry: Any) -> str:
    """Return the token from one continuation row, if present."""

    if not isinstance(entry, Mapping):
        return ""
    holder = entry.get(CONTINUATION_ITEM_KEY)
    if not isinstance(holder, Mapping):
        return ""
    return _text(dig(holder, CONTINUATION_TOKEN_PATH))


def search_sections(payload: Any) -> Optional[list]:
    """Return search sections from either first-page or continuation shape."""

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
    """Return identified video renderers and their continuation token."""

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
            if isinstance(renderer, Mapping) and _text(renderer.get(VIDEO_ID_KEY)):
                found.append(renderer)
    return (tuple(found), cursor)


def comment_items(payload: Any) -> Optional[Sequence[Any]]:
    """Return comment rows from continuation or first-page watch shapes."""

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
    if not isinstance(sections, list):
        return None
    for section in sections:
        item = section.get(ITEM_SECTION_KEY) if isinstance(section, Mapping) else None
        if not isinstance(item, Mapping):
            continue
        if item.get(SECTION_IDENTIFIER_KEY) != COMMENT_SECTION_IDENTIFIER:
            continue
        rows = item.get(CONTENTS_KEY)
        return rows if isinstance(rows, list) else None
    return ()


def comment_entities(payload: Any) -> Optional[Dict[str, Mapping[str, Any]]]:
    """Return comment entities keyed by the identifiers view models address."""

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
    carried = []
    for source, key in (
        (toolbar, LIKE_COUNT_NOTLIKED_KEY),
        (properties, PUBLISHED_TIME_KEY),
    ):
        value = source.get(key)
        if isinstance(value, str) and value:
            carried.append((key, value))
    return tuple(carried)


def _view_model_record(
    position: int,
    entity: Optional[Mapping[str, Any]],
    video_id: str,
) -> NativeRecord:
    entity = entity if isinstance(entity, Mapping) else {}
    author = entity.get(ENTITY_AUTHOR_KEY)
    author = author if isinstance(author, Mapping) else {}
    properties = entity.get(ENTITY_PROPERTIES_KEY)
    properties = properties if isinstance(properties, Mapping) else {}
    toolbar = entity.get(ENTITY_TOOLBAR_KEY)
    toolbar = toolbar if isinstance(toolbar, Mapping) else {}
    row = {
        COMMENT_ID_KEY: _text(properties.get(COMMENT_ID_KEY)),
        ENTITY_CONTENT_KEY: _text(dig(properties, ENTITY_CONTENT_PATH)),
        ENTITY_AUTHOR_NAME_KEY: _text(author.get(ENTITY_AUTHOR_NAME_KEY)),
    }
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
    row = {
        VIDEO_ID_KEY: _text(renderer.get(VIDEO_ID_KEY)),
        TITLE_KEY: route_text(renderer.get(TITLE_KEY)),
        OWNER_TEXT_KEY: route_text(renderer.get(OWNER_TEXT_KEY)),
    }
    return NativeRecord(
        canonical_content_kind=VIDEO_KIND,
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


def transcript_params(cursor: str) -> Dict[str, str]:
    """Return a transcript continuation as timed-text request parameters."""

    return dict(urllib.parse.parse_qsl(cursor, keep_blank_values=True))


def transcript_text(payload: Any) -> Tuple[str, int, int]:
    """Return json3 track text, cue count, and ending millisecond."""

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


def _transcript_record(
    video_id: str, language: str, kind: str, text: str, cues: int, end_ms: int
) -> NativeRecord:
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
        native_item_id=video_id,
        body=text,
        attributes=tuple(pair for pair in named if pair[1]),
        native_position=0,
    )


def _transcript_page(response: transport.TransportResponse, cursor: str):
    """Parse page two: one caption track at the address page one published."""

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


def _with_continuation(page, response, cursor_out: str, extra_warning: str = ""):
    """Carry one player page forward with the transcript continuation."""

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
        SCHEMA_DRIFT,
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
        else (
            "{0} answered 200 with a results section holding no video".format(
                SEARCH_OPERATION
            ),
        ),
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
    if cursor:
        warning = (
            "{0} answered 200 with the {1} carrying a continuation token and no"
            " thread".format(NEXT_OPERATION, COMMENT_SECTION_IDENTIFIER)
        )
    else:
        warning = "{0} answered 200 and the video lists no comment".format(
            NEXT_OPERATION
        )
    return _answered(response, (), "empty", cursor_out=cursor, warnings=(warning,))


def _playability_loss(status: str) -> str:
    if status in ATTESTED_PLAYABILITY:
        return ATTESTATION_REQUIRED
    if status in CREDENTIAL_PLAYABILITY:
        return AUTH_REQUIRED
    return WITHHELD


def _playability_warning(playability: Mapping[str, Any]) -> str:
    status = _text(playability.get(PLAYABILITY_STATUS_KEY))
    said = "{0} answered 200 with playability {1} ({2}).".format(
        PLAYER_OPERATION,
        status or "unstated",
        _text(playability.get(PLAYABILITY_REASON_KEY)) or "no reason given",
    )
    if status in ATTESTED_PLAYABILITY:
        return said + (
            " The probes recorded this status across five clients and three"
            " videos and names the cause as PoToken/BotGuard attestation. The"
            " origin's own reason is quoted above: this status is also what it"
            " answers for a video it no longer holds, and the payload beside it"
            " tells the two apart — a held"
            " video answers with its videoDetails, an unheld id without them."
        )
    if status in CREDENTIAL_PLAYABILITY:
        return said + (
            " That is the origin refusing this read on its own account, not an"
            " attestation this package could perform: no credential makes a"
            " keyless route credentialed, and none is supplied."
        )
    return said + (
        " The probes did not record this status, so nothing here names a"
        " cause: the origin declined to serve the payload and the reason it"
        " gave is quoted above."
    )


def _player_page(response: transport.TransportResponse, payload: Any) -> NativePage:
    playability = payload.get(PLAYABILITY_KEY) if isinstance(payload, Mapping) else None
    if not isinstance(playability, Mapping):
        return _drifted(response, PLAYER_OPERATION, "stated no " + PLAYABILITY_KEY)
    status = _text(playability.get(PLAYABILITY_STATUS_KEY))
    details = payload.get(VIDEO_DETAILS_KEY)
    if not isinstance(details, Mapping):
        # Measured, both sides on the web client: a held video
        # answers its non-`OK` playability *with* `videoDetails` beside it,
        # and an id the origin does not hold answers without them, under a
        # byte-identical reason string. The details are the one part of the
        # answer that tells the two apart, so a refusal is only a refusal of
        # the whole read when it carried none.
        if status != PLAYABLE_STATUS:
            return _failed(
                response, _playability_loss(status), _playability_warning(playability)
            )
        return _drifted(response, PLAYER_OPERATION, "stated no " + VIDEO_DETAILS_KEY)
    withheld = captions_withheld(payload)
    loss: Tuple[str, ...] = ()
    warnings: Tuple[str, ...] = ()
    if status != PLAYABLE_STATUS:
        # The origin served the row and refused the playback beside it. That
        # is the web client's standing keyless posture, and the loss is what
        # keeps this answer tellable apart from a healthy one rather than the
        # row being thrown away with the playback.
        loss = (_playability_loss(status),)
        warnings = (_playability_warning(playability),)
    if withheld and ATTESTATION_REQUIRED not in loss:
        loss = loss + (ATTESTATION_REQUIRED,)
    if withheld:
        warnings = warnings + (
            "{0} answered 200 listing no caption track at {1}. Measured:"
            " the web-family clients are served no track on any"
            " video — the tracks sit behind an attestation this package does"
            " not perform — while the Android client the transcript operation"
            " presents is served them where a video has them. This is not a"
            " statement that the video has none.".format(
                PLAYER_OPERATION, ".".join(CAPTION_TRACKS_PATH)
            ),
        )
    return _answered(
        response,
        (_player_record(payload, withheld),),
        "ok",
        warnings=warnings,
        loss=loss,
    )


def _page_from(
    response: transport.TransportResponse, operation: str, argument: str
) -> NativePage:
    """Turn one response the origin itself sent into exactly one page."""

    if response.status == STALE_IDENTIFIER_STATUS:
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


# The facade alone owns the signed caption address. The field is read once,
# where the first transcript page turns it into the continuation page two
# spends; no parser or second caller can independently reach that URL.
CAPTION_FETCH_FIELD = "baseUrl"


def transcript_cursor(video_id: str, track: Mapping[str, Any]) -> str:
    """Build the continuation for one caption track's signed address."""

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


def operation_for(request: AdapterRequest) -> Tuple[str, str]:
    """Return the explicitly named operation or the step-shape default."""

    named = request.target_ids[0] if request.target_ids else request.query
    kind, separator, argument = named.partition(":")
    if separator and kind in INNERTUBE_OPERATIONS:
        return (kind, argument)
    return (PLAYER_OPERATION if request.target_ids else SEARCH_OPERATION, named)


def _transcript_first_page(
    response: transport.TransportResponse, video_id: str, language: str
) -> NativePage:
    """Parse the player page and publish the selected caption continuation."""

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


def transcript_target(argument: str) -> Tuple[str, str]:
    """Return ``<video id>[:<language>]`` as its two named values."""

    video_id, _, language = argument.partition(":")
    return (video_id.strip(), language.strip())


def _instant_seconds(stamped: str) -> Optional[int]:
    """One manifest instant as whole UTC seconds, or nothing unparseable.

    A local parser rather than a shared one, matching another
    origin-adjacent adapter module's own tiny parser of the same name: each
    owns its own rather than reaching into `ordering`, which stays a
    core-only import.
    """

    if not stamped:
        return None
    try:
        moment = datetime.strptime(stamped, RECORD_INSTANT_FORMAT).replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return int(moment.timestamp())


# Upload-date filter values, measured live against `search` with a
# query returning results old enough to show each boundary: every returned
# `publishedTimeText` stayed inside the named span (hour: minutes-scale;
# today: up to "1 day ago"; week: up to "7 days ago"; month: up to "1 month
# ago"; year: up to "11 months ago"), against an unfiltered baseline whose
# oldest result was nine years old. The value is base64 protobuf this
# module never decodes or builds — it is the origin's own opaque term, spent
# verbatim, the same way a cursor is.
_UPLOAD_DATE_SPANS = (
    ("EgIIAQ==", 3600),
    ("EgIIAg==", 86400),
    ("EgIIAw==", 7 * 86400),
    ("EgIIBA==", 30 * 86400),
    ("EgIIBQ==", 365 * 86400),
)


def origin_upload_date_filter(window_start: str, window_end: str) -> str:
    """The `search` filter value that still reaches `window_start`, or nothing.

    A pure function of the step's two instants, imitating the shape's
    exemplar's three properties: it lives beside this adapter, it returns
    the origin's own term, and it returns nothing when there is no bound to
    state. Like a comparable adapter's own bucket, this filter is a span
    measured back from *now* rather than from an explicit endpoint — there
    is no origin term for "before a date" at all, only "within the last
    span" — so `window_end` plays no part in the answer, and a window whose
    oldest edge is more than a year back gets no filter at all: the ladder's
    widest rung is "This year", and sending nothing already reaches further
    than that.
    """

    del window_end  # Documented above: the filter is a span back from "now".
    start_seconds = _instant_seconds(window_start)
    if start_seconds is None:
        return ""
    now_seconds = _instant_seconds(transport.utc_now_iso())
    if now_seconds is None:
        return ""
    age = now_seconds - start_seconds
    for value, span in _UPLOAD_DATE_SPANS:
        if age <= span:
            return value
    return ""


def fetch_native_page(
    carrier: transport.Transport, request: AdapterRequest
) -> NativePage:
    """Read one InnerTube operation and return exactly one native page."""

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

    # Every metadata operation presents the web client, `player` included.
    # Measured: the app clients' player answers — `ANDROID` at the
    # pinned version and a newer one, `IOS`, `ANDROID_VR` — stopped carrying
    # `microformat`, and a whole-body scan found no date field anywhere in
    # them, while `WEB` still carries `publishDate` beside a complete
    # `videoDetails`. What `WEB` is not served is captions, which is why the
    # transcript branch above alone presents the Android client.
    params = {
        "endpoint": operation,
        "client_name": CLIENT_NAME,
        "client_version": CLIENT_VERSION,
    }
    if request.cursor:
        params["continuation"] = request.cursor
    elif operation == SEARCH_OPERATION:
        params["query"] = argument
        upload_date_filter = origin_upload_date_filter(request.window_start, request.window_end)
        if upload_date_filter:
            params["params"] = upload_date_filter
    else:
        params["video_id"] = argument

    def parse(response: transport.TransportResponse) -> NativePage:
        return _page_from(response, operation, argument)

    return fetch_one_page(
        DESCRIPTOR, carrier, params=params, parse=parse, native_order=NATIVE_ORDER
    )
