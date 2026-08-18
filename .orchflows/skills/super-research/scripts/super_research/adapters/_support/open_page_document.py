"""Document parsing and record extraction for the open-page adapter."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from ... import transport
from .. import NativeRecord


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

RECORD_INSTANT_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
DATE_ONLY_LENGTH = 10
FIELD_OMITTED = "field_omitted"
DATE_PRECISION_ONLY = "date_precision_only"


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


def document_record(
    response: transport.TransportResponse, requested_url: str, page_kind: str
) -> Tuple[NativeRecord, Tuple[str, ...]]:
    """Extract one HTML document record without deciding response policy."""

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
        loss.append(FIELD_OMITTED)
    if date_only:
        loss.append(DATE_PRECISION_ONLY)
    return (
        NativeRecord(
            canonical_content_kind=page_kind,
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


def plain_record(
    response: transport.TransportResponse, requested_url: str, page_kind: str
) -> NativeRecord:
    """Extract one plain or structured text record."""

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
        canonical_content_kind=page_kind,
        canonical_locator=response.final_url or requested_url,
        title="",
        body=body[:MAX_BODY_CHARACTERS],
        attributes=tuple(named),
        native_position=0,
        # A document with no title is short of the row every page promises, and
        # a plain-text answer never carries one.
        loss=(FIELD_OMITTED,),
    )


def unreadable_record(
    response: transport.TransportResponse, requested_url: str, page_kind: str
) -> NativeRecord:
    """Represent a response whose media type is not a readable document."""

    return NativeRecord(
        canonical_content_kind=page_kind,
        canonical_locator=response.final_url or requested_url,
        attributes=(
            (CONTENT_TYPE_ATTRIBUTE, response.content_type),
            (REQUESTED_URL_ATTRIBUTE, requested_url),
            (FINAL_URL_ATTRIBUTE, response.final_url or requested_url),
            (LINK_ATTRIBUTE, response.final_url or requested_url),
        ),
        native_position=0,
        loss=(FIELD_OMITTED,),
    )
