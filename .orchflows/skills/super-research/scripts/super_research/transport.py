"""Transport seam: the sole owner of route constants and outbound requests.

Nothing outside this module may name a host, a path, or a vendor-published
public client credential. Callers that need to know whether a route is
reachable ask :func:`route_admissions`, which answers in booleans only.

This module also owns the captive-portal detector. Every response it returns
names the party that answered it — the origin, or a local network appliance —
so a caller can never record this network's block as a platform gap.

Reliability bar: read-only. The default opener refuses any URL that is not
``https://`` and any method outside :func:`admitted_methods` — reads
everywhere, plus two closed exceptions named by route id: minting an anonymous
guest token, and asking a question InnerTube only takes in a JSON body. Both
are POSTs that create nothing at the origin. PUT, PATCH and DELETE are admitted
nowhere, no code path here can mutate a remote resource, and the offline
``fake`` route can never leave the process.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

DDG_HTML_ROUTE = "ddg_html"
ARCTIC_SHIFT_POSTS_ROUTE = "arctic_shift_posts_ids"
X_GUEST_ACTIVATE_ROUTE = "x_guest_activate"
X_SYNDICATION_TIMELINE_ROUTE = "x_syndication_timeline"
X_GUEST_GRAPHQL_ROUTE = "x_guest_graphql"
LINKEDIN_JOBS_GUEST_SEARCH_ROUTE = "linkedin_jobs_guest_search"
LINKEDIN_PUBLIC_PROFILE_ROUTE = "linkedin_public_profile"
YOUTUBE_INNERTUBE_ROUTE = "youtube_innertube"
INSTAGRAM_WEB_PROFILE_ROUTE = "instagram_web_profile"
HN_ALGOLIA_SEARCH_ROUTE = "hn_algolia_search"
HN_FIREBASE_ITEM_ROUTE = "hn_firebase_item"
GITHUB_REST_ROUTE = "github_rest"
GITHUB_SEARCH_ROUTE = "github_search"
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

# The status an origin answers with when it wants fewer requests, and the typed
# loss a caller records for it. Named here once each, because the scheduler that
# waits it out and the record that reports it must be talking about the same
# thing. A refusal is an outcome, never a reason to become a different client.
RATE_LIMITED_STATUS = 429
RATE_LIMITED = "rate_limited"

# The first closed exception to reads-only, named by route id: minting an
# anonymous guest token needs a POST, and that POST creates no account,
# session, or content at the origin.
TOKEN_ACTIVATION_ROUTES = (X_GUEST_ACTIVATE_ROUTE,)
TOKEN_ACTIVATION_METHODS = ("POST",)

# The second, and the last. InnerTube takes its query as a JSON body and has
# no GET form, so this is a read spelled in an awkward verb rather than a write
# — it asks a question and creates nothing. What keeps that true is not the
# verb but the body: it is rendered from the route's own `body_params` and from
# nothing else, so a caller supplies values into a shape this module declares
# and can never choose the shape. A route absent from both sets above reaches
# no method outside `READ_METHODS` by any path, and no route anywhere reaches
# PUT, PATCH or DELETE.
QUERY_BODY_ROUTES = (YOUTUBE_INNERTUBE_ROUTE,)
QUERY_BODY_METHODS = ("POST",)

# What a rendered body is sent as, and the only content type this module emits.
JSON_CONTENT_TYPE = "application/json"

# What an activation route issues, and where the route that needs it carries
# it. A guest token is not a vendor-published constant: the origin mints a new
# one on request, it names no user, and it lives in memory for as long as the
# process reading with it does.
GUEST_TOKEN_FIELD = "guest_token"
GUEST_TOKEN_HEADER = "x-guest-token"

# Where a public client credential goes on the wire.
QUERY_PLACEMENT = "query"
HEADER_PLACEMENT = "header"
CREDENTIAL_PLACEMENTS = (QUERY_PLACEMENT, HEADER_PLACEMENT)

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
    """A ``K1`` credential the vendor ships publicly in its own web client.

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
        placement=QUERY_PLACEMENT,
        name="key",
        value="AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8",
    ),
    # findings.md §1 (Instagram) records this one in full: the measured probe
    # sent `x-ig-app-id: 936619743392459` and got 200 with profile data.
    INSTAGRAM_WEB_APP_ID: PublicClientCredential(
        credential_id=INSTAGRAM_WEB_APP_ID,
        vendor="instagram",
        placement=HEADER_PLACEMENT,
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
        placement=HEADER_PLACEMENT,
        name="Authorization",
        value=(
            "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs"
            "%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA"
        ),
    ),
}


