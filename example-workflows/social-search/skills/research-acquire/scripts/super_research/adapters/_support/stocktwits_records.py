"""Stocktwits message and symbol record extraction."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List, Mapping, Optional, Sequence, Tuple

from ... import schema
from .. import NativeRecord

# Where a message and a symbol page live. It is Stocktwits' own site and not
# either route's origin, so the transport seam cannot resolve it against the
# API host. Measured 2026-08-17:
# `stocktwits.com/<username>/message/<id>` and `stocktwits.com/symbol/<SYM>`.
STOCKTWITS_SITE_ORIGIN = "https://stocktwits.com"
MESSAGE_PATH = "/message/"
SYMBOL_PATH = "/symbol/"

POST_KIND = "post"
SYMBOL_KIND = "symbol"

ID_KEY = "id"
BODY_KEY = "body"
CREATED_AT_KEY = "created_at"
USER_KEY = "user"
USERNAME_KEY = "username"
SOURCE_KEY = "source"
TITLE_KEY = "title"
SYMBOLS_KEY = "symbols"
SYMBOL_KEY = "symbol"
EXCHANGE_KEY = "exchange"
ENTITIES_KEY = "entities"
SENTIMENT_KEY = "sentiment"
BASIC_KEY = "basic"
LIKES_KEY = "likes"
TOTAL_KEY = "total"
CONVERSATION_KEY = "conversation"
PARENT_KEY = "parent"
PARENT_MESSAGE_ID_KEY = "parent_message_id"
IN_REPLY_TO_MESSAGE_ID_KEY = "in_reply_to_message_id"
LIKES_METRIC = "likes"
WATCHLIST_COUNT_METRIC = "watchlist_count"

MESSAGE_ROW_KEYS = (ID_KEY, BODY_KEY, CREATED_AT_KEY, USERNAME_KEY)
SYMBOL_ROW_KEYS = (SYMBOL_KEY, TITLE_KEY)

ROUTE_INSTANT_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
RECORD_INSTANT_FORMAT = schema.INSTANT_FORMAT
FIELD_OMITTED = "field_omitted"


def message_locator(username: str, message_id: str) -> str:
    """One message's address on Stocktwits' own site, or nothing without both parts."""

    if not username or not message_id:
        return ""
    return STOCKTWITS_SITE_ORIGIN + "/" + username + MESSAGE_PATH + message_id


def symbol_locator(symbol: str) -> str:
    """One symbol's stream page on Stocktwits' own site, or nothing without a symbol."""

    return STOCKTWITS_SITE_ORIGIN + SYMBOL_PATH + symbol if symbol else ""


def _text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def exact_count(value: Any) -> Optional[int]:
    """One count Stocktwits published as an exact number, or nothing at all."""

    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def id_text(value: Any) -> str:
    """One Stocktwits id as its decimal spelling, which is the only form a record holds."""

    if isinstance(value, bool):
        return ""
    if isinstance(value, int):
        return str(value)
    return value if isinstance(value, str) else ""


def route_instant_to_utc_iso(created_at: Any) -> str:
    """The stream's stamp as the artifact's instant, or nothing."""

    if not isinstance(created_at, str) or not created_at.strip():
        return ""
    try:
        moment = datetime.strptime(created_at.strip(), ROUTE_INSTANT_FORMAT)
    except ValueError:
        return ""
    return moment.replace(tzinfo=timezone.utc).strftime(RECORD_INSTANT_FORMAT)


def _missing(row: Mapping[str, Any], keys: Sequence[str]) -> Tuple[str, ...]:
    """Which of this row's declared fields the payload did not report."""

    return tuple(key for key in keys if row.get(key) is None or row.get(key) == "")


def _engagement(pairs: Sequence[Tuple[str, Any]]) -> Tuple[Tuple[str, int], ...]:
    counted = []
    for name, value in pairs:
        exact = exact_count(value)
        if exact is not None:
            counted.append((name, exact))
    return tuple(counted)


def _nested(payload: Mapping[str, Any], *keys: str) -> Any:
    """One value under a key path, or None the moment the path leaves a mapping."""

    held: Any = payload
    for key in keys:
        if not isinstance(held, Mapping):
            return None
        held = held.get(key)
    return held


def reply_parent_of(message: Mapping[str, Any]) -> Tuple[str, str]:
    """The message this one answers, and the root of the thread it sits in."""

    conversation = message.get(CONVERSATION_KEY)
    if not isinstance(conversation, Mapping) or conversation.get(PARENT_KEY) is True:
        return ("", "")
    root = id_text(conversation.get(PARENT_MESSAGE_ID_KEY))
    answered = id_text(conversation.get(IN_REPLY_TO_MESSAGE_ID_KEY)) or root
    return (answered, root)


def _message_record(position: int, message: Mapping[str, Any], symbol: str) -> NativeRecord:
    """One message as the stream listed it."""

    message_id = id_text(message.get(ID_KEY))
    username = _text(_nested(message, USER_KEY, USERNAME_KEY))
    row = {
        ID_KEY: message_id,
        BODY_KEY: _text(message.get(BODY_KEY)),
        CREATED_AT_KEY: route_instant_to_utc_iso(message.get(CREATED_AT_KEY)),
        USERNAME_KEY: username,
    }
    answered, root = reply_parent_of(message)
    named: List[Tuple[str, str]] = []
    sentiment = _text(_nested(message, ENTITIES_KEY, SENTIMENT_KEY, BASIC_KEY))
    if sentiment:
        named.append((SENTIMENT_KEY, sentiment))
    symbols = message.get(SYMBOLS_KEY)
    for tagged in symbols if isinstance(symbols, list) else ():
        ticker = _text(tagged.get(SYMBOL_KEY)) if isinstance(tagged, Mapping) else ""
        if ticker:
            named.append((SYMBOL_KEY, ticker))
    source = _text(_nested(message, SOURCE_KEY, TITLE_KEY))
    if source:
        named.append((SOURCE_KEY, source))
    if root:
        named.append((PARENT_MESSAGE_ID_KEY, root))
    return NativeRecord(
        canonical_content_kind=POST_KIND,
        canonical_locator=message_locator(username, message_id),
        native_item_id=message_id,
        native_parent_id=answered,
        body=row[BODY_KEY],
        author=username,
        community=symbol,
        published_at=row[CREATED_AT_KEY],
        engagement=_engagement(((LIKES_METRIC, _nested(message, LIKES_KEY, TOTAL_KEY)),)),
        attributes=tuple(named),
        native_position=position,
        loss=(FIELD_OMITTED,) if _missing(row, MESSAGE_ROW_KEYS) else (),
    )


def _symbol_record(position: int, result: Mapping[str, Any]) -> NativeRecord:
    """One symbol as the search listed it."""

    row = {
        SYMBOL_KEY: _text(result.get(SYMBOL_KEY)),
        TITLE_KEY: _text(result.get(TITLE_KEY)),
    }
    exchange = _text(result.get(EXCHANGE_KEY))
    return NativeRecord(
        canonical_content_kind=SYMBOL_KIND,
        canonical_locator=symbol_locator(row[SYMBOL_KEY]),
        native_item_id=row[SYMBOL_KEY],
        title=row[TITLE_KEY],
        engagement=_engagement(
            ((WATCHLIST_COUNT_METRIC, result.get(WATCHLIST_COUNT_METRIC)),)
        ),
        attributes=((EXCHANGE_KEY, exchange),) if exchange else (),
        native_position=position,
        loss=(FIELD_OMITTED,) if _missing(row, SYMBOL_ROW_KEYS) else (),
    )
