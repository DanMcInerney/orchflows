"""Route table: every endpoint this package can reach, spelled once.

A route states its access class, method, origin, path grammar, accept type,
operator and the public client credential it needs. :mod:`.transport` is the
one module that opens a socket and re-exports every name here, so callers
reach route data through it. Nothing here reaches the network.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

ARCTIC_SHIFT_SEARCH_ROUTE = "arctic_shift_posts_search"
REDDIT_SEARCH_FEED_ROUTE = "reddit_search_feed"
XCANCEL_SEARCH_ROUTE = "xcancel_search"
XCANCEL_STATUS_ROUTE = "xcancel_status"
X_SITE_ORIGIN = "https://x.com"
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
GDELT_DOC_ROUTE = "gdelt_doc"
STACKEXCHANGE_SEARCH_ROUTE = "stackexchange_search_advanced"
WIKIMEDIA_PAGEVIEWS_ROUTE = "wikimedia_pageviews_per_article"
OPENALEX_WORKS_ROUTE = "openalex_works"
CROSSREF_WORKS_ROUTE = "crossref_works"
ARXIV_QUERY_ROUTE = "arxiv_query"
TIKTOK_VIDEO_PAGE_ROUTE = "tiktok_video_page"
TIKTOK_PROFILE_PAGE_ROUTE = "tiktok_profile_page"
YOUTUBE_OEMBED_ROUTE = "youtube_oembed"
VIMEO_OEMBED_ROUTE = "vimeo_oembed"
SPOTIFY_OEMBED_ROUTE = "spotify_oembed"
SOUNDCLOUD_OEMBED_ROUTE = "soundcloud_oembed"
TIKTOK_OEMBED_ROUTE = "tiktok_oembed"
X_PUBLISH_OEMBED_ROUTE = "x_publish_oembed"
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
    # The probes records this key elided, as `AIzaSy...11qcW8`:
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
    # The probes records this one in full: the measured probe
    # sent `x-ig-app-id: 936619743392459` and got 200 with profile data.
    INSTAGRAM_WEB_APP_ID: PublicClientCredential(
        credential_id=INSTAGRAM_WEB_APP_ID,
        vendor="instagram",
        placement=HEADER_PLACEMENT,
        name="x-ig-app-id",
        value="936619743392459",
    ),
    # The probes records the activation returning 200 with a guest
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


# Order is part of the public table: schedulers and fixtures traverse this
# mapping without sorting.
ROUTE_CONSTANTS: Dict[str, RouteConstant] = {
    ARCTIC_SHIFT_SEARCH_ROUTE: RouteConstant(
        route_id=ARCTIC_SHIFT_SEARCH_ROUTE, access_class="K3", method="GET",
        origin=ARCTIC_SHIFT_ORIGIN, path="/api/posts/search",
        accept="application/json", operator_identity="arctic-shift",
    ),
    REDDIT_SEARCH_FEED_ROUTE: RouteConstant(
        route_id=REDDIT_SEARCH_FEED_ROUTE, access_class="K0", method="GET",
        origin=REDDIT_SITE_ORIGIN, path="/search.rss", accept="application/atom+xml",
        operator_identity="reddit",
    ),
    XCANCEL_SEARCH_ROUTE: RouteConstant(
        route_id=XCANCEL_SEARCH_ROUTE, access_class="K3", method="GET",
        origin="https://xcancel.com", path="/search", accept="text/html",
        operator_identity="xcancel",
    ),
    XCANCEL_STATUS_ROUTE: RouteConstant(
        route_id=XCANCEL_STATUS_ROUTE, access_class="K3", method="GET",
        origin="https://xcancel.com", path="", accept="text/html",
        operator_identity="xcancel", path_params=("handle", "collection", "id"),
    ),
    DDG_HTML_ROUTE: RouteConstant(
        route_id=DDG_HTML_ROUTE,
        access_class="K4",
        method="GET",
        origin="https://html.duckduckgo.com",
        path="/html/",
        accept="text/html",
        operator_identity="duckduckgo",
    ),
    # Measured: `html.duckduckgo.com`
    # answered 202 with a bot challenge to the package identity and to a
    # browser identity alike, so a second and third index are declared as
    # parallel planned routes, never substitutes. Bing publishes an RSS form
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
    # Measured: `news.google.com/rss/search?q=<q>+when:30d&hl=en-US
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
    # Measured: the `/svc/shreddit/`
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
    # `.json` forms answer 403 on this host to every identity, as the
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
    # Measured: a caption track's `baseUrl` from an
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
    # Measured: `hn.algolia.com/api/v1/items/<id>` answered 200 with
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
    # Measured: all three answered 200 keyless.
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
    # Measured: `api/2/streams/symbol/<SYM>.json`
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
    # Bluesky's public AppView, documented keyless. Measured on this
    # host: `searchPosts` answered 403 from the CDN in front of it ("Request
    # forbidden by administrative rules") while `getProfile` answered 200 —
    # the route is declared on the documentation and a live read decides
    # per host.
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
    # Measured: FxTwitter's public API answered 200
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
    # The probes: 200, 378 KB in 2.5 s, carrying 100 timeline entries
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
    # The probes: three GraphQL operations answered 200 with a guest
    # token. The measurement records the activation origin and not this one,
    # so the endpoint is pinned to the origin it does record; a live read is
    # what proves it. Both path segments come from the
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
    # The probes: 200, 27 KB in 0.7 s, ten jobs per page each
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
    # The probes: 200, 577 KB in 1.3 s, carrying a complete
    # ld+json Person block — **not** the 999 authwall an earlier assumption put
    # this whole platform behind. The slug is a path segment,
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
    # The probes: `youtubei/v1/search` answered 200 with 2.27 MB
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
    # The origin is the host the measurement names youtubei as living under,
    # and like the web key's elided middle it is unproven until a live read.
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
            # `search`'s upload-date filter, measured live:
            # an opaque origin-published value, spent verbatim like a cursor
            # is, never decoded or built here. Added because a param outside
            # this closed list is appended as a query string instead
            # (`transport.build_transport_request`), which is not where this
            # route reads a filter.
            ("params", ("params",)),
        ),
    ),
    # The probes: `api/v1/users/web_profile_info/?username=`
    # under `x-ig-app-id: 936619743392459` answered 200 with 455 KB in 2.9 s,
    # carrying username, biography, followers, post count and 12 recent posts.
    # The measurement records the path and the header and not the host, so
    # the origin here is this package's belief — Instagram's own web client
    # asks this of `www.instagram.com` — and it is unproven until a live read,
    # exactly as the X GraphQL origin is.
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
    # The probes: `hn.algolia.com/api/v1/search_by_date`
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
    # The probes:
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
    # The probes: `api.github.com` answered anonymously,
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
    # The probes: `api.github.com/search/repositories`
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
    # The probes: `www.reddit.com/r/<sub>.rss` answered 200 with
    # 32 KB in 1.4 s carrying title, link, author and updated — the one Reddit
    # surface that answered this host at all. Every `.json` form answered 403,
    # on `www.`, `old.` and `api.` alike, to a curl UA, a custom app UA and a
    # browser UA alike: IP-class blocking no header set changes, which is why
    # no `.json` route is declared here and none is a substitute.
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
    # The probes: `feeds/videos.xml?channel_id=` answered 200 with
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
    # The article host is this package's belief: the measurement records
    # `wikipedia.org` and articles live on the language subdomain. Unproven
    # until a live read, exactly as the Instagram and X GraphQL origins are.
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
    # GDELT DOC 2.0, a global news index with an origin-side time bound
    # (`startdatetime`/`enddatetime`, `timespan`), measured
    # answering keyless with `mode=artlist&format=json` rows carrying `url`,
    # `title`, `seendate` and `domain`, and asking one request per five
    # seconds in a plain-text 429 body. The measurement was over plain HTTP:
    # port 443 to this origin timed out from this host on every attempt,
    # curl and this package's own opener alike, while port 80 answered — and
    # the transport admits https only, so from such a host a read reports
    # `unreachable` rather than a platform fact. Declared on the
    # documentation; a live read decides per host, exactly as it does for the
    # Bluesky search surface.
    GDELT_DOC_ROUTE: RouteConstant(
        route_id=GDELT_DOC_ROUTE,
        access_class="K4",
        method="GET",
        origin="https://api.gdeltproject.org",
        path="/api/v2/doc/doc",
        accept=JSON_CONTENT_TYPE,
        operator_identity="gdelt",
    ),
    # Measured: keyless 200 with
    # `fromdate`/`todate` unix-second bounds genuinely filtering, the 300/day
    # anonymous quota reported in the body (`quota_max`/`quota_remaining`),
    # and — via this package's own opener — an uncompressed answer when no
    # `Accept-Encoding` is sent, gzip when one is; `transport.decoded_body`
    # honors the stated encoding either way.
    STACKEXCHANGE_SEARCH_ROUTE: RouteConstant(
        route_id=STACKEXCHANGE_SEARCH_ROUTE,
        access_class="K0",
        method="GET",
        origin="https://api.stackexchange.com",
        path="/2.3/search/advanced",
        accept="application/json",
        operator_identity="stackexchange",
    ),
    # Measured: keyless 200; the date range is two path segments,
    # `YYYYMMDD00` each, and the answer holds exactly the days inside them.
    # A cold read from a fresh address answered 429 once and 200 on the next
    # try — the ordinary cooldown covers it. The origin serves a metric
    # series keyed by article title, not documents.
    WIKIMEDIA_PAGEVIEWS_ROUTE: RouteConstant(
        route_id=WIKIMEDIA_PAGEVIEWS_ROUTE,
        access_class="K0",
        method="GET",
        origin="https://wikimedia.org",
        path="/api/rest_v1/metrics/pageviews/per-article",
        accept="application/json",
        operator_identity="wikimedia",
        path_params=("project", "access", "agent", "article", "granularity", "start", "end"),
    ),
    # The three scholarly surfaces, measured keyless 200, each
    # bounding publication time at the origin in its own grammar: OpenAlex
    # `filter=from_publication_date:...,to_publication_date:...`, Crossref
    # `filter=from-pub-date:...,until-pub-date:...`, arXiv
    # `submittedDate:[... TO ...]` inside `search_query`. The documented
    # `mailto` etiquette on the first two is deliberately not sent: it asks
    # for an email address, and this package attaches no identity a route
    # constant does not spell.
    OPENALEX_WORKS_ROUTE: RouteConstant(
        route_id=OPENALEX_WORKS_ROUTE,
        access_class="K0",
        method="GET",
        origin="https://api.openalex.org",
        path="/works",
        accept="application/json",
        operator_identity="openalex",
    ),
    CROSSREF_WORKS_ROUTE: RouteConstant(
        route_id=CROSSREF_WORKS_ROUTE,
        access_class="K0",
        method="GET",
        origin="https://api.crossref.org",
        path="/works",
        accept="application/json",
        operator_identity="crossref",
    ),
    ARXIV_QUERY_ROUTE: RouteConstant(
        route_id=ARXIV_QUERY_ROUTE,
        access_class="K0",
        method="GET",
        origin="https://export.arxiv.org",
        path="/api/query",
        accept="application/atom+xml",
        operator_identity="arxiv",
    ),
    # TikTok's public video and profile pages, each embedding the web
    # client's own rehydration JSON in a `__UNIVERSAL_DATA_FOR_REHYDRATION__`
    # script tag. Measured from this host with no cookie and no
    # script run: a video page answered 200 with id, `createTime`, the
    # `statsV2` counts, author and hashtags; a profile page answered 200 with
    # the profile's own counts and an **empty** `itemList` — the recent-video
    # list is fetched by a signed client-side call this package does not
    # perform, so the profile surface carries the profile alone.
    TIKTOK_VIDEO_PAGE_ROUTE: RouteConstant(
        route_id=TIKTOK_VIDEO_PAGE_ROUTE,
        access_class="K2",
        method="GET",
        origin="https://www.tiktok.com",
        path="",
        accept="text/html",
        operator_identity="tiktok",
        path_params=("handle", "resource", "video_id"),
    ),
    TIKTOK_PROFILE_PAGE_ROUTE: RouteConstant(
        route_id=TIKTOK_PROFILE_PAGE_ROUTE,
        access_class="K2",
        method="GET",
        origin="https://www.tiktok.com",
        path="",
        accept="text/html",
        operator_identity="tiktok",
        path_params=("handle",),
    ),
    # Six documented keyless oEmbed endpoints, measured 200,
    # each turning one platform URL into the item's own author, title and
    # thumbnail. Every origin runs its own oEmbed — nothing here is a third
    # party — and three of the six share a host with another declared route,
    # which is the same "different endpoint, different route, own budget"
    # shape the YouTube feed and InnerTube pair already holds.
    YOUTUBE_OEMBED_ROUTE: RouteConstant(
        route_id=YOUTUBE_OEMBED_ROUTE,
        access_class="K0",
        method="GET",
        origin="https://www.youtube.com",
        path="/oembed",
        accept="application/json",
        operator_identity="youtube",
    ),
    VIMEO_OEMBED_ROUTE: RouteConstant(
        route_id=VIMEO_OEMBED_ROUTE,
        access_class="K0",
        method="GET",
        origin="https://vimeo.com",
        path="/api/oembed.json",
        accept="application/json",
        operator_identity="vimeo",
    ),
    SPOTIFY_OEMBED_ROUTE: RouteConstant(
        route_id=SPOTIFY_OEMBED_ROUTE,
        access_class="K0",
        method="GET",
        origin="https://open.spotify.com",
        path="/oembed",
        accept="application/json",
        operator_identity="spotify",
    ),
    SOUNDCLOUD_OEMBED_ROUTE: RouteConstant(
        route_id=SOUNDCLOUD_OEMBED_ROUTE,
        access_class="K0",
        method="GET",
        origin="https://soundcloud.com",
        path="/oembed",
        accept="application/json",
        operator_identity="soundcloud",
    ),
    TIKTOK_OEMBED_ROUTE: RouteConstant(
        route_id=TIKTOK_OEMBED_ROUTE,
        access_class="K0",
        method="GET",
        origin="https://www.tiktok.com",
        path="/oembed",
        accept="application/json",
        operator_identity="tiktok",
    ),
    # publish.x.com answered 200 to this host from both its own name and the
    # publish.twitter.com 301 in front of it; a report of 402 for datacenter
    # addresses did not reproduce here. Declared on the measurement; a live
    # read decides per host.
    X_PUBLISH_OEMBED_ROUTE: RouteConstant(
        route_id=X_PUBLISH_OEMBED_ROUTE,
        access_class="K0",
        method="GET",
        origin="https://publish.x.com",
        path="/oembed",
        accept="application/json",
        operator_identity="x",
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
