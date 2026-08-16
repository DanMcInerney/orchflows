"""Run-local cache seam: one run's memory of reads it already made.

Measured Reddit RSS answers 1–2 requests per 30 s per IP, whatever identity
asks (measured 2026-08-10). A run that re-reads what it just read therefore starves
rather than merely running slowly, which is why this cache is a correctness
requirement and not an optimization.

Reliability bar: this module remembers, and does nothing else. It stamps no
time — a served entry is the response the transport itself returned, so the
moment recorded against a record is always the moment the origin was really
read. It reaches no filesystem, socket, or process-external store: every entry
lives in one instance's memory for one run, and there is nowhere for an entry
to survive to. It holds no carrier: a caller passes in the fetch to use on a
miss, so pacing, retry, and route policy stay with whoever owns them.
"""

from __future__ import annotations

import time
import urllib.parse
from collections import OrderedDict
from dataclasses import dataclass
from typing import Callable, Dict, Tuple

from . import transport

# The typed loss code a served-from-cache record carries, spelled once here so
# the record and the run's own accounting cannot disagree about it.
CACHE_HIT = "cache_hit"

# How long one route's answer may stand in for a fresh read, in seconds. A TTL
# bounds how stale an observation a caller may be handed, so it belongs to the
# route's own volatility and not to the run. A route with no entry gets the
# default, which is short: a route nobody has measured is not one to trust for
# long. Whoever adds a route adds its TTL here.
DEFAULT_TTL_SECONDS = 60.0
ROUTE_TTL_SECONDS: Dict[str, float] = {
    # A web index's answer to one query is stable across a run's discovery
    # phase; the 2026-08-10 probes observed no throttle here, so this TTL exists to
    # stop a run asking the same question twice, not to dodge a limit.
    transport.DDG_HTML_ROUTE: 300.0,
    # An archive lookup by fixed id changes only as the archive backfills.
    transport.ARCTIC_SHIFT_POSTS_ROUTE: 900.0,
    # One author's whole timeline for 2.5 s and 378 KB (measured 2026-08-10), so
    # this is the route where remembering earns the most. Five minutes bounds
    # how stale an engagement count a caller can be handed, and a run asking
    # for the same author twice is asking the same question.
    transport.X_SYNDICATION_TIMELINE_ROUTE: 300.0,
    # One route, three operations, one TTL — so it takes the volatility of the
    # most volatile of them, a tweet's counts, and not that of a profile. The
    # read costs 0.5 s, so holding an answer longer buys less here than
    # anywhere else on X.
    transport.X_GUEST_GRAPHQL_ROUTE: 120.0,
    # The least volatile thing in the roster and the most expensive to read:
    # 577 KB in 1.3 s (measured 2026-08-10) for a block that changes when a member
    # edits their profile and carries no counter at all, so nothing in it goes
    # stale on a run's timescale. It is also the largest answer the evidence
    # has measured, and it fits: 577 KB is inside `MAX_ENTRY_BYTES`, so this
    # window binds on the body the evidence measured rather than only on a
    # smaller one.
    transport.LINKEDIN_PUBLIC_PROFILE_ROUTE: 900.0,
    # A third as long as the profile beside it, because a search list changes
    # as postings arrive where a profile does not, and because it is the cheap
    # read — 27 KB in 0.7 s, so holding an answer longer buys less and risks
    # handing back a page of results that has moved on.
    transport.LINKEDIN_JOBS_GUEST_SEARCH_ROUTE: 300.0,
    # The most expensive read in the roster — 455 KB in 2.9 s (measured 2026-08-10)
    # — so remembering earns more here per request than anywhere else, and a
    # run asking for the same account twice is asking the same question. It
    # still cannot take the LinkedIn profile's window: that block carries no
    # counter at all and changes only when a member edits it, while this
    # payload carries a follower count and twelve pairs of like and comment
    # counts, every one of which moves while nobody edits anything. Five
    # minutes is the syndication timeline's window, and for the same reason —
    # one author's recent posts with the platform's own counts on them. Like
    # that profile route, this one fits: 455 KB is inside `MAX_ENTRY_BYTES`,
    # with 569 KB of headroom, so this window binds on the body the evidence
    # measured rather than only on a smaller one.
    transport.INSTAGRAM_WEB_PROFILE_ROUTE: 300.0,
    # HN's index answers a query about a site whose front page turns over in
    # hours, so a list held too long is a list that has moved on. Three minutes
    # covers a run's discovery phase — the reason the web index beside it holds
    # five — and stops short of it, because a story that broke while the run
    # was working is exactly what a search of HN is for.
    transport.HN_ALGOLIA_SEARCH_ROUTE: 180.0,
    # Shorter than the index beside it, and that is the volatility talking
    # rather than the cost: an item's `score` and `descendants` move while
    # nobody edits anything, the way a tweet's counts do, and this is the
    # window the X GraphQL route holds them for. Two minutes also bounds a
    # `kids` traversal sensibly — a walk re-reading one item that fast is
    # asking the same question, and one re-reading it later wants the counts.
    transport.HN_FIREBASE_ITEM_ROUTE: 120.0,
    # The longest window this ticket declares, and the only one in the table
    # argued from a budget rather than from a latency. The 2026-08-10 probes recorded
    # the anonymous ceiling at 60/hr per bucket: a repeat read here costs a
    # full minute of the hour, where every other route in the roster costs
    # seconds of waiting. A repository's own row — its description, its star
    # and fork and open-issue counts — moves on a human timescale, so ten
    # minutes hands back nothing a caller would have read differently, and it
    # is what makes a run that reads one repository twice cost one read.
    transport.GITHUB_REST_ROUTE: 600.0,
    # Half of that, on the same ceiling, because a ranked search moves whenever
    # anything in it does — a repository created, starred, or pushed to
    # reorders the answer, where the repository's own row does not. Five
    # minutes is the window every other search in this table holds.
    transport.GITHUB_SEARCH_ROUTE: 300.0,
    # The route this whole module exists for, and the only one where a window
    # shorter than the interval that paces it could never bind at all: at one
    # read per 30 s the governor would already have made a caller wait longer
    # than the window before the second read arrived. Six intervals is enough
    # that a run polling several subreddits never pays twice for one, and short
    # enough that a freshness probe is still about now — a feed answered from
    # five-minute-old memory is reporting staleness as freshness. It is the
    # window the web index of a fast-moving front page holds, for that same
    # reason, and here the saving is a third of a minute rather than a second.
    transport.REDDIT_FEED_ROUTE: 180.0,
    # The cheapest read in the roster — 39 KB in 0.35 s (measured 2026-08-10) — so
    # this window earns the least of any here per request, and it exists to
    # stop a run asking one channel twice rather than to dodge a limit nobody
    # measured. Five minutes is what every "the same question twice" route in
    # this table holds. Volatility is low in an unusual way: an entry carries no
    # counter, and nothing in one changes after publication. What changes is
    # that a new entry appears at the head, so what a held answer risks is
    # completeness rather than accuracy.
    transport.YOUTUBE_CHANNEL_FEED_ROUTE: 300.0,
    # A reference document changes when somebody edits it and carries no
    # counter at all, so nothing in it goes stale on a run's timescale. That is
    # the same argument, and so the same window, as the roster's other
    # counter-free document.
    transport.PUBLIC_PAGE_ARTICLE_ROUTE: 900.0,
    # Zero, and it is the one entry in this table that is not a judgment about
    # volatility. A control read exists to answer "is this network answering
    # for the origin right now", and an answer out of a run's own memory cannot
    # answer that about now: it would report the channel healthy on the
    # strength of a read made before the appliance woke up. Every other route
    # here trades freshness for cost; this one has nothing to trade, because a
    # hit is a wrong answer rather than a stale one. Declared rather than left
    # to the default for exactly that reason — the default is a bound on
    # staleness, and this route wants none.
    transport.PUBLIC_PAGE_CONTROL_ROUTE: 0.0,
    # `transport.YOUTUBE_INNERTUBE_ROUTE` declares no window on purpose, and it
    # is the one route here where that is structural rather than a judgment:
    # it asks its question in a POST body, and `cacheable` holds only what came
    # back from a read method. No number written here could ever bind, so
    # writing one would state a freshness guarantee nothing honours. Two of its
    # three operations answer at 2.27 MB and 1.12 MB besides, both past
    # `MAX_ENTRY_BYTES` — the smaller of them only just, which is what fixes
    # the ceiling on that constant. Proved behaviourally, not asserted.
}

