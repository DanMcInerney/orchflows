"""K0 syndication: one generic RSS/Atom reader on one selected feed route.

Measured 2026-08-10 (findings.md §1): ``feeds/videos.xml?channel_id=`` answered
200 with 39 KB in 0.35 s — the cheapest read in the roster, and the only
RSS/Atom document the evidence records. That is the one route this adapter
declares.

**The roster row's "generic" is the parser, not the route.** Two syndication
vocabularies describe the same thing in different words — Atom says ``feed``,
``entry``, ``id``, ``published``; RSS 2.0 says ``rss``, ``item``, ``guid``,
``pubDate``, and dates them in a different grammar entirely — and a reader that
handled one would silently drop every document in the other. Both are read
here. Enclosures and transcript links are the rest of the row, and no route this
package declares is known to send either: what the fixtures prove is that the
parser reads them, not that this package fetches one. Adding a measured podcast
feed is a route constant and a second descriptor, never a caller-supplied
address.

**A generic reader stays generic.** The measured feed carries
``media:statistics views=`` in a vendor namespace, and this module does not read
it. Mining it would publish a count under a name this roster row does not name,
about a platform this adapter does not know it is reading, beside the adapter
that reads that platform's own API and reports the quantity from there. The
line is that this reader speaks the syndication vocabularies and no vendor's
extension of them, apart from the podcast transcript the row names.

**A syndication identity is recorded and never used to merge.** A ``guid`` is
unique inside its own feed and nowhere else, and nothing here can say which
identity space it belongs to. So the id travels — it is the row's "identity" —
and ``native_identity_namespace`` is left unstated, which is what makes
``normalize.strong_identity`` decline to fold two entries that happen to be
named the same thing. That is ``wrong_merge_law``'s safe direction: standing
alone costs a caller a duplicate, and folding costs it a fact.

The parser is :mod:`html.parser` rather than an XML reader, for the reason
every markup-reading adapter here uses it and one more: acquired text is
untrusted, and this parser expands no document-defined entity, so a feed cannot
ask it to allocate a gigabyte.
"""

from __future__ import annotations

import email.utils
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any, Dict, List, Tuple

from .. import transport
from . import (
    AdapterDescriptor,
    AdapterRequest,
    NativePage,
    NativeRecord,
    build_native_page,
    fetch_one_page,
)

DESCRIPTOR = AdapterDescriptor(
    adapter_id="rss_atom",
    adapter_version="1",
    access_class="K0",
    route_id=transport.YOUTUBE_CHANNEL_FEED_ROUTE,
    # The route's platform, which is a fact about the endpoint rather than
    # about the parser. A second measured feed arrives as a second descriptor
    # naming its own, under this same adapter id.
    platform="youtube",
    # Deliberately unstated. See the module docstring: an id out of a feed is
    # unique within that feed, and this adapter cannot qualify it.
    native_identity_namespace="",
    representation_kind="feed",
    operator_identity="youtube",
    # findings.md §1: 0.35 s per request. Nothing on this route was measured
    # refusing, so `burst` and `cooldown_ms` keep the protocol's conservative
    # defaults rather than a ceiling nobody observed.
    min_interval_ms=350,
    # A syndication entry carries no count of comments and no count of
    # replies. Declaring neither is a stated absence.
)

NATIVE_ORDER = "syndication_feed_order"
# What a generic reader knows it is holding: an entry in a feed. Whether the
# thing behind it is a video, an episode or an article is the publisher's
# business, and naming one would be a guess this adapter cannot support.
CONTENT_KIND = "feed_entry"

# The two vocabularies, spelled once each. `html.parser` lowercases every tag
# name, so every constant here is lowercase and a namespace prefix survives as
# part of the name.
ATOM_ROOT_TAG = "feed"
RSS_ROOT_TAG = "rss"
ROOT_TAGS = (ATOM_ROOT_TAG, RSS_ROOT_TAG)
ATOM_ITEM_TAG = "entry"
RSS_ITEM_TAG = "item"
ITEM_TAGS = (ATOM_ITEM_TAG, RSS_ITEM_TAG)

