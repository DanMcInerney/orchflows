"""Read a supplied RSS/Atom feed or a YouTube channel's feed through transport.

Feeds describe a publisher-selected slice, not a searchable archive. Publication
and modification times remain separate; feed-local IDs never merge across feeds.
"""

from __future__ import annotations

import email.utils
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import parse_qs, urljoin, urlsplit
from xml.etree import ElementTree as ET

from .. import schema, transport
from . import AdapterDescriptor, AdapterRequest, NativePage, NativeRecord, build_native_page, fetch_one_page, open_read_descriptor


DESCRIPTOR = AdapterDescriptor(
    adapter_id="rss_atom", adapter_version="2", access_class="K0",
    route_id=transport.YOUTUBE_CHANNEL_FEED_ROUTE, platform="youtube",
    native_identity_namespace="", representation_kind="feed",
    operator_identity="youtube", min_interval_ms=350,
)
# The HTTP route owns the budget; a feed is another interpretation of its body.
FEED_URL_DESCRIPTOR = open_read_descriptor("rss_atom", "feed", "2")
SURFACE_DESCRIPTORS = (DESCRIPTOR, FEED_URL_DESCRIPTOR)
NATIVE_ORDER = "syndication_feed_order"
CONTENT_KIND = "feed_entry"
ENCLOSURE_ATTRIBUTE = "enclosure"
ENCLOSURE_TYPE_ATTRIBUTE = "enclosure_type"
TRANSCRIPT_ATTRIBUTE = "transcript"
TRANSCRIPT_TYPE_ATTRIBUTE = "transcript_type"
AUTH_REQUIRED = "auth_required"
XML_BASE = "{http://www.w3.org/XML/1998/namespace}base"
ATOM_NAMESPACE = "http://www.w3.org/2005/Atom"
MAX_BODY_CHARACTERS = 40000
FEED_COVERAGE = "A feed lists a publisher-selected slice; no archive pagination or complete date-window coverage is implied."


def local_name(tag):
    return tag.rsplit("}", 1)[-1].lower()


def child(element, name):
    return next((part for part in element if local_name(part.tag) == name), None)


def text(element):
    return "" if element is None else "".join(element.itertext()).strip()


class _MarkupText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.hidden += 1
        elif tag == "br":
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.hidden:
            self.hidden -= 1
        elif tag in ("p", "div", "li", "br"):
            self.parts.append(" ")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def prose(element, html=False):
    raw = text(element)
    if element is not None and element.get("type") == "xhtml":
        raw = " ".join(element.itertext())
    if element is not None and (html or element.get("type") == "html"):
        parser = _MarkupText()
        parser.feed(raw)
        parser.close()
        raw = "".join(parser.parts)
    return " ".join(raw.split())


def rfc_3339_to_utc_iso(stamped):
    try:
        moment = datetime.fromisoformat(stamped.strip().replace("Z", "+00:00"))
        if moment.tzinfo is not None:
            return moment.astimezone(timezone.utc).strftime(schema.INSTANT_FORMAT)
    except (ValueError, OverflowError):
        pass
    return ""


def rfc_822_to_utc_iso(stamped):
    try:
        moment = email.utils.parsedate_to_datetime(stamped.strip())
        if moment is not None and moment.tzinfo is not None:
            return moment.astimezone(timezone.utc).strftime(schema.INSTANT_FORMAT)
    except (TypeError, ValueError, OverflowError):
        pass
    return ""


def _bases(root, address):
    bases = {}
    pending = [(root, address)]
    while pending:
        element, parent_base = pending.pop()
        base = urljoin(parent_base, element.get(XML_BASE, ""))
        bases[element] = base
        pending.extend((part, base) for part in element)
    return bases


def _locator(element, stated, bases):
    try:
        address = urljoin(bases[element], stated.strip()) if stated.strip() else ""
        parsed = urlsplit(address)
        return address if parsed.scheme in ("http", "https") and parsed.hostname and not parsed.username and not parsed.password else ""
    except ValueError:
        return ""


