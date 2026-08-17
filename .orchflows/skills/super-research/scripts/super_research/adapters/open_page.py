"""K0 open document read: the one route whose address is the caller's.

Measured 2026-08-17. Until this route, `public_page` served exactly two
documents — a Wikipedia article and a control — and refused any locator
carrying `:`, `/` or `\\` before making a call. So a press page a web index
discovered could never be hydrated by this package at all: the 2026-08-17
bakeoff's open-web lane returned three Wikipedia records and no press, and
`target_not_hydrated` on every index hit was a ceiling rather than a budget.

Its id is `open_page` and the kind it emits is `web_page`, which is the kind
`public_page` emits too: they are two ways to reach one sort of thing, and a
content kind is shared vocabulary where an adapter id is a module's own name.

This adapter reads the address a discovery step returned, under a policy the
transport owns and states: https only, a host that resolves, and never a host
a declared route already reads (`transport.open_read_refusal`) — an open read
is not a way around a measured budget. It is refused here, before any call,
with the transport's own sentence, so a caller learns which of the three rules
it met.

**What it extracts, and what it will not.** A document's own metadata is read
under the names the document used — `ld+json` first, because a publisher
states `datePublished` and `author` there deliberately, then the `og:` and
`article:` meta names, then a `<time datetime>`. Body text is the readable
prose: script, style and the page's furniture are dropped, the largest
paragraph-bearing container wins where the page marks one, and whitespace is
collapsed. Nothing is summarized, scored, or rewritten — a body is the page's
sentences in the page's order, and a page this adapter cannot read as a
document says so rather than answering with an empty one.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

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
    adapter_id="open_page",
    adapter_version="1",
    access_class="K0",
    route_id=transport.WEB_PAGE_OPEN_ROUTE,
    platform="web",
    # A document has no platform-native id anywhere: its identity is its
    # address, which is what the weak grouping key is built on.
    native_identity_namespace="",
    representation_kind="page",
    operator_identity="open_web",
    # No measured ceiling: every host is a different origin and none of them
    # has been measured, so this is the protocol's conservative default made
    # explicit. The governor paces this route per host rather than per route,
    # so one publisher's page never waits on another's.
    min_interval_ms=2000,
    burst=1,
    page_size=1,
)

NATIVE_ORDER = "web_page_document_order"
PAGE_KIND = "web_page"

# The elements whose text is never a document's prose, and the ones that carry
# it. Declared, because a reader that took every text node would return a page's
# navigation and its cookie banner as the article.
FURNITURE_TAGS = (
    "script",
    "style",
    "noscript",
    "nav",
    "header",
    "footer",
    "aside",
    "form",
    "svg",
    "iframe",
    "button",
    "select",
    "template",
)
BLOCK_TAGS = ("p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote", "pre", "dd")
# Where a page says its own article is. The first of these that holds prose
# wins; a page marking none falls back to everything outside the furniture.
MAIN_TAGS = ("article", "main")

# The metadata names this adapter reads, under the document's own vocabulary.
LD_JSON_TYPE = "application/ld+json"
TITLE_TAG = "title"
META_TAG = "meta"
LINK_TAG = "link"
TIME_TAG = "time"
OG_TITLE = "og:title"
OG_SITE_NAME = "og:site_name"
OG_DESCRIPTION = "og:description"
ARTICLE_PUBLISHED = "article:published_time"
ARTICLE_MODIFIED = "article:modified_time"
META_DESCRIPTION = "description"
META_AUTHOR = "author"
CANONICAL_REL = "canonical"
DATETIME_ATTRIBUTE = "datetime"
LD_HEADLINE = "headline"
LD_PUBLISHED = "datePublished"
LD_MODIFIED = "dateModified"
LD_AUTHOR = "author"
LD_TYPE = "@type"
LD_NAME = "name"
LD_GRAPH = "@graph"

# The attributes every record from this route carries about the read itself.
CONTENT_TYPE_ATTRIBUTE = "content_type"
REQUESTED_URL_ATTRIBUTE = "requested_url"
FINAL_URL_ATTRIBUTE = "final_url"
LINK_ATTRIBUTE = "link"
SITE_NAME_ATTRIBUTE = "site_name"
DESCRIPTION_ATTRIBUTE = "description"
LD_TYPE_ATTRIBUTE = "ld_type"
MODIFIED_ATTRIBUTE = "modified_at"
BODY_TRUNCATED_ATTRIBUTE = "body_truncated"

# How much prose one record carries. A document past this is carried to the
# bound and says so, rather than being held whole — a run's footprint is
# bounded by `cache.MAX_ENTRY_BYTES` upstream, and a record nobody can read is
# not a better answer than a record that states its own cut.
MAX_BODY_CHARACTERS = 200000

# The media types this adapter reads as a document, by what it does with each.
HTML_TYPES = ("text/html", "application/xhtml+xml")
TEXT_TYPES = ("text/plain",)
STRUCTURED_TYPES = ("application/json", "application/xml", "text/xml", "application/rss+xml")

RECORD_INSTANT_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
DATE_ONLY_LENGTH = 10

HTTP_STATUS = "http_status"
FIELD_OMITTED = "field_omitted"
UNSELECTED_TARGET = "unselected_target"
DATE_PRECISION_ONLY = "date_precision_only"


def media_type(content_type: str) -> str:
    """One answer's media type, without the parameters that follow it."""

    return (content_type or "").split(";")[0].strip().lower()