LINK_TAG = "link"
AUTHOR_TAG = "author"
NAME_TAG = "name"
ENCLOSURE_TAG = "enclosure"
TRANSCRIPT_LOCAL_NAME = "transcript"

HREF_ATTRIBUTE = "href"
URL_ATTRIBUTE = "url"
TYPE_ATTRIBUTE = "type"
REL_ATTRIBUTE = "rel"
ALTERNATE_REL = "alternate"

# Where each vocabulary states the same fact.
ATOM_ID_TAG = "id"
RSS_ID_TAG = "guid"
TITLE_TAG = "title"
ATOM_PUBLISHED_TAG = "published"
ATOM_UPDATED_TAG = "updated"
RSS_PUBLISHED_TAG = "pubdate"
# Where a resolved address is held while an item is being read. Not a tag:
# both vocabularies state the address somewhere else and this is the slot
# whichever one arrived lands in.
LOCATOR_FIELD = "locator"

# Text between tags, captured only inside an item. Every one of these also
# appears at feed level, where it describes the feed rather than an entry.
ITEM_TEXT_TAGS = (
    ATOM_ID_TAG,
    RSS_ID_TAG,
    TITLE_TAG,
    ATOM_PUBLISHED_TAG,
    ATOM_UPDATED_TAG,
    RSS_PUBLISHED_TAG,
    AUTHOR_TAG,
    LINK_TAG,
    NAME_TAG,
)
ITEM_KEYS = ITEM_TEXT_TAGS + (LOCATOR_FIELD,)

# The names an entry's media travels under. Each pair repeats in step — one
# `enclosure` and one `enclosure_type` per enclosure, in the feed's own order —
# so a caller reads them by position. A feed that declared a url and no type
# still contributes to both, with the type empty, because a pairing that
# silently slips by one is worse than an absence stated in its own slot.
ENCLOSURE_ATTRIBUTE = "enclosure"
ENCLOSURE_TYPE_ATTRIBUTE = "enclosure_type"
TRANSCRIPT_ATTRIBUTE = "transcript"
TRANSCRIPT_TYPE_ATTRIBUTE = "transcript_type"

# What an entry must state for its row to be complete. Enclosures and
# transcripts are absent from this list because most feeds publish neither, and
# marking every ordinary entry incomplete would make the mark meaningless.
IDENTITY_FIELD = "identity"
DATE_FIELD = "published"
ROSTER_FIELDS = (IDENTITY_FIELD, TITLE_TAG, LOCATOR_FIELD, DATE_FIELD)

RECORD_INSTANT_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
RFC_3339_FORMAT = "%Y-%m-%dT%H:%M:%S%z"

SCHEMA_DRIFT = "schema_drift"
HTTP_STATUS = "http_status"

# Declared here and produced nowhere in this module: a feed is a public
# document, and no status one answers with is a report that this package needed
# a credential it does not have.
AUTH_REQUIRED = "auth_required"


def local_name(tag: str) -> str:
    """One tag without its namespace prefix, which is the part that means something."""

    return tag.rsplit(":", 1)[-1]


