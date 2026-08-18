"""Documented-keyless K0 route declarations."""

from __future__ import annotations

from typing import Dict

from .route_contracts import (
    BLUESKY_AUTHOR_FEED_ROUTE,
    BLUESKY_SEARCH_POSTS_ROUTE,
    GITHUB_REST_ROUTE,
    GITHUB_SEARCH_ROUTE,
    HN_ALGOLIA_ITEM_ROUTE,
    HN_ALGOLIA_SEARCH_ROUTE,
    HN_FIREBASE_ITEM_ROUTE,
    KALSHI_MARKETS_ROUTE,
    LINKEDIN_JOBS_GUEST_SEARCH_ROUTE,
    MANIFOLD_MARKETS_ROUTE,
    OPEN_ORIGIN,
    POLYMARKET_GAMMA_ROUTE,
    PUBLIC_PAGE_ARTICLE_ROUTE,
    PUBLIC_PAGE_CONTROL_ROUTE,
    REDDIT_FEED_ROUTE,
    REDDIT_SITE_ORIGIN,
    STOCKTWITS_STREAM_ROUTE,
    STOCKTWITS_SYMBOL_SEARCH_ROUTE,
    WEB_PAGE_OPEN_ROUTE,
    YOUTUBE_CHANNEL_FEED_ROUTE,
    RouteConstant,
)


K0_ROUTE_CONSTANTS: Dict[str, RouteConstant] = {
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
}
