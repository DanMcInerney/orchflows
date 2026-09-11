"""Native-record construction for YouTube InnerTube rows."""

from typing import Any, Mapping, Optional, Tuple

from ... import transport
from .. import NativeRecord
from .youtube_innertube_contract import (
    ATTESTATION_REQUIRED,
    AUTHOR_KEY,
    AUTHOR_TEXT_KEY,
    COMMENT_ENTITY_ROW_KEYS,
    COMMENT_ID_KEY,
    COMMENT_KIND,
    COMMENT_ROW_KEYS,
    COMMENT_TEXT_FACTS,
    CONTENT_TEXT_KEY,
    DATE_PRECISION_ONLY,
    DESCRIPTION_KEY,
    DESCRIPTOR,
    EMBED_URL_PATH,
    ENTITY_AUTHOR_KEY,
    ENTITY_AUTHOR_NAME_KEY,
    ENTITY_CONTENT_KEY,
    ENTITY_CONTENT_PATH,
    ENTITY_PROPERTIES_KEY,
    ENTITY_TOOLBAR_KEY,
    LIKE_COUNT_NOTLIKED_KEY,
    MICROFORMAT_PATH,
    NAVIGATION_URL_PATH,
    OWNER_TEXT_KEY,
    PLAYER_ROW_KEYS,
    PUBLISHED_TIME_KEY,
    PUBLISH_DATE_KEY,
    REPLY_COUNT_METRIC,
    SEARCH_ROW_KEYS,
    SEARCH_TEXT_FACTS,
    TITLE_KEY,
    VIDEO_DETAILS_KEY,
    VIDEO_ID_KEY,
    VIDEO_KIND,
    VIEW_COUNT_METRIC,
)
from .youtube_innertube_values import (
    _missing,
    _named_facts,
    _text,
    dig,
    exact_count,
    route_date_to_utc_iso,
    route_text,
)


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
