"""The defect this ticket closes, kept beside the tree as a wrong result.

This is ``web_search`` as it stood at `0a365d9`: it makes the call itself and
tests ``status != 200`` first, so a response the local network produced is
recorded as the platform's own http failure — a route that was never reached
becomes a platform gap in the artifact. It declares ``web_search``'s own
descriptor because it stands in for it, at the adapter seam and at the
runner's own branch.

Loaded by path, part of no package, and never imported by the tree under
test. It exists so the interception oracles can be shown to fail when the
claim they stand for is false. Its success path is deliberately bare: the
failure branch is the whole point.
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
            warnings=("http status {0} from {1}".format(response.status, DESCRIPTOR.route_id),),
            outcome="failed",
            loss=("http_status",),
        )
    return parse_body(response)