# The two halves of one bound. Every route in the roster answers in kilobytes,
# so a body past `MAX_ENTRY_BYTES` is served through rather than held, and no
# more than `MAX_ENTRIES` answers are held at once: a run's cache can therefore
# cost no more than their product, 32 MiB, however long the run goes on.
MAX_ENTRY_BYTES = 1024 * 1024
MAX_ENTRIES = 32


class CacheError(RuntimeError):
    """A run's cache was asked to serve after the run that owns it ended."""


@dataclass(frozen=True)
class CacheKey:
    """What makes two reads the same read: the route, and the canonical request."""

    route_id: str
    canonical_request: str


# What is held against a key: the moment the read happened, and its answer.
CacheEntry = Tuple[float, transport.TransportResponse]


def canonical_request(request: transport.TransportRequest) -> str:
    """One line naming exactly the read a request performs.

    Normalized away, and only this: query-parameter order, header order, and
    header-name case, which HTTP itself treats as insignificant; a URL
    fragment, which ``urllib.request.Request`` strips before sending, so two
    requests differing only there are the same bytes on the wire; and a
    blank-valued parameter, which :func:`transport.build_transport_request`
    already drops, so the package cannot express the difference anyway.

    Everything else is kept verbatim. A different method, path, parameter, or
    header value is a different read and earns its own entry.

    Every part is percent-encoded into the result, so no value can impersonate
    a separator: this package's own ``User-Agent`` contains spaces, and a form
    that merely joined values would let one header stand in for two.
    """

    parts = urllib.parse.urlsplit(request.url)
    query = urllib.parse.urlencode(
        sorted(
            (name, value)
            for name, value in urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
            if value != ""
        )
    )
    headers = urllib.parse.urlencode(
        sorted((name.lower(), value) for name, value in request.headers)
    )
    return urllib.parse.urlencode(
        (
            ("method", request.method),
            ("location", urllib.parse.urlunsplit(
                (parts.scheme, parts.netloc, parts.path, query, "")
            )),
            ("headers", headers),
        )
    )


