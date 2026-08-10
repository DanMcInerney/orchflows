"""Transport seam: the sole owner of route constants and outbound requests.

Nothing outside this module may name a host, a path, or a vendor-published
public client credential. Callers that need to know whether a route is
reachable ask :func:`route_admissions`, which answers in booleans only.

This module also owns the captive-portal detector. Every response it returns
names the party that answered it — the origin, or a local network appliance —
so a caller can never record this network's block as a platform gap.

Reliability bar: read-only. The default opener refuses any URL that is not
``https://`` and any method outside :func:`admitted_methods` — reads
everywhere, plus one closed exception for minting an anonymous guest token,
which creates nothing at the origin. No code path here can mutate a remote
resource, and the offline ``fake`` route can never leave the process.
"""

from __future__ import annotations

import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Dict, List, Mapping, Optional, Tuple

DDG_HTML_ROUTE = "ddg_html"
ARCTIC_SHIFT_POSTS_ROUTE = "arctic_shift_posts_ids"
X_GUEST_ACTIVATE_ROUTE = "x_guest_activate"
FAKE_OFFLINE_ROUTE = "fake_offline"

YOUTUBE_INNERTUBE_WEB_KEY = "youtube_innertube_web_key"
INSTAGRAM_WEB_APP_ID = "instagram_web_app_id"
X_GUEST_PUBLIC_BEARER = "x_guest_public_bearer"

# One static identity. Never rotated: a rate limit is an observed constraint
# this package respects, not one it evades.
USER_AGENT = "super-research/0.1 (keyless read-only acquisition)"
REQUEST_TIMEOUT_SECONDS = 20
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
READ_METHODS = ("GET", "HEAD")

# The one closed exception to reads-only, named by route id: minting an
# anonymous guest token needs a POST, and that POST creates no account,
# session, or content at the origin. Nothing else may leave a read.
TOKEN_ACTIVATION_ROUTES = (X_GUEST_ACTIVATE_ROUTE,)

# Where a public client credential goes on the wire.
CREDENTIAL_PLACEMENTS = ("query", "header")

# Which party answered a request. `network_intercepted` is also the typed
# loss code a caller attaches, so an intercepted route is reported as
# unverified rather than as a platform gap.
ORIGIN_CONTENT = "origin_content"
ORIGIN_FAILURE = "origin_failure"
NETWORK_INTERCEPTED = "network_intercepted"
CHANNEL_VERDICTS = (ORIGIN_CONTENT, ORIGIN_FAILURE, NETWORK_INTERCEPTED)

# The one measured captive-portal signature (findings.md §0, 2026-08-10):
# this host's appliance answered tiktok.com and ecosia.org with HTTP 503 and
# a body carrying this marker, while example.com and wikipedia.org returned
# genuine 200 origin content. Widening this set requires a new measurement:
# a marker an origin also emits would record platform behavior as a local
# block, which is the mirror of the error §0 forbids.
CAPTIVE_PORTAL_MARKERS = ('<base href="/login/">',)


class TransportError(RuntimeError):
    """An outbound request was refused or could not be completed."""


@dataclass(frozen=True)
class PublicClientCredential:
    """A `K1` credential the vendor ships publicly in its own web client.

    It is not a user secret and it is never a manifest or artifact field: it
    is a route constant this module attaches at send time, so nothing the
    package records can carry it.
    """

    credential_id: str
    vendor: str
    placement: str
    name: str
    value: str


