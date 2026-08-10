"""The opposite wrong result: an adapter that blames the network for everything.

The same ``web_search`` stand-in, wrong in the other direction. It makes the
call itself and types every failure status as a local block, so the
platform's own 503 and its authwall stop being recordable as platform
behavior at all — the evidence this run exists to collect. That is what the
interception path must never widen into.

Loaded by path, part of no package, and never imported by the tree under
test. It exists so the interception oracle can be shown to fail in the
direction criterion 3 guards.
"""

from super_research import transport
from super_research.adapters import AdapterDescriptor, build_native_page

DESCRIPTOR = AdapterDescriptor(
    adapter_id="web_search",
    adapter_version="1",
    access_class="K4",
    route_id=transport.DDG_HTML_ROUTE,
    platform="duckduckgo",
    native_identity_namespace="",
    representation_kind="index",
    operator_identity="duckduckgo",
)


def parse_body(response):
    return build_native_page(
        DESCRIPTOR, (), observed_at=response.observed_at, outcome="empty"
    )


def fetch_native_page(carrier, request):
    response = carrier.fetch(
        transport.build_transport_request(
            DESCRIPTOR.route_id, {"q": request.query, "s": request.cursor}
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
