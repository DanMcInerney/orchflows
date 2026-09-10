"""Native-page parsing for YouTube search, comments, and player answers."""

import json
from typing import Any, Mapping, Tuple

from ... import transport
from .. import NativePage, NativeRecord, build_native_page
from .youtube_innertube_contract import (
    ATTESTATION_REQUIRED,
    ATTESTED_PLAYABILITY,
    AUTHORIZATION_STATUSES,
    AUTH_REQUIRED,
    CAPTION_TRACKS_PATH,
    CLIENT_NAME,
    CLIENT_VERSION,
    CLIENT_VERSION_RECOVERY,
    COMMENT_KEY_FIELD,
    COMMENT_PATH,
    COMMENT_SECTION_IDENTIFIER,
    COMMENT_THREAD_KEY,
    COMMENT_VIEW_MODEL_PATH,
    CREDENTIAL_PLAYABILITY,
    DESCRIPTOR,
    ENTITY_MUTATIONS_PATH,
    NATIVE_ORDER,
    NEXT_OPERATION,
    PLAYABILITY_KEY,
    PLAYABILITY_REASON_KEY,
    PLAYABILITY_STATUS_KEY,
    PLAYABLE_STATUS,
    PLAYER_OPERATION,
    SCHEMA_DRIFT,
    SEARCH_OPERATION,
    SEARCH_RESULTS_PATH,
    STALE_IDENTIFIER,
    STALE_IDENTIFIER_STATUS,
    VIDEO_DETAILS_KEY,
    WITHHELD,
)
from .youtube_innertube_rows import (
    _comment_record,
    _player_record,
    _search_record,
    _view_model_record,
)
from .youtube_innertube_values import (
    _text,
    captions_withheld,
    comment_entities,
    comment_items,
    continuation_in,
    dig,
    search_rows,
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
            " The 2026-08-10 probes recorded this status across five clients and three"
            " videos and names the cause as PoToken/BotGuard attestation. The"
            " origin's own reason is quoted above: this status is also what it"
            " answers for a video it no longer holds, and the 2026-08-31"
            " measurement tells the two apart by the payload beside it — a held"
            " video answers with its videoDetails, an unheld id without them."
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
        return _drifted(response, PLAYER_OPERATION, "stated no " + PLAYABILITY_KEY)
    status = _text(playability.get(PLAYABILITY_STATUS_KEY))
    details = payload.get(VIDEO_DETAILS_KEY)
    if not isinstance(details, Mapping):
        # Measured 2026-08-31, both sides on the web client: a held video
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
        # is the web client's standing keyless posture (measured 2026-08-31),
        # and the loss is what keeps this answer tellable apart from a healthy
        # one rather than the row being thrown away with the playback.
        loss = (_playability_loss(status),)
        warnings = (_playability_warning(playability),)
    if withheld and ATTESTATION_REQUIRED not in loss:
        loss = loss + (ATTESTATION_REQUIRED,)
    if withheld:
        warnings = warnings + (
            "{0} answered 200 listing no caption track at {1}. Measured"
            " 2026-08-31: the web-family clients are served no track on any"
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
