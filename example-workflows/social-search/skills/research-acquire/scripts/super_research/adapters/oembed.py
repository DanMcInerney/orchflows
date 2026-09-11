"""K0 oEmbed hydration over six platforms' own documented endpoints.

Measured 2026-09-01, all six keyless and all 200 from this host, each on one
platform URL passed as ``url``: YouTube's ``www.youtube.com/oembed?url=&
format=json`` answers ``author_name``, ``author_url``, ``title``,
``thumbnail_url`` and a ``type`` of ``video``. Vimeo's
``vimeo.com/api/oembed.json?url=`` answers ``title``, ``author_name``,
``author_url`` and ``type`` ``video`` on a public id, and 404 on a deleted or
private one. Spotify's ``open.spotify.com/oembed?url=`` answers ``title``,
``thumbnail_url`` and a ``type``, and never an ``author_name`` — a track has
no byline this endpoint states, and that absence is the payload's, not a
fetch failure. SoundCloud's ``soundcloud.com/oembed?url=&format=json``
answers ``title``, ``author_name``, ``author_url``, ``thumbnail_url``,
``description`` and a ``type`` of ``rich``. TikTok's
``www.tiktok.com/oembed?url=`` answers a ``title`` that is the clip's own
caption with its hashtags still in it, ``author_name``, ``author_unique_id``,
``author_url``, ``thumbnail_url``, an ``embed_product_id`` that is the video
id restated, and a ``type`` of ``video``. X's ``publish.x.com/oembed?url=``
answers ``author_name``, ``author_url`` and a ``type`` of ``rich``, and never
a ``title`` — the payload states none. ``publish.twitter.com`` answers this
host with a bare 301 onto ``publish.x.com``, so the newer name is the one
declared; a datacenter-IP survey elsewhere reported 402 from this same
endpoint and that did not reproduce from here, keyless, at any point in this
delivery. No provider states a structured publication date and none states
an engagement count of any kind — both are standing absences on every record
this module builds, never a zero or a time this module invented.

**One URL in, one record out.** A caller names the provider with a prefix —
``<provider>:<item url>`` — because an oEmbed endpoint is a hydration of one
address and there is no discovery shape here to default to the way a bare
symbol defaults to a stream elsewhere: the six prefixes are ``youtube``,
``vimeo``, ``spotify``, ``soundcloud``, ``tiktok`` and ``x``. A target naming
none of them, or naming one with no item url after the colon, is refused
before any call is made, the way :mod:`.public_page` refuses a selection it
does not serve.

**``type`` is the kind, exactly as the provider spelled it.** ``video`` and
``rich`` are not this module's words; they are read off the payload's own
``type`` and carried unchanged, so a seventh provider this module never saw
would still report its own kind rather than being folded into one of the
six above.

**The ``html`` blob is deliberately not carried.** Every provider answers one
— a ready-to-embed snippet, mostly a script tag and an iframe or blockquote —
and it is markup for a browser to render, not a fact about the item. Carrying
it would put one provider's whole rendering surface into ``attributes``
beside five providers that answer with none of their own, and a caller that
wants the embed can build it from the ``canonical_locator`` and its own
templates.

**Two standing losses, on every record this module returns.** No provider
states a publication time or a count of any kind, so
``UNKNOWN_PUBLICATION_TIME`` and ``ENGAGEMENT_UNAVAILABLE`` — the same two
codes :mod:`.web_search` stands on every index hit — are declared once as
each surface's ``standing_loss`` and ride on every record unconditionally,
never derived from what one particular answer happened to omit.

**Six routes, one budget each.** Three of the six share a host with another
declared route — YouTube's own site, Vimeo's, TikTok's — and each still gets
its own :class:`AdapterDescriptor` and its own paced budget, the same
"different endpoint, different route" shape the YouTube channel feed and
InnerTube pair already holds. Nothing here has a measured throttle, so every
descriptor keeps the protocol's conservative default rather than inventing
one.
"""

from __future__ import annotations

import json
from typing import Dict, Mapping, Optional, Tuple

