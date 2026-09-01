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
report rather than guessed here. Both are declared `None`: unmeasured, a
third reading distinct from either `True` or `False`, because a `False`
here would be a limit nobody actually checked and would read at the seam
exactly like `github_rest`'s `releases`, which R.02 did measure unable.
`can_bound_at_origin`/`reach_for` return the reading as given; the loss code
a windowed step carries for each is :func:`window_loss_code`'s.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

from .. import schema
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

# Loud and typed, beside it: a windowed step whose operation this table names
# but has never measured carries this code instead — never both at once, and
# never silently folded into `WINDOW_NOT_HONORED`, because a limit nobody
# checked and a limit R.02 proved are two different readings for a caller to
# act on differently. `window_loss_code` is the one place that chooses
# between them.
WINDOW_CAPABILITY_UNMEASURED = "window_capability_unmeasured"

# adapter_id -> operation -> whether that operation's origin can be asked to
# bound the read by time, in the origin's own terms — `True` or `False`, both
# measured — or `None`, declared but never measured. `""` is the operation
# key for an adapter whose calls are all one shape, matching the convention
# `coverage.DEPTH_TARGETS` already uses for `reddit_archive`.
WINDOW_REACH: Dict[str, Dict[str, Optional[bool]]] = {
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
    # hydrations with no ordering, measured `False`. `UserTweets` is the one
    # operation with one (`x_guest.py:139-143`) and R.02's prescribed live
    # measurement never ran: every attempt to mint a guest token answered
    # HTTP 401 (a stale `X_GUEST_PUBLIC_BEARER`), reproduced three times
    # across two origins. `None`, unmeasured, not the conservative `False`
    # a caller would read as a checked limit.
    "x_guest": {"TweetResultByRestId": False, "UserByScreenName": False, "UserTweets": None},
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
    # Not settled offline, and not settled live either: `operation_params`'s
    # own docstring (`x_fxtwitter.py:447-448`) says this module states no
    # term for a bound it could send without inventing a query syntax, and
    # R.02's prescribed live measurement found the origin unreachable for
    # it — six reads of `/2/search` across two arms and three query terms,
    # all HTTP 404, in the same window a sibling read of `/2/profile/SpaceX`
    # answered 200. `None`, unmeasured: an absence of a successful read, not
    # a proven absence of capability.
    "x_fxtwitter": {"": None},
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
    # Measured 2026-09-01 (the survey validation sweep), each in the origin's
    # own grammar: GDELT DOC's `startdatetime`/`enddatetime` returned only
    # in-window `seendate`s; Stack Exchange's `fromdate`/`todate` returned
    # only in-window `creation_date`s; the Wikimedia pageviews date range is
    # two path segments and the answer held exactly the days inside them;
    # OpenAlex, Crossref and arXiv each filtered publication time at the
    # origin, so `scholarly`'s three operations agree and it declares once.
    "gdelt": {"": True},
    "stack_exchange": {"": True},
    "wikimedia_pageviews": {"": True},
    "scholarly": {"": True},
    # Origin accepts none, measured 2026-09-01: a TikTok page read and an
    # oEmbed lookup each address one item and carry no time concept.
    "tiktok_public": {"": False},
    "oembed": {"": False},
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


def can_bound_at_origin(adapter_id: str, operation: str) -> Optional[bool]:
    """Whether this exact (adapter, operation) pair can bound time at the origin.

    Three readings, not two. `True` and `False` are both measured facts;
    `None` is a declaration this table carries with no measurement behind it
    yet, for an operation a live read was blocked before it could settle.
    Raises rather than guesses where the table names nothing at all: an
    adapter this table does not name and an operation a named adapter does
    not name are both a declaration nothing made, and reading either as
    `True`, `False` or `None` would be a capability this module never
    considered.
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


def reach_for(
    adapter_id: str, query: str = "", target_ids: Tuple[str, ...] = ()
) -> Optional[bool]:
    """Whether the operation this query or target names can bound time.

    The one entry point a caller needs: it resolves the operation the same
    way a real dispatch would and reads the declaration for it, without the
    caller building an :class:`AdapterRequest` of its own. `None` when that
    operation is declared but unmeasured, same as :func:`can_bound_at_origin`.
    """

    request = AdapterRequest(step_id="", query=query, target_ids=target_ids)
    return can_bound_at_origin(adapter_id, operation_for(adapter_id, request))


def window_loss_code(reach: Optional[bool]) -> Optional[str]:
    """The loss code one windowed call's own reach reading contributes, or none.

    Where :func:`reach_for`'s three readings become the two codes a caller
    sees on `StepResult.loss`: `None` — unmeasured — becomes
    :data:`WINDOW_CAPABILITY_UNMEASURED`; `False` — measured unable —
    becomes :data:`WINDOW_NOT_HONORED`; `True` contributes nothing, because a
    call that could bound the window needs no typed statement saying so.
    `runner.run_step` is the one caller.
    """

    if reach is None:
        return WINDOW_CAPABILITY_UNMEASURED
    if not reach:
        return WINDOW_NOT_HONORED
    return None


def step_window_loss(
    step: schema.AcquisitionStep, request: AdapterRequest, found: Optional[str]
) -> Optional[str]:
    """One call's contribution to its step's running window-loss reading.

    A declaration about the call's own shape, asked before the read rather
    than the answer: whether this operation could have spent the window at
    the origin does not depend on what came back. ``found`` is the step's
    reading so far and is returned unchanged once it holds anything, because
    a hydration step's calls address hits the caller named and are not
    guaranteed to share an operation the way a discovery step's continuations
    always do, and a caller wants to know a step's window went unspent at
    least once, not how many times. `runner.run_step` folds this across every
    call a step makes and appends the result to `StepResult.loss` once, at
    the end, the same place every other reading below the read loop lands.
    """

    if found is not None or not (step.window_start or step.window_end):
        return found
    reach = can_bound_at_origin(step.adapter_id, operation_for(step.adapter_id, request))
    return window_loss_code(reach)


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
