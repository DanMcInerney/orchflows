"""K0 Wikimedia per-article pageviews: attention over time, window in the path.

Placeholder pending implementation: the descriptor below is the declaration,
`fetch_native_page` is not yet written.
"""

from __future__ import annotations

from typing import Tuple

from .. import transport
from . import AdapterDescriptor, AdapterError, AdapterRequest, NativePage

DESCRIPTOR = AdapterDescriptor(
    adapter_id="wikimedia_pageviews",
    adapter_version="1",
    access_class="K0",
    route_id=transport.WIKIMEDIA_PAGEVIEWS_ROUTE,
    platform="wikimedia",
    native_identity_namespace="wikimedia",
    representation_kind="native",
    operator_identity="wikimedia",
    min_interval_ms=1000,
    burst=1,
)

SURFACE_DESCRIPTORS = (DESCRIPTOR,)


def fetch_native_page(carrier: transport.Transport, request: AdapterRequest) -> NativePage:
    raise AdapterError("wikimedia_pageviews is declared and not yet implemented")