def instant_from(stated: Any) -> Tuple[str, bool]:
    """One document's own time as the artifact's instant, and whether it was a date.

    ISO 8601 is what every source here writes — `2026-08-05T21:15:40Z`,
    `...+00:00`, `...-04:00`, or a bare `2026-08-05`. An offset is resolved to
    UTC because the document stated one; a date with no time is the date's
    instant and says so with `date_precision_only`. Anything else is a missing
    time rather than an approximated one.
    """

    if not isinstance(stated, str) or not stated.strip():
        return ("", False)
    text = stated.strip()
    if len(text) == DATE_ONLY_LENGTH:
        try:
            moment = datetime.strptime(text, "%Y-%m-%d")
        except ValueError:
            return ("", False)
        return (moment.replace(tzinfo=timezone.utc).strftime(RECORD_INSTANT_FORMAT), True)
    held = text[:-1] + "+00:00" if text.endswith("Z") else text
    # `fromisoformat` on the 3.9 floor reads no fractional-second precision
    # other than 3 or 6 digits, so a stamp it refuses is left missing rather
    # than trimmed into one it accepts: a time this module reshaped is a time
    # the document did not state.
    try:
        moment = datetime.fromisoformat(held)
    except ValueError:
        return ("", False)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return (moment.astimezone(timezone.utc).strftime(RECORD_INSTANT_FORMAT), False)


