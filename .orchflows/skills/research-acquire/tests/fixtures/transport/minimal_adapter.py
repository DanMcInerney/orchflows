"""A later adapter, written beside the tree: a DESCRIPTOR and a body parser.

This file is not part of the package. Nothing imports it, no discovery
pattern matches it, and ``tests/test_transport.py`` loads it by path. It
stands in for the adapters still to be added, and it deliberately writes no
failure handling at all — no status branch, no channel branch, no mention of
any verdict constant. Whatever it reports about a local network block it
inherits from the shared adapter protocol, which is exactly the claim it
exists to test.

It borrows the offline fixture route rather than naming one: only
``transport.py`` may define a route.
"""

from super_research import transport
from super_research.adapters import (
    AdapterDescriptor,
    NativeRecord,
    build_native_page,
    fetch_one_page,
)

DESCRIPTOR = AdapterDescriptor(
    adapter_id="minimal_probe",
    adapter_version="1",
    access_class="offline",
    route_id=transport.FAKE_OFFLINE_ROUTE,
    platform="fixture",
    native_identity_namespace="fixture",
    representation_kind="native",
    operator_identity="super-research-fixture",
)


def parse_body(response):
    """One record per nonempty line. The whole of this adapter's craft."""

    records = tuple(
        NativeRecord(
            canonical_content_kind="post",
            canonical_locator="fixture:line/{0}".format(index),
            body=line.strip(),
            native_position=index,
        )
        for index, line in enumerate(response.body.splitlines())
        if line.strip()
    )
    return build_native_page(
        DESCRIPTOR,
        records,
        observed_at=response.observed_at,
        outcome="ok" if records else "empty",
    )


def fetch_native_page(carrier, request):
    """The protocol's one entry point, delegating everything it can."""

    return fetch_one_page(
        DESCRIPTOR,
        carrier,
        params={"target": ",".join(request.target_ids)},
        parse=parse_body,
    )