PUBLIC_CLIENT_CREDENTIALS: Dict[str, PublicClientCredential] = {
    # findings.md §1 (YouTube) records this key elided, as `AIzaSy...11qcW8`:
    # it is embedded in youtube.com's own page source, and no account or
    # console project is involved. The middle is not in the evidence, so the
    # value below must be re-proved against a live probe before any YouTube
    # route is declared live.
    YOUTUBE_INNERTUBE_WEB_KEY: PublicClientCredential(
        credential_id=YOUTUBE_INNERTUBE_WEB_KEY,
        vendor="youtube",
        placement="query",
        name="key",
        value="AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8",
    ),
    # findings.md §1 (Instagram) records this one in full: the measured probe
    # sent `x-ig-app-id: 936619743392459` and got 200 with profile data.
    INSTAGRAM_WEB_APP_ID: PublicClientCredential(
        credential_id=INSTAGRAM_WEB_APP_ID,
        vendor="instagram",
        placement="header",
        name="x-ig-app-id",
        value="936619743392459",
    ),
    # findings.md §1 (X) records the activation returning 200 with a guest
    # token but does not record the bearer the probe sent. This is the bearer
    # x.com ships in its own logged-out web bundle; like the InnerTube key it
    # must be re-proved live before the X routes are declared live. The guest
    # token it mints is per-run state, never a constant.
    X_GUEST_PUBLIC_BEARER: PublicClientCredential(
        credential_id=X_GUEST_PUBLIC_BEARER,
        vendor="x",
        placement="header",
        name="Authorization",
        value=(
            "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs"
            "%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA"
        ),
    ),
}


@dataclass(frozen=True)
class RouteConstant:
    route_id: str
    access_class: str
    method: str
    origin: str
    path: str
    accept: str
    operator_identity: str = ""
    credential_id: str = ""


ROUTE_CONSTANTS: Dict[str, RouteConstant] = {
    DDG_HTML_ROUTE: RouteConstant(
        route_id=DDG_HTML_ROUTE,
        access_class="K4",
        method="GET",
        origin="https://html.duckduckgo.com",
        path="/html/",
        accept="text/html",
        operator_identity="duckduckgo",
    ),
    ARCTIC_SHIFT_POSTS_ROUTE: RouteConstant(
        route_id=ARCTIC_SHIFT_POSTS_ROUTE,
        access_class="K3",
        method="GET",
        origin="https://arctic-shift.photon-reddit.com",
        path="/api/posts/ids",
        accept="application/json",
        operator_identity="arctic-shift",
    ),
    X_GUEST_ACTIVATE_ROUTE: RouteConstant(
        route_id=X_GUEST_ACTIVATE_ROUTE,
        access_class="K1",
        method="POST",
        origin="https://api.twitter.com",
        path="/1.1/guest/activate.json",
        accept="application/json",
        operator_identity="x",
        credential_id=X_GUEST_PUBLIC_BEARER,
    ),
    FAKE_OFFLINE_ROUTE: RouteConstant(
        route_id=FAKE_OFFLINE_ROUTE,
        access_class="offline",
        method="GET",
        origin="fixture://fake",
        path="/page",
        accept="application/json",
        operator_identity="super-research-fixture",
    ),
}


@dataclass(frozen=True)
class TransportRequest:
    route_id: str
    method: str
    url: str
    headers: Tuple[Tuple[str, str], ...] = ()


@dataclass(frozen=True)
class TransportResponse:
    route_id: str
    url: str
    status: int
    body: str
    content_type: str
    observed_at: str
    channel_verdict: str


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def channel_verdict(status: int, body: str) -> str:
    """Name the party that answered: the origin, or a local network appliance.

    An interception needs both halves of the measured signature — a failure
    status and a portal marker. A success is never one: this host's control
    probes show a 2xx is genuine origin content, and an origin's own login
    page must stay platform behavior. A failure without the marker is the
    origin's own, so a real platform gap is still recordable as one.
    """

    if 200 <= status < 300:
        return ORIGIN_CONTENT
    lowered = body.lower()
    for marker in CAPTIVE_PORTAL_MARKERS:
        if marker in lowered:
            return NETWORK_INTERCEPTED
    return ORIGIN_FAILURE


def route_constant(route_id: str) -> RouteConstant:
    route = ROUTE_CONSTANTS.get(route_id)
    if route is None:
        raise TransportError("unknown route " + route_id)
    return route


def admitted_methods(route_id: str) -> Tuple[str, ...]:
    """Every method this route may use: reads, plus token activation where declared."""

    if route_id in TOKEN_ACTIVATION_ROUTES:
        return READ_METHODS + ("POST",)
    return READ_METHODS


