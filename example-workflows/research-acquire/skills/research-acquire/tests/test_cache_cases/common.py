"""Cache suite: a run-local cache that can remember, never restamp, never persist.

Two claims are defended here, and they fail in opposite directions.

The first is freshness honesty. A record served from cache carries the moment
the origin was really read, never the moment the cache answered. A cache that
restamps the serve time fabricates freshness silently — every downstream
ordering, recency, and staleness judgment then rests on a time nothing ever
observed. So the served ``observed_at`` is checked against the original at the
seam and again on the record a caller keeps.

The second is that the cache cannot outlive its run. Not "does not" — cannot:
it holds no filesystem or socket primitive, its whole state is instance state,
and a closed cache refuses rather than serving. A second run therefore starts
empty because there is nowhere for a first run's entry to have been kept.

Every test runs offline and on a fake clock. No wall-clock sleep exists in this
module or in the module it tests, and the TTL boundary is proven by advancing
the clock, not by waiting.
"""

from __future__ import annotations

import ast
import builtins
import contextlib
import importlib.util
import io
import os
import socket
import time
import unittest
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from tests import helpers
from super_research import cache, runner, schema, transport


TESTS_DIR = Path(__file__).resolve().parent.parent
PACKAGE_DIR = TESTS_DIR.parent / "scripts" / "super_research"
CACHE_SOURCE = PACKAGE_DIR / "cache.py"
FIXTURE_DIR = TESTS_DIR / "fixtures" / "cache"
# T01's tracer fixtures, read rather than copied: the strongest repeat-read
# claim is over the run's own end-to-end path, on the run's own data.
TRACER_FIXTURE_DIR = TESTS_DIR / "fixtures" / "tracer"

FIXTURE_ROUTE = transport.route_constant(transport.FAKE_OFFLINE_ROUTE)
ARCHIVE_ROUTE = transport.route_constant(transport.ARCTIC_SHIFT_POSTS_ROUTE)
FIXTURE_URL = FIXTURE_ROUTE.origin + FIXTURE_ROUTE.path
REPEAT_ROUTES = (transport.FAKE_OFFLINE_ROUTE, transport.ARCTIC_SHIFT_POSTS_ROUTE)
REDDIT_THREAD_LOCATOR = (
    "https://www.reddit.com/r/LocalLLaMA/comments/1abc234/"
    "what_is_the_best_local_model_right_now/"
)

REPEAT_MANIFEST = {
    "manifest_id": "cache-repeat-read",
    "as_of": "2026-08-10T00:00:00Z",
    "steps": [
        {
            "step_id": "s1-discover",
            "kind": "discovery",
            "adapter_id": "fake",
            "query": "fixture:local-model-index",
            "max_items": 6,
        },
        {
            "step_id": "s2-hydrate",
            "kind": "hydration",
            "adapter_id": "reddit_archive",
            "prior_step_id": "s1-discover",
            "selected_hits": [
                {"discovery_locator": REDDIT_THREAD_LOCATOR, "target_id": "1abc234"}
            ],
            "max_items": 6,
        },
    ],
}


