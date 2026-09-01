"""K0 scholarly works over three origins: OpenAlex, Crossref, arXiv.

Placeholder pending implementation: the descriptors below are the
declaration, `fetch_native_page` is not yet written.
"""

from __future__ import annotations

from typing import Tuple

from .. import transport
from . import AdapterDescriptor, AdapterError, AdapterRequest, NativePage

DESCRIPTOR = AdapterDescriptor(
    adapter_id="scholarly",
    adapter_version="1",
    access_class="K0",
    route_id=transport.OPENALEX_WORKS_ROUTE,
    platform="openalex",
    native_identity_namespace="openalex",
    representation_kind="native",
    operator_identity="openalex",
    min_interval_ms=1000,
    burst=1,
    page_size=25,
)

CROSSREF_DESCRIPTOR = AdapterDescriptor(
    adapter_id="scholarly",
    adapter_version="1",
    access_class="K0",
    route_id=transport.CROSSREF_WORKS_ROUTE,
    platform="crossref",
    native_identity_namespace="crossref",
    representation_kind="native",
    operator_identity="crossref",
    min_interval_ms=1000,
    burst=1,
    page_size=20,
)

ARXIV_DESCRIPTOR = AdapterDescriptor(
    adapter_id="scholarly",
    adapter_version="1",
    access_class="K0",
    route_id=transport.ARXIV_QUERY_ROUTE,
    platform="arxiv",
    native_identity_namespace="arxiv",
    representation_kind="native",
    operator_identity="arxiv",
    # arXiv's own API terms ask for one request every three seconds.
    min_interval_ms=3000,
    burst=1,
    page_size=10,
)

SURFACE_DESCRIPTORS = (DESCRIPTOR, CROSSREF_DESCRIPTOR, ARXIV_DESCRIPTOR)

OPENALEX_OPERATION = "openalex"
CROSSREF_OPERATION = "crossref"
ARXIV_OPERATION = "arxiv"
SCHOLARLY_OPERATIONS = (OPENALEX_OPERATION, CROSSREF_OPERATION, ARXIV_OPERATION)


def operation_for(request: AdapterRequest) -> Tuple[str, str]:
    """The operation this call performs, and the argument it performs it on."""

    named = request.target_ids[0] if request.target_ids else request.query
    kind, separator, argument = named.partition(":")
    if separator and kind in SCHOLARLY_OPERATIONS:
        return (kind, argument)
    return (OPENALEX_OPERATION, named)


def fetch_native_page(carrier: transport.Transport, request: AdapterRequest) -> NativePage:
    raise AdapterError("scholarly is declared and not yet implemented")
