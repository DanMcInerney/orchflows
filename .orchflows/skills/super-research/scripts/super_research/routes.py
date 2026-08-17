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
BING_RSS_ROUTE = "bing_rss"
BING_NEWS_RSS_ROUTE = "bing_news_rss"
GOOGLE_NEWS_RSS_ROUTE = "google_news_rss"
WEB_PAGE_OPEN_ROUTE = "web_page_open"
ARCTIC_SHIFT_POSTS_ROUTE = "arctic_shift_posts_ids"
REDDIT_SHREDDIT_LISTING_ROUTE = "reddit_shreddit_listing"
REDDIT_SHREDDIT_SEARCH_ROUTE = "reddit_shreddit_search"
REDDIT_SHREDDIT_SUBREDDIT_SEARCH_ROUTE = "reddit_shreddit_subreddit_search"
REDDIT_SHREDDIT_COMMENTS_ROUTE = "reddit_shreddit_comments"
YOUTUBE_TIMEDTEXT_ROUTE = "youtube_timedtext"
HN_ALGOLIA_ITEM_ROUTE = "hn_algolia_item"
POLYMARKET_GAMMA_ROUTE = "polymarket_gamma"
KALSHI_MARKETS_ROUTE = "kalshi_markets"
MANIFOLD_MARKETS_ROUTE = "manifold_markets"
STOCKTWITS_STREAM_ROUTE = "stocktwits_symbol_stream"
STOCKTWITS_SYMBOL_SEARCH_ROUTE = "stocktwits_symbol_search"
BLUESKY_SEARCH_POSTS_ROUTE = "bluesky_search_posts"
BLUESKY_AUTHOR_FEED_ROUTE = "bluesky_author_feed"
FXTWITTER_API_ROUTE = "fxtwitter_api"
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

# The Arctic Shift archive's origin, named once for the one route it serves.
ARCTIC_SHIFT_ORIGIN = "https://arctic-shift.photon-reddit.com"