def route_credential(route_id: str) -> Optional[PublicClientCredential]:
    """The public client credential this route needs, or None for a keyless one."""

    credential_id = route_constant(route_id).credential_id
    if not credential_id:
        return None
    credential = PUBLIC_CLIENT_CREDENTIALS.get(credential_id)
    if credential is None:
        raise TransportError("unknown public client credential " + credential_id)
    return credential


def credentialed_url(url: str, credential: Optional[PublicClientCredential]) -> str:
    """Apply a query-placed credential. Called at send time, never before."""

    if credential is None or credential.placement != "query":
        return url
    separator = "&" if "?" in url else "?"
    return url + separator + urllib.parse.urlencode(((credential.name, credential.value),))


def credentialed_headers(
    headers: Tuple[Tuple[str, str], ...], credential: Optional[PublicClientCredential]
) -> Tuple[Tuple[str, str], ...]:
    """Apply a header-placed credential. Called at send time, never before."""

    if credential is None or credential.placement != "header":
        return tuple(headers)
    return tuple(headers) + ((credential.name, credential.value),)


def route_admissions() -> Dict[str, bool]:
    """Per-route booleans — the only route knowledge the router ever sees.

    A route is admitted when it needs no user credential. ``K5`` is the one
    credentialed class, so it is the one class that can answer False here.
    """

    return {
        route_id: route.access_class != "K5"
        for route_id, route in sorted(ROUTE_CONSTANTS.items())
    }


def build_transport_request(
    route_id: str, params: Optional[Mapping[str, str]] = None
) -> TransportRequest:
    route = route_constant(route_id)
    pairs = [(key, value) for key, value in sorted((params or {}).items()) if value != ""]
    url = route.origin + route.path
    if pairs:
        url = url + "?" + urllib.parse.urlencode(pairs)
    return TransportRequest(
        route_id=route_id,
        method=route.method,
        url=url,
        headers=(("User-Agent", USER_AGENT), ("Accept", route.accept)),
    )


def urlopen_response(request: TransportRequest) -> Tuple[int, str, str]:
    """Default opener: one bounded read-only HTTPS request, no redirect games."""

    if not request.url.startswith("https://"):
        raise TransportError("refusing a non-https url for route " + request.route_id)
    if request.method not in admitted_methods(request.route_id):
        raise TransportError(
            "refusing a write-capable method {0} on route {1}".format(
                request.method, request.route_id
            )
        )

    credential = route_credential(request.route_id)
    outbound = urllib.request.Request(
        credentialed_url(request.url, credential), method=request.method
    )
    for name, value in credentialed_headers(request.headers, credential):
        outbound.add_header(name, value)
    try:
        with urllib.request.urlopen(outbound, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return (
                response.status,
                response.read(MAX_RESPONSE_BYTES).decode("utf-8", errors="replace"),
                response.headers.get("Content-Type", ""),
            )
    except urllib.error.HTTPError as error:
        # A status-bearing error is data, not a tool failure: the adapter
        # types it, and T02's detector separates a local block from an origin.
        return (
            error.code,
            error.read(MAX_RESPONSE_BYTES).decode("utf-8", errors="replace"),
            error.headers.get("Content-Type", "") if error.headers else "",
        )
    except OSError as error:
        raise TransportError("transport failed for " + request.route_id) from error


class Transport:
    """One run's outbound channel. Every attempt is recorded, in order."""

    def __init__(
        self,
        opener: Optional[Callable[[TransportRequest], Tuple[int, str, str]]] = None,
        now: Optional[Callable[[], str]] = None,
    ) -> None:
        self._opener = opener if opener is not None else urlopen_response
        self._now = now if now is not None else utc_now_iso
        self.calls: List[TransportRequest] = []

    def fetch(self, request: TransportRequest) -> TransportResponse:
        # Recorded before the opener runs, so a raising opener still leaves the
        # attempt visible: "an adapter never retries" is checked against this log.
        self.calls.append(request)
        status, body, content_type = self._opener(request)
        return TransportResponse(
            route_id=request.route_id,
            url=request.url,
            status=status,
            body=body,
            content_type=content_type,
            observed_at=self._now(),
            channel_verdict=channel_verdict(status, body),
        )
