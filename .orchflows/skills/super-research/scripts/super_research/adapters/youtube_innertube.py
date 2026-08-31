"""Keyless YouTube search, comments, player metadata, and transcripts.

The facade owns operation selection and the two-route transcript handoff. The
private support modules parse the platform's declared containers into native
values, rows, and pages while this module keeps the public adapter seam stable.
"""

from __future__ import annotations

import json
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Mapping, Optional, Tuple

from .. import transport
from . import AdapterRequest, NativePage, fetch_one_page
from ._support.youtube_innertube_contract import *  # noqa: F403
from ._support import youtube_innertube_pages as _pages
from ._support.youtube_innertube_pages import (
    _answered,
    _comments_page,
    _drifted,
    _failed,
    _page_from,
    _playability_loss,
    _playability_warning,
    _player_page,
    _search_page,
)
from ._support.youtube_innertube_rows import (
    _comment_record,
    _entity_facts,
    _player_record,
    _search_record,
    _view_model_record,
)
from ._support.youtube_innertube_transcript import (
    _transcript_page,
    _transcript_record,
    _with_continuation,
    transcript_params,
    transcript_text,
)
from ._support.youtube_innertube_values import (
    _missing,
    _named_facts,
    _text,
    caption_tracks,
    captions_withheld,
    chosen_track,
    comment_entities,
    comment_items,
    continuation_in,
    dig,
    exact_count,
    route_date_to_utc_iso,
    route_text,
    search_rows,
    search_sections,
)


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


# Upload-date filter values, measured live 2026-08-31 against `search` with a
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

    _pages.DESCRIPTOR = DESCRIPTOR
    _pages._search_record = _search_record
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
        "client_name": PLAYER_CLIENT_NAME if operation == PLAYER_OPERATION else CLIENT_NAME,
        "client_version": (
            PLAYER_CLIENT_VERSION if operation == PLAYER_OPERATION else CLIENT_VERSION
        ),
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