from .. import transport
from . import (
    AdapterDescriptor,
    AdapterRequest,
    NativePage,
    NativeRecord,
    build_native_page,
    fetch_one_page,
)

# Every code this module can attach, spelled once each. The first three are
# read-time failures; the last two are the two standing absences the whole
# surface has, never conditional on what one answer happened to omit.
HTTP_STATUS = "http_status"
MALFORMED_JSON = "malformed_json"
SCHEMA_DRIFT = "schema_drift"
UNSELECTED_TARGET = "unselected_target"
UNKNOWN_PUBLICATION_TIME = "unknown_publication_time"
ENGAGEMENT_UNAVAILABLE = "engagement_unavailable"

# No provider in this roster row states a time or a count of any kind, so
# both stand on every record every one of the six surfaces returns.
STANDING_LOSS: Tuple[str, ...] = (UNKNOWN_PUBLICATION_TIME, ENGAGEMENT_UNAVAILABLE)


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
        standing_loss=STANDING_LOSS,
    )


# The primary descriptor: an unprefixed target names no provider at all here
# (unlike :mod:`.public_page`'s closed table, nothing defaults), so this is
# only what a refusal is attributed to and what ``runner`` reads for the
# adapter's access class.
DESCRIPTOR = _descriptor(transport.YOUTUBE_OEMBED_ROUTE, "youtube")
VIMEO_DESCRIPTOR = _descriptor(transport.VIMEO_OEMBED_ROUTE, "vimeo")
SPOTIFY_DESCRIPTOR = _descriptor(transport.SPOTIFY_OEMBED_ROUTE, "spotify")
SOUNDCLOUD_DESCRIPTOR = _descriptor(transport.SOUNDCLOUD_OEMBED_ROUTE, "soundcloud")
TIKTOK_DESCRIPTOR = _descriptor(transport.TIKTOK_OEMBED_ROUTE, "tiktok")
X_DESCRIPTOR = _descriptor(transport.X_PUBLISH_OEMBED_ROUTE, "x")

# Every route this adapter can reach, one descriptor each. The core collects
# route budgets from here, because a route nothing declares a budget for is a
# route the scheduler refuses to pace.
SURFACE_DESCRIPTORS = (
    DESCRIPTOR,
    VIMEO_DESCRIPTOR,
    SPOTIFY_DESCRIPTOR,
    SOUNDCLOUD_DESCRIPTOR,
    TIKTOK_DESCRIPTOR,
    X_DESCRIPTOR,
)

# The six operations, spelled once each. A caller names one with a prefix;
# there is no default, because a hydration target with no provider named
# would otherwise have to guess which of six origins to spend a call on.
YOUTUBE_OPERATION = "youtube"
VIMEO_OPERATION = "vimeo"
SPOTIFY_OPERATION = "spotify"
SOUNDCLOUD_OPERATION = "soundcloud"
TIKTOK_OPERATION = "tiktok"
X_OPERATION = "x"
OEMBED_OPERATIONS = (
    YOUTUBE_OPERATION,
    VIMEO_OPERATION,
    SPOTIFY_OPERATION,
    SOUNDCLOUD_OPERATION,
    TIKTOK_OPERATION,
    X_OPERATION,
)

OPERATION_SURFACES: Dict[str, AdapterDescriptor] = {
    YOUTUBE_OPERATION: DESCRIPTOR,
    VIMEO_OPERATION: VIMEO_DESCRIPTOR,
    SPOTIFY_OPERATION: SPOTIFY_DESCRIPTOR,
    SOUNDCLOUD_OPERATION: SOUNDCLOUD_DESCRIPTOR,
    TIKTOK_OPERATION: TIKTOK_DESCRIPTOR,
    X_OPERATION: X_DESCRIPTOR,
}

NATIVE_ORDERS: Dict[str, str] = {
    operation: operation + "_oembed_hydration_order" for operation in OEMBED_OPERATIONS
}

# Attributed only when a real provider was at least named; an unprefixed or
# unrecognised target never reached a route, so it has none of its own.
UNSELECTED_ORDER = "oembed_unselected_target_order"

