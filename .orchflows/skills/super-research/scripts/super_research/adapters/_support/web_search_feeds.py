"""Private RSS parsing and parameter support for :mod:`web_search`."""

from __future__ import annotations

import email.utils
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Dict, List, Mapping, Optional, Tuple

from ... import transport
from .. import AdapterDescriptor, AdapterRequest, NativePage, NativeRecord, build_native_page

RSS_ROOT_TAG = "rss"
CHANNEL_TAG = "channel"
ITEM_TAG = "item"
TITLE_TAG = "title"
LINK_TAG = "link"
DESCRIPTION_TAG = "description"
PUBDATE_TAG = "pubdate"
SOURCE_TAG = "source"
SOURCE_URL_ATTRIBUTE = "url"
SOURCE_URL_FIELD = "source_url"
ITEM_TEXT_TAGS = (TITLE_TAG, LINK_TAG, DESCRIPTION_TAG, PUBDATE_TAG, SOURCE_TAG)
ITEM_FIELDS = ITEM_TEXT_TAGS + (SOURCE_URL_FIELD,)

SOURCE_ATTRIBUTE = "source"
SOURCE_URL_ATTRIBUTE_NAME = "source_url"
BING_NEWS_REDIRECT_PATH = "/news/apiclick.aspx"
BING_NEWS_REDIRECT_TARGET_FIELD = "url"

FORMAT_PARAM = "format"
RSS_FORMAT = "rss"
QUERY_PARAM = "q"
BING_OFFSET_PARAM = "first"
BING_FIRST_OFFSET = 1
GOOGLE_LOCALE_PARAMS = (("hl", "en-US"), ("gl", "US"), ("ceid", "US:en"))
GOOGLE_WHEN_OPERATOR = "when:"
GOOGLE_WHEN_UNIT = "d"
SECONDS_PER_DAY = 86400
RECORD_INSTANT_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


@dataclass(frozen=True)
class FeedConfig:
    """Facade-owned names and descriptors needed to interpret feed rows."""

    surfaces: Mapping[str, AdapterDescriptor]
    native_orders: Mapping[str, str]
    bing_operation: str
    bing_news_operation: str
    content_kind: str
    unknown_publication_time: str
    field_omitted: str
    schema_drift: str
    http_status: str


def local_name(tag: str) -> str:
    """One tag without its namespace prefix."""

    return tag.rsplit(":", 1)[-1]


class _RssIndexParser(HTMLParser):
    """Collect one RSS answer's root, channel, and item fields."""

    def __init__(self) -> None:
        HTMLParser.__init__(self, convert_charrefs=True)
        self.root = ""
        self.channels = 0
        self.items: List[Dict[str, str]] = []
        self._in_item = False
        self._field = ""

    def handle_starttag(self, tag, attrs):
        if not self.root and tag == RSS_ROOT_TAG:
            self.root = tag
            return
        if tag == CHANNEL_TAG:
            self.channels += 1
            return
        if tag == ITEM_TAG:
            self.items.append(dict.fromkeys(ITEM_FIELDS, ""))
            self._in_item = True
            self._field = ""
            return
        if not self._in_item:
            return
        name = local_name(tag)
        if name in ITEM_TEXT_TAGS:
            self._field = name
            if name == SOURCE_TAG:
                url = dict(attrs).get(SOURCE_URL_ATTRIBUTE) or ""
                if url:
                    self.items[-1][SOURCE_URL_FIELD] = url

    def handle_endtag(self, tag):
        if tag == ITEM_TAG:
            self._in_item = False
            self._field = ""
        elif self._in_item and local_name(tag) == self._field:
            self._field = ""

    def handle_data(self, data):
        if self._in_item and self._field:
            self.items[-1][self._field] += data


class _TextOnlyParser(HTMLParser):
    """Keep the text of a fragment and drop its tags."""

    def __init__(self) -> None:
        HTMLParser.__init__(self, convert_charrefs=True)
        self.parts: List[str] = []

    def handle_data(self, data):
        self.parts.append(data)


