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

from typing import Tuple

from .. import transport
from . import (
    AdapterDescriptor,
    AdapterRequest,
    NativePage,
    NativeRecord,
    build_native_page,
    fetch_one_page,
)
from ._support import open_page_document

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

# Preserve the facade's existing names while their implementation lives in the
# private document support module.
FURNITURE_TAGS = open_page_document.FURNITURE_TAGS
BLOCK_TAGS = open_page_document.BLOCK_TAGS
MAIN_TAGS = open_page_document.MAIN_TAGS
LD_JSON_TYPE = open_page_document.LD_JSON_TYPE
TITLE_TAG = open_page_document.TITLE_TAG
META_TAG = open_page_document.META_TAG
LINK_TAG = open_page_document.LINK_TAG
TIME_TAG = open_page_document.TIME_TAG
OG_TITLE = open_page_document.OG_TITLE
OG_SITE_NAME = open_page_document.OG_SITE_NAME
OG_DESCRIPTION = open_page_document.OG_DESCRIPTION
ARTICLE_PUBLISHED = open_page_document.ARTICLE_PUBLISHED
ARTICLE_MODIFIED = open_page_document.ARTICLE_MODIFIED
META_DESCRIPTION = open_page_document.META_DESCRIPTION
META_AUTHOR = open_page_document.META_AUTHOR
CANONICAL_REL = open_page_document.CANONICAL_REL
DATETIME_ATTRIBUTE = open_page_document.DATETIME_ATTRIBUTE
LD_HEADLINE = open_page_document.LD_HEADLINE
LD_PUBLISHED = open_page_document.LD_PUBLISHED
LD_MODIFIED = open_page_document.LD_MODIFIED
LD_AUTHOR = open_page_document.LD_AUTHOR
LD_TYPE = open_page_document.LD_TYPE
LD_NAME = open_page_document.LD_NAME
LD_GRAPH = open_page_document.LD_GRAPH
CONTENT_TYPE_ATTRIBUTE = open_page_document.CONTENT_TYPE_ATTRIBUTE
REQUESTED_URL_ATTRIBUTE = open_page_document.REQUESTED_URL_ATTRIBUTE
FINAL_URL_ATTRIBUTE = open_page_document.FINAL_URL_ATTRIBUTE
LINK_ATTRIBUTE = open_page_document.LINK_ATTRIBUTE
SITE_NAME_ATTRIBUTE = open_page_document.SITE_NAME_ATTRIBUTE
DESCRIPTION_ATTRIBUTE = open_page_document.DESCRIPTION_ATTRIBUTE
LD_TYPE_ATTRIBUTE = open_page_document.LD_TYPE_ATTRIBUTE
MODIFIED_ATTRIBUTE = open_page_document.MODIFIED_ATTRIBUTE
BODY_TRUNCATED_ATTRIBUTE = open_page_document.BODY_TRUNCATED_ATTRIBUTE
FIELD_OMITTED = open_page_document.FIELD_OMITTED
DATE_PRECISION_ONLY = open_page_document.DATE_PRECISION_ONLY
MAX_BODY_CHARACTERS = open_page_document.MAX_BODY_CHARACTERS
RECORD_INSTANT_FORMAT = open_page_document.RECORD_INSTANT_FORMAT
DATE_ONLY_LENGTH = open_page_document.DATE_ONLY_LENGTH
instant_from = open_page_document.instant_from
_text_of = open_page_document._text_of
_author_name = open_page_document._author_name
_ld_nodes = open_page_document._ld_nodes
_DocumentParser = open_page_document._DocumentParser
_ld_facts = open_page_document._ld_facts

# The media types this adapter reads as a document, by what it does with each.
HTML_TYPES = ("text/html", "application/xhtml+xml")
TEXT_TYPES = ("text/plain",)
STRUCTURED_TYPES = ("application/json", "application/xml", "text/xml", "application/rss+xml")

HTTP_STATUS = "http_status"
UNSELECTED_TARGET = "unselected_target"


def media_type(content_type: str) -> str:
    """One answer's media type, without the parameters that follow it."""

    return (content_type or "").split(";")[0].strip().lower()


def _document_record(
    response: transport.TransportResponse, requested_url: str
) -> Tuple[NativeRecord, Tuple[str, ...]]:
    open_page_document._DocumentParser = _DocumentParser
    return open_page_document.document_record(response, requested_url, PAGE_KIND)


def _plain_record(
    response: transport.TransportResponse, requested_url: str
) -> NativeRecord:
    return open_page_document.plain_record(response, requested_url, PAGE_KIND)


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
            open_page_document.unreadable_record(response, requested_url, PAGE_KIND),
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