def _text_of(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _author_name(value: Any) -> str:
    """One `ld+json` author's name, whichever of the three shapes it arrived in."""

    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return _text_of(value.get(LD_NAME))
    if isinstance(value, list):
        for entry in value:
            found = _author_name(entry)
            if found:
                return found
    return ""


def _ld_nodes(payload: Any) -> List[Mapping[str, Any]]:
    """Every object one `ld+json` block holds, flattened out of its wrappers."""

    found: List[Mapping[str, Any]] = []
    if isinstance(payload, Mapping):
        found.append(payload)
        graph = payload.get(LD_GRAPH)
        if isinstance(graph, list):
            for entry in graph:
                found.extend(_ld_nodes(entry))
    elif isinstance(payload, list):
        for entry in payload:
            found.extend(_ld_nodes(entry))
    return found


class _DocumentParser(HTMLParser):
    """One HTML document's metadata and its readable prose.

    Two things at once, because both are read from the same pass: the head's
    declarations, and the body's block text with the page's furniture dropped.
    Text is collected per container so the one a page marks as its article can
    be preferred over the page around it.
    """

    def __init__(self) -> None:
        HTMLParser.__init__(self, convert_charrefs=True)
        self.title = ""
        self.metas: Dict[str, str] = {}
        self.canonical = ""
        self.times: List[str] = []
        self.ld_blocks: List[str] = []
        self.blocks: List[str] = []
        self.main_blocks: List[str] = []
        self._furniture = 0
        self._in_title = False
        self._in_ld = False
        self._block: Optional[List[str]] = None
        self._main = 0

    def handle_starttag(self, tag, attrs):
        attributes = {name: (value or "") for name, value in attrs}
        if tag in FURNITURE_TAGS:
            if tag == "script" and attributes.get("type", "").strip().lower() == LD_JSON_TYPE:
                self._in_ld = True
                self.ld_blocks.append("")
                return
            self._furniture += 1
            return
        if tag == TITLE_TAG:
            self._in_title = True
        elif tag == META_TAG:
            named = attributes.get("property") or attributes.get("name")
            content = attributes.get("content", "")
            if named and content and named not in self.metas:
                self.metas[named] = content
        elif tag == LINK_TAG:
            if CANONICAL_REL in attributes.get("rel", "").split() and not self.canonical:
                self.canonical = attributes.get("href", "")
        elif tag == TIME_TAG:
            stamp = attributes.get(DATETIME_ATTRIBUTE, "")
            if stamp:
                self.times.append(stamp)
        elif tag in MAIN_TAGS:
            self._main += 1
        elif tag in BLOCK_TAGS and not self._furniture:
            self._block = []

    def handle_startendtag(self, tag, attrs):
        # A self-closing `<meta/>` or `<link/>` opens nothing to close.
        if tag in (META_TAG, LINK_TAG, TIME_TAG):
            self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag == "script" and self._in_ld:
            self._in_ld = False
            return
        if tag in FURNITURE_TAGS:
            if self._furniture:
                self._furniture -= 1
            return
        if tag == TITLE_TAG:
            self._in_title = False
        elif tag in MAIN_TAGS:
            if self._main:
                self._main -= 1
        elif tag in BLOCK_TAGS and self._block is not None:
            held = " ".join("".join(self._block).split())
            self._block = None
            if held:
                self.blocks.append(held)
                if self._main:
                    self.main_blocks.append(held)

    def handle_data(self, data):
        if self._in_ld:
            self.ld_blocks[-1] += data
            return
        if self._in_title:
            self.title += data
            return
        if self._block is not None and not self._furniture:
            self._block.append(data)


def _ld_facts(blocks: Sequence[str]) -> Dict[str, str]:
    """The three facts a publisher states in `ld+json`, first statement wins."""

    facts: Dict[str, str] = {}
    for raw in blocks:
        if not raw.strip():
            continue
        try:
            payload = json.loads(raw)
        except ValueError:
            # A block this module cannot read is a block the page wrote for
            # somebody else; the meta names below still answer.
            continue
        for node in _ld_nodes(payload):
            for key, name in (
                (LD_HEADLINE, "headline"),
                (LD_PUBLISHED, "published"),
                (LD_MODIFIED, "modified"),
            ):
                value = _text_of(node.get(key))
                if value and name not in facts:
                    facts[name] = value
            author = _author_name(node.get(LD_AUTHOR))
            if author and "author" not in facts:
                facts["author"] = author
            kind = node.get(LD_TYPE)
            if isinstance(kind, str) and kind and "type" not in facts:
                facts["type"] = kind
    return facts


def _document_record(
    response: transport.TransportResponse, requested_url: str
) -> Tuple[NativeRecord, Tuple[str, ...]]:
    parser = _DocumentParser()
    parser.feed(response.body)
    parser.close()
    facts = _ld_facts(parser.ld_blocks)
    final_url = response.final_url or requested_url

    title = " ".join(parser.title.split()) or facts.get("headline", "") or parser.metas.get(
        OG_TITLE, ""
    )
    blocks = parser.main_blocks or parser.blocks
    body = "\n".join(blocks)
    truncated = len(body) > MAX_BODY_CHARACTERS
    if truncated:
        body = body[:MAX_BODY_CHARACTERS]

    published, date_only = instant_from(
        facts.get("published")
        or parser.metas.get(ARTICLE_PUBLISHED)
        or (parser.times[0] if parser.times else "")
    )
    modified, _ = instant_from(facts.get("modified") or parser.metas.get(ARTICLE_MODIFIED))

    named: List[Tuple[str, str]] = [
        (CONTENT_TYPE_ATTRIBUTE, response.content_type),
        (REQUESTED_URL_ATTRIBUTE, requested_url),
        (FINAL_URL_ATTRIBUTE, final_url),
        (LINK_ATTRIBUTE, parser.canonical or final_url),
    ]
    for name, value in (
        (SITE_NAME_ATTRIBUTE, parser.metas.get(OG_SITE_NAME, "")),
        (DESCRIPTION_ATTRIBUTE, parser.metas.get(META_DESCRIPTION) or parser.metas.get(OG_DESCRIPTION, "")),
        (LD_TYPE_ATTRIBUTE, facts.get("type", "")),
        (MODIFIED_ATTRIBUTE, modified),
    ):
        if value:
            named.append((name, value))
    if truncated:
        named.append((BODY_TRUNCATED_ATTRIBUTE, "true"))

    loss: List[str] = []
    if not title:
        # The one field a document almost always has and this one did not.
        loss.append(FIELD_OMITTED)
    if date_only:
        loss.append(DATE_PRECISION_ONLY)
    return (
        NativeRecord(
            canonical_content_kind=PAGE_KIND,
            canonical_locator=final_url,
            title=title,
            body=body,
            author=facts.get("author", "") or parser.metas.get(META_AUTHOR, ""),
            published_at=published,
            attributes=tuple(named),
            native_position=0,
            loss=tuple(loss),
        ),
        (),
    )


def _plain_record(
    response: transport.TransportResponse, requested_url: str
) -> NativeRecord:
    body = response.body
    truncated = len(body) > MAX_BODY_CHARACTERS
    named = [
        (CONTENT_TYPE_ATTRIBUTE, response.content_type),
        (REQUESTED_URL_ATTRIBUTE, requested_url),
        (FINAL_URL_ATTRIBUTE, response.final_url or requested_url),
        (LINK_ATTRIBUTE, response.final_url or requested_url),
    ]
    if truncated:
        named.append((BODY_TRUNCATED_ATTRIBUTE, "true"))
    return NativeRecord(
        canonical_content_kind=PAGE_KIND,
        canonical_locator=response.final_url or requested_url,
        title="",
        body=body[:MAX_BODY_CHARACTERS],
        attributes=tuple(named),
        native_position=0,
        # A document with no title is short of the row every page promises, and
        # a plain-text answer never carries one.
        loss=(FIELD_OMITTED,),
    )


def _page_from(response: transport.TransportResponse, requested_url: str) -> NativePage:
    if response.status != 200:
        return build_native_page(
            DESCRIPTOR,
            (),
            observed_at=response.observed_at,
            native_order=NATIVE_ORDER,
            warnings=(
                "http status {0} from {1} for {2}".format(
                    response.status, DESCRIPTOR.route_id, requested_url
                ),
            ),
            outcome="failed",
            loss=(HTTP_STATUS,),
        )
    kind = media_type(response.content_type)
    if kind in HTML_TYPES or (not kind and "<html" in response.body[:2000].lower()):
        record, extra = _document_record(response, requested_url)
        return build_native_page(
            DESCRIPTOR,
            (record,),
            observed_at=response.observed_at,
            native_order=NATIVE_ORDER,
            warnings=extra,
        )
    if kind in TEXT_TYPES or kind in STRUCTURED_TYPES:
        return build_native_page(
            DESCRIPTOR,
            (_plain_record(response, requested_url),),
            observed_at=response.observed_at,
            native_order=NATIVE_ORDER,
        )
    # The route served the address and the payload is not a document. Not
    # `empty`, which would say the page has nothing; not `schema_drift`, which
    # would say a shape this adapter reads has moved. The read carried, and the
    # fields a document promises are the part that is missing.
    return build_native_page(
        DESCRIPTOR,
        (
            NativeRecord(
                canonical_content_kind=PAGE_KIND,
                canonical_locator=response.final_url or requested_url,
                attributes=(
                    (CONTENT_TYPE_ATTRIBUTE, response.content_type),
                    (REQUESTED_URL_ATTRIBUTE, requested_url),
                    (FINAL_URL_ATTRIBUTE, response.final_url or requested_url),
                    (LINK_ATTRIBUTE, response.final_url or requested_url),
                ),
                native_position=0,
                loss=(FIELD_OMITTED,),
            ),
        ),
        observed_at=response.observed_at,
        native_order=NATIVE_ORDER,
        warnings=(
            "content type {0!r} is not a document this adapter reads: the address"
            " answered and no prose was taken from it".format(response.content_type),
        ),
    )


def requested_address(request: AdapterRequest) -> str:
    """The one address this call reads: the target a caller froze, or its query."""

    return (request.target_ids[0] if request.target_ids else request.query).strip()


def fetch_native_page(carrier: transport.Transport, request: AdapterRequest) -> NativePage:
    """Read one open document once and return exactly one NativePage.

    The policy runs before the call, so an address this route does not serve
    costs a page and no read — the same shape `public_page` refuses an
    unselected document in, and the reason `runner.reached_origin` bills
    neither.
    """

    address = requested_address(request)
    refusal = transport.open_read_refusal(address)
    if refusal:
        return build_native_page(
            DESCRIPTOR,
            (),
            native_order=NATIVE_ORDER,
            warnings=(refusal,),
            outcome="refused",
            loss=(UNSELECTED_TARGET,),
        )

    def parse(response: transport.TransportResponse) -> NativePage:
        return _page_from(response, address)

    return fetch_one_page(
        DESCRIPTOR,
        carrier,
        params={transport.OPEN_URL_PARAM: address},
        parse=parse,
        native_order=NATIVE_ORDER,
    )
