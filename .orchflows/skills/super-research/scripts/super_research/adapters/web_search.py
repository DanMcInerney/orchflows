"""K4 web discovery over DuckDuckGo's keyless HTML endpoint.

Measured 2026-08-10 (Web discovery): of nine keyless
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

# The two markup names this route's shape rests on, above the anchor class.
# Declared so the parser can say which one went missing: a page keeping neither
# is a page this adapter no longer reads, and a page keeping the container and
# no result block is a search that matched nothing. Without the distinction
# both arrive as an empty index, and only one of them is about the query.
RESULTS_CONTAINER_CLASS = "results"
RESULT_BLOCK_CLASS = "result"

# The redirect wrapper this route puts every result behind, and the field it
# keeps the real address in.
REDIRECT_PATH = "/l/"
REDIRECT_TARGET_FIELD = "uddg"
REDIRECT_HOST_SUFFIX = "duckduckgo.com"
SCHEMA_DRIFT = "schema_drift"
HTTP_STATUS = "http_status"
FIELD_OMITTED = "field_omitted"


class _DuckDuckGoResultParser(HTMLParser):
    """Collect one HTML page's result anchors, snippets, and next-page offset.

    It also counts the two enclosing markup names, because what a page did
    *not* carry is the only way to tell a rotated class from a query nobody
    matched.
    """

    def __init__(self) -> None:
        HTMLParser.__init__(self, convert_charrefs=True)
        self.hits: List[List[str]] = []  # [locator, title, snippet]
        self.next_offset = ""
        self.results_containers = 0
        self.result_blocks = 0
        self._capturing: Optional[int] = None  # index 1 (title) or 2 (snippet)

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        classes = (attributes.get("class") or "").split()
        if RESULTS_CONTAINER_CLASS in classes:
            self.results_containers += 1
        if RESULT_BLOCK_CLASS in classes:
            self.result_blocks += 1
        if tag == "a" and RESULT_LINK_CLASS in classes:
            self.hits.append([unwrap_result_url(attributes.get("href") or ""), "", ""])
            self._capturing = 1
        elif tag == "a" and RESULT_SNIPPET_CLASS in classes and self.hits:
            self._capturing = 2
        elif tag == "input" and attributes.get("name") == NEXT_OFFSET_FIELD:
            # Last one wins, and a paginated page carries two of these: one in
            # the "< Previous" nav form and one in "Next". Which is which is not
            # in the evidence — the 2026-08-10 probes recorded page one,
            # where there is
            # only the forward form — so a rule preferring one would be markup
            # this package invented rather than markup it read, and reading the
            # last is at least a rule rather than a coincidence.
            #
            # Nothing spends the value: `runner.planned_calls` sets no cursor,
            # so a backwards offset is a field on a page and never a read. The
            # hazard is recorded here rather than guarded against, because the
            # guard would be a guess and the ticket that makes the core page is
            # the one that has to measure page two.
            self.next_offset = attributes.get("value") or ""

    def handle_endtag(self, tag):
        if tag == "a":
            self._capturing = None

    def handle_data(self, data):
        if self._capturing is None or not self.hits:
            return
        self.hits[-1][self._capturing] += data


def unwrap_result_url(href: str) -> str:
    """Return the target URL behind DuckDuckGo's ``/l/?uddg=`` redirect wrapper.

    The wrapper arrives in three shapes and only two of them name a host:
    protocol-relative ``//duckduckgo.com/l/?uddg=``, absolute
    ``https://duckduckgo.com/l/?uddg=``, and root-relative ``/l/?uddg=``. A
    root-relative link on a page this adapter just read is a link on this
    route's own origin, so requiring a host left the third shape wrapped.

    That failure is silent and it lands on the one route criterion 7 exists to
    protect. A still-wrapped locator is host-less, ``normalize.normalized_locator``
    keeps it host-less, and ``normalize.link_discovery_hydration`` matches a
    caller-frozen locator exactly — so the K4 discovery-to-hydration edge simply
    never forms. It fails as an absent edge and never as a merge, which is the
    one shape of K4 breakage no wrong_merge_law test would catch.
    """

    if href.startswith("//"):
        href = "https:" + href
    parts = urllib.parse.urlsplit(href)
    on_this_route = not parts.netloc or parts.netloc.endswith(REDIRECT_HOST_SUFFIX)
    if on_this_route and parts.path == REDIRECT_PATH:
        targets = urllib.parse.parse_qs(parts.query).get(REDIRECT_TARGET_FIELD, [])
        return targets[0] if targets else ""
    return href


def _record_for(position: int, locator: str, title: str, snippet: str) -> NativeRecord:
    loss: Tuple[str, ...] = DESCRIPTOR.standing_loss
    if not snippet:
        loss = loss + (FIELD_OMITTED,)
    return NativeRecord(
        canonical_content_kind="web_hit",
        canonical_locator=locator,
        title=title,
        body=snippet,
        native_position=position,
        loss=loss,
    )


def _drifted(response: transport.TransportResponse, detail: str) -> NativePage:
    """The origin answered 200, and what it answered with is not a result page.

    Never `empty`: an index that matched nothing and an index whose markup this
    adapter no longer reads arrive at the same door, and only the first is a
    statement about the query. The 2026-08-10 probes recorded three of the nine engines
    probed answering 200 with a challenge or a wall, so a 200 that is not a
    result page is a shape this route can genuinely produce.
    """

    return build_native_page(
        DESCRIPTOR,
        (),
        observed_at=response.observed_at,
        native_order=NATIVE_ORDER,
        warnings=(
            "route {0} answered {1} and {2}: the page this adapter reads has"
            " changed shape".format(DESCRIPTOR.route_id, response.status, detail),
        ),
        outcome="failed",
        loss=(SCHEMA_DRIFT,),
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
            loss=(HTTP_STATUS,),
        )

    parser = _DuckDuckGoResultParser()
    parser.feed(response.body)
    parser.close()

    records = tuple(
        _record_for(position, locator, title.strip(), snippet.strip())
        for position, (locator, title, snippet) in enumerate(parser.hits)
        if locator
    )
    if not records:
        if not parser.results_containers:
            return _drifted(
                response, "carried no ." + RESULTS_CONTAINER_CLASS + " container"
            )
        if parser.result_blocks:
            return _drifted(
                response,
                "carried {0} .{1} block(s) and no readable .{2} locator".format(
                    parser.result_blocks, RESULT_BLOCK_CLASS, RESULT_LINK_CLASS
                ),
            )
    return build_native_page(
        DESCRIPTOR,
        records,
        observed_at=response.observed_at,
        cursor_out=parser.next_offset,
        native_order=NATIVE_ORDER,
        outcome="ok" if records else "empty",
        warnings=()
        if records
        else (
            "route {0} answered 200 with a .{1} container holding no .{2}"
            " block: the index matched nothing".format(
                DESCRIPTOR.route_id, RESULTS_CONTAINER_CLASS, RESULT_BLOCK_CLASS
            ),
        ),
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