def cache_key(request: transport.TransportRequest) -> CacheKey:
    """The one key this cache is allowed to have."""

    return CacheKey(route_id=request.route_id, canonical_request=canonical_request(request))


def ttl_seconds(route_id: str) -> float:
    """This route's declared freshness window, or the bounded default."""

    return ROUTE_TTL_SECONDS.get(route_id, DEFAULT_TTL_SECONDS)


def cacheable(
    request: transport.TransportRequest, response: transport.TransportResponse
) -> bool:
    """Whether this answer may stand in for a later read of the same thing.

    Three kinds of answer may not. One that was not a read: replaying it would
    be this package answering for the origin. One the origin did not produce:
    the captive-portal caveat's local block, or a transient failure, says nothing about
    the origin, and holding it would make recovery inside the window
    unreachable. And one too large to hold, which the run's footprint forbids.
    """

    return (
        request.method in transport.READ_METHODS
        and response.channel_verdict == transport.ORIGIN_CONTENT
        and len(response.body.encode("utf-8")) <= MAX_ENTRY_BYTES
    )


@dataclass(frozen=True)
class CacheServe:
    """One answer to one request, and which party it actually came from.

    It carries no loss of its own. ``adapters._served_from_cache`` is what
    attaches `cache_hit`, to the page and to every record on it, and a second
    place that could produce the same code is a second place to keep in step.
    """

    response: transport.TransportResponse
    cache_hit: bool


class RunCache:
    """One run's memory of reads it already made. It dies with the run.

    The clock is monotonic seconds, never a wall clock: a TTL must not be
    shortened or extended by a clock adjustment. Nothing here reads or writes a
    wall-clock time — the served response carries the transport's own
    ``observed_at``, which is the moment the origin was really read.
    """

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        # Ordered least-recently-served first, which is eviction order.
        self._entries: OrderedDict[CacheKey, CacheEntry] = OrderedDict()
        self._closed = False

    def __len__(self) -> int:
        """How many answers are held right now — the bound, observable."""

        return len(self._entries)

    def serve(
        self,
        request: transport.TransportRequest,
        fetch: Callable[[transport.TransportRequest], transport.TransportResponse],
    ) -> CacheServe:
        """Answer one request, reaching ``fetch`` only when memory cannot.

        Read-through on purpose: the caller supplies the fetch, so a caller
        that paces or refuses reads pays that cost on a miss and never on a
        hit, and no caller can forget to remember what it just read.
        """

        if self._closed:
            raise CacheError("this run's cache ended; a later run makes its own")
        key = cache_key(request)
        entry = self._entries.get(key)
        if entry is not None:
            stored_at, response = entry
            # The window runs from the read that produced the entry, never from
            # the last serve: a hot entry must still expire.
            if self._clock() - stored_at < ttl_seconds(request.route_id):
                self._entries.move_to_end(key)
                return CacheServe(response=response, cache_hit=True)
            del self._entries[key]
        response = fetch(request)
        if cacheable(request, response):
            self._entries[key] = (self._clock(), response)
            # Assignment to an existing key keeps its old position, so say it.
            self._entries.move_to_end(key)
            while len(self._entries) > MAX_ENTRIES:
                self._entries.popitem(last=False)
        return CacheServe(response=response, cache_hit=False)

    def close(self) -> None:
        """End this run's cache. Idempotent, and there is no reopening it.

        Dropping the reference would free the memory just as well. Closing says
        the run ended, and makes the saying enforceable: a second run that
        reaches for this one is refused rather than quietly served a first
        run's reads.
        """

        self._entries = OrderedDict()
        self._closed = True
