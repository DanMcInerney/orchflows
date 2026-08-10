"""The defect this ticket closes, kept beside the tree as a wrong result.

Every adapter had this shape before the shared protocol read the channel: it
makes the call itself and tests ``status != 200`` first, so a response the
local network produced is recorded as the platform's own http failure — a
route that was never reached becomes a platform gap in the artifact.

Loaded by path, part of no package, and never imported by the tree under
test. It exists so the interception oracle can be shown to fail when the
claim it stands for is false.
"""

from super_research import transport
from super_research.adapters import AdapterDescriptor, build_native_page

DESCRIPTOR = AdapterDescriptor(
    adapter_id="status_first_probe",
    adapter_version="1",
    access_class="offline",
    route_id=transport.FAKE_OFFLINE_ROUTE,
    platform="fixture",
    native_identity_namespace="fixture",
    representation_kind="native",
    operator_identity="super-research-fixture",
)


def parse_body(response):
    """This fixture exists for its failure branch; a success is an empty page."""

    return build_native_page(
        DESCRIPTOR, (), observed_at=response.observed_at, outcome="empty"
    )


def fetch_native_page(carrier, request):
    response = carrier.fetch(
        transport.build_transport_request(
            DESCRIPTOR.route_id, {"target": ",".join(request.target_ids)}
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