class _SyndicationParser(HTMLParser):
    """Collect this document's root, its items, and the media hanging off them."""

    def __init__(self) -> None:
        HTMLParser.__init__(self, convert_charrefs=True)
        self.root = ""
        self.items: List[Dict[str, Any]] = []
        self._in_item = False
        self._in_author = False
        self._field = ""

    def handle_starttag(self, tag, attrs):
        if not self.root and tag in ROOT_TAGS:
            self.root = tag
            return
        if tag in ITEM_TAGS:
            item: Dict[str, Any] = dict.fromkeys(ITEM_KEYS, "")
            item[ENCLOSURE_ATTRIBUTE] = []
            item[TRANSCRIPT_ATTRIBUTE] = []
            self.items.append(item)
            self._in_item = True
            self._field = ""
            return
        if not self._in_item:
            return

        attributes = dict(attrs)
        item = self.items[-1]
        if local_name(tag) == TRANSCRIPT_LOCAL_NAME:
            self._add(item, TRANSCRIPT_ATTRIBUTE, attributes.get(URL_ATTRIBUTE), attributes)
            return
        if tag == ENCLOSURE_TAG:
            self._add(item, ENCLOSURE_ATTRIBUTE, attributes.get(URL_ATTRIBUTE), attributes)
            return
        if tag == LINK_TAG:
            # One tag, three jobs. Atom hangs enclosures and transcripts off a
            # `link` with a `rel`, and states an entry's own address as the
            # `alternate` one; RSS writes the address as text between tags,
            # which the data handler picks up because no `href` is set here.
            relation = attributes.get(REL_ATTRIBUTE) or ALTERNATE_REL
            href = attributes.get(HREF_ATTRIBUTE) or ""
            if relation == ENCLOSURE_TAG:
                self._add(item, ENCLOSURE_ATTRIBUTE, href, attributes)
            elif relation == TRANSCRIPT_LOCAL_NAME:
                self._add(item, TRANSCRIPT_ATTRIBUTE, href, attributes)
            elif relation == ALTERNATE_REL:
                if href:
                    item[LOCATOR_FIELD] = item[LOCATOR_FIELD] or href
                else:
                    self._field = LINK_TAG
            return
        if tag == AUTHOR_TAG:
            self._in_author = True
            self._field = AUTHOR_TAG
        elif tag == NAME_TAG and self._in_author:
            self._field = NAME_TAG
        elif tag in ITEM_TEXT_TAGS:
            self._field = tag

    def _add(self, item, name, url, attributes):
        """Record one media reference, url and declared type together or not at all."""

        if url:
            item[name].append((url, attributes.get(TYPE_ATTRIBUTE) or ""))

    def handle_endtag(self, tag):
        if tag in ITEM_TAGS:
            self._in_item = False
            self._in_author = False
            self._field = ""
        elif tag == AUTHOR_TAG:
            self._in_author = False
            self._field = ""
        elif tag == self._field:
            self._field = ""

    def handle_data(self, data):
        if self._field and self._in_item:
            self.items[-1][self._field] += data


def rfc_3339_to_utc_iso(stamped: str) -> str:
    """An Atom instant as the artifact's instant, or nothing."""

    text = stamped.strip()
    if not text:
        return ""
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        moment = datetime.strptime(text, RFC_3339_FORMAT)
    except ValueError:
        return ""
    return moment.astimezone(timezone.utc).strftime(RECORD_INSTANT_FORMAT)


def rfc_822_to_utc_iso(stamped: str) -> str:
    """An RSS ``pubDate`` as the artifact's instant, or nothing.

    RSS dates are RFC 822, which is a different grammar from Atom's and not one
    a format string can read. A stamp carrying no zone is refused rather than
    assumed: reading a local time as UTC would make the same document parse to
    two different instants on two machines.
    """

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


def entry_instant(item: Dict[str, Any]) -> str:
    """When this entry says it was published, in whichever grammar it said it.

    ``published`` before ``updated``: a feed that states both has said when the
    entry appeared and when it last changed, and a caller ordering by recency
    means the first. ``pubDate`` is RSS's word for the same fact.
    """

    return (
        rfc_3339_to_utc_iso(item[ATOM_PUBLISHED_TAG])
        or rfc_822_to_utc_iso(item[RSS_PUBLISHED_TAG])
        or rfc_3339_to_utc_iso(item[ATOM_UPDATED_TAG])
    )


def roster_row_of(item: Dict[str, Any]) -> Dict[str, str]:
    """One entry's roster row, in this adapter's own names."""

    return {
        # Atom's `id` and RSS's `guid` are one field with two spellings.
        IDENTITY_FIELD: (item[ATOM_ID_TAG] or item[RSS_ID_TAG]).strip(),
        TITLE_TAG: item[TITLE_TAG].strip(),
        # Atom states the address on a `link` attribute and RSS states it as
        # that tag's text; whichever arrived is the same fact.
        LOCATOR_FIELD: (item[LOCATOR_FIELD] or item[LINK_TAG]).strip(),
        # Atom nests the author's name; RSS writes the whole author line as
        # text. Neither is reshaped into the other.
        AUTHOR_TAG: (item[NAME_TAG] or item[AUTHOR_TAG]).strip(),
        DATE_FIELD: entry_instant(item),
    }


