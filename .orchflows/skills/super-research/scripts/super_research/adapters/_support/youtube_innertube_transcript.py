"""Timed-text parsing for the YouTube InnerTube transcript surface."""

import json
import urllib.parse
from typing import Any, Dict, Mapping, Tuple

from ... import transport
from .. import NativeRecord, build_native_page
from .youtube_innertube_contract import (
    CAPTION_KIND_FIELD,
    CAPTION_LANGUAGE_FIELD,
    CURSOR_KIND_FIELD,
    CURSOR_LANGUAGE_FIELD,
    CURSOR_VIDEO_FIELD,
    DESCRIPTOR,
    HTTP_STATUS,
    MALFORMED_JSON,
    NATIVE_ORDER,
    SCHEMA_DRIFT,
    TIMEDTEXT_DURATION_KEY,
    TIMEDTEXT_EVENTS_KEY,
    TIMEDTEXT_SEGMENTS_KEY,
    TIMEDTEXT_START_KEY,
    TIMEDTEXT_TEXT_KEY,
    TRANSCRIPT_DESCRIPTOR,
    TRANSCRIPT_KIND,
    TRANSCRIPT_NATIVE_ORDER,
    TRANSCRIPT_OPERATION,
)
from .youtube_innertube_values import _text, exact_count


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
