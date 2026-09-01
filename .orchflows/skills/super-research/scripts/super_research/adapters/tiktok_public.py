"""K2 TikTok public pages: the web client's own rehydration JSON, no script run.

Placeholder pending implementation: the descriptors below are the
declaration, `fetch_native_page` is not yet written.
"""

from __future__ import annotations

from typing import Tuple

from .. import transport
from . import AdapterDescriptor, AdapterError, AdapterRequest, NativePage

DESCRIPTOR = AdapterDescriptor(
    adapter_id="tiktok_public",
    adapter_version="1",
    access_class="K2",
    route_id=transport.TIKTOK_VIDEO_PAGE_ROUTE,
    platform="tiktok",
    native_identity_namespace="tiktok",
    representation_kind="native",
    operator_identity="tiktok",
    min_interval_ms=2000,
    burst=1,
    comment_count_metric="commentCount",
)

PROFILE_DESCRIPTOR = AdapterDescriptor(
    adapter_id="tiktok_public",
    adapter_version="1",
    access_class="K2",
    route_id=transport.TIKTOK_PROFILE_PAGE_ROUTE,
    platform="tiktok",
    native_identity_namespace="tiktok",
    representation_kind="native",
    operator_identity="tiktok",
    min_interval_ms=2000,
    burst=1,
)

SURFACE_DESCRIPTORS = (DESCRIPTOR, PROFILE_DESCRIPTOR)

VIDEO_OPERATION = "video"
PROFILE_OPERATION = "profile"
TIKTOK_OPERATIONS = (VIDEO_OPERATION, PROFILE_OPERATION)


def operation_for(request: AdapterRequest) -> Tuple[str, str]:
    """The operation this call performs, and the argument it performs it on."""

    named = request.target_ids[0] if request.target_ids else request.query
    kind, separator, argument = named.partition(":")
    if separator and kind in TIKTOK_OPERATIONS:
        return (kind, argument)
    return (PROFILE_OPERATION, named)


def fetch_native_page(carrier: transport.Transport, request: AdapterRequest) -> NativePage:
    raise AdapterError("tiktok_public is declared and not yet implemented")
