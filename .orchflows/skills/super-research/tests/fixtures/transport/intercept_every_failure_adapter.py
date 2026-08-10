"""The opposite wrong result: an adapter that blames the network for everything.

It makes the call itself and types every failure status as a local block, so
the platform's own 503 and its authwall stop being recordable as platform
behavior at all. That erases the evidence this run exists to collect, which
is why the interception path must not widen into it.

Loaded by path, part of no package, and never imported by the tree under
test. It exists so the interception oracle can be shown to fail in the
direction criterion 3 guards.
"""

from super_research import transport
from super_research.adapters import AdapterDescriptor, build_native_page

DESCRIPTOR = AdapterDescriptor(
    adapter_id="intercept_every_failure_probe",
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
            warnings=("route {0} was blocked".format(DESCRIPTOR.route_id),),
            outcome="failed",
            loss=(transport.NETWORK_INTERCEPTED,),
        )
    return parse_body(response)
