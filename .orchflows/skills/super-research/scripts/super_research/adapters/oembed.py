"""K0 oEmbed hydration over six platforms' own documented endpoints.

Placeholder pending implementation: the descriptors below are the
declaration, `fetch_native_page` is not yet written.
"""

from __future__ import annotations

from typing import Tuple

from .. import transport
from . import AdapterDescriptor, AdapterError, AdapterRequest, NativePage


def _descriptor(route_id: str, platform: str) -> AdapterDescriptor:
    return AdapterDescriptor(
        adapter_id="oembed",
        adapter_version="1",
        access_class="K0",
        route_id=route_id,
        platform=platform,
        native_identity_namespace=platform,
        representation_kind="native",
        operator_identity=platform,
        min_interval_ms=1000,
        burst=1,
    )


DESCRIPTOR = _descriptor(transport.YOUTUBE_OEMBED_ROUTE, "youtube")
VIMEO_DESCRIPTOR = _descriptor(transport.VIMEO_OEMBED_ROUTE, "vimeo")
SPOTIFY_DESCRIPTOR = _descriptor(transport.SPOTIFY_OEMBED_ROUTE, "spotify")
SOUNDCLOUD_DESCRIPTOR = _descriptor(transport.SOUNDCLOUD_OEMBED_ROUTE, "soundcloud")
TIKTOK_DESCRIPTOR = _descriptor(transport.TIKTOK_OEMBED_ROUTE, "tiktok")
X_DESCRIPTOR = _descriptor(transport.X_PUBLISH_OEMBED_ROUTE, "x")

SURFACE_DESCRIPTORS = (
    DESCRIPTOR,
    VIMEO_DESCRIPTOR,
    SPOTIFY_DESCRIPTOR,
    SOUNDCLOUD_DESCRIPTOR,
    TIKTOK_DESCRIPTOR,
    X_DESCRIPTOR,
)

OEMBED_OPERATIONS = ("youtube", "vimeo", "spotify", "soundcloud", "tiktok", "x")

OPERATION_SURFACES = {
    "youtube": DESCRIPTOR,
    "vimeo": VIMEO_DESCRIPTOR,
    "spotify": SPOTIFY_DESCRIPTOR,
    "soundcloud": SOUNDCLOUD_DESCRIPTOR,
    "tiktok": TIKTOK_DESCRIPTOR,
    "x": X_DESCRIPTOR,
}


def operation_for(request: AdapterRequest) -> Tuple[str, str]:
    """The operation this call performs, and the argument it performs it on."""

    named = request.target_ids[0] if request.target_ids else request.query
    kind, separator, argument = named.partition(":")
    if separator and kind in OEMBED_OPERATIONS:
        return (kind, argument)
    return ("", named)


def fetch_native_page(carrier: transport.Transport, request: AdapterRequest) -> NativePage:
    raise AdapterError("oembed is declared and not yet implemented")
