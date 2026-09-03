"""Value and container parsing for YouTube InnerTube payloads."""

from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

from .youtube_innertube_contract import (
    CAPTION_ASR_KIND,
    CAPTION_KIND_FIELD,
    CAPTION_LANGUAGE_FIELD,
    CAPTION_TRACKS_PATH,
    COMMENT_ENTITY_KEY,
    COMMENT_SECTION_IDENTIFIER,
    CONTENTS_KEY,
    CONTINUATION_ACTIONS,
    CONTINUATION_ITEM_KEY,
    CONTINUATION_ITEMS_KEY,
    CONTINUATION_TOKEN_PATH,
    ENTITY_KEY_FIELD,
    ENTITY_MUTATIONS_PATH,
    ENTITY_PAYLOAD_KEY,
    ITEM_SECTION_KEY,
    RECEIVED_COMMANDS_KEY,
    RECEIVED_ENDPOINTS_KEY,
    RECORD_INSTANT_FORMAT,
    ROUTE_DATE_FORMAT,
    ROUTE_DATETIME_FORMAT,
    RUNS_KEY,
    SEARCH_RESULTS_PATH,
    SECTION_IDENTIFIER_KEY,
    SIMPLE_TEXT_KEY,
    TEXT_KEY,
    VIDEO_ID_KEY,
    VIDEO_RENDERER_KEY,
    WATCH_NEXT_PATH,
)


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
