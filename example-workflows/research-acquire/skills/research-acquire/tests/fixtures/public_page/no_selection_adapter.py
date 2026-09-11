"""A wrong `public_page`: one that reads nothing, and passes by doing so.

Written beside the tree to hold the oracle honest in the other direction. It
cannot be pointed anywhere, cannot reach a host nobody selected, and cannot
send a write verb — because it cannot do anything at all. Every clause about
what a read may not do is satisfied perfectly by never reading.

Without the coverage clause, this file is what row 2 would actually be
certifying. Nothing in the package imports it and no discovery pattern matches
it.
"""

from __future__ import annotations

from super_research import transport
from super_research.adapters import (
    AdapterDescriptor,
    AdapterRequest,
    NativePage,
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
SURFACE_DESCRIPTORS = (DESCRIPTOR,)

# The empty table. Enumerable, closed, and worthless.
PAGE_SELECTIONS = {}

UNSELECTED_TARGET = "unselected_target"


def fetch_native_page(carrier: transport.Transport, request: AdapterRequest) -> NativePage:
    """Refuse everything, which is one way to reach no host a caller chose."""

    return build_native_page(
        DESCRIPTOR,
        (),
        warnings=("this adapter selects nothing at all",),
        outcome="refused",
        loss=(UNSELECTED_TARGET,),
    )
