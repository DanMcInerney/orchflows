"""Transport seam: protocol policy, request construction, the urllib opener, and the carrier.

Route declarations live in :mod:`.routes` and are re-exported here, so this
is the one address callers reach route data at and the one module that
opens a socket.
"""

from __future__ import annotations

import email.utils
import gzip
import io
import ipaddress
import socket
import urllib.error
import urllib.parse
import urllib.request
import zlib
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

from .routes import (
    ARCTIC_SHIFT_SEARCH_ROUTE,
    X_SITE_ORIGIN,
    WEB_PAGE_OPEN_ROUTE,
    ARCTIC_SHIFT_POSTS_ROUTE,
    REDDIT_SHREDDIT_LISTING_ROUTE,
    REDDIT_SHREDDIT_SEARCH_ROUTE,
    REDDIT_SHREDDIT_SUBREDDIT_SEARCH_ROUTE,
    REDDIT_SHREDDIT_COMMENTS_ROUTE,
    HN_ALGOLIA_ITEM_ROUTE,
    FXTWITTER_API_ROUTE,
    HN_ALGOLIA_SEARCH_ROUTE,
    HN_FIREBASE_ITEM_ROUTE,
    GITHUB_REST_ROUTE,
    GITHUB_SEARCH_ROUTE,
    YOUTUBE_CHANNEL_FEED_ROUTE,
    CROSSREF_WORKS_ROUTE,
    ARXIV_QUERY_ROUTE,
    FAKE_OFFLINE_ROUTE,
    REDDIT_SITE_ORIGIN,
    ARCTIC_SHIFT_ORIGIN,
    OPEN_ORIGIN,
    ROUTE_CONSTANTS,
    RouteConstant,
)
from dataclasses import dataclass
from . import schema


USER_AGENT = "super-research/0.1 (keyless read-only acquisition)"
READ_METHODS = ("GET", "HEAD")

RATE_LIMITED_STATUS = 429
RATE_LIMITED = "rate_limited"
RETRY_AFTER_HEADER = "Retry-After"
RATE_LIMIT_RESET_HEADER = "X-RateLimit-Reset"
SECONDARY_RATE_LIMITED_STATUS = 403
SECONDARY_RATE_LIMIT_MARKERS = ("secondary rate limit",)
OBSERVED_AT_FORMAT = schema.INSTANT_FORMAT

AnsweredHeaders = Tuple[Tuple[str, str], ...]


ORIGIN_CONTENT = "origin_content"
ORIGIN_FAILURE = "origin_failure"
NETWORK_INTERCEPTED = "network_intercepted"
CHANNEL_VERDICTS = (ORIGIN_CONTENT, ORIGIN_FAILURE, NETWORK_INTERCEPTED)
CAPTIVE_PORTAL_MARKERS = ('<base href="/login/">',)


UNREACHABLE = "unreachable"
AUTH_REQUIRED = "auth_required"


class TransportError(RuntimeError):
    """An outbound request was refused or could not be completed.

    ``loss`` is the typed reason recorded by the step. ``reached`` says the
    origin answered; accounting preserves that distinction from local failure.
    """

    def __init__(self, message: str, loss: str = UNREACHABLE, reached: bool = False, route_id: str = "") -> None:
        RuntimeError.__init__(self, message)
        self.loss = loss
        self.reached = reached
        self.route_id = route_id


@dataclass(frozen=True)
class TransportRequest:
    """One public read, spelled completely before it is sent."""

    route_id: str
    method: str
    url: str
    headers: Tuple[Tuple[str, str], ...] = ()
    body: str = ""


@dataclass(frozen=True)
class TransportResponse:
    """One answer and the protocol facts every caller may retain."""

    route_id: str
    url: str
    status: int
    body: str
    content_type: str
    observed_at: str
    channel_verdict: str
    cache_hit: bool = False
    final_url: str = ""
    headers: AnsweredHeaders = ()


def channel_verdict(status: int, body: str) -> str:
    """Name the party that answered: the origin, or a local network appliance."""

    if 200 <= status < 300:
        return ORIGIN_CONTENT
    lowered = body.lower()
    for marker in CAPTIVE_PORTAL_MARKERS:
        if marker in lowered:
            return NETWORK_INTERCEPTED
    return ORIGIN_FAILURE


