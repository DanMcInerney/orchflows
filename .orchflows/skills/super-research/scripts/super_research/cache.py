"""Run-local cache seam: one run's memory of reads it already made.

Measured Reddit RSS answers 1–2 requests per 30 s per IP, whatever identity
asks (findings.md §1). A run that re-reads what it just read therefore starves
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
# bounds how stale an observation a caller may be handed, so it is a property
# of the route's own volatility, not of the run.
DEFAULT_TTL_SECONDS = 60.0
# The two halves of one bound. Every route in the roster answers in kilobytes,
# so a body past `MAX_ENTRY_BYTES` is served through rather than held, and no
# more than `MAX_ENTRIES` answers are held at once: a run's cache can therefore
# cost no more than their product, 32 MiB, however long the run goes on.
MAX_ENTRY_BYTES = 512 * 1024
MAX_ENTRIES = 64
ROUTE_TTL_SECONDS: Dict[str, float] = {
    # A web index's answer to one query is stable across a run's discovery
    # phase; findings.md §1 observed no throttle here, so this TTL exists to
    # stop a run asking the same question twice, not to dodge a limit.
    transport.DDG_HTML_ROUTE: 300.0,
    # An archive lookup by fixed id changes only as the archive backfills.
    transport.ARCTIC_SHIFT_POSTS_ROUTE: 900.0,
}


class CacheError(RuntimeError):
    """A run's cache was asked to serve after the run that owns it ended."""


@dataclass(frozen=True)
class CacheKey:
    """What makes two reads the same read: the route, and the canonical request."""

    route_id: str
    canonical_request: str


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
    """

    parts = urllib.parse.urlsplit(request.url)
    query = urllib.parse.urlencode(
        sorted(
            (name, value)
            for name, value in urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
            if value != ""
        )
    )
    location = urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, query, ""))
    headers = " ".join(
        "{0}:{1}".format(name, value)
        for name, value in sorted((name.lower(), value) for name, value in request.headers)
    )
    return "{0} {1} {2}".format(request.method, location, headers)


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

    Three ways an answer must not: it was not a read, so replaying it would be
    this package answering for the origin; the origin did not produce it, so it
    says nothing about the origin and re-serving a local block or a transient
    failure would make recovery inside the window unreachable; or it is too
    large to hold, which the run's footprint, not its correctness, forbids.
    """

    return (
        request.method in transport.READ_METHODS
        and response.channel_verdict == transport.ORIGIN_CONTENT
        and len(response.body.encode("utf-8")) <= MAX_ENTRY_BYTES
    )


@dataclass(frozen=True)
class CacheServe:
    """One answer to one request, and which party it actually came from."""

    response: transport.TransportResponse
    cache_hit: bool

    @property
    def loss(self) -> Tuple[str, ...]:
        """The typed loss a record built from this answer carries."""

        return (CACHE_HIT,) if self.cache_hit else ()


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
        self._entries: "OrderedDict[CacheKey, Tuple[float, transport.TransportResponse]]"
        self._entries = OrderedDict()
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
