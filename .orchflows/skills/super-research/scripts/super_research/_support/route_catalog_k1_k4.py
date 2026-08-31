"""K1–K4 route declarations and the isolated offline fixture route."""

from __future__ import annotations

from typing import Dict

from .route_contracts import (
    ARCTIC_SHIFT_ORIGIN,
    ARCTIC_SHIFT_POSTS_ROUTE,
    BING_NEWS_RSS_ROUTE,
    BING_RSS_ROUTE,
    DDG_HTML_ROUTE,
    FAKE_OFFLINE_ROUTE,
    FXTWITTER_API_ROUTE,
    GOOGLE_NEWS_RSS_ROUTE,
    INSTAGRAM_WEB_APP_ID,
    INSTAGRAM_WEB_PROFILE_ROUTE,
    JSON_CONTENT_TYPE,
    LINKEDIN_PUBLIC_PROFILE_ROUTE,
    REDDIT_SHREDDIT_COMMENTS_ROUTE,
    REDDIT_SHREDDIT_LISTING_ROUTE,
    REDDIT_SHREDDIT_SEARCH_ROUTE,
    REDDIT_SHREDDIT_SUBREDDIT_SEARCH_ROUTE,
    REDDIT_SITE_ORIGIN,
    X_GUEST_ACTIVATE_ROUTE,
    X_GUEST_GRAPHQL_ROUTE,
    X_GUEST_PUBLIC_BEARER,
    X_SYNDICATION_TIMELINE_ROUTE,
    YOUTUBE_INNERTUBE_ROUTE,
    YOUTUBE_INNERTUBE_WEB_KEY,
    YOUTUBE_TIMEDTEXT_ROUTE,
    RouteConstant,
)


K1_K4_ROUTE_CONSTANTS: Dict[str, RouteConstant] = {
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
            # `search`'s upload-date filter, measured live 2026-08-31 (R.02):
            # an opaque origin-published value, spent verbatim like a cursor
            # is, never decoded or built here. Added because a param outside
            # this closed list is appended as a query string instead
            # (`_support/transport_request.py`), which is not where this
            # route reads a filter.
            ("params", ("params",)),
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
}


OFFLINE_ROUTE_CONSTANTS: Dict[str, RouteConstant] = {
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
