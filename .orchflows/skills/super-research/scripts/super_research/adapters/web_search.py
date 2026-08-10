"""K4 web discovery over DuckDuckGo's keyless HTML endpoint.

Measured 2026-08-10 (findings.md §1, "Web discovery"): of nine keyless
engines probed, ``html.duckduckgo.com/html/`` was the only one returning
clean title/URL/snippet triples — ten per page, no throttle at probe
volume. Brave and Bing returned content but resisted extraction and are
declared secondary providers, not free wins.

A hit from this route is an *index* representation. It carries a snippet,
never a native field: a snippet reading "120 votes, 88 comments" is prose
about a target this adapter has not hydrated.
"""

from __future__ import annotations

import urllib.parse
from html.parser import HTMLParser
from typing import List, Optional, Tuple

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
    adapter_id="web_search",
    adapter_version="1",
    access_class="K4",
    route_id=transport.DDG_HTML_ROUTE,
    platform="duckduckgo",
    native_identity_namespace="",
    representation_kind="index",
    operator_identity="duckduckgo",
    standing_loss=(
        "native_identity_unknown",
        "unknown_publication_time",
        "engagement_unavailable",
        "target_not_hydrated",
    ),
)

NATIVE_ORDER = "ddg_relevance"
RESULT_LINK_CLASS = "result__a"
RESULT_SNIPPET_CLASS = "result__snippet"
NEXT_OFFSET_FIELD = "s"


class _DuckDuckGoResultParser(HTMLParser):
    """Collect one HTML page's result anchors, snippets, and next-page offset."""

    def __init__(self) -> None:
        HTMLParser.__init__(self, convert_charrefs=True)
        self.hits: List[List[str]] = []  # [locator, title, snippet]
        self.next_offset = ""
        self._capturing: Optional[int] = None  # index 1 (title) or 2 (snippet)

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        classes = (attributes.get("class") or "").split()
        if tag == "a" and RESULT_LINK_CLASS in classes:
            self.hits.append([unwrap_result_url(attributes.get("href") or ""), "", ""])
            self._capturing = 1
        elif tag == "a" and RESULT_SNIPPET_CLASS in classes and self.hits:
            self._capturing = 2
        elif tag == "input" and attributes.get("name") == NEXT_OFFSET_FIELD:
            self.next_offset = attributes.get("value") or ""

    def handle_endtag(self, tag):
        if tag == "a":
            self._capturing = None

    def handle_data(self, data):
        if self._capturing is None or not self.hits:
            return
        self.hits[-1][self._capturing] += data


def unwrap_result_url(href: str) -> str:
    """Return the target URL behind DuckDuckGo's ``/l/?uddg=`` redirect wrapper."""

    if href.startswith("//"):
        href = "https:" + href
    parts = urllib.parse.urlsplit(href)
    if parts.netloc.endswith("duckduckgo.com") and parts.path == "/l/":
        targets = urllib.parse.parse_qs(parts.query).get("uddg", [])
        return targets[0] if targets else ""
    return href


def _record_for(position: int, locator: str, title: str, snippet: str) -> NativeRecord:
    loss: Tuple[str, ...] = DESCRIPTOR.standing_loss
    if not snippet:
        loss = loss + ("field_omitted",)
    return NativeRecord(
        canonical_content_kind="web_hit",
        canonical_locator=locator,
        title=title,
        body=snippet,
        native_position=position,
        loss=loss,
    )


def _page_from(response: transport.TransportResponse) -> NativePage:
    """Turn one response the origin itself sent into exactly one page."""

    if response.status != 200:
        return build_native_page(
            DESCRIPTOR,
            (),
            observed_at=response.observed_at,
            native_order=NATIVE_ORDER,
            warnings=("http status {0} from {1}".format(response.status, DESCRIPTOR.route_id),),
            outcome="failed",
            loss=("http_status",),
        )

    parser = _DuckDuckGoResultParser()
    parser.feed(response.body)
    parser.close()

    records = tuple(
        _record_for(position, locator, title.strip(), snippet.strip())
        for position, (locator, title, snippet) in enumerate(parser.hits)
        if locator
    )
    return build_native_page(
        DESCRIPTOR,
        records,
        observed_at=response.observed_at,
        cursor_out=parser.next_offset,
        native_order=NATIVE_ORDER,
        outcome="ok" if records else "empty",
    )


def fetch_native_page(carrier: transport.Transport, request: AdapterRequest) -> NativePage:
    """Fetch one DuckDuckGo HTML page and return exactly one NativePage."""

    return fetch_one_page(
        DESCRIPTOR,
        carrier,
        params={"q": request.query, "s": request.cursor},
        parse=_page_from,
        native_order=NATIVE_ORDER,
    )