def snippet_text(fragment: str) -> str:
    """Strip markup and fold whitespace in one feed description."""

    parser = _TextOnlyParser()
    parser.feed(fragment)
    parser.close()
    return " ".join("".join(parser.parts).split())


def rfc_822_to_utc_iso(stamped: str) -> str:
    """Return an RSS date as a UTC artifact instant, or nothing."""

    text = stamped.strip()
    if not text:
        return ""
    try:
        moment = email.utils.parsedate_to_datetime(text)
    except (TypeError, ValueError, OverflowError):
        return ""
    if moment is None or moment.tzinfo is None:
        return ""
    return moment.astimezone(timezone.utc).strftime(RECORD_INSTANT_FORMAT)


def unwrap_bing_news_url(link: str) -> str:
    """Return the publisher address behind Bing News's redirect wrapper."""

    parts = urllib.parse.urlsplit(link)
    if parts.path.lower() == BING_NEWS_REDIRECT_PATH:
        targets = urllib.parse.parse_qs(parts.query).get(BING_NEWS_REDIRECT_TARGET_FIELD, [])
        if targets:
            return targets[0]
    return link


def feed_locator(config: FeedConfig, operation: str, link: str) -> str:
    """Return the address represented by one feed hit."""

    held = link.strip()
    if operation == config.bing_news_operation:
        return unwrap_bing_news_url(held)
    return held


def _declared_fields(config: FeedConfig, operation: str) -> Tuple[str, ...]:
    base = (TITLE_TAG, LINK_TAG, DESCRIPTION_TAG, PUBDATE_TAG)
    if operation == config.bing_operation:
        return base
    if operation == config.bing_news_operation:
        return base + (SOURCE_TAG,)
    return base + (SOURCE_TAG, SOURCE_URL_FIELD)


def feed_record(
    config: FeedConfig, operation: str, position: int, item: Dict[str, str]
) -> NativeRecord:
    """Build one native record from the fields the feed listed."""

    descriptor = config.surfaces[operation]
    row = {
        TITLE_TAG: item[TITLE_TAG].strip(),
        LINK_TAG: feed_locator(config, operation, item[LINK_TAG]),
        DESCRIPTION_TAG: snippet_text(item[DESCRIPTION_TAG]),
        PUBDATE_TAG: rfc_822_to_utc_iso(item[PUBDATE_TAG]),
        SOURCE_TAG: item[SOURCE_TAG].strip(),
        SOURCE_URL_FIELD: item[SOURCE_URL_FIELD].strip(),
    }
    loss: Tuple[str, ...] = descriptor.standing_loss
    if not row[PUBDATE_TAG]:
        loss = loss + (config.unknown_publication_time,)
    if any(not row[name] for name in _declared_fields(config, operation)):
        loss = loss + (config.field_omitted,)
    named: List[Tuple[str, str]] = []
    if row[SOURCE_TAG]:
        named.append((SOURCE_ATTRIBUTE, row[SOURCE_TAG]))
    if row[SOURCE_URL_FIELD]:
        named.append((SOURCE_URL_ATTRIBUTE_NAME, row[SOURCE_URL_FIELD]))
    return NativeRecord(
        canonical_content_kind=config.content_kind,
        canonical_locator=row[LINK_TAG],
        title=row[TITLE_TAG],
        body=row[DESCRIPTION_TAG],
        published_at=row[PUBDATE_TAG],
        attributes=tuple(named),
        native_position=position,
        loss=loss,
    )


def feed_answered(
    config: FeedConfig,
    operation: str,
    response: transport.TransportResponse,
    records: Tuple[NativeRecord, ...] = (),
    outcome: str = "ok",
    cursor_out: str = "",
    warnings: Tuple[str, ...] = (),
    loss: Tuple[str, ...] = (),
) -> NativePage:
    return build_native_page(
        config.surfaces[operation],
        records,
        observed_at=response.observed_at,
        cursor_out=cursor_out,
        native_order=config.native_orders[operation],
        warnings=warnings,
        outcome=outcome,
        loss=loss,
    )


