"""Private request construction, credential placement, and token memory."""

from __future__ import annotations

import json
import urllib.parse
from typing import Any, Callable, Dict, Mapping, Optional, Tuple

from ..routes import (
    HEADER_PLACEMENT,
    JSON_CONTENT_TYPE,
    OPEN_ORIGIN,
    QUERY_PLACEMENT,
    PublicClientCredential,
    RouteConstant,
)
from .transport_protocol import (
    USER_AGENT,
    TransportError,
    TransportRequest,
    TransportResponse,
    route_constant,
)


GUEST_TOKEN_FIELD = "guest_token"
GUEST_TOKEN_HEADER = "x-guest-token"
OPEN_URL_PARAM = "url"


def origin_key(request: TransportRequest) -> str:
    """The host one request reads, lowercased."""

    host = urllib.parse.urlsplit(request.url).hostname
    return host.lower() if host else request.route_id


def is_open_route(route: RouteConstant) -> bool:
    """Whether this route reads a caller-provided address."""

    return route.origin == OPEN_ORIGIN


def budget_key(
    request: TransportRequest,
    route_constants: Mapping[str, RouteConstant],
    origin_key_fn=origin_key,
) -> str:
    """The route, or the open route and host, that pays for this read."""

    if is_open_route(route_constant(request.route_id, route_constants)):
        return request.route_id + "@" + origin_key_fn(request)
    return request.route_id


def origin_locator(
    route_id: str, published: str, route_constants: Mapping[str, RouteConstant]
) -> str:
    """Resolve one published locator against its declared origin."""

    if not published:
        return ""
    if urllib.parse.urlsplit(published).scheme:
        return published
    return urllib.parse.urljoin(route_constant(route_id, route_constants).origin, published)


def route_credential(
    route_id: str,
    route_constants: Mapping[str, RouteConstant],
    credentials: Mapping[str, PublicClientCredential],
) -> Optional[PublicClientCredential]:
    """The public client credential this route needs, or None."""

    credential_id = route_constant(route_id, route_constants).credential_id
    if not credential_id:
        return None
    credential = credentials.get(credential_id)
    if credential is None:
        raise TransportError("unknown public client credential " + credential_id)
    return credential


def credentialed_url(url: str, credential: Optional[PublicClientCredential]) -> str:
    """Apply a query-placed credential at send time."""

    if credential is None or credential.placement != QUERY_PLACEMENT:
        return url
    separator = "&" if "?" in url else "?"
    return url + separator + urllib.parse.urlencode(((credential.name, credential.value),))


def credentialed_headers(
    headers: Tuple[Tuple[str, str], ...], credential: Optional[PublicClientCredential]
) -> Tuple[Tuple[str, str], ...]:
    """Apply a header-placed credential at send time."""

    if credential is None or credential.placement != HEADER_PLACEMENT:
        return tuple(headers)
    return tuple(headers) + ((credential.name, credential.value),)


def path_segments(route: RouteConstant, params: Dict[str, str]) -> str:
    """Spend declared path params in order, removing them from params."""

    values = [params.pop(name, "") for name in route.path_params]
    spent = ""
    for value in values:
        if not value:
            return spent
        spent = spent + "/" + urllib.parse.quote(value, safe="")
    return spent + route.path_suffix


def json_body(route: RouteConstant, params: Dict[str, str]) -> str:
    """Spend declared body params into deterministic JSON."""

    if not route.body_params:
        return ""
    body: Dict[str, Any] = {}
    for name, key_path in route.body_params:
        value = params.pop(name, "")
        if not value:
            continue
        held = body
        for key in key_path[:-1]:
            held = held.setdefault(key, {})
        held[key_path[-1]] = value
    return json.dumps(body, separators=(",", ":"), sort_keys=True) if body else ""


class GuestTokenStore:
    """Anonymous guest tokens kept only in process memory."""

    def __init__(self) -> None:
        self._tokens: Dict[str, str] = {}

    def token_for(self, token_route_id: str) -> str:
        return self._tokens.get(token_route_id, "")

    def claim(self, token_route_id: str) -> bool:
        if token_route_id in self._tokens:
            return False
        self._tokens[token_route_id] = ""
        return True

    def remember(self, token_route_id: str, token: str) -> None:
        self._tokens[token_route_id] = token

    def clear(self) -> None:
        self._tokens.clear()


GUEST_TOKENS = GuestTokenStore()


def tokened_headers(
    headers: Tuple[Tuple[str, str], ...],
    token_route_id: str,
    store: GuestTokenStore,
) -> Tuple[Tuple[str, str], ...]:
    """Attach an already-minted guest token, never minting one."""

    if not token_route_id:
        return tuple(headers)
    token = store.token_for(token_route_id)
    if not token:
        return tuple(headers)
    return tuple(headers) + ((GUEST_TOKEN_HEADER, token),)


def declared_origin_hosts(
    route_constants: Mapping[str, RouteConstant]
) -> Tuple[str, ...]:
    """Every declared non-open origin host, lowercased."""

    hosts = set()
    for route in route_constants.values():
        if is_open_route(route):
            continue
        host = urllib.parse.urlsplit(route.origin).hostname
        if host:
            hosts.add(host.lower())
    return tuple(sorted(hosts))


def open_read_refusal(
    url: str,
    route_constants: Mapping[str, RouteConstant],
    declared_origin_hosts_fn=declared_origin_hosts,
) -> str:
    """Why an open read is refused, or an empty string when admitted."""

    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https":
        return "an open read takes an https address, not " + repr(url)
    host = (parts.hostname or "").lower()
    if not host:
        return "an open read takes an address naming a host, not " + repr(url)
    if host in declared_origin_hosts_fn(route_constants):
        return (
            "an open read never lands on a host a declared route reads: {0}; ask that"
            " route".format(host)
        )
    return ""


def build_transport_request(
    route_id: str,
    params: Optional[Mapping[str, str]],
    route_constants: Mapping[str, RouteConstant],
) -> TransportRequest:
    """Build one credential-free request from declared route grammar."""

    route = route_constant(route_id, route_constants)
    supplied = dict(params or {})
    if is_open_route(route):
        url = supplied.pop(OPEN_URL_PARAM, "")
        refusal = open_read_refusal(url, route_constants)
        if refusal:
            raise TransportError(refusal)
        headers = (("User-Agent", USER_AGENT), ("Accept", route.accept))
        return TransportRequest(route_id=route_id, method=route.method, url=url, headers=headers)
    path = route.path + path_segments(route, supplied)
    body = json_body(route, supplied)
    pairs = [(key, value) for key, value in sorted(supplied.items()) if value != ""]
    url = route.origin + path
    if pairs:
        url = url + "?" + urllib.parse.urlencode(pairs)
    headers = (("User-Agent", USER_AGENT), ("Accept", route.accept))
    if body:
        headers = headers + (("Content-Type", JSON_CONTENT_TYPE),)
    return TransportRequest(
        route_id=route_id, method=route.method, url=url, headers=headers, body=body
    )


def _mint_guest_token(
    fetch: Callable[[TransportRequest], TransportResponse],
    token_route_id: str,
    build_request: Callable[[str], TransportRequest],
) -> str:
    """Issue one activation request and return its token, if any."""

    try:
        response = fetch(build_request(token_route_id))
    except TransportError:
        return ""
    if response.status != 200:
        return ""
    try:
        payload = json.loads(response.body)
    except ValueError:
        return ""
    token = payload.get(GUEST_TOKEN_FIELD) if isinstance(payload, dict) else None
    return token if isinstance(token, str) else ""