# The one route whose origin is not spelled here: `web_page_open` reads the
# address a discovery step returned, so its host is the caller's and not this
# table's. `transport.open_route_hosts_refused` is what keeps it from reaching a
# host another route already declares — an open read is never a way around a
# declared route's budget — and `transport.urlopen_read` still refuses anything
# that is not https. The empty origin is the marker the transport reads.
OPEN_ORIGIN = ""

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
    # The 2026-08-10 probes (YouTube) records this key elided, as `AIzaSy...11qcW8`:
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
    # The 2026-08-10 probes (Instagram) records this one in full: the measured probe
    # sent `x-ig-app-id: 936619743392459` and got 200 with profile data.
    INSTAGRAM_WEB_APP_ID: PublicClientCredential(
        credential_id=INSTAGRAM_WEB_APP_ID,
        vendor="instagram",
        placement=HEADER_PLACEMENT,
        name="x-ig-app-id",
        value="936619743392459",
    ),
    # The 2026-08-10 probes (X) records the activation returning 200 with a guest
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
    # Measured 2026-08-17 (web discovery, second sweep): `html.duckduckgo.com`
    # answered 202 with a bot challenge to the package identity and to a
    # browser identity alike, so a second and third index are declared as
    # parallel planned routes rather than fallbacks. Bing publishes an RSS form
    # of its web results — `?format=rss` answered 200 with ten items per page
    # and `first=` paging — and of its news results, whose links are wrapped in
    # `news/apiclick.aspx?...&url=<encoded>` and unwrapped by the adapter.
    BING_RSS_ROUTE: RouteConstant(
        route_id=BING_RSS_ROUTE,
        access_class="K4",
        method="GET",
        origin="https://www.bing.com",
        path="/search",
        accept="application/rss+xml",
        operator_identity="bing",
    ),
    BING_NEWS_RSS_ROUTE: RouteConstant(
        route_id=BING_NEWS_RSS_ROUTE,
        access_class="K4",
        method="GET",
        origin="https://www.bing.com",
        path="/news/search",
        accept="application/rss+xml",
        operator_identity="bing",
    ),
    # Measured 2026-08-17: `news.google.com/rss/search?q=<q>+when:30d&hl=en-US
    # &gl=US&ceid=US:en` answered 200 with 131 KB of press items. Each item's
    # link is a redirect on this origin that resolves to the publisher when
    # read; the publisher's own host rides in the item's `<source url=>`.
    GOOGLE_NEWS_RSS_ROUTE: RouteConstant(
        route_id=GOOGLE_NEWS_RSS_ROUTE,
        access_class="K4",
        method="GET",
        origin="https://news.google.com",
        path="/rss/search",
        accept="application/rss+xml",
        operator_identity="google",
    ),
    # The open document read: the one route whose host is the caller's, taken
    # from a locator a discovery step returned. Its policy is the transport's —
    # https only, GET only, no credential, no body, and never a host another
    # route declares. It is what makes a discovered press page hydratable at
    # all; before it, `public_page` served exactly two documents.
    WEB_PAGE_OPEN_ROUTE: RouteConstant(
        route_id=WEB_PAGE_OPEN_ROUTE,
        access_class="K0",
        method="GET",
        origin=OPEN_ORIGIN,
        path="",
        accept="text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        operator_identity="open_web",
    ),
    ARCTIC_SHIFT_POSTS_ROUTE: RouteConstant(
        route_id=ARCTIC_SHIFT_POSTS_ROUTE,
        access_class="K3",
        method="GET",
        origin=ARCTIC_SHIFT_ORIGIN,
        path="/api/posts/ids",
        accept="application/json",
        operator_identity="arctic-shift",
    ),
    # Measured 2026-08-17 (Reddit, shreddit partials): the `/svc/shreddit/`
    # HTML partials Reddit's own web client loads answered 200 to the package
    # identity, on a bucket of 200 reads per window (`x-ratelimit-remaining:
    # 199.0` after the first read) — a different bucket from the `.rss`
    # surface's one-per-minute. `community-more-posts/{sort}/?name=<sub>&t=`
    # carried 24 `<shreddit-post>` elements each stating `score`,
    # `comment-count`, `post-title`, `author`, `created-timestamp` and
    # `permalink`; `search?q=&sort=&t=&type=posts` and `r/<sub>/search?...`
    # carried seven posts per page with a continuation token and a
    # `faceplate-number` pair per post; `comments/r/<sub>/t3_<id>?sort=`
    # carried 25 `<shreddit-comment>` elements with `score`, `depth`,
    # `author`, `created`, `permalink` and the body under
    # `id="<thingid>-post-rtjson-content"`. The `more-comments` continuation
    # that partial names is **not** declared: it states `method="post"`, and a
    # GET of it answered 200 carrying no comment at all (measured the same
    # day), so the deeper replies are reachable only by a verb this package
    # does not admit. This is structured data embedded in a public HTML page,
    # which is `K2`; the
    # `.json` forms answer 403 on this host to every identity, as the 2026-08-10
    # measurement recorded, and stay undeclared.
    REDDIT_SHREDDIT_LISTING_ROUTE: RouteConstant(
        route_id=REDDIT_SHREDDIT_LISTING_ROUTE,
        access_class="K2",
        method="GET",
        origin=REDDIT_SITE_ORIGIN,
        path="/svc/shreddit/community-more-posts",
        accept="text/html",
        operator_identity="reddit",
        path_params=("sort",),
        path_suffix="/",
    ),
    REDDIT_SHREDDIT_SEARCH_ROUTE: RouteConstant(
        route_id=REDDIT_SHREDDIT_SEARCH_ROUTE,
        access_class="K2",
        method="GET",
        origin=REDDIT_SITE_ORIGIN,
        path="/svc/shreddit/search",
        accept="text/html",
        operator_identity="reddit",
    ),
    REDDIT_SHREDDIT_SUBREDDIT_SEARCH_ROUTE: RouteConstant(
        route_id=REDDIT_SHREDDIT_SUBREDDIT_SEARCH_ROUTE,
        access_class="K2",
        method="GET",
        origin=REDDIT_SITE_ORIGIN,
        path="/svc/shreddit/r",
        accept="text/html",
        operator_identity="reddit",
        path_params=("subreddit",),
        path_suffix="/search",
    ),
    REDDIT_SHREDDIT_COMMENTS_ROUTE: RouteConstant(
        route_id=REDDIT_SHREDDIT_COMMENTS_ROUTE,
        access_class="K2",
        method="GET",
        origin=REDDIT_SITE_ORIGIN,
        path="/svc/shreddit/comments/r",
        accept="text/html",
        operator_identity="reddit",
        path_params=("subreddit", "post_fullname"),
    ),
    # Measured 2026-08-17 (YouTube): a caption track's `baseUrl` from an
    # `ANDROID` player answer names this endpoint on this origin, carrying its
    # own signed query (`signature`, `sparams`, `expire`, `v`, `lang`, `kind`,
    # `fmt`), and rebuilding that query through the transport's own sorted
    # `urlencode` still answered 200 with 109 KB of `srv3` XML; `fmt=json3` and
    # `tlang=` also answered. Same origin as InnerTube and a different endpoint,
    # so a different route with its own budget, the way the channel feed is.
    YOUTUBE_TIMEDTEXT_ROUTE: RouteConstant(
        route_id=YOUTUBE_TIMEDTEXT_ROUTE,
        access_class="K1",
        method="GET",
        origin="https://www.youtube.com",
        path="/api/timedtext",
        accept="text/xml",
        operator_identity="youtube",
    ),
    # Measured 2026-08-17: `hn.algolia.com/api/v1/items/<id>` answered 200 with
    # a story and its whole comment tree — 259 nodes in 135 KB, one call —
    # where Firebase serves one node per call. Same origin as the search route
    # and a different endpoint shape, so a route of its own.
    HN_ALGOLIA_ITEM_ROUTE: RouteConstant(
        route_id=HN_ALGOLIA_ITEM_ROUTE,
        access_class="K0",
        method="GET",
        origin="https://hn.algolia.com",
        path="/api/v1/items",
        accept="application/json",
        operator_identity="algolia",
        path_params=("item_id",),
    ),
    # Measured 2026-08-17 (prediction markets): all three answered 200 keyless.
    # Polymarket's Gamma API serves `public-search?q=`, `events` and `markets`
    # under one origin, so the endpoint is a path segment; Kalshi's public
    # trade API serves `markets` and `events` with a `cursor`; Manifold serves
    # `search-markets?term=`. None takes a credential.
    POLYMARKET_GAMMA_ROUTE: RouteConstant(
        route_id=POLYMARKET_GAMMA_ROUTE,
        access_class="K0",
        method="GET",
        origin="https://gamma-api.polymarket.com",
        path="",
        accept="application/json",
        operator_identity="polymarket",
        path_params=("endpoint",),
    ),
    KALSHI_MARKETS_ROUTE: RouteConstant(
        route_id=KALSHI_MARKETS_ROUTE,
        access_class="K0",
        method="GET",
        origin="https://api.elections.kalshi.com",
        path="/trade-api/v2",
        accept="application/json",
        operator_identity="kalshi",
        path_params=("endpoint",),
    ),
    MANIFOLD_MARKETS_ROUTE: RouteConstant(
        route_id=MANIFOLD_MARKETS_ROUTE,
        access_class="K0",
        method="GET",
        origin="https://api.manifold.markets",
        path="/v0/search-markets",
        accept="application/json",
        operator_identity="manifold",
    ),
    # Measured 2026-08-17 (Stocktwits): `api/2/streams/symbol/<SYM>.json`
    # answered 200 with 30 messages, each carrying `likes.total`, `created_at`
    # and `entities.sentiment.basic`, and a `cursor.max` for the next page;
    # `search/symbols.json?q=` answered 200. Keyless, and the one finance-native
    # surface in the roster. Stocktwits names the representation with a path
    # suffix, the way Reddit and Firebase do.
    STOCKTWITS_STREAM_ROUTE: RouteConstant(
        route_id=STOCKTWITS_STREAM_ROUTE,
        access_class="K0",
        method="GET",
        origin="https://api.stocktwits.com",
        path="/api/2/streams/symbol",
        accept="application/json",
        operator_identity="stocktwits",
        path_params=("symbol",),
        path_suffix=".json",
    ),
    STOCKTWITS_SYMBOL_SEARCH_ROUTE: RouteConstant(
        route_id=STOCKTWITS_SYMBOL_SEARCH_ROUTE,
        access_class="K0",
        method="GET",
        origin="https://api.stocktwits.com",
        path="/api/2/search/symbols.json",
        accept="application/json",
        operator_identity="stocktwits",
    ),
    # Bluesky's public AppView, documented keyless. Measured 2026-08-17 on this
    # host: `searchPosts` answered 403 from the CDN in front of it ("Request
    # forbidden by administrative rules") while `getProfile` answered 200 —
    # the route is declared on the documentation and the smoke decides
    # liveness per host, which is what a smoke is for.
    BLUESKY_SEARCH_POSTS_ROUTE: RouteConstant(
        route_id=BLUESKY_SEARCH_POSTS_ROUTE,
        access_class="K0",
        method="GET",
        origin="https://public.api.bsky.app",
        path="/xrpc/app.bsky.feed.searchPosts",
        accept="application/json",
        operator_identity="bluesky",
    ),
    BLUESKY_AUTHOR_FEED_ROUTE: RouteConstant(
        route_id=BLUESKY_AUTHOR_FEED_ROUTE,
        access_class="K0",
        method="GET",
        origin="https://public.api.bsky.app",
        path="/xrpc/app.bsky.feed.getAuthorFeed",
        accept="application/json",
        operator_identity="bluesky",
    ),
    # Measured 2026-08-17 (X, third party): FxTwitter's public API answered 200
    # keyless to `/2/search?q=&feed=latest|top&count=` (paged by a token),
    # `/2/profile/<handle>/statuses`, `/2/profile/<handle>` and
    # `/2/conversation/<id>`, each carrying the platform's own counts. It is
    # an independent operator reading X on this package's behalf, so every
    # record it produces is `K3` and carries `third_party_archive` — the same
    # law Arctic Shift lives under — and it is the one keyless path to an X
    # *search* at all: the guest GraphQL search is refused (`x_guest`), and
    # the syndication timeline is one handle's voice. Three segments, spent in
    # order, so the endpoint's shape stays owned here.
    FXTWITTER_API_ROUTE: RouteConstant(
        route_id=FXTWITTER_API_ROUTE,
        access_class="K3",
        method="GET",
        origin="https://api.fxtwitter.com",
        path="/2",
        accept="application/json",
        operator_identity="fxtwitter",
        path_params=("endpoint", "subject", "collection"),
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
    # The 2026-08-10 probes (X): 200, 378 KB in 2.5 s, carrying 100 timeline entries
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
    # The 2026-08-10 probes (X): three GraphQL operations answered 200 with a guest
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
    # The 2026-08-10 probes (LinkedIn): 200, 27 KB in 0.7 s, ten jobs per page each
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
    # The 2026-08-10 probes (LinkedIn): 200, 577 KB in 1.3 s, carrying a complete
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
    # The 2026-08-10 probes (YouTube): `youtubei/v1/search` answered 200 with 2.27 MB
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
    # The 2026-08-10 probes (Instagram): `api/v1/users/web_profile_info/?username=`
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
    # The 2026-08-10 probes (carry-over routes): `hn.algolia.com/api/v1/search_by_date`
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
    # The 2026-08-10 probes (carry-over routes):
    # `hacker-news.firebaseio.com/v0/item/<id>`
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
    # The 2026-08-10 probes (carry-over routes): `api.github.com` answered anonymously,
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
    # The 2026-08-10 probes (carry-over routes): `api.github.com/search/repositories`
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
    # The 2026-08-10 probes (Reddit): `www.reddit.com/r/<sub>.rss` answered 200 with
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
    # The 2026-08-10 probes (YouTube): `feeds/videos.xml?channel_id=` answered 200 with
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
    # segment. The captive-portal caveat's control probes measured both —
    # `example.com` and `wikipedia.org` returned 200 with genuine origin content
    # from this host while the network appliance answered other domains with a
    # 503 login portal.
    #
    # The article host is this package's belief: the caveat records
    # `wikipedia.org` and
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
    # it is asked. It is what the captive-portal caveat is built on — a read
    # whose content is fixed is the only read that can tell "this network is
    # answering for the
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
