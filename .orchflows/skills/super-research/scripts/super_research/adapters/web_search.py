"""K4 web discovery over four keyless indexes: DuckDuckGo HTML, and three RSS forms.

Measured 2026-08-10 (Web discovery): of nine keyless
engines probed, ``html.duckduckgo.com/html/`` was the only one returning
clean title/URL/snippet triples — ten per page, no throttle at probe
volume. Brave and Bing returned content but resisted extraction and are
declared secondary providers, not free wins.

Measured 2026-08-17 (second sweep, this host, the package identity): the
DuckDuckGo route answered 202 with a bot challenge — to this identity and to a
browser identity alike — so one index closed both web lanes of the bakeoff.
Three more indexes are declared here as **parallel planned routes**, never as
fallbacks: Bing publishes an RSS 2.0 form of its web results
(``bing.com/search?format=rss``, ten ``<item>`` per page, ``first=`` paging,
each item a direct publisher ``<link>`` and an RFC 822 ``<pubDate>``); Bing
News publishes the same shape for its news index (``news/search?format=rss``,
ten to fourteen items measured across queries, each ``<link>`` wrapped in
``news/apiclick.aspx?...&url=<percent-encoded publisher>`` and unwrapped here,
plus ``<News:Source>``); and Google News publishes an RSS search
(``rss/search?q=<q>+when:30d&hl=en-US&gl=US&ceid=US:en``, one hundred items in
131 KB, each ``<link>`` an opaque redirect on Google's own origin, each
``<source url=>`` naming the publisher). All three answered 200 today.

Two of the measurements bear on what a caller may expect. Bing's ``first=``
answered page one again for two of three queries probed and an unrelated set
for the third, so the cursor this adapter surfaces is the origin's stated
paging and not a proof that page two exists; the core dedupes what it reads. And
a Google News item's ``<link>`` does not resolve to the publisher on this host:
it answers 302 to itself with locale parameters and then a 200 interstitial on
Google's origin, and that origin is a declared route's host, which the open page
read refuses. A Google News hit therefore carries the publisher's home in
``source_url`` and no address this package can hydrate.

A hit from any of these routes is an *index* representation. It carries a
snippet, never a native field: a snippet reading "120 votes, 88 comments" is
prose about a target this adapter has not hydrated. What the RSS forms add over
DuckDuckGo is a publication time — ``<pubDate>`` on every item measured — so
``unknown_publication_time`` is standing on the DuckDuckGo surface and
attached per record on the other three, only where an item lacks one.

The RSS forms are read with :mod:`html.parser`, the way every markup-reading
adapter here reads its origin and for one more reason: acquired text is
untrusted, and this parser expands no document-defined entity, so a feed cannot
ask it to allocate a gigabyte.
"""

from __future__ import annotations

import urllib.parse
from html.parser import HTMLParser
from typing import List, Optional, Tuple

from .. import transport
from ._support import web_search_feeds as _feeds
from . import (
    AdapterDescriptor,
    AdapterRequest,
    NativePage,
    NativeRecord,
    build_native_page,
    fetch_one_page,
)

# Every code this module can attach, spelled once each so a search over a name
# finds the branch that emits it. The first three stand on every index hit,
# whichever surface listed it: an index row names no platform id, publishes no
# count, and has hydrated nothing. The fourth stands only where the surface
# states no time at all.
NATIVE_IDENTITY_UNKNOWN = "native_identity_unknown"
UNKNOWN_PUBLICATION_TIME = "unknown_publication_time"
ENGAGEMENT_UNAVAILABLE = "engagement_unavailable"
TARGET_NOT_HYDRATED = "target_not_hydrated"
SCHEMA_DRIFT = "schema_drift"
HTTP_STATUS = "http_status"
FIELD_OMITTED = "field_omitted"

INDEX_STANDING_LOSS = (
    NATIVE_IDENTITY_UNKNOWN,
    ENGAGEMENT_UNAVAILABLE,
    TARGET_NOT_HYDRATED,
)

