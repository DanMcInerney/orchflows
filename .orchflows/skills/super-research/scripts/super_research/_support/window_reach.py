"""Window-reach seam: whether one operation's origin can bound acquisition time.

Capability is a property of an *operation*, not of an adapter. `bluesky`
sends `since`/`until` on its search method and none on its author feed
(`adapters/bluesky.py:456-486`); `x_guest` and `github_rest` split the same
way. A tuple of adapter ids cannot say that, so this table is keyed by
adapter id and then by operation, and an adapter whose operations agree
declares once under the empty-string operation.

``WINDOW_REACH`` is total over the live roster and total over `fake`: every
key :data:`super_research.probes.SMOKE_PROBES` names resolves through
:func:`operation_for` to a row this table has, checked once below at import
— the same "fails loudly on an unnamed declaration" idiom
``adapters.AdapterDescriptor.__post_init__`` already holds for an unnamed
access class. An adapter or operation nothing here names raises
:class:`WindowReachError` rather than reading as either "can" or "cannot",
because a silent default would be a claim this module never measured.

Seven adapters read more than one operation from the wire, and the table
names each: `bluesky`, `hacker_news`, `web_search`, `reddit_shreddit`,
`github_rest`, `x_guest`, and `youtube_innertube`. The rest declare once,
either because every call they make is the same shape or because the
origin accepts none, measured. This module does not carry a bound into
any origin request — that is each adapter's own, which is the whole
reason the two tickets are split.

`R.02` settled every row `R.01` left conservatively `False` pending a live
read, except two: `x_guest`'s `UserTweets` and `x_fxtwitter`'s search both
have a measurement Details prescribes, and both were blocked before that
measurement could run — a stale credential on the one, a search endpoint
answering 404 to every live attempt on the other — recorded in R.02's own
report rather than guessed here. Both stay the conservative `False` a
caller reads honestly: a false "cannot" costs a caller a typed statement
it did not strictly need, while a false "can" would tell a windowed
step's reader nothing where the origin was silently never bounded.
"""

from __future__ import annotations

from typing import Dict, Tuple

from ..adapters import AdapterRequest
from ..adapters import (
    bluesky,
    github_rest,
    hacker_news,
    reddit_shreddit,
    web_search,
    x_guest,
    youtube_innertube,
)
from .. import probes


class WindowReachError(ValueError):
    """An adapter or operation named no window-reach declaration."""


# Loud and typed, on `StepResult.loss`: a windowed step whose operation is
# declared unable to bound time at the origin carries this code, so an empty
# in-window answer (no code) and an unhonored bound (this code) are two
# readings a caller tells apart mechanically rather than by parsing a
# sentence. `runner.run_step` is the one place that appends it.
WINDOW_NOT_HONORED = "window_not_honored"