def load_cache_fixture(name):
    """Load one wrong-result module by path.

    These are not package modules: nothing in the package imports them and no
    discovery pattern matches them. They exist so the oracles here can be shown
    to reject a wrong cache without mutating the tree under test.
    """

    spec = importlib.util.spec_from_file_location(
        "cache_fixture_" + name, FIXTURE_DIR / (name + ".py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def tracer_responses():
    """One canned origin answer per route the repeat manifest reads."""

    return {
        transport.FAKE_OFFLINE_ROUTE: (
            200,
            TRACER_FIXTURE_DIR.joinpath("index_results.json").read_text(encoding="utf-8"),
            "application/json",
        ),
        transport.ARCTIC_SHIFT_POSTS_ROUTE: (
            200,
            TRACER_FIXTURE_DIR.joinpath("arctic_shift_posts_ids.json").read_text(
                encoding="utf-8"
            ),
            "application/json",
        ),
    }


class FakeClock:
    """One fake clock driving both TTL arithmetic and the transport's wall stamp.

    Advancing it moves both together, so the moment a cache would restamp with
    is always visibly different from the moment the origin was read. Nothing in
    this suite waits: expiry is reached by moving this clock.
    """

    def __init__(self, start="2026-08-10T09:00:00Z"):
        self._start = datetime.strptime(start, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        self.seconds = 0.0

    def advance(self, seconds):
        self.seconds += seconds

    def monotonic(self):
        return self.seconds

    def stamp(self):
        return (self._start + timedelta(seconds=self.seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")


class RecordingOpener:
    """Offline opener: one canned response per route, every call recorded.

    Nothing here can reach a socket, so an unseeded route fails loudly rather
    than egressing.
    """

    def __init__(self, responses):
        self.responses = dict(responses)
        self.opened = []

    def __call__(self, request):
        self.opened.append(request)
        if request.route_id not in self.responses:
            raise transport.TransportError("no offline response seeded for " + request.route_id)
        outcome = self.responses[request.route_id]
        if isinstance(outcome, Exception):
            raise outcome
        return helpers.answered(request, outcome)


def offline_transport(clock, responses=None):
    """A real carrier whose only fake parts are the opener and the clock."""

    opener = RecordingOpener(tracer_responses() if responses is None else responses)
    return transport.Transport(opener=opener, now=clock.stamp), opener


class CachingCarrier:
    """The minimal shape a governor takes around the carrier, for proof only.

    It holds the carrier and the cache, serves through the cache, and keeps
    what each serve was. T04 owns the real one, which adds pacing on the miss
    path; this exists here so the cache seam is shown to be wrappable at all,
    and so a wrong cache can be plugged into the same place.
    """

    def __init__(self, carrier, run_cache):
        self._carrier = carrier
        self._cache = run_cache
        self.serves = []

    @property
    def calls(self):
        return self._carrier.calls

    def fetch(self, request):
        serve = self._cache.serve(request, self._carrier.fetch)
        self.serves.append(serve)
        return serve.response


class RefusingSocket(socket.socket):
    """A socket that cannot be opened.

    It stays a *subclass* on purpose: ``ssl`` does ``class SSLSocket(socket)``
    at import time, so a guard that swaps ``socket.socket`` for a plain
    function breaks any stdlib module that has not been imported yet.
    """

    def __init__(self, *args, **kwargs):
        raise AssertionError("a socket was opened inside a zero-I/O guard")


@contextlib.contextmanager
def forbid_io():
    """Make every filesystem and socket primitive raise for the guarded block."""

    def refuse(*args, **kwargs):
        raise AssertionError("I/O attempted inside a zero-I/O guard")

    with contextlib.ExitStack() as stack:
        stack.enter_context(mock.patch.object(builtins, "open", refuse))
        stack.enter_context(mock.patch.object(io, "open", refuse))
        stack.enter_context(mock.patch.object(os, "open", refuse))
        stack.enter_context(mock.patch.object(socket, "socket", RefusingSocket))
        stack.enter_context(mock.patch.object(socket, "create_connection", refuse))
        stack.enter_context(mock.patch.object(urllib.request, "urlopen", refuse))
        yield


def imported_names(path):
    """Every module and imported symbol path one source file names in an import."""

    names = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module:
                names.add(module)
            for alias in node.names:
                names.add(module + "." + alias.name if module else alias.name)
    return names


def called_names(path):
    """Every bare function name one source file calls, builtins included."""

    return {
        node.func.id
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }


@contextlib.contextmanager
def forbid_sleep():
    """Make any wall-clock sleep raise: TTL is proven by moving a fake clock."""

    def refuse(*args, **kwargs):
        raise AssertionError("a wall-clock wait was attempted inside a fake-clock proof")

    with mock.patch.object(time, "sleep", refuse):
        yield


def assert_repeat_read_is_served_unrestamped(run_cache, clock):
    """Row 1's oracle, run end to end through a carrier a governor would wrap.

    Raises ``AssertionError`` naming the one clause that broke: not served
    inside its TTL, not marked as a hit, restamped with the serve time, or
    still served after expiry.
    """

    carrier, opener = offline_transport(clock)
    caching = CachingCarrier(carrier, run_cache)
    manifest = schema.parse_manifest(REPEAT_MANIFEST)
    soonest = min(cache.ttl_seconds(route) for route in REPEAT_ROUTES)
    latest = max(cache.ttl_seconds(route) for route in REPEAT_ROUTES)

    first = runner.run_acquisition(manifest, caching)
    reads = len(opener.opened)
    if reads == 0 or not first.records:
        raise AssertionError("the first read never reached the origin: nothing to serve later")

    clock.advance(soonest / 2.0)
    already_served = len(caching.serves)
    second = runner.run_acquisition(manifest, caching)
    repeat_serves = caching.serves[already_served:]

    if len(opener.opened) != reads:
        raise AssertionError(
            "the cache did not serve a repeat read inside its TTL: {0} origin reads"
            " repeating {1}".format(len(opener.opened) - reads, reads)
        )
    unmarked = [serve for serve in repeat_serves if not serve.cache_hit]
    if unmarked:
        raise AssertionError(
            "a cache hit was not marked cache_hit: {0} of {1} repeat serves".format(
                len(unmarked), len(repeat_serves)
            )
        )
    if len(second.records) != len(first.records):
        raise AssertionError("a repeat run yielded a different number of records")
    restamped = [
        (before.record_id, before.observed_at, after.observed_at)
        for before, after in zip(first.records, second.records)
        if before.observed_at != after.observed_at
    ]
    if restamped:
        raise AssertionError(
            "a served-from-cache record was restamped with the serve time:"
            " record {0} observed at {1} came back observed at {2}".format(*restamped[0])
        )
    if second.records != first.records:
        raise AssertionError("a served-from-cache record differed from the record it repeats")

    clock.advance(latest)
    third = runner.run_acquisition(manifest, caching)
    if len(opener.opened) != reads * 2:
        raise AssertionError(
            "an entry outlived its TTL: {0} origin reads after expiry, expected {1}".format(
                len(opener.opened) - reads, reads
            )
        )
    if third.records[0].observed_at == first.records[0].observed_at:
        raise AssertionError("the clock never moved, so the restamp clause proves nothing")


def fixture_request(url=FIXTURE_URL + "?q=local+model&s=30", method="GET", headers=None):
    """One request on the discovery route, spelled exactly as the caller asks."""

    return transport.TransportRequest(
        route_id=transport.FAKE_OFFLINE_ROUTE,
        method=method,
        url=url,
        headers=(("User-Agent", "probe"), ("Accept", "text/html"))
        if headers is None
        else headers,
    )
