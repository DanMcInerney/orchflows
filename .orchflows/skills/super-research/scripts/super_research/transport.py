"""Transport seam: the sole owner of route constants and outbound requests.

Nothing outside this module may name a host, a path, or a vendor-published
public client credential. Callers that need to know whether a route is
reachable ask :func:`route_admissions`, which answers in booleans only.

Reliability bar: read-only. The default opener refuses any URL that is not
``https://`` and any method that is not ``GET`` or ``HEAD``, so no code
path here can mutate a remote resource, and the offline ``fake`` route can
never leave the process.
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
FAKE_OFFLINE_ROUTE = "fake_offline"

# One static identity. Never rotated: a rate limit is an observed constraint
# this package respects, not one it evades.
USER_AGENT = "super-research/0.1 (keyless read-only acquisition)"
REQUEST_TIMEOUT_SECONDS = 20
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
READ_METHODS = ("GET", "HEAD")


class TransportError(RuntimeError):
    """An outbound request was refused or could not be completed."""


@dataclass(frozen=True)
class RouteConstant:
    route_id: str
    access_class: str
    method: str
    origin: str
    path: str
    accept: str
    operator_identity: str = ""


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


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def route_constant(route_id: str) -> RouteConstant:
    route = ROUTE_CONSTANTS.get(route_id)
    if route is None:
        raise TransportError("unknown route " + route_id)
    return route


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
    if request.method not in READ_METHODS:
        raise TransportError("refusing a write-capable method " + request.method)

    outbound = urllib.request.Request(request.url, method=request.method)
    for name, value in request.headers:
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
        )
