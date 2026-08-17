"""Probe table: the one liveness read each live adapter is smoked on.

Thirteen probes, one per live adapter, and the offline adapter deliberately has
none — a smoke for ``fake`` would report this suite's health as a platform's.
Each probe names the step its read is made as, the route it leaves by, and the
field set that adapter's row in the spec's adapter roster promises. Nothing
here runs: this module is the declaration, :mod:`.smoke` is what does it.

It is a literal table for the reason every other enumeration in this package
is one. A probe is the exact target a real origin will be asked about, and
exact search over an adapter's name has to find it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from . import transport

# The adapter that reads a fixture rather than an origin, and so is the one
# member of the roster with no smoke.
OFFLINE_ADAPTER = "fake"

# How a declared field name is read off a record. A bare name is a record
# field; the two prefixes reach the two places a route's own vocabulary lands.
ENGAGEMENT_PREFIX = "engagement:"
ATTRIBUTE_PREFIX = "attribute:"


@dataclass(frozen=True)
class SmokeProbe:
    """One adapter's liveness read, spelled completely and frozen.

    ``target`` is a query for a discovery probe and a target id for a
    hydration one — the same two shapes a manifest step carries, because a
    smoke is one ordinary step and not a private path into an adapter.

    ``field_sets`` is the roster row, by the content kind each part of it
    describes. Most rows describe one kind; Instagram's row describes two, a
    profile and the posts under it, and no single record carries both halves.

    ``target_recovery`` is how to obtain a current target when this one stops
    resolving. A query never goes stale and declares none; a named item, slug
    or channel id can, and a probe target that has quietly rotted would
    otherwise report a working platform as a gap. Same shape, and the same
    reason, as an adapter's ``volatile_identifiers``.
    """

    adapter_id: str
    kind: str
    target: str
    route_id: str
    field_sets: Tuple[Tuple[str, Tuple[str, ...]], ...]
    target_recovery: str = ""
    # Set above every page size the roster measured, so a whole answer is never
    # reported as a truncated one. It says only how much of that one answer is
    # kept, and it bounds nothing about what the read costs: what holds a smoke
    # to one call is `smoke.PAGES_PER_SMOKE`, the page bound the step this probe
    # becomes declares. Until the core could page, that bound was an emergent
    # property of a discovery step authorizing exactly one call and was written
    # down nowhere; it is a stated one now, and no probe can opt out of it.
    max_items: int = 200


# Thirteen probes, one per live adapter, each asserting the field set its row
# in the spec's adapter roster names. Two rows name a field the artifact
# contract cannot carry and are noted where they occur; nothing else is
# omitted, and nothing is asserted that the row does not name.
SMOKE_PROBES = (
    SmokeProbe(
        adapter_id="web_search",
        kind="discovery",
        target="rate limiting",
        route_id=transport.DDG_HTML_ROUTE,
        field_sets=(("web_hit", ("title", "canonical_locator", "body")),),
    ),
    SmokeProbe(
        adapter_id="public_page",
        kind="hydration",
        # The selection and the one document inside it, in this adapter's own
        # grammar. Nothing here is an address: the host belongs to the route.
        target="article:Rate_limiting",
        route_id=transport.PUBLIC_PAGE_ARTICLE_ROUTE,
        field_sets=(
            (
                "web_page",
                (
                    "body",
                    "exact_content_hash",
                    "observed_at",
                    ATTRIBUTE_PREFIX + "content_type",
                    ATTRIBUTE_PREFIX + "link",
                    # The row's "redirects", which is these two facts: what was
                    # asked, and what answered.
                    ATTRIBUTE_PREFIX + "requested_url",
                    ATTRIBUTE_PREFIX + "final_url",
                ),
            ),
        ),
        target_recovery=(
            "Any article title this route's own origin serves; the selection"
            " table in adapters/public_page.py names the two selections and"
            " refuses anything shaped like an address."
        ),
    ),
    SmokeProbe(
        adapter_id="reddit_archive",
        kind="hydration",
        # A long-archived post rather than a recent one: this is an archive,
        # and an old submission is the target least likely to be absent from it.
        target="z1c9z",
        route_id=transport.ARCTIC_SHIFT_POSTS_ROUTE,
        field_sets=(
            (
                "post",
                (
                    "title",
                    "author",
                    "community",
                    "canonical_locator",
                    "published_at",
                    ENGAGEMENT_PREFIX + "score",
                    ENGAGEMENT_PREFIX + "num_comments",
                ),
            ),
        ),
        # The row also names `upvote_ratio` and `selftext`. Neither is asserted:
        # a ratio is a float and the artifact admits only exact integer metrics,
        # and a link submission has no self text, so requiring it would fail a
        # healthy read.
        target_recovery=(
            "Any base-36 submission id; one comes back on the canonical_locator"
            " of every reddit_feed record."
        ),
    ),
    SmokeProbe(
        adapter_id="reddit_feed",
        kind="discovery",
        target="programming",
        route_id=transport.REDDIT_FEED_ROUTE,
        field_sets=(("post", ("title", "author", "canonical_locator", "published_at")),),
    ),
    SmokeProbe(
        adapter_id="x_syndication",
        kind="hydration",
        target="simonw",
        route_id=transport.X_SYNDICATION_TIMELINE_ROUTE,
        field_sets=(
            (
                "post",
                (
                    "body",
                    "published_at",
                    "native_parent_id",
                    ENGAGEMENT_PREFIX + "favorite_count",
                    ENGAGEMENT_PREFIX + "retweet_count",
                    ENGAGEMENT_PREFIX + "reply_count",
                    ENGAGEMENT_PREFIX + "quote_count",
                ),
            ),
        ),
        target_recovery="Any public account's handle.",
    ),
    SmokeProbe(
        adapter_id="x_guest",
        kind="hydration",
        # The account operation rather than the post one: a handle outlives any
        # single post id, and reaching it at all is what proves the guest token
        # still activates and still authorizes a read.
        target="user:simonw",
        route_id=transport.X_GUEST_GRAPHQL_ROUTE,
        field_sets=(
            (
                "profile",
                (
                    "native_item_id",
                    "title",
                    "author",
                    "canonical_locator",
                    "published_at",
                    ENGAGEMENT_PREFIX + "followers_count",
                ),
            ),
        ),
        target_recovery=(
            "Any public account's handle, prefixed `user:`. The three"
            " operations this route serves are named in adapters/x_guest.py."
        ),
    ),
    SmokeProbe(
        adapter_id="linkedin_public",
        kind="hydration",
        target="williamhgates",
        route_id=transport.LINKEDIN_PUBLIC_PROFILE_ROUTE,
        field_sets=(
            (
                "profile",
                (
                    "title",
                    "body",
                    ATTRIBUTE_PREFIX + "jobTitle",
                    ATTRIBUTE_PREFIX + "addressLocality",
                    ATTRIBUTE_PREFIX + "worksFor",
                    ATTRIBUTE_PREFIX + "alumniOf",
                ),
            ),
        ),
        target_recovery=(
            "Any public profile slug — the last path segment of a"
            " linkedin.com/in/ address. A profile whose owner published no"
            " locality or schooling carries fewer fields than the row names."
        ),
    ),
    SmokeProbe(
        adapter_id="linkedin_jobs",
        kind="discovery",
        target="reliability engineer",
        route_id=transport.LINKEDIN_JOBS_GUEST_SEARCH_ROUTE,
        field_sets=(
            ("job_posting", ("native_item_id", "title", "author", "published_at")),
        ),
    ),
    SmokeProbe(
        adapter_id="youtube_innertube",
        kind="hydration",
        target="dQw4w9WgXcQ",
        route_id=transport.YOUTUBE_INNERTUBE_ROUTE,
        field_sets=(
            (
                "video",
                ("title", "published_at", ENGAGEMENT_PREFIX + "viewCount"),
            ),
        ),
        target_recovery="Any public video id; the row's fields are the player answer's.",
    ),
    SmokeProbe(
        adapter_id="instagram_public",
        kind="hydration",
        target="instagram",
        route_id=transport.INSTAGRAM_WEB_PROFILE_ROUTE,
        field_sets=(
            (
                "profile",
                ("title", "author", "body", ENGAGEMENT_PREFIX + "edge_followed_by.count"),
            ),
            (
                "post",
                (
                    "native_item_id",
                    "published_at",
                    ENGAGEMENT_PREFIX + "edge_liked_by.count",
                    ENGAGEMENT_PREFIX + "edge_media_to_comment.count",
                ),
            ),
        ),
        target_recovery=(
            "Any public account's username. An account that hides its like"
            " counts carries fewer fields than the row names."
        ),
    ),
    SmokeProbe(
        adapter_id="hacker_news",
        kind="discovery",
        # This adapter reads two surfaces and a smoke makes one call. Search is
        # the one the row leads with and the capability the prior spec's
        # adapter did not have at all; the Firebase surface the row also names
        # is reached by a hydration step, not by this probe.
        target="python",
        route_id=transport.HN_ALGOLIA_SEARCH_ROUTE,
        field_sets=(
            (
                "story",
                (
                    "title",
                    "author",
                    "published_at",
                    ENGAGEMENT_PREFIX + "points",
                    ENGAGEMENT_PREFIX + "num_comments",
                ),
            ),
        ),
    ),
    SmokeProbe(
        adapter_id="github_rest",
        kind="hydration",
        # The repository surface rather than the search one, for the same
        # reason in reverse: an anonymous hour is sixty reads, and this is the
        # surface whose answer carries the row's counts.
        target="python/cpython",
        route_id=transport.GITHUB_REST_ROUTE,
        field_sets=(
            (
                "repository",
                (
                    "title",
                    "body",
                    "author",
                    "published_at",
                    ENGAGEMENT_PREFIX + "stargazers_count",
                    ENGAGEMENT_PREFIX + "forks_count",
                    ENGAGEMENT_PREFIX + "open_issues_count",
                ),
            ),
        ),
        target_recovery="Any public owner/name pair.",
    ),
    SmokeProbe(
        adapter_id="rss_atom",
        kind="discovery",
        target="UC_x5XG1OV2P6uZZ5FSM9Ttw",
        route_id=transport.YOUTUBE_CHANNEL_FEED_ROUTE,
        field_sets=(
            (
                "feed_entry",
                ("native_item_id", "title", "author", "canonical_locator", "published_at"),
            ),
        ),
    ),
    SmokeProbe(
        adapter_id="reddit_shreddit",
        kind="discovery",
        # A listing rather than a search: it is the surface that names both
        # counts as its own attributes, so the row this asserts is the widest
        # one this adapter can carry.
        target="listing:programming",
        route_id=transport.REDDIT_SHREDDIT_LISTING_ROUTE,
        field_sets=(
            (
                "post",
                (
                    "native_item_id",
                    "title",
                    "author",
                    "community",
                    "canonical_locator",
                    "published_at",
                    ENGAGEMENT_PREFIX + "score",
                    ENGAGEMENT_PREFIX + "comment-count",
                ),
            ),
        ),
        target_recovery=(
            "Any subreddit name. The grammar is listing:<subreddit>[:<sort>[:<window>]]"
            " and adapters/reddit_shreddit.py names the sorts and windows the route"
            " serves."
        ),
    ),
    SmokeProbe(
        adapter_id="open_page",
        kind="hydration",
        # A document on a host no other route declares — an open read that
        # landed on a declared host is refused, which is the policy rather than
        # a liveness answer — and one whose content is stable enough that a
        # smoke is about the route rather than about today's news.
        target="https://www.iana.org/help/example-domains",
        route_id=transport.WEB_PAGE_OPEN_ROUTE,
        field_sets=(
            (
                "web_page",
                (
                    "title",
                    "body",
                    "exact_content_hash",
                    "observed_at",
                    ATTRIBUTE_PREFIX + "content_type",
                    ATTRIBUTE_PREFIX + "requested_url",
                    ATTRIBUTE_PREFIX + "final_url",
                    ATTRIBUTE_PREFIX + "link",
                ),
            ),
        ),
        target_recovery=(
            "Any https document on a host routes.py does not declare; the transport's"
            " own open_read_refusal names the three rules an address must meet."
        ),
    ),
    SmokeProbe(
        adapter_id="bluesky",
        kind="discovery",
        # The author feed rather than the search this adapter's primary
        # descriptor names. Measured 2026-08-17: the public AppView's
        # `searchPosts` answered 403 from the CDN in front of it on this host
        # while its sibling methods answered 200, so a smoke on the search
        # surface would report a working adapter dead. A probe names the
        # surface it takes, and this one takes the surface that answers.
        target="author:bsky.app",
        route_id=transport.BLUESKY_AUTHOR_FEED_ROUTE,
        field_sets=(
            (
                "post",
                (
                    "body",
                    "author",
                    "canonical_locator",
                    "published_at",
                    ENGAGEMENT_PREFIX + "likeCount",
                    ENGAGEMENT_PREFIX + "replyCount",
                    ATTRIBUTE_PREFIX + "did",
                    ATTRIBUTE_PREFIX + "cid",
                ),
            ),
        ),
        target_recovery="Any current Bluesky handle or DID; the AppView resolves both.",
    ),
    SmokeProbe(
        adapter_id="x_fxtwitter",
        kind="discovery",
        target="search:spacex",
        route_id=transport.FXTWITTER_API_ROUTE,
        field_sets=(
            (
                "post",
                (
                    "body",
                    "author",
                    "canonical_locator",
                    "published_at",
                    ENGAGEMENT_PREFIX + "likes",
                    ENGAGEMENT_PREFIX + "reposts",
                    ENGAGEMENT_PREFIX + "replies",
                    ATTRIBUTE_PREFIX + "lang",
                    ATTRIBUTE_PREFIX + "created_at",
                ),
            ),
        ),
        target_recovery=(
            "Any subject with posts. This operator answers 404 to a read it"
            " answers 200 to seconds later, reproduced 2026-08-17; nothing here"
            " retries, so a 404 is typed http_status and a second smoke decides."
        ),
    ),
    SmokeProbe(
        adapter_id="prediction_markets",
        kind="discovery",
        target="polymarket:SpaceX",
        route_id=transport.POLYMARKET_GAMMA_ROUTE,
        field_sets=(
            (
                "market",
                (
                    "native_item_id",
                    "title",
                    "canonical_locator",
                    ATTRIBUTE_PREFIX + "outcomes",
                    ATTRIBUTE_PREFIX + "outcomePrices",
                ),
            ),
        ),
        target_recovery=(
            "Any subject with an open market. A query matching nothing is an empty"
            " answer rather than a dead route, so a subject nobody is trading on"
            " would report this route unmet."
        ),
    ),
    SmokeProbe(
        adapter_id="stocktwits",
        kind="discovery",
        # A symbol with a stream that never goes quiet: an empty stream is an
        # honest answer and a useless liveness check.
        target="stream:AAPL",
        route_id=transport.STOCKTWITS_STREAM_ROUTE,
        field_sets=(
            (
                "post",
                ("native_item_id", "body", "author", "canonical_locator", "published_at"),
            ),
        ),
        target_recovery="Any listed ticker; symbols:<name> resolves one.",
    ),
)


def probe_for(adapter_id: str) -> Optional[SmokeProbe]:
    """This adapter's smoke, or nothing at all. No guessing, no default."""

    for probe in SMOKE_PROBES:
        if probe.adapter_id == adapter_id:
            return probe
    return None
