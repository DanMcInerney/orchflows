"""Synthetic incorrect channel classification, used only by offline oracles."""

from super_research import transport
from super_research.adapters import AdapterDescriptor, build_native_page

DESCRIPTOR = AdapterDescriptor(
    adapter_id="rss_atom",
    adapter_version="1",
    access_class="K0",
    route_id=transport.WEB_PAGE_OPEN_ROUTE,
    platform="fixture",
    native_identity_namespace="",
    representation_kind="feed",
    operator_identity="fixture",
)


def parse_body(response):
    return build_native_page(
        DESCRIPTOR, (), observed_at=response.observed_at, outcome="empty"
    )


def fetch_native_page(carrier, request):
    response = carrier.fetch(
        transport.build_transport_request(
            DESCRIPTOR.route_id, {"url": request.query}
        )
    )
    if response.status != 200:
        return build_native_page(
            DESCRIPTOR,
            (),
            observed_at=response.observed_at,
            warnings=("route {0} was blocked".format(DESCRIPTOR.route_id),),
            outcome="failed",
            loss=(transport.NETWORK_INTERCEPTED,),
        )
    return parse_body(response)