# The DuckDuckGo HTML surface, and this adapter's primary: an unprefixed query
# reads it, which is what a bare discovery step on this adapter has always
# meant. It states no publication time on any hit, so that loss stands here.
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
        NATIVE_IDENTITY_UNKNOWN,
        UNKNOWN_PUBLICATION_TIME,
        ENGAGEMENT_UNAVAILABLE,
        TARGET_NOT_HYDRATED,
    ),
)

# Bing's RSS form of its web index. Ten items per answer, measured 2026-08-17.
BING_DESCRIPTOR = AdapterDescriptor(
    adapter_id="web_search",
    adapter_version="1",
    access_class="K4",
    route_id=transport.BING_RSS_ROUTE,
    platform="bing",
    native_identity_namespace="",
    representation_kind="index",
    operator_identity="bing",
    standing_loss=INDEX_STANDING_LOSS,
    page_size=10,
)

# Bing's RSS form of its news index. Fourteen items was the most one answer
# held across the queries measured 2026-08-17 (ten, eleven, twelve and four
# on others): the number is a ceiling the origin reached, not a promise.
BING_NEWS_DESCRIPTOR = AdapterDescriptor(
    adapter_id="web_search",
    adapter_version="1",
    access_class="K4",
    route_id=transport.BING_NEWS_RSS_ROUTE,
    platform="bing_news",
    native_identity_namespace="",
    representation_kind="index",
    operator_identity="bing",
    standing_loss=INDEX_STANDING_LOSS,
    page_size=14,
)

# Google News's RSS search. One hundred items in one answer, measured
# 2026-08-17; it states no next page.
GOOGLE_NEWS_DESCRIPTOR = AdapterDescriptor(
    adapter_id="web_search",
    adapter_version="1",
    access_class="K4",
    route_id=transport.GOOGLE_NEWS_RSS_ROUTE,
    platform="google_news",
    native_identity_namespace="",
    representation_kind="index",
    operator_identity="google",
    standing_loss=INDEX_STANDING_LOSS,
    page_size=100,
)

# Every route this adapter can reach, one descriptor each. The core collects
# route budgets from here, because a route nothing declares a budget for is a
# route the scheduler refuses to pace.
SURFACE_DESCRIPTORS = (
    DESCRIPTOR,
    BING_DESCRIPTOR,
    BING_NEWS_DESCRIPTOR,
    GOOGLE_NEWS_DESCRIPTOR,
)

# The four operations, spelled once each. A caller names one with a prefix on
# the query, because four indexes answer four different questions; absent a
# prefix the primary answers, and never the characters in the argument — a
# query that happens to begin with a word and a colon is a query.
DDG_OPERATION = "ddg"
BING_OPERATION = "bing"
BING_NEWS_OPERATION = "bingnews"
GOOGLE_NEWS_OPERATION = "gnews"
WEB_OPERATIONS = (
    DDG_OPERATION,
    BING_OPERATION,
    BING_NEWS_OPERATION,
    GOOGLE_NEWS_OPERATION,
)
PRIMARY_OPERATION = DDG_OPERATION

SURFACE_OF = {
    DDG_OPERATION: DESCRIPTOR,
    BING_OPERATION: BING_DESCRIPTOR,
    BING_NEWS_OPERATION: BING_NEWS_DESCRIPTOR,
    GOOGLE_NEWS_OPERATION: GOOGLE_NEWS_DESCRIPTOR,
}

NATIVE_ORDER = "ddg_relevance"
NATIVE_ORDERS = {
    DDG_OPERATION: NATIVE_ORDER,
    BING_OPERATION: "bing_relevance",
    BING_NEWS_OPERATION: "bing_news_relevance",
    GOOGLE_NEWS_OPERATION: "google_news_relevance",
}

CONTENT_KIND = "web_hit"

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
        canonical_content_kind=CONTENT_KIND,
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


# Feed parsing stays private while these original-facade names remain stable.
_FEED_CONFIG = _feeds.FeedConfig(
    surfaces=SURFACE_OF,
    native_orders=NATIVE_ORDERS,
    bing_operation=BING_OPERATION,
    bing_news_operation=BING_NEWS_OPERATION,
    content_kind=CONTENT_KIND,
    unknown_publication_time=UNKNOWN_PUBLICATION_TIME,
    field_omitted=FIELD_OMITTED,
    schema_drift=SCHEMA_DRIFT,
    http_status=HTTP_STATUS,
)

