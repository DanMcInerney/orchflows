from .common import *


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