# The one query parameter every surface takes, and the one two of the six
# also take. Measured: YouTube and SoundCloud's plain answers were not both
# proved JSON without it, so ``format=json`` is sent only where the evidence
# says it is needed; the other four answered JSON with no such param at all.
URL_PARAM = "url"
FORMAT_PARAM = "format"
FORMAT_JSON = "json"
FORMAT_JSON_OPERATIONS = (YOUTUBE_OPERATION, SOUNDCLOUD_OPERATION)

# Where an oEmbed answer keeps what this module reads. Declared, never
# searched for; every one of the six surfaces uses the same names for the
# same facts, because oEmbed is one specification and six implementations
# of it.
TYPE_KEY = "type"
TITLE_KEY = "title"
AUTHOR_NAME_KEY = "author_name"
AUTHOR_URL_KEY = "author_url"
THUMBNAIL_URL_KEY = "thumbnail_url"
PROVIDER_NAME_KEY = "provider_name"
AUTHOR_UNIQUE_ID_KEY = "author_unique_id"
DESCRIPTION_KEY = "description"
EMBED_PRODUCT_ID_KEY = "embed_product_id"

# The named facts an oEmbed answer carries that no record field already
# means, read in this fixed order regardless of the order the payload wrote
# them in, and only where the payload actually carries one.
ATTRIBUTE_KEYS: Tuple[str, ...] = (
    AUTHOR_URL_KEY,
    THUMBNAIL_URL_KEY,
    PROVIDER_NAME_KEY,
    AUTHOR_UNIQUE_ID_KEY,
    DESCRIPTION_KEY,
)


def _text(value: object) -> str:
    return value if isinstance(value, str) else ""


def operation_for(request: AdapterRequest) -> Tuple[str, str]:
    """The provider this call names, and the item url it names it for.

    A caller names the provider with a prefix on the query or the target;
    absent one, or naming a prefix this module does not serve, there is no
    provider to return, because nothing here is inferred from the characters
    in an argument the way a bare symbol would be elsewhere. The colon is the
    whole grammar: everything after the first one is the item url exactly as
    the caller spelled it, whether or not it itself contains one.
    """

    named = request.target_ids[0] if request.target_ids else request.query
    kind, separator, argument = named.partition(":")
    if separator and kind in OEMBED_OPERATIONS:
        return (kind, argument)
    return ("", named)


def _params_for(operation: str, item_url: str) -> Dict[str, str]:
    params: Dict[str, str] = {URL_PARAM: item_url}
    if operation in FORMAT_JSON_OPERATIONS:
        params[FORMAT_PARAM] = FORMAT_JSON
    return params


def _record_from_payload(
    descriptor: AdapterDescriptor, payload: Mapping[str, object], item_url: str
) -> Optional[NativeRecord]:
    """One oEmbed answer as its own provider reported it, or nothing at all.

    ``canonical_locator`` is the address the caller named, not any url the
    payload itself restates — that is the address this hydration was asked
    to read, and it is exact regardless of what a provider's own ``url``
    field happens to normalize it to. ``None`` here means the payload named
    no ``type``: an oEmbed answer that states no kind is not one this parser
    reads, and reporting it as an empty answer would be a lie about what the
    origin actually declined to state.
    """

    kind = _text(payload.get(TYPE_KEY))
    if not kind:
        return None
    attributes = tuple(
        (key, _text(payload.get(key))) for key in ATTRIBUTE_KEYS if _text(payload.get(key))
    )
    return NativeRecord(
        canonical_content_kind=kind,
        canonical_locator=item_url,
        native_item_id=_text(payload.get(EMBED_PRODUCT_ID_KEY)),
        title=_text(payload.get(TITLE_KEY)),
        author=_text(payload.get(AUTHOR_NAME_KEY)),
        attributes=attributes,
        native_position=0,
        loss=descriptor.standing_loss,
    )


