"""Every adapter this core can reach, spelled once, and the literal branches that reach it.

``ADAPTER_IDS`` is a literal tuple, not a registry: exact search over an id
finds every branch below, and a later adapter listed here without all of them
fails loudly. :func:`descriptor_for` answers what an adapter reads,
:func:`surface_descriptors` every route it spends a budget on,
:func:`call_adapter` makes one bounded call, and :func:`operation_for` resolves
the operation a request performs the adapter's own way. Nothing here paces,
pages, or reaches the network on its own.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

from . import transport
from .adapters import AdapterDescriptor, AdapterRequest, NativePage
from .adapters import bluesky, fake, gdelt, github_rest, hacker_news, instagram_public
from .adapters import linkedin_jobs, linkedin_public, oembed, open_page, prediction_markets
from .adapters import public_page, reddit_archive, reddit_feed, reddit_shreddit
from .adapters import rss_atom, scholarly, stack_exchange, stocktwits, tiktok_public
from .adapters import web_search, wikimedia_pageviews
from .adapters import x_fxtwitter, x_guest, x_syndication, x_xcancel, youtube_innertube

# Every adapter this core can reach, spelled once. It is a literal tuple, not a
# registry: exact search over an id still finds the two branches below, and a
# later adapter listed here without both of them fails loudly.
ADAPTER_IDS = (
    "bluesky",
    "fake",
    "gdelt",
    "github_rest",
    "hacker_news",
    "instagram_public",
    "linkedin_jobs",
    "linkedin_public",
    "oembed",
    "open_page",
    "prediction_markets",
    "public_page",
    "reddit_archive",
    "reddit_feed",
    "reddit_shreddit",
    "rss_atom",
    "scholarly",
    "stack_exchange",
    "stocktwits",
    "tiktok_public",
    "web_search",
    "wikimedia_pageviews",
    "x_xcancel",
    "x_fxtwitter",
    "x_guest",
    "x_syndication",
    "youtube_innertube",
)


class RunnerError(RuntimeError):
    """The core was asked for something it refuses to guess at."""


def descriptor_for(adapter_id: str) -> Optional[AdapterDescriptor]:
    """Literal branches only. An unknown adapter is refused, never guessed."""

    if adapter_id == "bluesky":
        return bluesky.DESCRIPTOR
    if adapter_id == "fake":
        return fake.DESCRIPTOR
    if adapter_id == "gdelt":
        return gdelt.DESCRIPTOR
    if adapter_id == "github_rest":
        return github_rest.DESCRIPTOR
    if adapter_id == "hacker_news":
        return hacker_news.DESCRIPTOR
    if adapter_id == "instagram_public":
        return instagram_public.DESCRIPTOR
    if adapter_id == "linkedin_jobs":
        return linkedin_jobs.DESCRIPTOR
    if adapter_id == "linkedin_public":
        return linkedin_public.DESCRIPTOR
    if adapter_id == "oembed":
        return oembed.DESCRIPTOR
    if adapter_id == "open_page":
        return open_page.DESCRIPTOR
    if adapter_id == "prediction_markets":
        return prediction_markets.DESCRIPTOR
    if adapter_id == "public_page":
        return public_page.DESCRIPTOR
    if adapter_id == "reddit_archive":
        return reddit_archive.DESCRIPTOR
    if adapter_id == "reddit_feed":
        return reddit_feed.DESCRIPTOR
    if adapter_id == "reddit_shreddit":
        return reddit_shreddit.DESCRIPTOR
    if adapter_id == "rss_atom":
        return rss_atom.DESCRIPTOR
    if adapter_id == "scholarly":
        return scholarly.DESCRIPTOR
    if adapter_id == "stack_exchange":
        return stack_exchange.DESCRIPTOR
    if adapter_id == "stocktwits":
        return stocktwits.DESCRIPTOR
    if adapter_id == "tiktok_public":
        return tiktok_public.DESCRIPTOR
    if adapter_id == "web_search":
        return web_search.DESCRIPTOR
    if adapter_id == "wikimedia_pageviews":
        return wikimedia_pageviews.DESCRIPTOR
    if adapter_id == "x_xcancel":
        return x_xcancel.DESCRIPTOR
    if adapter_id == "x_fxtwitter":
        return x_fxtwitter.DESCRIPTOR
    if adapter_id == "x_guest":
        return x_guest.DESCRIPTOR
    if adapter_id == "x_syndication":
        return x_syndication.DESCRIPTOR
    if adapter_id == "youtube_innertube":
        return youtube_innertube.DESCRIPTOR
    return None


def call_adapter(
    adapter_id: str, carrier: transport.Transport, request: AdapterRequest
) -> NativePage:
    """One bounded adapter call returning exactly one NativePage."""

    if adapter_id == "bluesky":
        return bluesky.fetch_native_page(carrier, request)
    if adapter_id == "fake":
        return fake.fetch_native_page(carrier, request)
    if adapter_id == "gdelt":
        return gdelt.fetch_native_page(carrier, request)
    if adapter_id == "github_rest":
        return github_rest.fetch_native_page(carrier, request)
    if adapter_id == "hacker_news":
        return hacker_news.fetch_native_page(carrier, request)
    if adapter_id == "instagram_public":
        return instagram_public.fetch_native_page(carrier, request)
    if adapter_id == "linkedin_jobs":
        return linkedin_jobs.fetch_native_page(carrier, request)
    if adapter_id == "linkedin_public":
        return linkedin_public.fetch_native_page(carrier, request)
    if adapter_id == "oembed":
        return oembed.fetch_native_page(carrier, request)
    if adapter_id == "open_page":
        return open_page.fetch_native_page(carrier, request)
    if adapter_id == "prediction_markets":
        return prediction_markets.fetch_native_page(carrier, request)
    if adapter_id == "public_page":
        return public_page.fetch_native_page(carrier, request)
    if adapter_id == "reddit_archive":
        return reddit_archive.fetch_native_page(carrier, request)
    if adapter_id == "reddit_feed":
        return reddit_feed.fetch_native_page(carrier, request)
    if adapter_id == "reddit_shreddit":
        return reddit_shreddit.fetch_native_page(carrier, request)
    if adapter_id == "rss_atom":
        return rss_atom.fetch_native_page(carrier, request)
    if adapter_id == "scholarly":
        return scholarly.fetch_native_page(carrier, request)
    if adapter_id == "stack_exchange":
        return stack_exchange.fetch_native_page(carrier, request)
    if adapter_id == "stocktwits":
        return stocktwits.fetch_native_page(carrier, request)
    if adapter_id == "tiktok_public":
        return tiktok_public.fetch_native_page(carrier, request)
    if adapter_id == "web_search":
        return web_search.fetch_native_page(carrier, request)
    if adapter_id == "wikimedia_pageviews":
        return wikimedia_pageviews.fetch_native_page(carrier, request)
    if adapter_id == "x_xcancel":
        return x_xcancel.fetch_native_page(carrier, request)
    if adapter_id == "x_fxtwitter":
        return x_fxtwitter.fetch_native_page(carrier, request)
    if adapter_id == "x_guest":
        return x_guest.fetch_native_page(carrier, request)
    if adapter_id == "x_syndication":
        return x_syndication.fetch_native_page(carrier, request)
    if adapter_id == "youtube_innertube":
        return youtube_innertube.fetch_native_page(carrier, request)
    raise RunnerError("no adapter branch for " + adapter_id)


def surface_descriptors(adapter_id: str) -> Tuple[AdapterDescriptor, ...]:
    """Every route one adapter can reach, one descriptor each.

    Most adapters read one route and this is its one descriptor. Sixteen do not.
    Nine read a further route plainly — ``bluesky``, ``oembed``,
    ``prediction_markets``, ``reddit_shreddit``, ``scholarly``,
    ``stocktwits``, ``tiktok_public``, ``web_search`` and
    ``youtube_innertube`` — and four are worth a reason each: ``hacker_news``
    reads two origins, ``github_rest`` reads one origin whose anonymous hour is
    counted in two separate buckets, ``public_page`` selects between two
    documents, and ``x_guest`` spends an activation to authorize the route it
    reads. A budget belongs to whoever sets it, so an adapter like those
    declares one descriptor per route and this is where the second becomes
    reachable. Literal branches, like the two above: a surface the core cannot
    see here is a route the scheduler would refuse to pace.

    A surface is not always something a caller reads. ``x_guest``'s activation
    returns a token rather than a record, so it appears here — where budgets
    are collected — and never in :func:`descriptor_for`, which answers what an
    adapter reads.
    """

    if adapter_id == "x_xcancel":
        return x_xcancel.SURFACE_DESCRIPTORS
    if adapter_id == "reddit_archive":
        return reddit_archive.SURFACE_DESCRIPTORS
    if adapter_id == "reddit_feed":
        return reddit_feed.SURFACE_DESCRIPTORS
    if adapter_id == "bluesky":
        return bluesky.SURFACE_DESCRIPTORS
    if adapter_id == "github_rest":
        return github_rest.SURFACE_DESCRIPTORS
    if adapter_id == "hacker_news":
        return hacker_news.SURFACE_DESCRIPTORS
    if adapter_id == "oembed":
        return oembed.SURFACE_DESCRIPTORS
    if adapter_id == "prediction_markets":
        return prediction_markets.SURFACE_DESCRIPTORS
    if adapter_id == "public_page":
        return public_page.SURFACE_DESCRIPTORS
    if adapter_id == "reddit_shreddit":
        return reddit_shreddit.SURFACE_DESCRIPTORS
    if adapter_id == "scholarly":
        return scholarly.SURFACE_DESCRIPTORS
    if adapter_id == "stocktwits":
        return stocktwits.SURFACE_DESCRIPTORS
    if adapter_id == "tiktok_public":
        return tiktok_public.SURFACE_DESCRIPTORS
    if adapter_id == "web_search":
        return web_search.SURFACE_DESCRIPTORS
    if adapter_id == "x_guest":
        return x_guest.SURFACE_DESCRIPTORS
    if adapter_id == "youtube_innertube":
        return youtube_innertube.SURFACE_DESCRIPTORS
    descriptor = descriptor_for(adapter_id)
    return () if descriptor is None else (descriptor,)


def declared_descriptors() -> Dict[str, AdapterDescriptor]:
    """Every adapter this core lists, by id."""

    found: Dict[str, AdapterDescriptor] = {}
    for adapter_id in ADAPTER_IDS:
        descriptor = descriptor_for(adapter_id)
        if descriptor is not None:
            found[adapter_id] = descriptor
    return found


def operation_for(adapter_id: str, request: AdapterRequest) -> str:
    """The operation this request performs, resolved the adapter's own way.

    Literal branches, like `descriptor_for` and `call_adapter`:
    an adapter whose operations disagree is asked its own already-correct
    parse rather than have that parse re-derived here a second time. Every
    other adapter's calls are one shape, so its operation is the empty
    string regardless of what the request names.
    """

    if adapter_id == "reddit_archive":
        return reddit_archive.operation_for(request)[0]
    if adapter_id == "reddit_feed":
        return reddit_feed.operation_for(request)[0]
    if adapter_id == "x_xcancel":
        return x_xcancel.operation_for(request)[0]
    if adapter_id == "bluesky":
        return bluesky.operation_for(request)[0]
    if adapter_id == "github_rest":
        return github_rest.operation_for(request)[0]
    if adapter_id == "hacker_news":
        return hacker_news.operation_for(request)[0]
    if adapter_id == "reddit_shreddit":
        return reddit_shreddit.operation_for(request)[0]
    if adapter_id == "web_search":
        return web_search.operation_for(request)[0]
    if adapter_id == "x_guest":
        target_id = request.target_ids[0] if request.target_ids else request.query
        return x_guest.operation_for(target_id)[0]
    if adapter_id == "youtube_innertube":
        return youtube_innertube.operation_for(request)[0]
    return ""
