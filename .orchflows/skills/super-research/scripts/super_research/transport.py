"""Transport facade: wall clock, urllib seam, answering address, and carrier.

Route declarations remain in :mod:`.routes`. Protocol policy and credential-free
request construction are implemented in private support modules and re-exported
here so every existing caller and monkeypatch still reaches ``transport.*``.
"""

from __future__ import annotations

import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

from ._support import transport_request as _request
from ._support import transport_protocol as _protocol
from ._support.transport_protocol import (
    AnsweredHeaders,
    CAPTIVE_PORTAL_MARKERS,
    CHANNEL_VERDICTS,
    NETWORK_INTERCEPTED,
    OBSERVED_AT_FORMAT,
    ORIGIN_CONTENT,
    ORIGIN_FAILURE,
    QUERY_BODY_METHODS,
    QUERY_BODY_ROUTES,
    RATE_LIMITED,
    RATE_LIMITED_STATUS,
    RATE_LIMIT_RESET_COUNTDOWN_CEILING_SECONDS,
    RATE_LIMIT_RESET_HEADER,
    READ_METHODS,
    RETRY_AFTER_HEADER,
    SECONDARY_RATE_LIMITED_STATUS,
    SECONDARY_RATE_LIMIT_MARKERS,
    TOKEN_ACTIVATION_METHODS,
    TOKEN_ACTIVATION_ROUTES,
    UNREACHABLE,
    USER_AGENT,
    TransportError,
    TransportRequest,
    TransportResponse,
    admitted_methods,
    channel_verdict,
    epoch_moment,
    header_value,
    http_date_moment,
    observed_moment,
    rate_refused,
    remaining_seconds,
    retry_after_seconds,
    stated_cooldown_seconds,
)
from ._support.transport_request import (
    GUEST_TOKEN_FIELD,
    GUEST_TOKEN_HEADER,
    GUEST_TOKENS,
    OPEN_URL_PARAM,
    GuestTokenStore,
    credentialed_headers,
    credentialed_url,
    is_open_route,
    json_body,
    origin_key,
    path_segments,
)
from .routes import (
    ARCTIC_SHIFT_ORIGIN,
    ARCTIC_SHIFT_POSTS_ROUTE,
    BING_NEWS_RSS_ROUTE,
    BING_RSS_ROUTE,
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


REQUEST_TIMEOUT_SECONDS = 20
MAX_RESPONSE_BYTES = 8 * 1024 * 1024


def utc_now_iso() -> str:
    """Read the facade's wall clock in the artifact timestamp format."""

    return datetime.now(timezone.utc).strftime(OBSERVED_AT_FORMAT)


# These wrappers deliberately read facade globals at call time. Tests and
# embedders replace the public tables here; a private module must not bypass
# that established seam by retaining its own imported binding.
def route_constant(route_id: str) -> RouteConstant:
    return _protocol.route_constant(route_id, ROUTE_CONSTANTS)


def route_admissions() -> Dict[str, bool]:
    return _protocol.route_admissions(ROUTE_CONSTANTS)


def budget_key(request: TransportRequest) -> str:
    return _request.budget_key(request, ROUTE_CONSTANTS, origin_key)


def origin_locator(route_id: str, published: str) -> str:
    return _request.origin_locator(route_id, published, ROUTE_CONSTANTS)


def route_credential(route_id: str) -> Optional[PublicClientCredential]:
    return _request.route_credential(
        route_id, ROUTE_CONSTANTS, PUBLIC_CLIENT_CREDENTIALS
    )


def tokened_headers(
    headers: Tuple[Tuple[str, str], ...], token_route_id: str
) -> Tuple[Tuple[str, str], ...]:
    return _request.tokened_headers(headers, token_route_id, GUEST_TOKENS)


def declared_origin_hosts() -> Tuple[str, ...]:
    return _request.declared_origin_hosts(ROUTE_CONSTANTS)


def open_read_refusal(url: str) -> str:
    return _request.open_read_refusal(
        url, ROUTE_CONSTANTS, lambda routes: declared_origin_hosts()
    )


def channel_verdict(status: int, body: str) -> str:
    _protocol.CAPTIVE_PORTAL_MARKERS = CAPTIVE_PORTAL_MARKERS
    return _protocol.channel_verdict(status, body)


def build_transport_request(
    route_id: str, params: Optional[Mapping[str, str]] = None
) -> TransportRequest:
    return _request.build_transport_request(route_id, params, ROUTE_CONSTANTS)


def mint_guest_token(
    fetch: Callable[[TransportRequest], TransportResponse], token_route_id: str
) -> str:
    """One activation request, returning its token or nothing.

    A refused mint yields no invented token and the dependent read goes out
    unauthorized. The caller's fetch remains the recorded and paced seam.
    """

    return _request._mint_guest_token(fetch, token_route_id, build_transport_request)


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

    answered = getattr(response, "url", "") or request.url
    return without_query_credential(answered, route_credential(request.route_id))


def answered_headers(carried: Any) -> AnsweredHeaders:
    """What an answer carried, as ordered string pairs."""

    if not carried:
        return ()
    return tuple((str(name), str(value)) for name, value in carried.items())


def urlopen_read(request: TransportRequest) -> Tuple[int, str, str, str, AnsweredHeaders]:
    """One bounded HTTPS read through urllib on an admitted method."""

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

    credential = route_credential(request.route_id)
    outbound = urllib.request.Request(
        credentialed_url(request.url, credential),
        data=request.body.encode("utf-8") if request.body else None,
        method=request.method,
    )
    headers = tokened_headers(
        credentialed_headers(request.headers, credential),
        route_constant(request.route_id).token_route_id,
    )
    for name, value in headers:
        outbound.add_header(name, value)
    try:
        with urllib.request.urlopen(outbound, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return (
                response.status,
                response.read(MAX_RESPONSE_BYTES).decode("utf-8", errors="replace"),
                response.headers.get("Content-Type", ""),
                answering_address(response, request),
                answered_headers(response.headers),
            )
    except urllib.error.HTTPError as error:
        return (
            error.code,
            error.read(MAX_RESPONSE_BYTES).decode("utf-8", errors="replace"),
            error.headers.get("Content-Type", "") if error.headers else "",
            answering_address(error, request),
            answered_headers(error.headers),
        )
    except OSError as error:
        raise TransportError("transport failed for " + request.route_id) from error


def urlopen_response(request: TransportRequest) -> Tuple[int, str, str]:
    """The compatible three-value view of :func:`urlopen_read`."""

    return urlopen_read(request)[:3]


class Transport:
    """One run's outbound channel. Every attempt is recorded in order."""

    def __init__(
        self,
        opener: Optional[Callable[[TransportRequest], Tuple[int, str, str]]] = None,
        now: Optional[Callable[[], str]] = None,
    ) -> None:
        self._opener = opener if opener is not None else urlopen_read
        self._now = now if now is not None else utc_now_iso
        self.calls: List[TransportRequest] = []

    def fetch(self, request: TransportRequest) -> TransportResponse:
        self.calls.append(request)
        answered = self._opener(request)
        status, body, content_type = answered[:3]
        final_url = answered[3] if len(answered) > 3 else request.url
        headers = answered[4] if len(answered) > 4 else ()
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