def rate_refused(status: int, body: str) -> bool:
    """Whether this answer is the origin asking for fewer requests."""

    if status == RATE_LIMITED_STATUS:
        return True
    if status != SECONDARY_RATE_LIMITED_STATUS:
        return False
    lowered = body.lower()
    for marker in SECONDARY_RATE_LIMIT_MARKERS:
        if marker in lowered:
            return True
    return False


def refusal_loss(status: int, body: str) -> Optional[str]:
    """The loss an origin's refusal carries, used by persisted refusal checkpoints."""
    if rate_refused(status, body):
        return RATE_LIMITED
    if status in (401, 403):
        return AUTH_REQUIRED
    return None


def header_value(headers: AnsweredHeaders, name: str) -> str:
    """One header off an answer, matched without regard to case."""

    wanted = name.lower()
    for held, value in headers:
        if held.lower() == wanted:
            return value
    return ""


def observed_moment(observed_at: str) -> Optional[datetime]:
    """The moment an answer says it was read, or None when unusable."""

    try:
        return datetime.strptime(observed_at, OBSERVED_AT_FORMAT).replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return None


def http_date_moment(stated: str) -> Optional[datetime]:
    """One RFC 7231 HTTP-date, or None for anything unreadable."""

    try:
        moment = email.utils.parsedate_to_datetime(stated)
    except (TypeError, ValueError, OverflowError):
        return None
    if moment is None:
        return None
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=timezone.utc)


RATE_LIMIT_RESET_COUNTDOWN_CEILING_SECONDS = 100000000


def epoch_moment(stated: str, read_at: Optional[datetime] = None) -> Optional[datetime]:
    """When an X-RateLimit-Reset says its window ends, in either spelling."""

    held = stated.strip()
    if not held:
        return None
    try:
        seconds = int(held)
    except ValueError:
        return None
    if seconds < RATE_LIMIT_RESET_COUNTDOWN_CEILING_SECONDS:
        if read_at is None or seconds < 0:
            return None
        return read_at + timedelta(seconds=seconds)
    try:
        return datetime.fromtimestamp(seconds, timezone.utc)
    except (ValueError, OverflowError, OSError):
        return None


def remaining_seconds(deadline: Optional[datetime], read_at: Optional[datetime]) -> float:
    """Seconds from the read moment until an absolute deadline."""

    if deadline is None or read_at is None:
        return 0.0
    return max(0.0, (deadline - read_at).total_seconds())


def retry_after_seconds(stated: str, read_at: Optional[datetime]) -> float:
    """Retry-After in either RFC 7231 spelling, as seconds remaining."""

    held = stated.strip()
    if not held:
        return 0.0
    if held.isascii() and held.isdigit():
        return float(held)
    return remaining_seconds(http_date_moment(held), read_at)


def stated_cooldown_seconds(response: TransportResponse) -> float:
    """The longest usable interval this origin asked to be left alone."""

    read_at = observed_moment(response.observed_at)
    return max(
        retry_after_seconds(header_value(response.headers, RETRY_AFTER_HEADER), read_at),
        remaining_seconds(
            epoch_moment(header_value(response.headers, RATE_LIMIT_RESET_HEADER), read_at),
            read_at,
        ),
    )


def route_constant(route_id: str) -> RouteConstant:
    """Resolve a declared route, or refuse an unknown id."""

    route = ROUTE_CONSTANTS.get(route_id)
    if route is None:
        raise TransportError("unknown route " + route_id)
    return route


OPEN_URL_PARAM = "url"


def origin_key(request: TransportRequest) -> str:
    """The host one request reads, lowercased."""

    host = urllib.parse.urlsplit(request.url).hostname
    return host.lower() if host else request.route_id


def is_open_route(route: RouteConstant) -> bool:
    """Whether this route reads a caller-provided address."""

    return route.origin == OPEN_ORIGIN


def budget_key(request: TransportRequest) -> str:
    """The measured budget paying for this read, separate from cache identity."""

    if is_open_route(route_constant(request.route_id)):
        return request.route_id + "@" + origin_key(request)
    return request.route_id


