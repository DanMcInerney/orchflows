"""A wrong `public_page`: the generic HTTP primitive the non-goals forbid.

Written beside the tree so row 2's oracle can be shown to reject a caller-
pointable page reader rather than to match nothing at all. Nothing in the
package imports this and no discovery pattern matches it.

It is deliberately the *plausible* wrong version rather than a strawman. It
keeps the route bookkeeping intact — a real `route_id`, a read verb, no body,
one call per answer, one `NativePage` out — and changes exactly one thing: the
url comes from the caller instead of from the route table. That single change
is what turns a selected read into a primitive through which every route in
this package could be reached, and it is the change the oracle has to catch.
"""

from __future__ import annotations

from html.parser import HTMLParser
from typing import List, Tuple

from super_research import transport
from super_research.adapters import (
    AdapterDescriptor,
    AdapterRequest,
    NativePage,
    NativeRecord,
    build_native_page,
)

DESCRIPTOR = AdapterDescriptor(
    adapter_id="public_page",
    adapter_version="1",
    access_class="K0",
    route_id=transport.PUBLIC_PAGE_ARTICLE_ROUTE,
    platform="",
    native_identity_namespace="",
    representation_kind="page",
    operator_identity="wikimedia",
)
CONTROL_DESCRIPTOR = AdapterDescriptor(
    adapter_id="public_page",
    adapter_version="1",
    access_class="K0",
    route_id=transport.PUBLIC_PAGE_CONTROL_ROUTE,
    platform="",
    native_identity_namespace="",
    representation_kind="page",
    operator_identity="iana",
)
SURFACE_DESCRIPTORS = (DESCRIPTOR, CONTROL_DESCRIPTOR)

# The same table the shipped adapter declares, so every clause but the last
# one passes: this fixture fails for the one reason it exists to fail for.
PAGE_SELECTIONS = {
    "article": (DESCRIPTOR, "title"),
    "control": (CONTROL_DESCRIPTOR, ""),
}

CONTENT_KIND = "web_page"
LINK_ATTRIBUTE = "link"


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        HTMLParser.__init__(self, convert_charrefs=True)
        self.links: List[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)


def _record(response: transport.TransportResponse) -> NativeRecord:
    parser = _LinkParser()
    parser.feed(response.body)
    parser.close()
    named: List[Tuple[str, str]] = [(LINK_ATTRIBUTE, link) for link in parser.links]
    return NativeRecord(
        canonical_content_kind=CONTENT_KIND,
        canonical_locator=response.url,
        body=response.body,
        attributes=tuple(named),
        native_position=0,
    )


def fetch_native_page(carrier: transport.Transport, request: AdapterRequest) -> NativePage:
    """Read whatever the caller named. This is the whole defect, in one line.

    A target that names a selection is served from the table like the shipped
    adapter; a target that names an address is read at that address. The second
    branch is the generic primitive: the caller supplies the host, so the route
    table stops being the thing that decides where a read can go.
    """

    named = request.target_ids[0] if request.target_ids else request.query
    kind, separator, argument = named.partition(":")
    if separator and kind in PAGE_SELECTIONS:
        descriptor, parameter = PAGE_SELECTIONS[kind]
        outbound = transport.build_transport_request(
            descriptor.route_id, {parameter: argument} if parameter else {}
        )
    elif named in PAGE_SELECTIONS:
        descriptor, _ = PAGE_SELECTIONS[named]
        outbound = transport.build_transport_request(descriptor.route_id, {})
    else:
        descriptor = DESCRIPTOR
        outbound = transport.TransportRequest(
            route_id=descriptor.route_id,
            method="GET",
            url=named,
            headers=(("User-Agent", transport.USER_AGENT), ("Accept", "text/html")),
        )

    response = carrier.fetch(outbound)
    if response.status != 200:
        return build_native_page(
            descriptor,
            (),
            observed_at=response.observed_at,
            outcome="failed",
            loss=("http_status",),
        )
    return build_native_page(
        descriptor, (_record(response),), observed_at=response.observed_at
    )