def next_bing_offset(cursor: str, listed: int, page_size: int) -> str:
    """Return Bing's next ``first=`` offset when a full page was listed."""

    if listed < page_size:
        return ""
    try:
        offset = int(cursor) if cursor else BING_FIRST_OFFSET
    except ValueError:
        return ""
    return str(offset + page_size)


def feed_page_from(
    config: FeedConfig,
    operation: str,
    response: transport.TransportResponse,
    cursor: str,
) -> NativePage:
    """Turn one RSS answer the origin sent into exactly one page."""

    descriptor = config.surfaces[operation]
    if response.status != 200:
        return feed_answered(
            config,
            operation,
            response,
            outcome="failed",
            warnings=(
                "http status {0} from {1}".format(response.status, descriptor.route_id),
            ),
            loss=(config.http_status,),
        )

    parser = _RssIndexParser()
    parser.feed(response.body)
    parser.close()
    if not parser.root or not parser.channels:
        return feed_answered(
            config,
            operation,
            response,
            outcome="failed",
            warnings=(
                "route {0} answered 200 with a document carrying no <{1}> {2}: the"
                " feed this adapter reads has changed shape".format(
                    descriptor.route_id,
                    RSS_ROOT_TAG if not parser.root else CHANNEL_TAG,
                    "root" if not parser.root else "container",
                ),
            ),
            loss=(config.schema_drift,),
        )

    records = tuple(
        feed_record(config, operation, position, item)
        for position, item in enumerate(parser.items)
        if feed_locator(config, operation, item[LINK_TAG])
    )
    if not records:
        return feed_answered(
            config,
            operation,
            response,
            outcome="empty",
            warnings=(
                "route {0} answered 200 with a <{1}> holding no <{2}>: the index"
                " matched nothing".format(descriptor.route_id, CHANNEL_TAG, ITEM_TAG),
            )
            if not parser.items
            else (
                "route {0} answered 200 with {1} <{2}>(s) and no readable <{3}>: the"
                " index listed nothing this adapter can address".format(
                    descriptor.route_id, len(parser.items), ITEM_TAG, LINK_TAG
                ),
            ),
        )
    return feed_answered(
        config,
        operation,
        response,
        records=records,
        cursor_out=next_bing_offset(cursor, len(parser.items), descriptor.page_size)
        if operation == config.bing_operation
        else "",
    )


def instant_moment(stamped: str) -> Optional[datetime]:
    """Return one manifest instant as a moment, or ``None``."""

    try:
        return datetime.strptime(stamped, RECORD_INSTANT_FORMAT).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def google_when_days(window_start: str, window_end: str) -> int:
    """Return the whole days Google's relative ``when:`` should cover."""

    start = instant_moment(window_start) if window_start else None
    if start is None:
        return 0
    end = instant_moment(window_end) if window_end else instant_moment(transport.utc_now_iso())
    if end is None:
        return 0
    seconds = (end - start).total_seconds()
    days = int(seconds // SECONDS_PER_DAY) + (1 if seconds % SECONDS_PER_DAY else 0)
    return max(1, days)


def feed_params(
    config: FeedConfig, operation: str, query: str, request: AdapterRequest
) -> Dict[str, str]:
    """Return the origin parameters for one feed surface."""

    if operation == config.bing_operation:
        return {QUERY_PARAM: query, FORMAT_PARAM: RSS_FORMAT, BING_OFFSET_PARAM: request.cursor}
    if operation == config.bing_news_operation:
        return {QUERY_PARAM: query, FORMAT_PARAM: RSS_FORMAT}
    days = google_when_days(request.window_start, request.window_end)
    if days:
        query = query + " " + GOOGLE_WHEN_OPERATOR + str(days) + GOOGLE_WHEN_UNIT
    params = {QUERY_PARAM: query}
    params.update(GOOGLE_LOCALE_PARAMS)
    return params