def origin_locator(route_id: str, published: str) -> str:
    """Resolve one published locator against its declared origin."""

    if not published:
        return ""
    if urllib.parse.urlsplit(published).scheme:
        return published
    return urllib.parse.urljoin(route_constant(route_id).origin, published)


def path_segments(route: RouteConstant, params: Dict[str, str]) -> str:
    """Spend declared path params in order, removing them from params."""

    values = [params.pop(name, "") for name in route.path_params]
    spent = ""
    for value in values:
        if not value:
            return spent
        spent = spent + "/" + urllib.parse.quote(value, safe="")
    return spent + route.path_suffix


def declared_origin_hosts() -> Tuple[str, ...]:
    """Every declared non-open origin host, lowercased."""

    hosts = set()
    for route in ROUTE_CONSTANTS.values():
        if is_open_route(route):
            continue
        host = urllib.parse.urlsplit(route.origin).hostname
        if host:
            hosts.add(host.lower())
    return tuple(sorted(hosts))


def open_read_refusal(url: str) -> str:
    """Why an open read is refused, or an empty string when admitted."""

    try:
        parts = urllib.parse.urlsplit(url)
        host = (parts.hostname or "").lower().rstrip(".")
        port = parts.port
    except ValueError:
        return "an open read takes a valid public HTTPS address"
    if any(ord(character) <= 32 or ord(character) == 127 for character in url):
        return "an open read refuses whitespace and control characters in addresses"
    if parts.scheme != "https":
        return "an open read takes an https address, not " + repr(url)
    if not host:
        return "an open read takes an address naming a host, not " + repr(url)
    if parts.username is not None or parts.password is not None or port not in (None, 443):
        return "an open read refuses credentials and nonstandard ports"
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal")) or "." not in host:
        return "an open read takes a public host, not " + repr(host)
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        if not address.is_global:
            return "an open read refuses non-public IP addresses"
    if host in declared_origin_hosts():
        return (
            "an open read never lands on a host a declared route reads: {0}; ask that"
            " route".format(host)
        )
    return ""


def _validate_open_destination(url: str) -> None:
    """Check the actual destination before an open read or redirect reaches it."""
    refusal = open_read_refusal(url)
    if refusal:
        raise TransportError(refusal)
    host = urllib.parse.urlsplit(url).hostname
    try:
        answers = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except OSError as error:
        raise TransportError("could not resolve the open-read host") from error
    if not answers or any(not ipaddress.ip_address(answer[4][0]).is_global for answer in answers):
        raise TransportError("an open read refuses hosts resolving to non-public addresses")


