"""Route table: every address this package can reach, and nothing else.

One auditable closed allowlist of reachable hosts, in one file — this one.
Every origin, every endpoint, and every vendor-published public client
credential the package can name is declared below, so the set of hosts a run
can reach is read by reading this file, and a module outside the declared route
owners naming any of them is a failing test rather than a review note.

Declarations only: nothing here imports a sibling, reaches the network, or
decides anything, the way :mod:`.probes` is thirteen declarations and
:mod:`.smoke` is the mechanism that reads them. :mod:`.transport` is that
mechanism for these two tables — it admits the method, opens the socket, and
attaches the credential — and it re-exports every name below under the name it
has always had. Each name still has exactly one definition; ``transport`` stays
the one address the suite, the adapters and the CLI reach it at.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

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
REDDIT_FEED_ROUTE = "reddit_feed"
YOUTUBE_CHANNEL_FEED_ROUTE = "youtube_channel_feed"
PUBLIC_PAGE_ARTICLE_ROUTE = "public_page_article"
PUBLIC_PAGE_CONTROL_ROUTE = "public_page_control"
FAKE_OFFLINE_ROUTE = "fake_offline"

# Reddit's own site, named once. It is the feed route's origin, and it is also
# the host an Arctic Shift permalink is relative to — an archive answers from
# its own origin about items that live here, so that adapter composes an
# address from this constant rather than from `origin_locator`, which resolves
# against the route that answered. A host any route uses is this module's to
# spell, so the constant is exported rather than repeated.
REDDIT_SITE_ORIGIN = "https://www.reddit.com"

YOUTUBE_INNERTUBE_WEB_KEY = "youtube_innertube_web_key"
INSTAGRAM_WEB_APP_ID = "instagram_web_app_id"
X_GUEST_PUBLIC_BEARER = "x_guest_public_bearer"

# The JSON media type, named once for the two things that spell it: the routes
# whose answer is JSON, and the seam's `Content-Type` on the one body it sends.
JSON_CONTENT_TYPE = "application/json"

# Where a public client credential goes on the wire.
QUERY_PLACEMENT = "query"
HEADER_PLACEMENT = "header"
CREDENTIAL_PLACEMENTS = (QUERY_PLACEMENT, HEADER_PLACEMENT)


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
    one needs, and the activation is a route here like any other — it declares
    its own budget and the scheduler spends it. Only the attach happens at send
    time, inside the opener, beside every other credential; the mint itself
    belongs to whoever paces this run.
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
    # findings.md §1 (Reddit): `www.reddit.com/r/<sub>.rss` answered 200 with
    # 32 KB in 1.4 s carrying title, link, author and updated — the one Reddit
    # surface that answered this host at all. Every `.json` form answered 403,
    # on `www.`, `old.` and `api.` alike, to a curl UA, a custom app UA and a
    # browser UA alike: IP-class blocking no header set changes, which is why
    # no `.json` route is declared here and none is a fallback.
    #
    # Reddit names the representation with a path suffix rather than with an
    # Accept header, the way Firebase does, so `.rss` is part of the endpoint's
    # shape and is spelled here; an adapter composing it would own the endpoint.
    REDDIT_FEED_ROUTE: RouteConstant(
        route_id=REDDIT_FEED_ROUTE,
        access_class="K0",
        method="GET",
        origin=REDDIT_SITE_ORIGIN,
        path="/r",
        accept="application/atom+xml",
        operator_identity="reddit",
        path_params=("subreddit",),
        path_suffix=".rss",
    ),
    # findings.md §1 (YouTube): `feeds/videos.xml?channel_id=` answered 200 with
    # 39 KB in 0.35 s — the cheapest read in the roster, and the one RSS/Atom
    # document the evidence measures. The channel is a query parameter, which is
    # how the measured url spells it.
    #
    # Same origin as the InnerTube route and a different endpoint, so it is a
    # different route with its own budget and its own window: a public feed and
    # a private-ish API on one host are not one ceiling.
    YOUTUBE_CHANNEL_FEED_ROUTE: RouteConstant(
        route_id=YOUTUBE_CHANNEL_FEED_ROUTE,
        access_class="K0",
        method="GET",
        origin="https://www.youtube.com",
        path="/feeds/videos.xml",
        accept="application/atom+xml",
        operator_identity="youtube",
    ),
    # The two documents `public_page` may select between, and the reason it is a
    # selected read rather than an HTTP primitive: a page's host and endpoint are
    # declared here like every other route's, and a caller fills one declared
    # segment. findings.md §0 measured both — `example.com` and `wikipedia.org`
    # returned 200 with genuine origin content from this host while the network
    # appliance answered other domains with a 503 login portal.
    #
    # The article host is this package's belief: §0 records `wikipedia.org` and
    # articles live on the language subdomain. Unproven until criterion 12's
    # live smoke, exactly as the Instagram and X GraphQL origins are.
    PUBLIC_PAGE_ARTICLE_ROUTE: RouteConstant(
        route_id=PUBLIC_PAGE_ARTICLE_ROUTE,
        access_class="K0",
        method="GET",
        origin="https://en.wikipedia.org",
        path="/wiki",
        accept="text/html",
        operator_identity="wikimedia",
        path_params=("title",),
    ),
    # The channel control: one document, no argument, and an answer known before
    # it is asked. It is what §0's caveat is built on — a read whose content is
    # fixed is the only read that can tell "this network is answering for the
    # origin" from "the origin has nothing", and `channel_verdict` needs
    # something to be right about.
    PUBLIC_PAGE_CONTROL_ROUTE: RouteConstant(
        route_id=PUBLIC_PAGE_CONTROL_ROUTE,
        access_class="K0",
        method="GET",
        origin="https://example.com",
        path="/",
        accept="text/html",
        operator_identity="iana",
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
