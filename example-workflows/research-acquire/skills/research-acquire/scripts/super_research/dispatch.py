"""Static adapter dispatch; each module owns its descriptors, parsing and reads.

The table pairs each imported module with the operation resolver used for window
capability decisions, or None when all its operations share one capability.
Nothing here discovers plugins, paces requests or reaches the network itself.
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

ADAPTERS = {
    "bluesky": (bluesky, bluesky.operation_for),
    "fake": (fake, None),
    "gdelt": (gdelt, None),
    "github_rest": (github_rest, github_rest.operation_for),
    "hacker_news": (hacker_news, hacker_news.operation_for),
    "instagram_public": (instagram_public, None),
    "linkedin_jobs": (linkedin_jobs, None),
    "linkedin_public": (linkedin_public, None),
    "oembed": (oembed, None),
    "open_page": (open_page, None),
    "prediction_markets": (prediction_markets, None),
    "public_page": (public_page, None),
    "reddit_archive": (reddit_archive, reddit_archive.operation_for),
    "reddit_feed": (reddit_feed, reddit_feed.operation_for),
    "reddit_shreddit": (reddit_shreddit, reddit_shreddit.operation_for),
    "rss_atom": (rss_atom, None),
    "scholarly": (scholarly, None),
    "stack_exchange": (stack_exchange, None),
    "stocktwits": (stocktwits, None),
    "tiktok_public": (tiktok_public, None),
    "web_search": (web_search, web_search.operation_for),
    "wikimedia_pageviews": (wikimedia_pageviews, None),
    "x_xcancel": (x_xcancel, x_xcancel.operation_for),
    "x_fxtwitter": (x_fxtwitter, None),
    "x_guest": (x_guest, lambda request: x_guest.operation_for(request.target_ids[0] if request.target_ids else request.query)),
    "x_syndication": (x_syndication, None),
    "youtube_innertube": (youtube_innertube, youtube_innertube.operation_for),
}
ADAPTER_IDS = tuple(ADAPTERS)


class RunnerError(RuntimeError):
    """The core was asked for something it refuses to guess at."""


def descriptor_for(adapter_id: str) -> Optional[AdapterDescriptor]:
    """The adapter's readable surface; unknown adapters have none."""
    entry = ADAPTERS.get(adapter_id)
    return entry[0].DESCRIPTOR if entry is not None else None


def call_adapter(
    adapter_id: str, carrier: transport.Transport, request: AdapterRequest
) -> NativePage:
    """One bounded adapter call returning exactly one NativePage."""
    entry = ADAPTERS.get(adapter_id)
    if entry is None:
        raise RunnerError("unknown adapter " + adapter_id)
    return entry[0].fetch_native_page(carrier, request)


def surface_descriptors(adapter_id: str) -> Tuple[AdapterDescriptor, ...]:
    """Every budgeted route, including token activation that returns no records."""
    entry = ADAPTERS.get(adapter_id)
    if entry is None:
        return ()
    module = entry[0]
    return getattr(module, "SURFACE_DESCRIPTORS", (module.DESCRIPTOR,))


def declared_descriptors() -> Dict[str, AdapterDescriptor]:
    """Every adapter this core lists, by id."""
    return {adapter_id: module.DESCRIPTOR for adapter_id, (module, _) in ADAPTERS.items()}


def operation_for(adapter_id: str, request: AdapterRequest) -> str:
    """Resolve the operation only when window capability differs by operation."""
    entry = ADAPTERS.get(adapter_id)
    return entry[1](request)[0] if entry is not None and entry[1] is not None else ""
