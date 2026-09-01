"""K0 Stack Exchange search/advanced with unix-second window bounds.

Placeholder pending implementation: the descriptor below is the declaration,
`fetch_native_page` is not yet written.
"""

from __future__ import annotations

from typing import Tuple

from .. import transport
from . import AdapterDescriptor, AdapterError, AdapterRequest, NativePage

DESCRIPTOR = AdapterDescriptor(
    adapter_id="stack_exchange",
    adapter_version="1",
    access_class="K0",
    route_id=transport.STACKEXCHANGE_SEARCH_ROUTE,
    platform="stackexchange",
    native_identity_namespace="stackexchange",
    representation_kind="native",
    operator_identity="stackexchange",
    min_interval_ms=1000,
    burst=1,
    reply_count_metric="answer_count",
    page_size=30,
)

SURFACE_DESCRIPTORS = (DESCRIPTOR,)


def fetch_native_page(carrier: transport.Transport, request: AdapterRequest) -> NativePage:
    raise AdapterError("stack_exchange is declared and not yet implemented")
