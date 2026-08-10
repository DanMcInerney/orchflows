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

import contextlib
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from super_research import cache, runner, schema, transport


CACHE_SOURCE = (
    Path(__file__).resolve().parent.parent / "scripts" / "super_research" / "cache.py"
)
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
        return self.responses[request.route_id]


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
        self.assertEqual(miss.loss, ())
        self.assertTrue(hit.cache_hit)
        self.assertEqual(hit.loss, (cache.CACHE_HIT,))
        self.assertEqual(hit.response, miss.response)

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


if __name__ == "__main__":
    unittest.main()
