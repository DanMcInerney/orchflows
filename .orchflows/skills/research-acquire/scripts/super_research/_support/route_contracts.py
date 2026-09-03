"""Route identifiers, value contracts, and public client credentials."""

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
