"""K4 GDELT DOC 2.0: a global news index with an origin-side time bound.

Placeholder pending implementation: the descriptor below is the declaration,
`fetch_native_page` is not yet written.
"""

from __future__ import annotations

from typing import Tuple

from .. import transport
from . import AdapterDescriptor, AdapterError, AdapterRequest, NativePage

DESCRIPTOR = AdapterDescriptor(
    adapter_id="gdelt",
    adapter_version="1",
    access_class="K4",
    route_id=transport.GDELT_DOC_ROUTE,
    platform="gdelt",
    native_identity_namespace="gdelt",
    representation_kind="index",
    operator_identity="gdelt",
    # The origin's own stated ceiling, in a plain-text 429 body measured
    # 2026-09-01: one request per five seconds.
    min_interval_ms=5000,
    burst=1,
    cooldown_ms=60000,
    page_size=75,
)

SURFACE_DESCRIPTORS = (DESCRIPTOR,)


def fetch_native_page(carrier: transport.Transport, request: AdapterRequest) -> NativePage:
    raise AdapterError("gdelt is declared and not yet implemented")