class _PublicReadRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _validate_open_destination(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def build_transport_request(
    route_id: str, params: Optional[Mapping[str, str]] = None
) -> TransportRequest:
    """Build one credential-free request from declared route grammar."""

    route = route_constant(route_id)
    supplied = dict(params or {})
    if is_open_route(route):
        url = supplied.pop(OPEN_URL_PARAM, "")
        refusal = open_read_refusal(url)
        if refusal:
            raise TransportError(refusal)
        headers = (("User-Agent", USER_AGENT), ("Accept", route.accept))
        return TransportRequest(route_id=route_id, method=route.method, url=url, headers=headers)
    path = route.path + path_segments(route, supplied)
    pairs = [(key, value) for key, value in sorted(supplied.items()) if value != ""]
    url = route.origin + path
    if pairs:
        url = url + "?" + urllib.parse.urlencode(pairs)
    headers = (("User-Agent", USER_AGENT), ("Accept", route.accept))
    return TransportRequest(
        route_id=route_id, method=route.method, url=url, headers=headers
    )


REQUEST_TIMEOUT_SECONDS = 20
MAX_RESPONSE_BYTES = 8 * 1024 * 1024


def utc_now_iso() -> str:
    """Read the facade's wall clock in the artifact timestamp format."""

    return datetime.now(timezone.utc).strftime(OBSERVED_AT_FORMAT)


def answering_address(response: Any, request: TransportRequest) -> str:
    """The address at which the public read was answered."""

    return response.url


def answered_headers(carried: Any) -> AnsweredHeaders:
    """What an answer carried, as ordered string pairs."""

    if not carried:
        return ()
    return tuple((str(name), str(value)) for name, value in carried.items())


def decoded_body(raw: bytes, headers: Any) -> str:
    """One answer's bytes as text, gunzipped when the origin says it gzipped.

    Origins may compress an answer whether or not the request asked. Gzip
    bytes decoded as UTF-8 are garbage an adapter can only
    type as `malformed_json` — a wrong reading of an origin that answered
    correctly. The stated encoding is honored here, bounded by the same byte
    ceiling the raw read has. A body that declares gzip and is not gzip is a
    transport failure: the read is refused rather than decoded into something
    an adapter would mis-type.
    """

    encoding = headers.get("Content-Encoding", "") if headers else ""
    if encoding.strip().lower() == "gzip":
        # Three ways the bytes can fail the declaration — no gzip header, a
        # stream cut short, a corrupt deflate body — and one typed failure.
        try:
            raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read(MAX_RESPONSE_BYTES)
        except (OSError, EOFError, zlib.error) as error:
            raise TransportError("the answer declared gzip and its bytes are not gzip") from error
    return raw.decode("utf-8", errors="replace")


def urlopen_read(request: TransportRequest) -> Tuple[int, str, str, str, AnsweredHeaders]:
    """One bounded HTTPS read through urllib on an admitted method.

    The answer is the status, the body as text, its content type, the address
    it was answered from, and its headers. A read the transport declines to
    send raises :class:`TransportError` before any socket is opened.
    """

    if not request.url.startswith("https://"):
        raise TransportError("refusing a non-https url for route " + request.route_id)
    if request.method not in READ_METHODS:
        raise TransportError(
            "refusing a write-capable method {0} on route {1}".format(
                request.method, request.route_id
            )
        )
    open_route = is_open_route(route_constant(request.route_id))
    if open_route:
        _validate_open_destination(request.url)
    if request.body:
        raise TransportError("a public read cannot carry a request body")
    if any(name.lower() in ("authorization", "cookie", "x-api-key", "x-guest-token")
           for name, _ in request.headers):
        raise TransportError("a public read cannot carry credentials")
    outbound = urllib.request.Request(request.url, method=request.method)
    for name, value in request.headers:
        outbound.add_header(name, value)
    opener = (urllib.request.build_opener(_PublicReadRedirect()).open
              if open_route else urllib.request.urlopen)
    try:
        with opener(outbound, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return (
                response.status,
                decoded_body(response.read(MAX_RESPONSE_BYTES), response.headers),
                response.headers.get("Content-Type", ""),
                answering_address(response, request),
                answered_headers(response.headers),
            )
    except urllib.error.HTTPError as error:
        return (
            error.code,
            decoded_body(error.read(MAX_RESPONSE_BYTES), error.headers),
            error.headers.get("Content-Type", "") if error.headers else "",
            answering_address(error, request),
            answered_headers(error.headers),
        )
    except OSError as error:
        raise TransportError("transport failed for " + request.route_id) from error


class Transport:
    """One run's outbound channel. Every attempt is recorded in order.

    The opener answers the way :func:`urlopen_read` does — status, body,
    content type, the answering address, and headers — or raises
    :class:`TransportError`.
    """

    def __init__(
        self,
        opener: Optional[
            Callable[[TransportRequest], Tuple[int, str, str, str, AnsweredHeaders]]
        ] = None,
        now: Optional[Callable[[], str]] = None,
    ) -> None:
        self._opener = opener if opener is not None else urlopen_read
        self._now = now if now is not None else utc_now_iso
        self.calls: List[TransportRequest] = []

    def fetch(self, request: TransportRequest) -> TransportResponse:
        self.calls.append(request)
        status, body, content_type, final_url, headers = self._opener(request)
        return TransportResponse(
            route_id=request.route_id,
            url=request.url,
            status=status,
            body=body,
            content_type=content_type,
            observed_at=self._now(),
            channel_verdict=channel_verdict(status, body),
            final_url=final_url,
            headers=headers,
        )