def _record_for(position, entry, bases, feed_url, final_url):
    title = prose(child(entry, "title"))
    native_id = text(child(entry, "id")) or text(child(entry, "guid"))
    author = child(entry, "author")
    author_name = text(child(author, "name")) if author is not None else ""
    author_name = author_name or text(author) or text(child(entry, "creator"))
    published = (rfc_3339_to_utc_iso(text(child(entry, "published")))
                 or rfc_822_to_utc_iso(text(child(entry, "pubdate"))))
    modified = rfc_3339_to_utc_iso(text(child(entry, "updated")))
    attributes = [("feed_url", feed_url), ("final_feed_url", final_url)]
    if modified:
        attributes.append(("modified_at", modified))
    locator = ""
    for part in entry:
        name = local_name(part.tag)
        relation = part.get("rel", "alternate")
        if name == "link" and relation == "alternate" and not locator:
            locator = _locator(part, part.get("href", "") or text(part), bases)
        media = name if name in ("enclosure", "transcript") else relation if name == "link" else ""
        if media in ("enclosure", "transcript"):
            address = _locator(part, part.get("url", "") or part.get("href", ""), bases)
            if address:
                attributes.extend(((media, address), (media + "_type", part.get("type", ""))))
    guid = child(entry, "guid")
    if not locator and guid is not None and guid.get("isPermaLink", "true").lower() == "true":
        locator = _locator(guid, text(guid), bases)
    body = ""
    for tag in ("content", "encoded", "summary", "description"):
        part = child(entry, tag)
        if part is not None:
            body = prose(part, html=tag in ("encoded", "description"))
            if body:
                attributes.append(("feed_text_kind", tag))
                break
    if len(body) > MAX_BODY_CHARACTERS:
        attributes.append(("body_truncated", "true"))
    return NativeRecord(
        canonical_content_kind=CONTENT_KIND, canonical_locator=locator,
        native_item_id=native_id, title=title, body=body[:MAX_BODY_CHARACTERS],
        author=author_name, published_at=published, attributes=tuple(attributes),
        native_position=position,
        loss=("field_omitted",) if not all((native_id, title, locator, published)) else (),
    )


def _page_from(response, descriptor=DESCRIPTOR, feed_url=""):
    def page(records=(), warnings=(), outcome="ok", loss=()):
        return build_native_page(descriptor, records, observed_at=response.observed_at,
                                 native_order=NATIVE_ORDER, warnings=warnings,
                                 outcome=outcome, loss=loss)

    if response.status != 200:
        return page(warnings=("http status {0} from {1}".format(response.status, descriptor.route_id),),
                    outcome="failed", loss=("http_status",))
    # Do not expand feed-defined entities. Malformed/truncated XML is a gap,
    # not a tolerant partial read presented as an empty or complete feed.
    try:
        if re.search(r"<!\s*(?:DOCTYPE|ENTITY)\b", response.body, re.I):
            raise ValueError("document type and entity declarations are unsupported")
        root = ET.fromstring(response.body)
        root_name = local_name(root.tag)
        if root_name == "feed" and root.tag in ("feed", "{" + ATOM_NAMESPACE + "}feed"):
            entries = [part for part in root if local_name(part.tag) == "entry"]
        elif root.tag == "rss" and child(root, "channel") is not None:
            entries = [part for part in child(root, "channel") if part.tag == "item"]
        else:
            raise ValueError("document is not an RSS 2.0 or Atom feed")
        feed_url = feed_url or response.url
        final_url = response.final_url or feed_url
        bases = _bases(root, final_url)
    except (ET.ParseError, ValueError) as error:
        return page(warnings=("Feed parse failed: " + str(error),),
                    outcome="failed", loss=("schema_drift",))
    records = tuple(_record_for(index, entry, bases, feed_url, final_url)
                    for index, entry in enumerate(entries))
    warnings = (FEED_COVERAGE,)
    if any("field_omitted" in record.loss for record in records):
        warnings += ("Some entries omit identity, title, usable link or publication time; updated is kept separately and never substituted for publication.",)
    return page(records, warnings, "ok" if records else "empty")


def fetch_native_page(carrier: transport.Transport, request: AdapterRequest) -> NativePage:
    """Read one supplied HTTPS feed URL; never infer or discover another target."""
    address = (request.target_ids[0] if request.target_ids else request.query).strip()
    channel_id = ""
    try:
        parsed = urlsplit(address)
        if (parsed.scheme == "https" and parsed.netloc in ("www.youtube.com", "youtube.com")
                and parsed.path == "/feeds/videos.xml"):
            params = parse_qs(parsed.query)
            if set(params) == {"channel_id"} and len(params["channel_id"]) == 1:
                channel_id = params["channel_id"][0]
    except ValueError:
        pass
    if channel_id:
        params = {"channel_id": channel_id}
        descriptor = DESCRIPTOR
        feed_url = address
    else:
        descriptor = FEED_URL_DESCRIPTOR
        refusal = transport.open_read_refusal(address)
        if refusal:
            return build_native_page(descriptor, (), native_order=NATIVE_ORDER,
                                     warnings=(refusal,), outcome="refused", loss=("unselected_target",))
        params = {transport.OPEN_URL_PARAM: address}
        feed_url = address
    return fetch_one_page(descriptor, carrier, params=params,
                          parse=lambda response: _page_from(response, descriptor, feed_url),
                          native_order=NATIVE_ORDER)
