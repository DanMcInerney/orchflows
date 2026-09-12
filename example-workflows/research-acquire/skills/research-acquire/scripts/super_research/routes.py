"""Declared public read routes, including their endpoint grammar and operator.

Transport re-exports this table and owns HTTPS and host-budget enforcement.
The open page/feed route takes a caller URL; all other origins are declared here.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Tuple

ARCTIC_SHIFT_SEARCH_ROUTE = "arctic_shift_posts_search"
X_SITE_ORIGIN = "https://x.com"
WEB_PAGE_OPEN_ROUTE = "web_page_open"
ARCTIC_SHIFT_POSTS_ROUTE = "arctic_shift_posts_ids"
REDDIT_SHREDDIT_LISTING_ROUTE = "reddit_shreddit_listing"
REDDIT_SHREDDIT_SEARCH_ROUTE = "reddit_shreddit_search"
REDDIT_SHREDDIT_SUBREDDIT_SEARCH_ROUTE = "reddit_shreddit_subreddit_search"
REDDIT_SHREDDIT_COMMENTS_ROUTE = "reddit_shreddit_comments"
HN_ALGOLIA_ITEM_ROUTE = "hn_algolia_item"
FXTWITTER_API_ROUTE = "fxtwitter_api"
HN_ALGOLIA_SEARCH_ROUTE = "hn_algolia_search"
HN_FIREBASE_ITEM_ROUTE = "hn_firebase_item"
GITHUB_REST_ROUTE = "github_rest"
GITHUB_SEARCH_ROUTE = "github_search"
YOUTUBE_CHANNEL_FEED_ROUTE = "youtube_channel_feed"
CROSSREF_WORKS_ROUTE = "crossref_works"
ARXIV_QUERY_ROUTE = "arxiv_query"
FAKE_OFFLINE_ROUTE = "fake_offline"
REDDIT_SITE_ORIGIN = "https://www.reddit.com"
ARCTIC_SHIFT_ORIGIN = "https://arctic-shift.photon-reddit.com"
OPEN_ORIGIN = ""

@dataclass(frozen=True)
class RouteConstant:
    """One endpoint; path parameters and suffix are consumed before query encoding."""
    route_id: str
    access_class: str
    method: str
    origin: str
    path: str
    accept: str
    operator_identity: str = ""
    path_params: Tuple[str, ...] = ()
    path_suffix: str = ""

ROUTE_CONSTANTS: Dict[str, RouteConstant] = {
    ARCTIC_SHIFT_SEARCH_ROUTE: RouteConstant(
        route_id=ARCTIC_SHIFT_SEARCH_ROUTE, access_class="K3", method="GET",
        origin=ARCTIC_SHIFT_ORIGIN, path="/api/posts/search",
        accept="application/json", operator_identity="arctic-shift",
    ),
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
    FXTWITTER_API_ROUTE: RouteConstant(
        route_id=FXTWITTER_API_ROUTE,
        access_class="K3",
        method="GET",
        origin="https://api.fxtwitter.com",
        path="/2/conversation",
        accept="application/json",
        operator_identity="fxtwitter",
        path_params=("subject",),
    ),
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
    YOUTUBE_CHANNEL_FEED_ROUTE: RouteConstant(
        route_id=YOUTUBE_CHANNEL_FEED_ROUTE,
        access_class="K0",
        method="GET",
        origin="https://www.youtube.com",
        path="/feeds/videos.xml",
        accept="application/atom+xml",
        operator_identity="youtube",
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