# adapter_id -> operation -> whether that operation's origin can be asked to
# bound the read by time, in the origin's own terms. `""` is the operation
# key for an adapter whose calls are all one shape, matching the convention
# `coverage.DEPTH_TARGETS` already uses for `reddit_archive`.
WINDOW_REACH: Dict[str, Dict[str, bool]] = {
    # Measured: `bluesky.py:478-481` sends `since`/`until` on search only;
    # `:463-465` states the author feed takes none.
    "bluesky": {"search": True, "author": False},
    # Measured: `hacker_news.py:451-489` routes search, search_by_date and
    # comments through `_fetch_search`, which always applies
    # `window_filters`; item and tree read Firebase/Algolia by one id and
    # have no ordering a window could act on.
    "hacker_news": {
        "search": True,
        "search_by_date": True,
        "comments": True,
        "item": False,
        "tree": False,
    },
    # Measured: `_support/web_search_feeds.py:344-358` sends Google's
    # `when:Nd` only on the `gnews` branch; `ddg`, `bing` and `bingnews`
    # never build one.
    "web_search": {"gnews": True, "ddg": False, "bing": False, "bingnews": False},
    # Measured: `_fetch_listing`/`_fetch_search` (`adapters/reddit_shreddit.py`)
    # both send `t=<window>`, derived from the step's own `window_start` when
    # one is carried (`_origin_window`, `_support/reddit_shreddit_contract.
    # origin_time_bucket`) or from the argument grammar otherwise;
    # `_fetch_comments` takes no window at all.
    "reddit_shreddit": {"listing": True, "search": True, "comments": False},
    # `repo` is a single repository hydration by name: no ordering, no bound.
    # `issues` and `search` measured live 2026-08-31: `since=` on an active
    # repository's issue list and `created:` on search both genuinely filter
    # (`adapters/github_rest.origin_since_param`, `.origin_created_qualifier`).
    # `releases` measured the same way and does not: a `since=` set minutes in
    # the future answered the identical unfiltered page, so it stays `False`
    # as a measured fact rather than a conservative default.
    "github_rest": {"repo": False, "issues": True, "releases": False, "search": True},
    # `TweetResultByRestId` and `UserByScreenName` are single-item
    # hydrations with no ordering. `UserTweets` is the one operation with
    # one (`x_guest.py:139-143`) and is not settled offline: R.02 measures
    # it live, gated on the guest query id being current.
    "x_guest": {"TweetResultByRestId": False, "UserByScreenName": False, "UserTweets": False},
    # Origin accepts none, measured: neither selection carries a time
    # concept (`adapters/public_page.py`).
    "public_page": {"": False},
    # Origin accepts none: an arbitrary document fetch takes no query string
    # at all (`_support/transport_request.py:217-223` returns before one is
    # built).
    "open_page": {"": False},
    # Origin accepts none for this hydration: one archived post by id.
    "reddit_archive": {"": False},
    "reddit_feed": {"": False},
    "rss_atom": {"": False},
    "x_syndication": {"": False},
    # Origin accepts none, measured: this adapter never sets `published_at`
    # at all, so there is nothing on either side for a window to act on.
    "linkedin_public": {"": False},
    "instagram_public": {"": False},
    # Origin accepts none, measured in the adapter's own source: the
    # stream's `since` and `max` are message ids and not moments
    # (`stocktwits.py:399-402`); the symbol search is a name lookup.
    "stocktwits": {"": False},
    # Origin accepts none, measured in the adapter's own source
    # (`prediction_markets.py:410-413`).
    "prediction_markets": {"": False},
    # Measured live 2026-08-31: `keywords=python` bare vs. with a candidate
    # `f_TPR=r<seconds>` moved the oldest posting's date forward, and on a
    # rarer keyword (not already saturating the page) also dropped the row
    # count 10 -> 6 (`adapters/linkedin_jobs.origin_recency_term`).
    "linkedin_jobs": {"": True},
    # Not settled offline. `operation_params`'s own docstring
    # (`x_fxtwitter.py:447-448`) says this module states no term for a
    # bound it could send without inventing a query syntax — an absence of
    # documentation in this package, not a proven absence of capability.
    "x_fxtwitter": {"": False},
    # `search` measured live 2026-08-31: an origin-published upload-date
    # filter value, added to the route's closed POST-body list
    # (`_support/route_catalog_k1_k4.py`), moved every returned
    # `publishedTimeText` inside the named span against a nine-year-old
    # unfiltered baseline (`adapters/youtube_innertube.origin_upload_date_
    # filter`). `player`, `next` and `transcript` read one video and have
    # no time concept regardless — confidently `False`, not re-measured.
    "youtube_innertube": {
        "search": True,
        "player": False,
        "next": False,
        "transcript": False,
    },
    # The offline fixture reader: no origin exists for a bound to reach.
    "fake": {"": False},
}


def operation_for(adapter_id: str, request: AdapterRequest) -> str:
    """The operation this request performs, resolved the adapter's own way.

    Literal branches, like `runner.descriptor_for` and `runner.call_adapter`:
    an adapter whose operations disagree is asked its own already-correct
    parse rather than have that parse re-derived here a second time. Every
    other adapter's calls are one shape, so its operation is the empty
    string regardless of what the request names.
    """

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


def can_bound_at_origin(adapter_id: str, operation: str) -> bool:
    """Whether this exact (adapter, operation) pair can bound time at the origin.

    Raises rather than guesses on either side: an adapter this table does
    not name and an operation a named adapter does not name are both a
    declaration nothing made, and reading either as `True` or as `False`
    would be a capability this module never measured.
    """

    row = WINDOW_REACH.get(adapter_id)
    if row is None:
        raise WindowReachError(
            "no window-reach declared for adapter {0!r}; declared: {1}".format(
                adapter_id, ", ".join(sorted(WINDOW_REACH))
            )
        )
    if operation not in row:
        raise WindowReachError(
            "adapter {0!r} declares no window-reach for operation {1!r}; declared: {2}".format(
                adapter_id, operation, ", ".join(sorted(row)) or "<none>"
            )
        )
    return row[operation]


def reach_for(adapter_id: str, query: str = "", target_ids: Tuple[str, ...] = ()) -> bool:
    """Whether the operation this query or target names can bound time.

    The one entry point a caller needs: it resolves the operation the same
    way a real dispatch would and reads the declaration for it, without the
    caller building an :class:`AdapterRequest` of its own.
    """

    request = AdapterRequest(step_id="", query=query, target_ids=target_ids)
    return can_bound_at_origin(adapter_id, operation_for(adapter_id, request))


def _check_probe_completeness() -> None:
    """Every live probe's own operation resolves here, checked once at import.

    The same roster :mod:`super_research.probes` smokes is the roster this
    table must cover — not `runner.ADAPTER_IDS`, which this module cannot
    import without importing `runner` importing this module back. A probe
    naming an adapter or operation this table does not have fails the
    import that defines it, the same moment
    `adapters.AdapterDescriptor.__post_init__` would fail one declaring an
    unnamed access class.
    """

    for probe in probes.SMOKE_PROBES:
        if probe.kind == "discovery":
            request = AdapterRequest(step_id="", query=probe.target)
        else:
            request = AdapterRequest(step_id="", target_ids=(probe.target,))
        can_bound_at_origin(probe.adapter_id, operation_for(probe.adapter_id, request))


_check_probe_completeness()