@dataclass(frozen=True)
class RouteConstant:
    """One endpoint, spelled once.

    ``path_params`` names the inputs this endpoint takes as path segments
    rather than as query parameters, in the order they appear. The segment
    names are the route's, so the endpoint's shape stays owned here; only the
    values come from the caller. A route that takes none has none.

    ``body_params`` does for a JSON body what ``path_params`` does for a path:
    it names the inputs this endpoint takes there, each paired with the key
    path it occupies inside the body. The nesting is the endpoint's shape and
    stays owned here; only the values come from the caller, and a param the
    route does not name here never reaches the body at all.

    ``path_suffix`` is what an endpoint spells after its last segment. Firebase
    v0 names a resource's representation that way — ``/v0/item/8863.json`` —
    rather than by an Accept header, and that is the endpoint's shape too, so
    it is owned here for the same reason the segments are. It is spent only
    when every declared segment was, because a half-filled path with a suffix
    on it would name a different resource.

    ``token_route_id`` names the activation route that mints the token this
    one needs. It is what makes an authorized read still one read to everyone
    above this module: the mint happens at send time, inside the opener,
    beside every other credential.
    """

    route_id: str
    access_class: str
    method: str
    origin: str
    path: str
    accept: str
    operator_identity: str = ""
    credential_id: str = ""
    path_params: Tuple[str, ...] = ()
    path_suffix: str = ""
    body_params: Tuple[Tuple[str, Tuple[str, ...]], ...] = ()
    token_route_id: str = ""


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
    # findings.md §1 (X): 200, 378 KB in 2.5 s, carrying 100 timeline entries
    # in the page's own `__NEXT_DATA__`. The handle is a path segment, not a
    # query parameter.
    X_SYNDICATION_TIMELINE_ROUTE: RouteConstant(
        route_id=X_SYNDICATION_TIMELINE_ROUTE,
        access_class="K2",
        method="GET",
        origin="https://syndication.twitter.com",
        path="/srv/timeline-profile/screen-name",
        accept="text/html",
        operator_identity="x",
        path_params=("screen_name",),
    ),
    # findings.md §1 (X): three GraphQL operations answered 200 with a guest
    # token. The evidence records the activation origin and not this one, so
    # the endpoint is pinned to the origin the evidence does record; criterion
    # 12's live smoke is what proves it. Both path segments come from the
    # adapter: the query id rotates per web release and is declared as that
    # adapter's volatile identifier, which is why a stale one answers 404 here
    # rather than an error inside a 200 body.
    X_GUEST_GRAPHQL_ROUTE: RouteConstant(
        route_id=X_GUEST_GRAPHQL_ROUTE,
        access_class="K1",
        method="GET",
        origin="https://api.twitter.com",
        path="/graphql",
        accept="application/json",
        operator_identity="x",
        credential_id=X_GUEST_PUBLIC_BEARER,
        path_params=("query_id", "operation_name"),
        token_route_id=X_GUEST_ACTIVATE_ROUTE,
    ),
    # findings.md §1 (LinkedIn): 200, 27 KB in 0.7 s, ten jobs per page each
    # carrying a jobPosting URN, a title, a company and a datetime, with
    # `start=` paginating. A guest surface in the plainest sense — no account,
    # no token, and no vendor-published credential attached here or anywhere.
    LINKEDIN_JOBS_GUEST_SEARCH_ROUTE: RouteConstant(
        route_id=LINKEDIN_JOBS_GUEST_SEARCH_ROUTE,
        access_class="K0",
        method="GET",
        origin="https://www.linkedin.com",
        path="/jobs-guest/jobs/api/seeMoreJobPostings/search",
        accept="text/html",
        operator_identity="linkedin",
    ),
    # findings.md §1 (LinkedIn): 200, 577 KB in 1.3 s, carrying a complete
    # ld+json Person block — **not** the 999 authwall the superseded spec put
    # this whole platform outside the roster for. The slug is a path segment,
    # so the endpoint's shape stays owned here and only the value is the
    # caller's; `linkedin.com/company/<slug>` is a different path and would be
    # a different route.
    LINKEDIN_PUBLIC_PROFILE_ROUTE: RouteConstant(
        route_id=LINKEDIN_PUBLIC_PROFILE_ROUTE,
        access_class="K2",
        method="GET",
        origin="https://www.linkedin.com",
        path="/in",
        accept="text/html",
        operator_identity="linkedin",
        path_params=("slug",),
    ),
    # findings.md §1 (YouTube): `youtubei/v1/search` answered 200 with 2.27 MB
    # in 1.4 s, `youtubei/v1/next` 200 with 1.12 MB in 2.2 s, and
    # `youtubei/v1/player` 200 with 21 KB in 0.3 s — all three keyless, under
    # the web key youtube.com embeds in its own page source. The endpoint is a
    # path segment, so three operations are one route with one budget, the way
    # the X GraphQL operations are.
    #
    # This is the one route in the table whose read is spelled POST: InnerTube
    # takes its query in a JSON body and publishes no GET form. The body is
    # rendered from `body_params` alone. `context.client` is InnerTube's own
    # required envelope and carries the client version that rotates, which is
    # why the adapter declares that version as a volatile identifier rather
    # than this module pinning one.
    #
    # The origin is the host the evidence names youtubei as living under, and
    # like the web key's elided middle it is unproven until criterion 12's
    # live smoke.
    YOUTUBE_INNERTUBE_ROUTE: RouteConstant(
        route_id=YOUTUBE_INNERTUBE_ROUTE,
        access_class="K1",
        method="POST",
        origin="https://www.youtube.com",
        path="/youtubei/v1",
        accept=JSON_CONTENT_TYPE,
        operator_identity="youtube",
        credential_id=YOUTUBE_INNERTUBE_WEB_KEY,
        path_params=("endpoint",),
        body_params=(
            ("client_name", ("context", "client", "clientName")),
            ("client_version", ("context", "client", "clientVersion")),
            ("query", ("query",)),
            ("video_id", ("videoId",)),
            ("continuation", ("continuation",)),
        ),
    ),
    # findings.md §1 (Instagram): `api/v1/users/web_profile_info/?username=`
    # under `x-ig-app-id: 936619743392459` answered 200 with 455 KB in 2.9 s,
    # carrying username, biography, followers, post count and 12 recent posts.
    # The evidence records the path and the header and not the host, so the
    # origin here is this package's belief — Instagram's own web client asks
    # this of `www.instagram.com` — and it is unproven until criterion 12's
    # live smoke, exactly as the X GraphQL origin is.
    INSTAGRAM_WEB_PROFILE_ROUTE: RouteConstant(
        route_id=INSTAGRAM_WEB_PROFILE_ROUTE,
        access_class="K1",
        method="GET",
        origin="https://www.instagram.com",
        path="/api/v1/users/web_profile_info/",
        accept=JSON_CONTENT_TYPE,
        operator_identity="instagram",
        credential_id=INSTAGRAM_WEB_APP_ID,
    ),
    # findings.md §1 (carry-over routes): `hn.algolia.com/api/v1/search_by_date`
    # answered 200 with full-text HN search, and `.../search?tags=comment`
    # answered 200 for comments. The endpoint is a path segment, so both are one
    # route with one budget, the way the InnerTube operations are; the tag that
    # selects comments is an ordinary query parameter, because it selects rows
    # rather than an endpoint.
    #
    # HN's own search is operated by Algolia and published by HN — the platform
    # indexing itself, not an independent mirror of it — which is why the
    # evidence classes it `K0` documented-keyless rather than `K3`, and why
    # nothing read here carries `third_party_archive`.
    HN_ALGOLIA_SEARCH_ROUTE: RouteConstant(
        route_id=HN_ALGOLIA_SEARCH_ROUTE,
        access_class="K0",
        method="GET",
        origin="https://hn.algolia.com",
        path="/api/v1",
        accept="application/json",
        operator_identity="algolia",
        path_params=("endpoint",),
    ),
    # findings.md §1 (carry-over routes): `hacker-news.firebaseio.com/v0/item/<id>`
    # answered 200 with `by`, `descendants` and the `kids` tree — the one
    # surface that carries a story's comment tree, and the one with no search.
    # Firebase names a resource's representation with a path suffix rather than
    # with an Accept header, so `.json` is part of the endpoint and is spelled
    # here; an adapter composing it would own the endpoint's shape.
    HN_FIREBASE_ITEM_ROUTE: RouteConstant(
        route_id=HN_FIREBASE_ITEM_ROUTE,
        access_class="K0",
        method="GET",
        origin="https://hacker-news.firebaseio.com",
        path="/v0/item",
        accept="application/json",
        operator_identity="hacker-news",
        path_params=("item_id",),
        path_suffix=".json",
    ),
    # findings.md §1 (carry-over routes): `api.github.com` answered anonymously,
    # and `api.github.com/rate_limit` reported the anonymous ceiling as 60/hr
    # for **core** and 60/hr for **code_search** — two buckets, measured apart.
    # They are two routes here for that reason and for one more: a repository's
    # path and a search index's path do not share a shape, and one route with a
    # generic leading segment would hand the endpoint's shape to the caller.
    #
    # This is the origin in the roster with the largest write surface, and none
    # of it is reachable: the route declares a read, `admitted_methods` returns
    # reads only for any route outside the two closed exceptions above, and the
    # opener refuses everything else before a socket exists.
    GITHUB_REST_ROUTE: RouteConstant(
        route_id=GITHUB_REST_ROUTE,
        access_class="K0",
        method="GET",
        origin="https://api.github.com",
        path="/repos",
        # GitHub's own documented media type for its REST API.
        accept="application/vnd.github+json",
        operator_identity="github",
        # `/repos/<owner>/<repo>` is the repository itself; the third segment is
        # the collection under it, and a request that leaves it empty asks about
        # the repository.
        path_params=("owner", "repo", "resource"),
    ),
    # findings.md §1 (carry-over routes): `api.github.com/search/repositories`
    # answered 200 anonymously. The index is a path segment and the question is
    # `q`, which is how GitHub spells both.
    GITHUB_SEARCH_ROUTE: RouteConstant(
        route_id=GITHUB_SEARCH_ROUTE,
        access_class="K0",
        method="GET",
        origin="https://api.github.com",
        path="/search",
        accept="application/vnd.github+json",
        operator_identity="github",
        path_params=("index",),
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
    """One read, spelled completely, before any credential is attached.

    ``body`` is the JSON a query-body route asks its question in, rendered from
    that route's declared ``body_params``. Every other route carries none, and
    no caller can put anything in one: the shape is the route's and only the
    values are the caller's.
    """

    route_id: str
    method: str
    url: str
    headers: Tuple[Tuple[str, str], ...] = ()
    body: str = ""


@dataclass(frozen=True)
class TransportResponse:
    """One answer, and everything a caller needs to know about how it got here.

    ``cache_hit`` says a run's own memory answered rather than the origin.
    Nothing in this module ever sets it: only a caller holding a cache knows,
    and it says so by copying the response with the flag raised — which is why
    ``observed_at`` stays the moment the origin was really read.
    """

    route_id: str
    url: str
    status: int
    body: str
    content_type: str
    observed_at: str
    channel_verdict: str
    cache_hit: bool = False


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


def route_admissions() -> Dict[str, bool]:
    """Per-route booleans — the only route knowledge the router ever sees.

    A route is admitted when it needs no user credential. ``K5`` is the one
    credentialed class, so it is the one class that can answer False here.
    """

    return {
        route_id: route.access_class != "K5"
        for route_id, route in sorted(ROUTE_CONSTANTS.items())
    }


def admitted_methods(route_id: str) -> Tuple[str, ...]:
    """Every method this route may use: reads, plus the two closed exceptions.

    A route named in neither exception set reads and nothing else, and no
    route in either one gains a verb that could change anything at an origin:
    both exceptions are the same POST, on a named route, for an operation that
    creates nothing.
    """

    if route_id in TOKEN_ACTIVATION_ROUTES:
        return READ_METHODS + TOKEN_ACTIVATION_METHODS
    if route_id in QUERY_BODY_ROUTES:
        return READ_METHODS + QUERY_BODY_METHODS
    return READ_METHODS


def origin_locator(route_id: str, published: str) -> str:
    """One address on a route's own origin, resolved where hosts are spelled.

    Both `K1` platforms in the roster publish an item's address relative to
    themselves — a ``/watch?v=`` path — or not at all, leaving a caller to
    address a post by the shortcode the payload carries. An adapter may name no
    route host, so either the resolution happens here or every record on those
    routes carries no address. An address that is already absolute is handed
    back untouched: resolving one somebody else resolved would be this module
    rewriting what an origin said.
    """

    if not published:
        return ""
    if urllib.parse.urlsplit(published).scheme:
        return published
    return urllib.parse.urljoin(route_constant(route_id).origin, published)


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

    if credential is None or credential.placement != QUERY_PLACEMENT:
        return url
    separator = "&" if "?" in url else "?"
    return url + separator + urllib.parse.urlencode(((credential.name, credential.value),))


def credentialed_headers(
    headers: Tuple[Tuple[str, str], ...], credential: Optional[PublicClientCredential]
) -> Tuple[Tuple[str, str], ...]:
    """Apply a header-placed credential. Called at send time, never before."""

    if credential is None or credential.placement != HEADER_PLACEMENT:
        return tuple(headers)
    return tuple(headers) + ((credential.name, credential.value),)


def path_segments(route: RouteConstant, params: Dict[str, str]) -> str:
    """Spend this route's declared path params, in order, removing them from ``params``.

    Segments stop at the first one the caller left empty: a later segment
    appended past a missing earlier one would name a different endpoint, and
    guessing which is not this module's to do. A declared ``path_suffix``
    follows the last segment, and only a complete path takes one — for the
    same reason, and it is the same mistake one character further along.
    """

    values = [params.pop(name, "") for name in route.path_params]
    spent = ""
    for value in values:
        if not value:
            return spent
        spent = spent + "/" + urllib.parse.quote(value, safe="")
    return spent + route.path_suffix


def json_body(route: RouteConstant, params: Dict[str, str]) -> str:
    """Spend this route's declared body params into the JSON it asks in.

    The keys are the route's, taken from ``body_params`` and from nothing else,
    so a param the endpoint never declared cannot reach the body — it stays an
    ordinary query parameter, in the open, on a url the run records. A route
    that declares none carries no body whatever it is handed, which is what
    keeps this from being a generic HTTP primitive.

    Serialized with sorted keys and no spaces, so one request is one string and
    two identical reads are identical bytes.
    """

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


def mint_guest_token(token_route_id: str) -> str:
    """One activation request, returning the token it issued or nothing at all.

    A mint that does not produce a token yields an empty string rather than an
    exception: the read that needed it then goes out unauthorized and the
    origin answers 401 or 403, which the adapter records as the platform's own
    refusal. Inventing a token, or turning a failed mint into a retry of the
    read, are the two wrong answers.
    """

    try:
        status, body, _ = urlopen_response(build_transport_request(token_route_id))
    except TransportError:
        return ""
    if status != 200:
        return ""
    try:
        payload = json.loads(body)
    except ValueError:
        return ""
    token = payload.get(GUEST_TOKEN_FIELD) if isinstance(payload, dict) else None
    return token if isinstance(token, str) else ""


class GuestTokenStore:
    """Anonymous guest tokens, held in memory for as long as the process reads.

    One token per activation route, minted on first use and spent on every
    later read: a run that minted per read would spend two requests where the
    origin expects one, and one that persisted a token would carry state
    across runs. There is no file, no environment variable, and no artifact
    field here — a token exists only in this object.
    """

    def __init__(self) -> None:
        self._tokens: Dict[str, str] = {}

    def token_for(self, token_route_id: str) -> str:
        held = self._tokens.get(token_route_id)
        if held is None:
            held = mint_guest_token(token_route_id)
            self._tokens[token_route_id] = held
        return held

    def clear(self) -> None:
        self._tokens.clear()


GUEST_TOKENS = GuestTokenStore()


def tokened_headers(
    headers: Tuple[Tuple[str, str], ...], token_route_id: str
) -> Tuple[Tuple[str, str], ...]:
    """Attach this route's guest token, minting one if the process holds none."""

    if not token_route_id:
        return tuple(headers)
    token = GUEST_TOKENS.token_for(token_route_id)
    if not token:
        return tuple(headers)
    return tuple(headers) + ((GUEST_TOKEN_HEADER, token),)


def build_transport_request(
    route_id: str, params: Optional[Mapping[str, str]] = None
) -> TransportRequest:
    route = route_constant(route_id)
    supplied = dict(params or {})
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


def urlopen_response(request: TransportRequest) -> Tuple[int, str, str]:
    """Default opener: one bounded HTTPS read on an admitted method, no redirect games.

    Credentials are attached here and nowhere earlier, which is why a
    ``TransportRequest`` a caller holds can never carry one. A route that
    declares a ``token_route_id`` also mints its guest token here, at most once
    per process — one more request on the wire, still one read to every caller.
    """

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
            )
    except urllib.error.HTTPError as error:
        # A status-bearing error is data, not a tool failure: `channel_verdict`
        # separates a local block from the origin's own failure, and the
        # adapter types the result.
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
