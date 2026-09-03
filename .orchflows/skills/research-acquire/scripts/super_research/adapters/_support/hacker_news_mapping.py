"""Private record mapping for Hacker News payloads."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List, Mapping, Optional, Sequence, Tuple

from .. import NativeRecord
from .hacker_news_config import (
    AUTHOR_KEY,
    BY_KEY,
    CHILDREN_KEY,
    COMMENT_SEARCH_OPERATION,
    COMMENT_TEXT_KEY,
    COMMENT_TYPE,
    CREATED_AT_I_KEY,
    CREATED_AT_KEY,
    DEFAULT_HIT_ROW_KEYS,
    DEFAULT_ITEM_ROW_KEYS,
    DEFAULT_TREE_ROW_KEYS,
    DEPTH_ATTRIBUTE,
    DESCENDANTS_METRIC,
    DESCRIPTOR,
    FILTER_SEPARATOR,
    HITS_KEY,
    HITS_PER_PAGE_PARAM,
    HIT_ROW_KEYS,
    HN_ITEM_ORIGIN,
    HN_ITEM_PATH,
    HN_OPERATIONS,
    HTTP_STATUS,
    ITEM_ID_KEY,
    ITEM_OPERATION,
    ITEM_ROW_KEYS,
    ITEM_TREE_DESCRIPTOR,
    ITEM_TYPE_KEY,
    ITEM_TYPES,
    KIDS_KEY,
    MALFORMED_JSON,
    NATIVE_ORDERS,
    NUMERIC_FILTERS_PARAM,
    NUM_COMMENTS_METRIC,
    OBJECT_ID_KEY,
    PAGE_COUNT_KEY,
    PAGE_KEY,
    PARENT_ID_KEY,
    PARENT_KEY,
    POINTS_METRIC,
    RECORD_INSTANT_FORMAT,
    ROUTE_INSTANT_FORMAT,
    SCHEMA_DRIFT,
    SCORE_METRIC,
    SEARCH_BY_DATE_OPERATION,
    SEARCH_DESCRIPTOR,
    SEARCH_ENDPOINTS,
    SEARCH_OPERATION,
    SEARCH_PAGE_SIZE,
    STORY_ID_KEY,
    STORY_TEXT_KEY,
    SURFACE_DESCRIPTORS,
    TAGS_KEY,
    TEXT_KEY,
    TEXT_TYPES,
    TIME_KEY,
    TITLE_KEY,
    TREE_OPERATION,
    TREE_ROW_KEYS,
    TYPO_TOLERANCE_OFF,
    TYPO_TOLERANCE_PARAM,
    URL_KEY,
    WINDOW_END_FILTER,
    WINDOW_START_FILTER,
)

def item_locator(item_id: str) -> str:
    """One item's address on HN's own site, or nothing without an id."""

    return HN_ITEM_ORIGIN + HN_ITEM_PATH + item_id if item_id else ""


def _text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def exact_count(value: Any) -> Optional[int]:
    """One count a surface published as an exact number, or nothing at all.

    A bool is not a count and a string is not one either: both surfaces publish
    their counts as json numbers, so anything else is a field this adapter was
    not given rather than one it can recover.
    """

    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def id_text(value: Any) -> str:
    """One HN id as its decimal spelling, which is the only form a record holds.

    Firebase publishes an id as a json number and Algolia publishes the same id
    as a string, so one of the two has to be written the other's way for a
    search hit and an item read to name the same thing. Nothing is rounded,
    formatted, or made here: an identifier's decimal digits are the identifier.
    """

    if isinstance(value, bool):
        return ""
    if isinstance(value, int):
        return str(value)
    return value if isinstance(value, str) else ""


def route_instant_to_utc_iso(created_at: Any) -> str:
    """Algolia's stamp as the artifact's instant, or nothing.

    Milliseconds and a trailing ``Z`` are the shape this index writes.
    Anything else is a missing time rather than an approximated one.
    """

    if not isinstance(created_at, str) or not created_at.strip():
        return ""
    text = created_at.strip()
    if text.endswith("Z"):
        text = text[:-1]
    text = text.split(".")[0]
    try:
        moment = datetime.strptime(text, ROUTE_INSTANT_FORMAT)
    except ValueError:
        return ""
    return moment.replace(tzinfo=timezone.utc).strftime(RECORD_INSTANT_FORMAT)


def epoch_to_utc_iso(seconds: Any) -> str:
    """Firebase's stamp as the artifact's instant, or nothing.

    Epoch seconds are an exact instant, so this loses no precision and states
    none it was not given: a value that is not a whole number of seconds is a
    missing time, and so is one no clock can represent. A payload that moved
    must arrive as a typed answer rather than as an exception — an adapter that
    raised would cost the core the one page it is owed.
    """

    if isinstance(seconds, bool) or not isinstance(seconds, int):
        return ""
    try:
        moment = datetime.fromtimestamp(seconds, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return ""
    return moment.strftime(RECORD_INSTANT_FORMAT)


def instant_to_epoch_text(instant: str) -> str:
    """One manifest instant as the epoch seconds the search index filters on, or nothing.

    The other direction of :func:`epoch_to_utc_iso`, for the one place this
    module sends a time rather than reads one. A bound this function cannot
    read is a bound not sent — the core's own window filter still holds on
    every row that comes back — rather than a bound sent wrong, which would
    narrow the index's answer to a range nobody asked for.
    """

    if not isinstance(instant, str) or not instant.strip():
        return ""
    try:
        moment = datetime.strptime(instant.strip(), RECORD_INSTANT_FORMAT)
    except ValueError:
        return ""
    return str(int(moment.replace(tzinfo=timezone.utc).timestamp()))


def window_filters(window_start: str, window_end: str) -> str:
    """A caller's window in Algolia's own `numericFilters` syntax, or nothing.

    Either bound alone is a filter; both together are two, comma-joined, on the
    same field. Rows are never dropped here on either: the index applies what
    it is sent and the core counts what falls outside.
    """

    bounds = []
    start = instant_to_epoch_text(window_start)
    if start:
        bounds.append(WINDOW_START_FILTER + start)
    end = instant_to_epoch_text(window_end)
    if end:
        bounds.append(WINDOW_END_FILTER + end)
    return FILTER_SEPARATOR.join(bounds)


def _missing(row: Mapping[str, Any], keys: Sequence[str]) -> Tuple[str, ...]:
    """Which of this row's declared fields the payload did not report.

    Absence, never falsehood: a story nobody has voted on reports zero points,
    and zero is a count. Marking it omitted would erase the one distinction
    `field_omitted` exists to make.
    """

    return tuple(key for key in keys if row.get(key) is None or row.get(key) == "")


def _engagement(pairs: Sequence[Tuple[str, Any]]) -> Tuple[Tuple[str, int], ...]:
    counted = []
    for name, value in pairs:
        exact = exact_count(value)
        if exact is not None:
            counted.append((name, exact))
    return tuple(counted)


def hit_kind(hit: Mapping[str, Any]) -> str:
    """The item type this index row states, or nothing when it states none.

    Algolia lists a row's type among its own `_tags`, beside tags for the
    author and the story it belongs to, so the first tag naming an item type is
    the row's kind. The tag is read rather than guessed at from the fields
    present: a row is a comment because HN says so, not because this module
    recognized a shape with a `comment_text` in it.
    """

    tags = hit.get(TAGS_KEY)
    for tag in tags if isinstance(tags, list) else ():
        if tag in ITEM_TYPES:
            return tag
    return ""


def _hit_record(position: int, hit: Mapping[str, Any], kind: str) -> NativeRecord:
    """One index row as Algolia listed it."""

    item_id = id_text(hit.get(OBJECT_ID_KEY))
    row = {
        OBJECT_ID_KEY: item_id,
        TITLE_KEY: _text(hit.get(TITLE_KEY)),
        AUTHOR_KEY: _text(hit.get(AUTHOR_KEY)),
        CREATED_AT_KEY: route_instant_to_utc_iso(hit.get(CREATED_AT_KEY)),
        COMMENT_TEXT_KEY: _text(hit.get(COMMENT_TEXT_KEY)),
    }
    # A comment's own text, or a story's own text where it has one. A comment
    # row also carries the title of the story it sits under, and that is
    # deliberately read nowhere here: it is a fact about the story, and a
    # comment titled with its story's title is a record that claims to be one.
    body = row[COMMENT_TEXT_KEY] if kind in TEXT_TYPES else _text(hit.get(STORY_TEXT_KEY))
    named: List[Tuple[str, str]] = []
    link = _text(hit.get(URL_KEY))
    if link:
        named.append((URL_KEY, link))
    story_id = id_text(hit.get(STORY_ID_KEY))
    if story_id:
        # The root this row sits under, which `native_parent_id` does not mean:
        # a reply's parent is the comment it answers.
        named.append((STORY_ID_KEY, story_id))
    return NativeRecord(
        canonical_content_kind=kind,
        canonical_locator=item_locator(item_id),
        native_item_id=item_id,
        native_parent_id=id_text(hit.get(PARENT_ID_KEY)),
        title=row[TITLE_KEY],
        body=body,
        author=row[AUTHOR_KEY],
        published_at=row[CREATED_AT_KEY],
        engagement=_engagement(
            ((POINTS_METRIC, hit.get(POINTS_METRIC)),
             (NUM_COMMENTS_METRIC, hit.get(NUM_COMMENTS_METRIC)))
        ),
        attributes=tuple(named),
        native_position=position,
        loss=("field_omitted",)
        if _missing(row, HIT_ROW_KEYS.get(kind, DEFAULT_HIT_ROW_KEYS))
        else (),
    )


def _item_record(item: Mapping[str, Any], kind: str) -> NativeRecord:
    """One item as Firebase holds it, with the ids of what hangs off it."""

    item_id = id_text(item.get(ITEM_ID_KEY))
    row = {
        ITEM_ID_KEY: item_id,
        ITEM_TYPE_KEY: kind,
        BY_KEY: _text(item.get(BY_KEY)),
        TIME_KEY: epoch_to_utc_iso(item.get(TIME_KEY)),
        TITLE_KEY: _text(item.get(TITLE_KEY)),
        TEXT_KEY: _text(item.get(TEXT_KEY)),
    }
    named: List[Tuple[str, str]] = []
    link = _text(item.get(URL_KEY))
    if link:
        named.append((URL_KEY, link))
    kids = item.get(KIDS_KEY)
    for kid in kids if isinstance(kids, list) else ():
        # The tree, one id at a time, in the order HN listed them. They travel
        # as ids rather than as a walked tree because walking one here would
        # make a bounded call a crawl: the core spends these as its next calls.
        kid_id = id_text(kid)
        if kid_id:
            named.append((KIDS_KEY, kid_id))
    return NativeRecord(
        canonical_content_kind=kind,
        canonical_locator=item_locator(item_id),
        native_item_id=item_id,
        native_parent_id=id_text(item.get(PARENT_KEY)),
        title=row[TITLE_KEY],
        body=row[TEXT_KEY],
        author=row[BY_KEY],
        published_at=row[TIME_KEY],
        # A comment carries neither of these and a story carries both. An
        # absent count is left absent rather than reported as a zero nobody
        # published.
        engagement=_engagement(
            ((SCORE_METRIC, item.get(SCORE_METRIC)),
             (DESCENDANTS_METRIC, item.get(DESCENDANTS_METRIC)))
        ),
        attributes=tuple(named),
        native_position=0,
        loss=("field_omitted",)
        if _missing(row, ITEM_ROW_KEYS.get(kind, DEFAULT_ITEM_ROW_KEYS))
        else (),
    )


def _tree_record(
    position: int, node: Mapping[str, Any], kind: str, depth: int
) -> NativeRecord:
    """One node of the tree as Algolia listed it, and how deep it sat."""

    item_id = id_text(node.get(ITEM_ID_KEY))
    row = {
        ITEM_ID_KEY: item_id,
        ITEM_TYPE_KEY: kind,
        AUTHOR_KEY: _text(node.get(AUTHOR_KEY)),
        CREATED_AT_KEY: route_instant_to_utc_iso(node.get(CREATED_AT_KEY)),
        TITLE_KEY: _text(node.get(TITLE_KEY)),
        TEXT_KEY: _text(node.get(TEXT_KEY)),
    }
    named: List[Tuple[str, str]] = []
    link = _text(node.get(URL_KEY))
    if link:
        named.append((URL_KEY, link))
    story_id = id_text(node.get(STORY_ID_KEY))
    if story_id:
        # The root this node sits under, which `native_parent_id` does not
        # mean: a reply's parent is the comment it answers.
        named.append((STORY_ID_KEY, story_id))
    named.append((DEPTH_ATTRIBUTE, str(depth)))
    return NativeRecord(
        canonical_content_kind=kind,
        canonical_locator=item_locator(item_id),
        native_item_id=item_id,
        native_parent_id=id_text(node.get(PARENT_ID_KEY)),
        title=row[TITLE_KEY],
        body=row[TEXT_KEY],
        author=row[AUTHOR_KEY],
        published_at=row[CREATED_AT_KEY],
        # This node's own points and only its own: the tree states `null` on
        # every comment, and an absent count is left absent rather than filled
        # from the story above it.
        engagement=_engagement(((POINTS_METRIC, node.get(POINTS_METRIC)),)),
        attributes=tuple(named),
        native_position=position,
        loss=("field_omitted",)
        if _missing(row, TREE_ROW_KEYS.get(kind, DEFAULT_TREE_ROW_KEYS))
        else (),
    )


def _flatten_tree(
    root: Mapping[str, Any]
) -> Tuple[Tuple[NativeRecord, ...], int]:
    """Every node of one tree, depth first, root first, children in listed order.

    Also how many nodes were passed over: a node stating no type this adapter
    knows, or no id, is not a row — it can be neither typed nor addressed —
    and it is counted so the page can say the tree held more than it read.
    Its children are still walked, because a hole in a thread is not the end
    of it. Iterative rather than recursive on purpose: a thread is as deep as
    HN let it get, and a payload must never turn into a recursion error.
    """

    records: List[NativeRecord] = []
    untyped = 0
    pending: List[Tuple[Any, int]] = [(root, 0)]
    while pending:
        node, depth = pending.pop()
        if not isinstance(node, Mapping):
            untyped += 1
            continue
        kind = _text(node.get(ITEM_TYPE_KEY))
        if kind in ITEM_TYPES and id_text(node.get(ITEM_ID_KEY)):
            records.append(_tree_record(len(records), node, kind, depth))
        else:
            untyped += 1
        children = node.get(CHILDREN_KEY)
        if isinstance(children, list):
            # Pushed in reverse so the first-listed child is the next popped:
            # the order HN listed them is the order the records hold.
            for child in reversed(children):
                pending.append((child, depth + 1))
    return (tuple(records), untyped)