def _answered(
    descriptor: AdapterDescriptor,
    response: transport.TransportResponse,
    native_order: str,
    records: Tuple[NativeRecord, ...] = (),
    outcome: str = "ok",
    warnings: Tuple[str, ...] = (),
    loss: Tuple[str, ...] = (),
) -> NativePage:
    return build_native_page(
        descriptor,
        records,
        observed_at=response.observed_at,
        native_order=native_order,
        warnings=warnings,
        outcome=outcome,
        loss=loss,
    )


def _failed(
    descriptor: AdapterDescriptor,
    response: transport.TransportResponse,
    native_order: str,
    loss: str,
    warning: str,
) -> NativePage:
    return _answered(
        descriptor, response, native_order, outcome="failed", warnings=(warning,), loss=(loss,)
    )


def _page_from(
    descriptor: AdapterDescriptor,
    response: transport.TransportResponse,
    native_order: str,
    operation: str,
    item_url: str,
) -> NativePage:
    """Turn one response the origin itself sent into exactly one page."""

    if response.status != 200:
        detail = (
            ": a 404 here usually means the item was deleted or made private"
            if response.status == 404
            else ""
        )
        return _failed(
            descriptor,
            response,
            native_order,
            HTTP_STATUS,
            "http status {0} from {1}{2}".format(response.status, descriptor.route_id, detail),
        )
    try:
        payload = json.loads(response.body)
    except ValueError:
        return _failed(
            descriptor,
            response,
            native_order,
            MALFORMED_JSON,
            "{0} answered 200 with no json body".format(operation),
        )
    if not isinstance(payload, Mapping):
        return _failed(
            descriptor,
            response,
            native_order,
            SCHEMA_DRIFT,
            "{0} answered 200 with a body this adapter cannot read as an oEmbed"
            " answer: the payload has changed shape".format(operation),
        )
    record = _record_from_payload(descriptor, payload, item_url)
    if record is None:
        return _failed(
            descriptor,
            response,
            native_order,
            SCHEMA_DRIFT,
            "{0} answered 200 with no {1}: the payload this adapter reads has"
            " changed shape".format(operation, TYPE_KEY),
        )
    return _answered(descriptor, response, native_order, records=(record,))


def _refusal_reason(named: str, operation: str) -> str:
    if operation:
        return (
            "{0!r} names the {1} provider and no item url: a hydration target"
            " is <provider>:<item url>".format(named, operation)
        )
    return (
        "{0!r} does not name one of this adapter's six providers ({1}): a"
        " hydration target is <provider>:<item url>".format(
            named, ", ".join(OEMBED_OPERATIONS)
        )
    )


def _refused(reason: str) -> NativePage:
    """A target this adapter will not read, refused without touching the network.

    The same placement :mod:`.public_page` refuses a bad selection at. There
    is no observation time on it because nothing was observed, and it is
    attributed to the primary descriptor because no real provider was ever
    selected for it to be attributed to instead.
    """

    return build_native_page(
        DESCRIPTOR,
        (),
        native_order=UNSELECTED_ORDER,
        warnings=(reason,),
        outcome="refused",
        loss=(UNSELECTED_TARGET,),
    )


def fetch_native_page(carrier: transport.Transport, request: AdapterRequest) -> NativePage:
    """Read one provider's oEmbed endpoint once and return exactly one NativePage.

    One call, one provider: a caller names exactly one of the six with a
    prefix and this reads exactly that surface. The refusal happens ahead of
    any read, so a target naming no provider costs the network nothing.
    """

    named = request.target_ids[0] if request.target_ids else request.query
    operation, item_url = operation_for(request)
    if not operation or not item_url:
        return _refused(_refusal_reason(named, operation))

    descriptor = OPERATION_SURFACES[operation]
    native_order = NATIVE_ORDERS[operation]

    def parse(response: transport.TransportResponse) -> NativePage:
        return _page_from(descriptor, response, native_order, operation, item_url)

    return fetch_one_page(
        descriptor,
        carrier,
        params=_params_for(operation, item_url),
        parse=parse,
        native_order=native_order,
    )
