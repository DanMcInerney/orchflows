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
            warnings=("http status {0} from {1}".format(response.status, DESCRIPTOR.route_id),),
            outcome="failed",
            loss=("http_status",),
        )
    return parse_body(response)
