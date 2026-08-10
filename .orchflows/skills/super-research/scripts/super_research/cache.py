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

import urllib.parse
from dataclasses import dataclass

from . import transport


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