def _media_attributes(item: Dict[str, Any]) -> Tuple[Tuple[str, str], ...]:
    """Every enclosure and transcript this entry published, in its own order."""

    named: List[Tuple[str, str]] = []
    for name, type_name in (
        (ENCLOSURE_ATTRIBUTE, ENCLOSURE_TYPE_ATTRIBUTE),
        (TRANSCRIPT_ATTRIBUTE, TRANSCRIPT_TYPE_ATTRIBUTE),
    ):
        for url, media_type in item[name]:
            named.append((name, url))
            named.append((type_name, media_type))
    return tuple(named)


def _record_for(position: int, item: Dict[str, Any]) -> NativeRecord:
    roster = roster_row_of(item)
    missing = tuple(name for name in ROSTER_FIELDS if not roster[name])
    return NativeRecord(
        canonical_content_kind=CONTENT_KIND,
        canonical_locator=roster[LOCATOR_FIELD],
        native_item_id=roster[IDENTITY_FIELD],
        title=roster[TITLE_TAG],
        author=roster[AUTHOR_TAG],
        published_at=roster[DATE_FIELD],
        attributes=_media_attributes(item),
        native_position=position,
        loss=("field_omitted",) if missing else (),
    )


def _page(
    response: transport.TransportResponse,
    records: Tuple[NativeRecord, ...] = (),
    warnings: Tuple[str, ...] = (),
    outcome: str = "ok",
    loss: Tuple[str, ...] = (),
) -> NativePage:
    return build_native_page(
        DESCRIPTOR,
        records,
        observed_at=response.observed_at,
        native_order=NATIVE_ORDER,
        warnings=warnings,
        outcome=outcome,
        loss=loss,
    )


def _page_from(response: transport.TransportResponse) -> NativePage:
    """Turn one response the origin itself sent into exactly one page."""

    if response.status != 200:
        return _page(
            response,
            warnings=(
                "http status {0} from {1}".format(response.status, DESCRIPTOR.route_id),
            ),
            outcome="failed",
            loss=(HTTP_STATUS,),
        )

    parser = _SyndicationParser()
    parser.feed(response.body)
    parser.close()

    if not parser.root:
        return _page(
            response,
            warnings=(
                "route {0} answered 200 with a document rooted in neither <{1}>"
                " nor <{2}>: it is not a feed this adapter can read".format(
                    DESCRIPTOR.route_id, ATOM_ROOT_TAG, RSS_ROOT_TAG
                ),
            ),
            outcome="failed",
            loss=(SCHEMA_DRIFT,),
        )

    records = tuple(
        _record_for(position, item) for position, item in enumerate(parser.items)
    )
    if records:
        return _page(response, records=records)
    return _page(
        response,
        warnings=(
            "route {0} answered 200 with a <{1}> holding no <{2}>: this feed"
            " lists nothing".format(
                DESCRIPTOR.route_id,
                parser.root,
                ATOM_ITEM_TAG if parser.root == ATOM_ROOT_TAG else RSS_ITEM_TAG,
            ),
        ),
        outcome="empty",
    )


def fetch_native_page(carrier: transport.Transport, request: AdapterRequest) -> NativePage:
    """Read one feed once and return exactly one NativePage.

    A feed states no next page and none is derived: syndication publishes a
    window onto the most recent entries, and deciding there is more behind it
    is not something a document of this shape supports.
    """

    channel_id = request.target_ids[0] if request.target_ids else request.query
    return fetch_one_page(
        DESCRIPTOR,
        carrier,
        params={"channel_id": channel_id},
        parse=_page_from,
        native_order=NATIVE_ORDER,
    )
