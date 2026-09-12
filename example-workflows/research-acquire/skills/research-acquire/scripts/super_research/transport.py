"""Transport seam: protocol policy, request construction, credentials, the urllib opener, and the carrier.

Route declarations live in :mod:`.routes` and are re-exported here, so this
is the one address callers reach route data at and the one module that
opens a socket.
"""

from __future__ import annotations

import email.utils
import gzip
import io
import json
import urllib.error
import urllib.parse
import urllib.request
import zlib
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

from .routes import (
    ARCTIC_SHIFT_SEARCH_ROUTE,
    REDDIT_SEARCH_FEED_ROUTE,
    XCANCEL_SEARCH_ROUTE,
    XCANCEL_STATUS_ROUTE,
    X_SITE_ORIGIN,
    ARCTIC_SHIFT_ORIGIN,
    ARCTIC_SHIFT_POSTS_ROUTE,
    ARXIV_QUERY_ROUTE,
    BING_NEWS_RSS_ROUTE,
    BING_RSS_ROUTE,
    CROSSREF_WORKS_ROUTE,
    GDELT_DOC_ROUTE,
    OPENALEX_WORKS_ROUTE,
    SOUNDCLOUD_OEMBED_ROUTE,
    SPOTIFY_OEMBED_ROUTE,
    STACKEXCHANGE_SEARCH_ROUTE,
    TIKTOK_OEMBED_ROUTE,
    TIKTOK_PROFILE_PAGE_ROUTE,
    TIKTOK_VIDEO_PAGE_ROUTE,
    VIMEO_OEMBED_ROUTE,
    WIKIMEDIA_PAGEVIEWS_ROUTE,
    X_PUBLISH_OEMBED_ROUTE,
    YOUTUBE_OEMBED_ROUTE,
    BLUESKY_AUTHOR_FEED_ROUTE,
    BLUESKY_SEARCH_POSTS_ROUTE,
    CREDENTIAL_PLACEMENTS,
    DDG_HTML_ROUTE,
    FAKE_OFFLINE_ROUTE,
    FXTWITTER_API_ROUTE,
    GITHUB_REST_ROUTE,
    GITHUB_SEARCH_ROUTE,
    GOOGLE_NEWS_RSS_ROUTE,
    HEADER_PLACEMENT,
    HN_ALGOLIA_ITEM_ROUTE,
    HN_ALGOLIA_SEARCH_ROUTE,
    HN_FIREBASE_ITEM_ROUTE,
    INSTAGRAM_WEB_APP_ID,
    INSTAGRAM_WEB_PROFILE_ROUTE,
    JSON_CONTENT_TYPE,
    KALSHI_MARKETS_ROUTE,
    LINKEDIN_JOBS_GUEST_SEARCH_ROUTE,
    LINKEDIN_PUBLIC_PROFILE_ROUTE,
    MANIFOLD_MARKETS_ROUTE,
    OPEN_ORIGIN,
    POLYMARKET_GAMMA_ROUTE,
    PUBLIC_CLIENT_CREDENTIALS,
    PUBLIC_PAGE_ARTICLE_ROUTE,
    PUBLIC_PAGE_CONTROL_ROUTE,
    QUERY_PLACEMENT,
    REDDIT_FEED_ROUTE,
    REDDIT_SHREDDIT_COMMENTS_ROUTE,
    REDDIT_SHREDDIT_LISTING_ROUTE,
    REDDIT_SHREDDIT_SEARCH_ROUTE,
    REDDIT_SHREDDIT_SUBREDDIT_SEARCH_ROUTE,
    REDDIT_SITE_ORIGIN,
    ROUTE_CONSTANTS,
    STOCKTWITS_STREAM_ROUTE,
    STOCKTWITS_SYMBOL_SEARCH_ROUTE,
    PublicClientCredential,
    RouteConstant,
    WEB_PAGE_OPEN_ROUTE,
    X_GUEST_ACTIVATE_ROUTE,
    X_GUEST_GRAPHQL_ROUTE,
    X_GUEST_PUBLIC_BEARER,
    X_SYNDICATION_TIMELINE_ROUTE,
    YOUTUBE_CHANNEL_FEED_ROUTE,
    YOUTUBE_INNERTUBE_ROUTE,
    YOUTUBE_INNERTUBE_WEB_KEY,
    YOUTUBE_TIMEDTEXT_ROUTE,
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

TOKEN_ACTIVATION_ROUTES = (X_GUEST_ACTIVATE_ROUTE,)
TOKEN_ACTIVATION_METHODS = ("POST",)
QUERY_BODY_ROUTES = (YOUTUBE_INNERTUBE_ROUTE,)
QUERY_BODY_METHODS = ("POST",)

ORIGIN_CONTENT = "origin_content"
ORIGIN_FAILURE = "origin_failure"
NETWORK_INTERCEPTED = "network_intercepted"
CHANNEL_VERDICTS = (ORIGIN_CONTENT, ORIGIN_FAILURE, NETWORK_INTERCEPTED)
CAPTIVE_PORTAL_MARKERS = ('<base href="/login/">',)


UNREACHABLE = "unreachable"
AUTH_REQUIRED = "auth_required"


class TransportError(RuntimeError):
    """An outbound request was refused or could not be completed.

    ``loss`` is the code a step records for the read this error cost it:
    `unreachable` for a channel that carried nothing, or the activation's
    refusal (`auth_required` or `rate_limited`) for a read needing its token.
    ``reached`` says an origin answered the read this error cost — a refused
    activation did — so the ledger bills that call.
    """

    def __init__(self, message: str, loss: str = UNREACHABLE, reached: bool = False) -> None:
        RuntimeError.__init__(self, message)
        self.loss = loss
        self.reached = reached


@dataclass(frozen=True)
class TransportRequest:
    """One read, spelled completely, before any credential is attached."""

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
    """The loss an origin's refusal carries, shared by activation and checkpoints."""
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


def admitted_methods(route_id: str) -> Tuple[str, ...]:
    """Every method this route may use: reads plus two closed exceptions."""

    if route_id in TOKEN_ACTIVATION_ROUTES:
        return READ_METHODS + TOKEN_ACTIVATION_METHODS
    if route_id in QUERY_BODY_ROUTES:
        return READ_METHODS + QUERY_BODY_METHODS
    return READ_METHODS


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


def budget_key(request: TransportRequest) -> str:
    """The measured budget paying for this read, separate from cache identity."""

    # Reddit's RSS listing and search share the same measured origin ceiling.
    if request.route_id in (REDDIT_FEED_ROUTE, REDDIT_SEARCH_FEED_ROUTE):
        return REDDIT_FEED_ROUTE + "@" + origin_key(request)
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


def route_credential(route_id: str) -> Optional[PublicClientCredential]:
    """The public client credential this route needs, or None."""

    credential_id = route_constant(route_id).credential_id
    if not credential_id:
        return None
    credential = PUBLIC_CLIENT_CREDENTIALS.get(credential_id)
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
    """Anonymous guest tokens kept only in process memory.

    A token route is claimed once per process. The claim then holds either the
    token the activation minted or the failure it met, and a failed activation
    is never retried: every read that needed the token is refused with that
    failure.
    """

    def __init__(self) -> None:
        self._tokens: Dict[str, str] = {}
        self._failures: Dict[str, TransportError] = {}

    def token_for(self, token_route_id: str) -> str:
        return self._tokens.get(token_route_id, "")

    def failure_for(self, token_route_id: str) -> Optional[TransportError]:
        return self._failures.get(token_route_id)

    def claim(self, token_route_id: str) -> bool:
        if token_route_id in self._tokens:
            return False
        self._tokens[token_route_id] = ""
        return True

    def remember(self, token_route_id: str, token: str) -> None:
        self._tokens[token_route_id] = token

    def refuse(self, token_route_id: str, failure: TransportError) -> None:
        self._failures[token_route_id] = failure

    def clear(self) -> None:
        self._tokens.clear()
        self._failures.clear()


GUEST_TOKENS = GuestTokenStore()


def tokened_headers(
    headers: Tuple[Tuple[str, str], ...], token_route_id: str
) -> Tuple[Tuple[str, str], ...]:
    """Attach an already-minted guest token, never minting one."""

    if not token_route_id:
        return tuple(headers)
    token = GUEST_TOKENS.token_for(token_route_id)
    if not token:
        return tuple(headers)
    return tuple(headers) + ((GUEST_TOKEN_HEADER, token),)


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

    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https":
        return "an open read takes an https address, not " + repr(url)
    host = (parts.hostname or "").lower()
    if not host:
        return "an open read takes an address naming a host, not " + repr(url)
    if host in declared_origin_hosts():
        return (
            "an open read never lands on a host a declared route reads: {0}; ask that"
            " route".format(host)
        )
    return ""


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


def mint_guest_token(
    fetch: Callable[[TransportRequest], TransportResponse], token_route_id: str
) -> str:
    """One activation request, returning the token it minted.

    An activation the origin refuses raises a :class:`TransportError` carrying
    its refusal loss; an answer without a token is typed `auth_required`.
    Both are marked reached, since the origin answered: every dependent read is refused
    rather than sent unauthorized, and the activation is never retried. An
    activation the channel never carried raises the transport's own error.
    The caller's fetch remains the recorded and paced seam.
    """

    response = fetch(build_transport_request(token_route_id))
    if response.status != 200:
        raise TransportError(
            "activation {0} answered http status {1}: the reads it authorizes are"
            " refused rather than sent unauthorized".format(token_route_id, response.status),
            loss=refusal_loss(response.status, response.body) or AUTH_REQUIRED,
            reached=True,
        )
    try:
        payload = json.loads(response.body)
    except ValueError:
        payload = None
    token = payload.get(GUEST_TOKEN_FIELD) if isinstance(payload, dict) else None
    if not isinstance(token, str) or not token:
        raise TransportError(
            "activation {0} answered 200 with no {1}: the reads it authorizes are"
            " refused rather than sent unauthorized".format(token_route_id, GUEST_TOKEN_FIELD),
            loss=AUTH_REQUIRED,
            reached=True,
        )
    return token


REQUEST_TIMEOUT_SECONDS = 20
MAX_RESPONSE_BYTES = 8 * 1024 * 1024


def utc_now_iso() -> str:
    """Read the facade's wall clock in the artifact timestamp format."""

    return datetime.now(timezone.utc).strftime(OBSERVED_AT_FORMAT)


def without_query_credential(
    url: str, credential: Optional[PublicClientCredential]
) -> str:
    """Remove this route's query credential from an answering address."""

    if credential is None or credential.placement != QUERY_PLACEMENT:
        return url
    split = urllib.parse.urlsplit(url)
    pairs = urllib.parse.parse_qsl(split.query, keep_blank_values=True)
    if not any(name == credential.name for name, _ in pairs):
        return url
    kept = [(name, value) for name, value in pairs if name != credential.name]
    return urllib.parse.urlunsplit(
        (split.scheme, split.netloc, split.path, urllib.parse.urlencode(kept), split.fragment)
    )


def answering_address(response: Any, request: TransportRequest) -> str:
    """Where the read was answered, without a query credential."""

    return without_query_credential(response.url, route_credential(request.route_id))


def answered_headers(carried: Any) -> AnsweredHeaders:
    """What an answer carried, as ordered string pairs."""

    if not carried:
        return ()
    return tuple((str(name), str(value)) for name, value in carried.items())


def decoded_body(raw: bytes, headers: Any) -> str:
    """One answer's bytes as text, gunzipped when the origin says it gzipped.

    Stack Exchange's API compresses every answer whether or not the request
    asked, and gzip bytes decoded as UTF-8 are garbage an adapter can only
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
    if request.method not in admitted_methods(request.route_id):
        raise TransportError(
            "refusing a write-capable method {0} on route {1}".format(
                request.method, request.route_id
            )
        )
    if is_open_route(route_constant(request.route_id)):
        refusal = open_read_refusal(request.url)
        if refusal:
            raise TransportError(refusal)
    token_route_id = route_constant(request.route_id).token_route_id
    if token_route_id and not GUEST_TOKENS.token_for(token_route_id):
        raise TransportError(
            "route {0} reads under a guest token from {1} and none was minted: refused"
            " rather than sent unauthorized".format(request.route_id, token_route_id),
            loss=AUTH_REQUIRED,
        )

    credential = route_credential(request.route_id)
    outbound = urllib.request.Request(
        credentialed_url(request.url, credential),
        data=request.body.encode("utf-8") if request.body else None,
        method=request.method,
    )
    headers = tokened_headers(credentialed_headers(request.headers, credential), token_route_id)
    for name, value in headers:
        outbound.add_header(name, value)
    try:
        with urllib.request.urlopen(outbound, timeout=REQUEST_TIMEOUT_SECONDS) as response:
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
