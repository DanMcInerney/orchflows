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
import re
import socket
import time
import unittest
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from super_research import cache, runner, schema, transport


PACKAGE_DIR = Path(__file__).resolve().parent.parent / "scripts" / "super_research"
CACHE_SOURCE = PACKAGE_DIR / "cache.py"
PROTOCOL_SOURCE = Path(__file__).resolve().parent.parent / "references" / "protocol.md"
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "cache"
# T01's tracer fixtures, read rather than copied: the strongest repeat-read
# claim is over the run's own end-to-end path, on the run's own data.
TRACER_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "tracer"

DDG_ROUTE = transport.route_constant(transport.DDG_HTML_ROUTE)
ARCHIVE_ROUTE = transport.route_constant(transport.ARCTIC_SHIFT_POSTS_ROUTE)
DDG_URL = DDG_ROUTE.origin + DDG_ROUTE.path
REPEAT_ROUTES = (transport.DDG_HTML_ROUTE, transport.ARCTIC_SHIFT_POSTS_ROUTE)
REDDIT_THREAD_LOCATOR = (
    "https://www.reddit.com/r/LocalLLaMA/comments/1abc234/"
    "what_is_the_best_local_model_right_now/"
)

REPEAT_MANIFEST = {
    "schema_version": 2,
    "manifest_id": "cache-repeat-read",
    "mode": "staged",
    "as_of": "2026-08-10T00:00:00Z",
    "steps": [
        {
            "step_id": "s1-discover",
            "kind": "discovery",
            "adapter_id": "web_search",
            "query": "site:reddit.com best local model",
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
        transport.DDG_HTML_ROUTE: (
            200,
            TRACER_FIXTURE_DIR.joinpath("ddg_html_results.html").read_text(encoding="utf-8"),
            "text/html",
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
        return outcome


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


# A byte count as this package's own prose writes one, and what it means. The
# package spells a measured body in KB and MB and the cap in KiB, and means
# binary multiples throughout — `MEASURED_INSTAGRAM_BYTES` in `test_adapters`
# is `455 * 1024` for the "455 KB" findings.md records.
SIZE_UNIT_BYTES = {"KB": 1024, "KiB": 1024, "MB": 1024 * 1024, "MiB": 1024 * 1024}
STATED_SIZE = re.compile(r"(\d+(?:\.\d+)?)\s*(KB|KiB|MB|MiB)\b")
STATED_HEADROOM = re.compile(r"(\d+(?:\.\d+)?)\s*(KB|KiB|MB|MiB) of headroom")
STATED_PRODUCT = re.compile(r"product,\s*(\d+(?:\.\d+)?)\s*(KB|KiB|MB|MiB)")
STATED_ENTRIES = re.compile(r"MAX_ENTRIES=(\d+)")
STATED_ENTRY_BYTES = re.compile(r"MAX_ENTRY_BYTES=(\d+(?:\.\d+)?)\s*(KB|KiB|MB|MiB)")
# How a comment can place a body against the entry cap. A comment claiming
# neither is reasoning about something else and is left alone.
OVER_THE_CAP = ("exceed", "past", "too large")
UNDER_THE_CAP = ("is inside", "fits")


def as_bytes(amount, unit):
    """One stated size in bytes."""

    return int(round(float(amount) * SIZE_UNIT_BYTES[unit]))


def stated_sizes(text):
    """Every byte count this prose states, in bytes, in the order stated."""

    return [as_bytes(amount, unit) for amount, unit in STATED_SIZE.findall(text)]


def comment_blocks(lines):
    """Each contiguous run of ``#`` lines, joined into one string."""

    blocks = []
    current = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            current.append(stripped.lstrip("#").strip())
        elif current:
            blocks.append(" ".join(current))
            current = []
    if current:
        blocks.append(" ".join(current))
    return blocks


def route_table_comments():
    """The per-route comments inside ``ROUTE_TTL_SECONDS``, one string each.

    Read off the source rather than restated here, because the thing under
    test is what the comment actually says.
    """

    lines = CACHE_SOURCE.read_text(encoding="utf-8").splitlines()
    start = next(
        index for index, line in enumerate(lines) if line.startswith("ROUTE_TTL_SECONDS")
    )
    end = next(index for index, line in enumerate(lines) if index > start and line == "}")
    return comment_blocks(lines[start + 1 : end])


def footprint_comment():
    """The comment block declaring the footprint law, above the constants."""

    lines = CACHE_SOURCE.read_text(encoding="utf-8").splitlines()
    end = next(
        index for index, line in enumerate(lines) if line.startswith("MAX_ENTRY_BYTES")
    )
    start = end
    while start > 0 and lines[start - 1].strip().startswith("#"):
        start -= 1
    return " ".join(comment_blocks(lines[start:end]))


def protocol_footprint_paragraphs():
    """Every paragraph in ``protocol.md`` that states the footprint law."""

    text = PROTOCOL_SOURCE.read_text(encoding="utf-8")
    return [
        " ".join(block.split())
        for block in text.split("\n\n")
        if "MAX_ENTRIES=" in block
    ]


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


def ddg_request(url=DDG_URL + "?q=local+model&s=30", method="GET", headers=None):
    """One request on the discovery route, spelled exactly as the caller asks."""

    return transport.TransportRequest(
        route_id=transport.DDG_HTML_ROUTE,
        method=method,
        url=url,
        headers=(("User-Agent", "probe"), ("Accept", "text/html"))
        if headers is None
        else headers,
    )


class CacheKeyTest(unittest.TestCase):
    """Criterion 3, keying half: the key is exactly (route_id, canonical_request).

    The canonicalizer normalizes away only what HTTP itself treats as
    insignificant, plus the one thing this package's own request builder
    already drops. Everything else is a different read and gets its own entry.
    """

    def test_the_key_is_the_route_paired_with_the_canonical_request(self):
        request = ddg_request()

        key = cache.cache_key(request)

        self.assertEqual(
            key,
            cache.CacheKey(
                route_id=transport.DDG_HTML_ROUTE,
                canonical_request=cache.canonical_request(request),
            ),
        )

    def test_a_spelling_the_canonicalizer_normalizes_away_shares_one_entry(self):
        same_read = {
            "query parameter order": ddg_request(url=DDG_URL + "?s=30&q=local+model"),
            "a blank parameter the builder itself drops": ddg_request(
                url=DDG_URL + "?q=local+model&s=30&cursor="
            ),
            "a fragment urllib never sends": ddg_request(
                url=DDG_URL + "?q=local+model&s=30#results"
            ),
            "header order": ddg_request(
                headers=(("Accept", "text/html"), ("User-Agent", "probe"))
            ),
            "header name case": ddg_request(
                headers=(("user-agent", "probe"), ("accept", "text/html"))
            ),
        }

        for spelling, variant in same_read.items():
            with self.subTest(normalized_away=spelling):
                self.assertEqual(cache.cache_key(variant), cache.cache_key(ddg_request()))

    def test_no_read_can_impersonate_another_by_where_a_separator_falls(self):
        # A canonical form that joins values with a separator collides when a
        # value contains that separator, and this package's own User-Agent
        # contains spaces. Two different reads sharing one entry is the worst
        # thing a cache key can do, so the encoding must be unambiguous.
        one = ddg_request(
            headers=(("User-Agent", transport.USER_AGENT), ("Accept", "text/html"))
        )
        other = ddg_request(
            headers=(("Accept", "text/html user-agent:" + transport.USER_AGENT),)
        )
        self.assertIn(" ", transport.USER_AGENT)

        self.assertNotEqual(cache.cache_key(one), cache.cache_key(other))

    def test_any_other_difference_is_a_different_entry(self):
        archive_url = ARCHIVE_ROUTE.origin + ARCHIVE_ROUTE.path
        distinct_reads = {
            "route": transport.TransportRequest(
                route_id=transport.ARCTIC_SHIFT_POSTS_ROUTE,
                method="GET",
                url=DDG_URL + "?q=local+model&s=30",
                headers=(("User-Agent", "probe"), ("Accept", "text/html")),
            ),
            "method": ddg_request(method="HEAD"),
            "path": ddg_request(url=archive_url + "?q=local+model&s=30"),
            "parameter value": ddg_request(url=DDG_URL + "?q=other+model&s=30"),
            "parameter name": ddg_request(url=DDG_URL + "?query=local+model&s=30"),
            "an extra parameter": ddg_request(url=DDG_URL + "?q=local+model&s=30&page=2"),
            "a dropped parameter": ddg_request(url=DDG_URL + "?q=local+model"),
            "header value": ddg_request(
                headers=(("User-Agent", "probe"), ("Accept", "application/json"))
            ),
            "an extra header": ddg_request(
                headers=(
                    ("User-Agent", "probe"),
                    ("Accept", "text/html"),
                    ("X-Probe", "1"),
                )
            ),
        }

        for difference, variant in distinct_reads.items():
            with self.subTest(differs_by=difference):
                self.assertNotEqual(cache.cache_key(variant), cache.cache_key(ddg_request()))


class TtlServeTest(unittest.TestCase):
    """Criteria 1 and 4: served inside its TTL, refetched after, never restamped."""

    def test_the_run_cache_serves_a_repeat_read_unrestamped(self):
        clock = FakeClock()

        with forbid_sleep():
            assert_repeat_read_is_served_unrestamped(cache.RunCache(clock=clock.monotonic), clock)

    def test_a_hit_and_a_miss_are_told_apart_at_the_serve_seam(self):
        clock = FakeClock()
        carrier, opener = offline_transport(clock)
        run_cache = cache.RunCache(clock=clock.monotonic)
        request = transport.build_transport_request(
            transport.DDG_HTML_ROUTE, {"q": "local model"}
        )

        miss = run_cache.serve(request, carrier.fetch)
        hit = run_cache.serve(request, carrier.fetch)

        self.assertEqual(len(opener.opened), 1)
        self.assertFalse(miss.cache_hit)
        self.assertTrue(hit.cache_hit)
        self.assertEqual(hit.response, miss.response)
        # The serve says which party answered and stops there. Turning that
        # into a loss code is `adapters._served_from_cache`'s, and a second
        # place that could produce `cache_hit` is a second one to keep in step.
        self.assertFalse(hasattr(hit, "loss"))

    def test_each_route_expires_on_its_own_ttl(self):
        clock = FakeClock()
        carrier, opener = offline_transport(clock)
        run_cache = cache.RunCache(clock=clock.monotonic)
        sooner = transport.build_transport_request(
            transport.DDG_HTML_ROUTE, {"q": "local model"}
        )
        later = transport.build_transport_request(
            transport.ARCTIC_SHIFT_POSTS_ROUTE, {"ids": "1abc234"}
        )
        sooner_ttl = cache.ttl_seconds(sooner.route_id)
        later_ttl = cache.ttl_seconds(later.route_id)
        # Without two different TTLs the per-route claim would be vacuous.
        self.assertLess(sooner_ttl, later_ttl)

        with forbid_sleep():
            run_cache.serve(sooner, carrier.fetch)
            run_cache.serve(later, carrier.fetch)
            clock.advance((sooner_ttl + later_ttl) / 2.0)

            self.assertFalse(run_cache.serve(sooner, carrier.fetch).cache_hit)
            self.assertTrue(run_cache.serve(later, carrier.fetch).cache_hit)

        self.assertEqual(len(opener.opened), 3)

    def test_the_ttl_boundary_is_the_last_instant_before_expiry(self):
        request = transport.build_transport_request(
            transport.DDG_HTML_ROUTE, {"q": "local model"}
        )
        ttl = cache.ttl_seconds(request.route_id)

        for elapsed, served in ((ttl - 0.001, True), (ttl, False), (ttl + 0.001, False)):
            with self.subTest(elapsed=elapsed):
                clock = FakeClock()
                carrier, _ = offline_transport(clock)
                run_cache = cache.RunCache(clock=clock.monotonic)

                with forbid_sleep():
                    run_cache.serve(request, carrier.fetch)
                    clock.advance(elapsed)

                    self.assertEqual(run_cache.serve(request, carrier.fetch).cache_hit, served)

    def test_a_hit_never_extends_the_life_of_what_it_served(self):
        # TTL bounds how stale an observation may be, so it runs from the read
        # that produced it. A sliding window would let a hot entry never expire.
        clock = FakeClock()
        carrier, opener = offline_transport(clock)
        run_cache = cache.RunCache(clock=clock.monotonic)
        request = transport.build_transport_request(
            transport.DDG_HTML_ROUTE, {"q": "local model"}
        )
        ttl = cache.ttl_seconds(request.route_id)

        with forbid_sleep():
            run_cache.serve(request, carrier.fetch)
            for _ in range(4):
                clock.advance(ttl / 5.0)
                self.assertTrue(run_cache.serve(request, carrier.fetch).cache_hit)
            clock.advance(ttl / 5.0)

            self.assertFalse(run_cache.serve(request, carrier.fetch).cache_hit)

        self.assertEqual(len(opener.opened), 2)

    def test_the_cache_cannot_wait_out_a_ttl(self):
        self.assertNotIn("sleep", CACHE_SOURCE.read_text(encoding="utf-8"))


class CacheabilityTest(unittest.TestCase):
    """What may be remembered at all: one read the origin itself answered.

    Every rule here is a way a cache can turn something that was true once
    into something a caller reads as still true.
    """

    def serve_twice(self, route_id, outcome, params=None):
        """Serve one request twice and report how many reads reached the origin."""

        clock = FakeClock()
        carrier, opener = offline_transport(clock, {route_id: outcome})
        run_cache = cache.RunCache(clock=clock.monotonic)
        request = transport.build_transport_request(route_id, params)

        first = run_cache.serve(request, carrier.fetch)
        second = run_cache.serve(request, carrier.fetch)

        return first, second, len(opener.opened)

    def test_an_origin_answer_is_the_thing_that_is_remembered(self):
        first, second, reads = self.serve_twice(
            transport.DDG_HTML_ROUTE, (200, "<html></html>", "text/html"), {"q": "local model"}
        )

        self.assertEqual((first.cache_hit, second.cache_hit, reads), (False, True, 1))

    def test_a_write_capable_method_is_never_remembered(self):
        # The one route that may leave a read mints an anonymous guest token.
        # A minted token is per-run state, and a POST is not a read: replaying
        # one from memory would be this package answering for the origin.
        first, second, reads = self.serve_twice(
            transport.X_GUEST_ACTIVATE_ROUTE, (200, '{"guest_token": "1"}', "application/json")
        )

        self.assertEqual(
            transport.route_constant(transport.X_GUEST_ACTIVATE_ROUTE).method,
            "POST",
        )
        self.assertNotIn("POST", transport.READ_METHODS)
        self.assertEqual((first.cache_hit, second.cache_hit, reads), (False, False, 2))

    def test_a_local_network_block_is_never_remembered(self):
        # findings.md §0: an appliance answering for the origin says nothing
        # about the origin. Holding one for a TTL would freeze a transient
        # local block and re-serve it as though the origin had spoken.
        intercepted = (503, "<html>" + transport.CAPTIVE_PORTAL_MARKERS[0] + "</html>", "text/html")

        first, second, reads = self.serve_twice(
            transport.DDG_HTML_ROUTE, intercepted, {"q": "local model"}
        )

        self.assertEqual((first.cache_hit, second.cache_hit, reads), (False, False, 2))
        self.assertEqual(first.response.channel_verdict, transport.NETWORK_INTERCEPTED)

    def test_an_origin_failure_is_never_remembered(self):
        # Backoff belongs to whoever paces the route. A cache that remembers a
        # failure makes recovery inside the window unreachable.
        first, second, reads = self.serve_twice(
            transport.DDG_HTML_ROUTE, (503, "<html>busy</html>", "text/html"), {"q": "local model"}
        )

        self.assertEqual((first.cache_hit, second.cache_hit, reads), (False, False, 2))
        self.assertEqual(first.response.channel_verdict, transport.ORIGIN_FAILURE)

    def test_a_response_too_large_to_hold_is_served_through(self):
        for size, remembered in (
            (cache.MAX_ENTRY_BYTES, True),
            (cache.MAX_ENTRY_BYTES + 1, False),
        ):
            with self.subTest(body_bytes=size):
                first, second, reads = self.serve_twice(
                    transport.DDG_HTML_ROUTE, (200, "x" * size, "text/html"), {"q": "local model"}
                )

                self.assertFalse(first.cache_hit)
                self.assertEqual(second.cache_hit, remembered)
                self.assertEqual(reads, 1 if remembered else 2)

    def test_a_fetch_that_never_answered_leaves_no_entry(self):
        clock = FakeClock()
        carrier, opener = offline_transport(
            clock, {transport.DDG_HTML_ROUTE: transport.TransportError("origin unreachable")}
        )
        run_cache = cache.RunCache(clock=clock.monotonic)
        request = transport.build_transport_request(
            transport.DDG_HTML_ROUTE, {"q": "local model"}
        )

        with self.assertRaises(transport.TransportError):
            run_cache.serve(request, carrier.fetch)
        opener.responses[transport.DDG_HTML_ROUTE] = (200, "<html></html>", "text/html")

        self.assertFalse(run_cache.serve(request, carrier.fetch).cache_hit)
        self.assertTrue(run_cache.serve(request, carrier.fetch).cache_hit)
        self.assertEqual(len(opener.opened), 2)


class RunLocalTest(unittest.TestCase):
    """Criterion 2: cross-run persistence is unreachable, not merely unused.

    Three legs, because "nothing was written" and "nothing could be" are
    different claims. The import scan rules out every module a cache would
    need to reach a store; the zero-I/O guard rules out the builtins too, at
    runtime, over the whole seam; and the cache's whole state being instance
    state is shown by two caches, and two runs, sharing nothing.
    """

    # Every module a cache would have to reach for to outlive its process.
    PERSISTENCE_MODULES = (
        "os",
        "io",
        "pathlib",
        "tempfile",
        "shutil",
        "shelve",
        "pickle",
        "marshal",
        "dbm",
        "sqlite3",
        "socket",
        "ssl",
        "subprocess",
        "multiprocessing",
        "http.client",
        "urllib.request",
    )

    def one_request(self):
        return transport.build_transport_request(
            transport.DDG_HTML_ROUTE, {"q": "local model"}
        )

    def test_the_cache_imports_nothing_that_can_outlive_the_process(self):
        named = imported_names(CACHE_SOURCE)

        for module in self.PERSISTENCE_MODULES:
            with self.subTest(module=module):
                self.assertNotIn(module, named)

    def test_the_cache_calls_no_builtin_that_can_write(self):
        self.assertNotIn("open", called_names(CACHE_SOURCE))

    def test_the_persistence_scan_can_fail(self):
        # A cache that does persist, written beside the tree, so the scan is
        # shown to discriminate rather than to match nothing at all.
        disk = FIXTURE_DIR / "disk_backed_cache.py"

        found = sorted(
            module for module in self.PERSISTENCE_MODULES if module in imported_names(disk)
        )

        self.assertEqual(found, ["os", "pathlib"])
        self.assertIn("open", called_names(disk))

    def test_the_whole_seam_runs_with_every_io_primitive_refused(self):
        clock = FakeClock()
        carrier, opener = offline_transport(clock)
        run_cache = cache.RunCache(clock=clock.monotonic)
        caching = CachingCarrier(carrier, run_cache)
        manifest = schema.parse_manifest(REPEAT_MANIFEST)

        with forbid_io():
            first = runner.run_acquisition(manifest, caching)
            clock.advance(30.0)
            second = runner.run_acquisition(manifest, caching)
            run_cache.close()

        self.assertEqual(second.records, first.records)
        self.assertEqual(len(opener.opened), 2)

    def test_the_zero_io_guard_stops_a_cache_that_writes_to_disk(self):
        clock = FakeClock()
        carrier, _ = offline_transport(clock)
        store = FIXTURE_DIR / "never-created" / "entries.json"
        wrong = load_cache_fixture("disk_backed_cache").DiskBackedCache(clock.monotonic, store)

        with forbid_io():
            with self.assertRaises(AssertionError):
                wrong.serve(self.one_request(), carrier.fetch)

        self.assertFalse(store.parent.exists())

    def test_two_caches_in_one_process_never_share_an_entry(self):
        clock = FakeClock()
        carrier, opener = offline_transport(clock)
        request = self.one_request()
        one = cache.RunCache(clock=clock.monotonic)
        other = cache.RunCache(clock=clock.monotonic)

        one.serve(request, carrier.fetch)

        self.assertEqual(len(other), 0)
        self.assertFalse(other.serve(request, carrier.fetch).cache_hit)
        self.assertEqual(len(opener.opened), 2)

    def test_a_second_run_starts_with_nothing_the_first_run_read(self):
        clock = FakeClock()
        carrier, opener = offline_transport(clock)
        request = self.one_request()

        first_run = cache.RunCache(clock=clock.monotonic)
        first_run.serve(request, carrier.fetch)
        self.assertTrue(first_run.serve(request, carrier.fetch).cache_hit)
        first_run.close()

        second_run = cache.RunCache(clock=clock.monotonic)

        self.assertEqual(len(second_run), 0)
        self.assertFalse(second_run.serve(request, carrier.fetch).cache_hit)
        self.assertEqual(len(opener.opened), 2)

    def test_a_closed_cache_holds_nothing_and_refuses_to_serve(self):
        clock = FakeClock()
        carrier, _ = offline_transport(clock)
        request = self.one_request()
        run_cache = cache.RunCache(clock=clock.monotonic)
        run_cache.serve(request, carrier.fetch)
        self.assertEqual(len(run_cache), 1)

        run_cache.close()

        self.assertEqual(len(run_cache), 0)
        with self.assertRaises(cache.CacheError):
            run_cache.serve(request, carrier.fetch)
        run_cache.close()
        self.assertEqual(len(run_cache), 0)


class BoundedCacheTest(unittest.TestCase):
    """Criterion 3, bound half: the cache is bounded and eviction is observable.

    A cache with no bound is a memory leak that lives as long as the run. The
    entry a run keeps asking for is the last one worth dropping, so the entry
    dropped at the bound is the one least recently served.
    """

    def filled_cache(self, count):
        clock = FakeClock()
        carrier, opener = offline_transport(
            clock, {transport.DDG_HTML_ROUTE: (200, "<html></html>", "text/html")}
        )
        run_cache = cache.RunCache(clock=clock.monotonic)
        requests = tuple(
            transport.build_transport_request(
                transport.DDG_HTML_ROUTE, {"q": "query {0}".format(index)}
            )
            for index in range(count)
        )
        return run_cache, carrier, opener, requests

    def test_the_cache_never_holds_more_than_its_bound(self):
        run_cache, carrier, opener, requests = self.filled_cache(cache.MAX_ENTRIES + 8)

        for request in requests:
            run_cache.serve(request, carrier.fetch)
            self.assertLessEqual(len(run_cache), cache.MAX_ENTRIES)

        self.assertEqual(len(run_cache), cache.MAX_ENTRIES)
        self.assertEqual(len(opener.opened), len(requests))

    def test_the_entry_dropped_at_the_bound_is_the_least_recently_served(self):
        run_cache, carrier, opener, requests = self.filled_cache(cache.MAX_ENTRIES + 1)
        oldest, next_oldest, newcomer = requests[0], requests[1], requests[-1]
        for request in requests[:-1]:
            run_cache.serve(request, carrier.fetch)

        self.assertTrue(run_cache.serve(oldest, carrier.fetch).cache_hit)
        run_cache.serve(newcomer, carrier.fetch)

        self.assertEqual(len(run_cache), cache.MAX_ENTRIES)
        self.assertFalse(run_cache.serve(next_oldest, carrier.fetch).cache_hit)
        self.assertTrue(run_cache.serve(oldest, carrier.fetch).cache_hit)

    def test_a_working_set_at_the_bound_never_thrashes(self):
        run_cache, carrier, opener, requests = self.filled_cache(cache.MAX_ENTRIES)
        for request in requests:
            run_cache.serve(request, carrier.fetch)

        for _ in range(3):
            for request in requests:
                self.assertTrue(run_cache.serve(request, carrier.fetch).cache_hit)

        self.assertEqual(len(opener.opened), cache.MAX_ENTRIES)


class OracleCanFailTest(unittest.TestCase):
    """Criterion 5: the row-1 oracle rejects each specific way of being wrong.

    Its other half is ``TtlServeTest.test_the_run_cache_serves_a_repeat_read_unrestamped``,
    which shows the same oracle accepts the real cache. Every wrong cache is a
    file beside the tree; nothing under test is mutated to produce one.
    """

    def wrong_caches(self):
        return load_cache_fixture("wrong_caches")

    def test_a_cache_that_stamps_the_serve_time_fails_the_oracle(self):
        clock = FakeClock()
        wrong = self.wrong_caches().RestampingCache(clock.monotonic, clock.stamp)

        with self.assertRaisesRegex(AssertionError, "restamped with the serve time"):
            assert_repeat_read_is_served_unrestamped(wrong, clock)

    def test_a_cache_that_serves_without_saying_so_fails_the_oracle(self):
        clock = FakeClock()
        wrong = self.wrong_caches().UnmarkedCache(clock.monotonic)

        with self.assertRaisesRegex(AssertionError, "was not marked cache_hit"):
            assert_repeat_read_is_served_unrestamped(wrong, clock)

    def test_a_cache_whose_entries_never_expire_fails_the_oracle(self):
        clock = FakeClock()
        wrong = self.wrong_caches().NeverExpiringCache(clock.monotonic)

        with self.assertRaisesRegex(AssertionError, "outlived its TTL"):
            assert_repeat_read_is_served_unrestamped(wrong, clock)

    def test_a_cache_that_never_serves_fails_the_oracle(self):
        clock = FakeClock()
        wrong = self.wrong_caches().PassThroughCache(clock.monotonic)

        with self.assertRaisesRegex(AssertionError, "did not serve a repeat read inside its TTL"):
            assert_repeat_read_is_served_unrestamped(wrong, clock)

    def test_the_correct_fixture_cache_passes_the_same_oracle(self):
        # Each wrong cache above is this one with a single method overridden,
        # so its rejection is attributable to that override and nothing else.
        clock = FakeClock()

        assert_repeat_read_is_served_unrestamped(
            self.wrong_caches().CorrectCache(clock.monotonic), clock
        )

    def test_nothing_in_the_package_can_reach_a_wrong_cache(self):
        named = [
            path.name
            for path in PACKAGE_DIR.rglob("*.py")
            if "wrong_caches" in path.read_text(encoding="utf-8")
        ]

        self.assertEqual(named, [])


class RouteTtlTableTest(unittest.TestCase):
    """A TTL is declared per route, and only for routes that exist."""

    def test_every_declared_ttl_names_a_route_transport_owns(self):
        unknown = sorted(
            route_id
            for route_id in cache.ROUTE_TTL_SECONDS
            if route_id not in transport.ROUTE_CONSTANTS
        )

        self.assertEqual(unknown, [])

    def test_a_route_with_no_declared_ttl_still_gets_a_bounded_one(self):
        undeclared = sorted(
            route_id
            for route_id in transport.ROUTE_CONSTANTS
            if route_id not in cache.ROUTE_TTL_SECONDS
        )
        self.assertNotEqual(undeclared, [])

        for route_id in undeclared:
            with self.subTest(route=route_id):
                self.assertEqual(cache.ttl_seconds(route_id), cache.DEFAULT_TTL_SECONDS)
                self.assertGreater(cache.ttl_seconds(route_id), 0.0)


# What findings.md §1 actually measured, in the sizes it recorded them. The
# first two are the largest answers in the roster; the third is the smallest
# measurement above the cap, so it is the one that fixes the cap's ceiling.
MEASURED_LINKEDIN_BYTES = 577 * 1024
MEASURED_INSTAGRAM_BYTES = 455 * 1024
MEASURED_INNERTUBE_NEXT_BYTES = 1120 * 1024
MEASURED_INNERTUBE_SEARCH_BYTES = 2270 * 1024


class MeasuredBodyTest(unittest.TestCase):
    """Criteria 1-3: the cap sits above the measurements, not below them.

    A declared TTL on a body the cache refuses to hold is a freshness window
    that never binds: the route is read in full every time, and the window
    states something about the run that is not true of it. So the two largest
    answers the evidence records are held at the size it recorded them, and the
    guard still refuses what is genuinely too large.

    Asserted as the guard's decision on one body rather than by filling a
    cache: the question here is where the cap sits, and thirty-two megabyte
    bodies would answer it no better.
    """

    def held(self, body_bytes):
        """Whether a body of this size survives to answer the next read."""

        clock = FakeClock()
        carrier, opener = offline_transport(
            clock, {transport.DDG_HTML_ROUTE: (200, "x" * body_bytes, "text/html")}
        )
        run_cache = cache.RunCache(clock=clock.monotonic)
        request = transport.build_transport_request(
            transport.DDG_HTML_ROUTE, {"q": "local model"}
        )

        run_cache.serve(request, carrier.fetch)
        return run_cache.serve(request, carrier.fetch).cache_hit

    def test_the_largest_answer_the_evidence_measured_is_held(self):
        # findings.md §1: LinkedIn's public profile, 577 KB in 1.3 s — the
        # roster's most expensive read and its longest declared window. A cap
        # below this meant that window had never once bound on a real page.
        self.assertTrue(self.held(MEASURED_LINKEDIN_BYTES))

    def test_the_second_largest_answer_the_evidence_measured_is_held(self):
        # findings.md §1: Instagram's web profile, 455 KB in 2.9 s.
        self.assertTrue(self.held(MEASURED_INSTAGRAM_BYTES))

    def test_a_body_past_the_cap_is_still_served_through(self):
        # The guard still guards. It guards at a higher number.
        self.assertFalse(self.held(cache.MAX_ENTRY_BYTES + 1))

    def test_the_measurements_above_the_cap_are_still_served_through(self):
        # The cap's ceiling, held as behaviour rather than as arithmetic: a cap
        # raised past the smaller of these would begin holding an answer this
        # package has always served through. Both are InnerTube measurements,
        # and `cacheable` refuses that route on its method as well — this asks
        # the size guard alone, on a route whose method it would otherwise hold.
        for measured in (
            MEASURED_INNERTUBE_NEXT_BYTES,
            MEASURED_INNERTUBE_SEARCH_BYTES,
        ):
            with self.subTest(body_bytes=measured):
                self.assertFalse(self.held(measured))


class FootprintLawTest(unittest.TestCase):
    """Criterion 4: the declared footprint law says what the constants do.

    The law is stated twice — once beside the constants in `cache.py`, once in
    `protocol.md` for a reader who never opens the source — and a run's whole
    memory ceiling is the product of two numbers. Either sentence drifting from
    the constants turns a bound a caller relies on into a wrong number that
    nothing reddens to report, so both are parsed here rather than restated.
    """

    def protocol_sentence(self):
        stated = protocol_footprint_paragraphs()

        self.assertEqual(len(stated), 1, "the footprint law is stated once in protocol.md")
        return stated[0]

    def test_the_source_sentence_names_both_halves_of_the_bound(self):
        stated = footprint_comment()

        self.assertIn("MAX_ENTRY_BYTES", stated)
        self.assertIn("MAX_ENTRIES", stated)

    def test_the_protocol_sentence_states_the_constants_the_package_holds(self):
        stated = self.protocol_sentence()
        entries = STATED_ENTRIES.findall(stated)
        entry_bytes = STATED_ENTRY_BYTES.findall(stated)

        self.assertEqual(len(entries), 1)
        self.assertEqual(len(entry_bytes), 1)
        self.assertEqual(int(entries[0]), cache.MAX_ENTRIES)
        self.assertEqual(as_bytes(*entry_bytes[0]), cache.MAX_ENTRY_BYTES)

    def test_both_sentences_state_a_product_the_constants_multiply_to(self):
        # The bound is the product, so a sentence may state the two halves
        # correctly and still state the ceiling wrong.
        for where, stated in (
            ("cache.py", footprint_comment()),
            ("protocol.md", self.protocol_sentence()),
        ):
            with self.subTest(sentence=where):
                product = STATED_PRODUCT.findall(stated)

                self.assertEqual(len(product), 1, "states no product: " + stated)
                self.assertEqual(
                    as_bytes(*product[0]), cache.MAX_ENTRIES * cache.MAX_ENTRY_BYTES
                )


class RouteCommentTest(unittest.TestCase):
    """Criterion 6: a route comment's arithmetic agrees with the entry cap.

    These comments argue about which measured answers the cache can hold, so a
    cap that moves underneath one turns an argument into a false statement.
    That is the worse half of the hazard: a wrong comment beside a green suite
    is a claim nothing will ever redden to report. Read off the source here so
    the cap and the prose cannot drift apart silently.
    """

    def claiming(self, phrases):
        """Every route comment placing a measured body against the cap."""

        return [
            block
            for block in route_table_comments()
            if "MAX_ENTRY_BYTES" in block
            and any(phrase in block for phrase in phrases)
            and stated_sizes(block)
        ]

    def test_a_comment_calling_a_body_too_large_names_one_that_is(self):
        claims = self.claiming(OVER_THE_CAP)
        self.assertNotEqual(claims, [])

        for block in claims:
            for size in stated_sizes(block):
                with self.subTest(claim=block[:70], body_bytes=size):
                    self.assertGreater(size, cache.MAX_ENTRY_BYTES)

    def test_a_comment_calling_a_body_small_enough_names_one_that_is(self):
        claims = self.claiming(UNDER_THE_CAP)
        self.assertNotEqual(claims, [])

        for block in claims:
            for size in stated_sizes(block):
                with self.subTest(claim=block[:70], body_bytes=size):
                    self.assertLessEqual(size, cache.MAX_ENTRY_BYTES)

    def test_a_comment_stating_headroom_states_what_the_cap_really_leaves(self):
        # "with N KB of headroom, and not a byte more" is the most precise
        # claim in the table and the first one a cap change falsifies.
        claims = [
            block for block in route_table_comments() if STATED_HEADROOM.search(block)
        ]
        self.assertNotEqual(claims, [])

        for block in claims:
            stated = STATED_HEADROOM.search(block)
            body = min(
                size for size in stated_sizes(block) if size != as_bytes(*stated.groups())
            )
            with self.subTest(claim=block[:70]):
                self.assertEqual(
                    as_bytes(*stated.groups()), cache.MAX_ENTRY_BYTES - body
                )


if __name__ == "__main__":
    unittest.main()