local_name = _feeds.local_name
_RssIndexParser = _feeds._RssIndexParser
_TextOnlyParser = _feeds._TextOnlyParser
snippet_text = _feeds.snippet_text
rfc_822_to_utc_iso = _feeds.rfc_822_to_utc_iso
unwrap_bing_news_url = _feeds.unwrap_bing_news_url
instant_moment = _feeds.instant_moment
google_when_days = _feeds.google_when_days


def _feed_locator(operation: str, link: str) -> str:
    return _feeds.feed_locator(_FEED_CONFIG, operation, link)


def _feed_record(operation: str, position: int, item) -> NativeRecord:
    return _feeds.feed_record(_FEED_CONFIG, operation, position, item)


def _feed_answered(
    operation: str,
    response: transport.TransportResponse,
    records: Tuple[NativeRecord, ...] = (),
    outcome: str = "ok",
    cursor_out: str = "",
    warnings: Tuple[str, ...] = (),
    loss: Tuple[str, ...] = (),
) -> NativePage:
    return _feeds.feed_answered(
        _FEED_CONFIG, operation, response, records, outcome, cursor_out, warnings, loss
    )


def next_bing_offset(cursor: str, listed: int) -> str:
    return _feeds.next_bing_offset(cursor, listed, BING_DESCRIPTOR.page_size)


def _feed_page_from(
    operation: str, response: transport.TransportResponse, cursor: str
) -> NativePage:
    return _feeds.feed_page_from(_FEED_CONFIG, operation, response, cursor)


def _feed_params(operation: str, query: str, request: AdapterRequest):
    return _feeds.feed_params(_FEED_CONFIG, operation, query, request)


def operation_for(request: AdapterRequest) -> Tuple[str, str]:
    """The operation this call performs, and the query it performs it on.

    A caller names the operation with a prefix on the query. Absent one, the
    primary answers, which is what a bare discovery step on this adapter has
    always meant. Neither is inferred from the characters in the query: a
    query written as ``site:reddit.com ...`` names no operation of this
    adapter's and stays a query, prefix and all.
    """

    kind, separator, argument = request.query.partition(":")
    if separator and kind in WEB_OPERATIONS:
        return (kind, argument)
    return (PRIMARY_OPERATION, request.query)


def _feed_params(operation: str, query: str, request: AdapterRequest) -> Dict[str, str]:
    """The parameters one feed surface takes, in the origin's own names."""

    if operation == BING_OPERATION:
        return {QUERY_PARAM: query, FORMAT_PARAM: RSS_FORMAT, BING_OFFSET_PARAM: request.cursor}
    if operation == BING_NEWS_OPERATION:
        return {QUERY_PARAM: query, FORMAT_PARAM: RSS_FORMAT}
    days = google_when_days(request.window_start, request.window_end)
    if days:
        query = query + " " + GOOGLE_WHEN_OPERATOR + str(days) + GOOGLE_WHEN_UNIT
    params = {QUERY_PARAM: query}
    params.update(GOOGLE_LOCALE_PARAMS)
    return params


def fetch_native_page(carrier: transport.Transport, request: AdapterRequest) -> NativePage:
    """Fetch one index page from one surface and return exactly one NativePage.

    One call, one origin: the four surfaces are separate routes with separate
    budgets, and which to ask is the caller's, named on the query. Nothing here
    tries a second index when the first answers badly — a 202 challenge from
    one is a typed page from that one, and the next surface is the next step.
    """

    operation, query = operation_for(request)
    if operation == DDG_OPERATION:
        return fetch_one_page(
            DESCRIPTOR,
            carrier,
            params={"q": query, "s": request.cursor},
            parse=_page_from,
            native_order=NATIVE_ORDER,
        )

    def parse(response: transport.TransportResponse) -> NativePage:
        return _feed_page_from(operation, response, request.cursor)

    return fetch_one_page(
        SURFACE_OF[operation],
        carrier,
        params=_feed_params(operation, query, request),
        parse=parse,
        native_order=NATIVE_ORDERS[operation],
    )
