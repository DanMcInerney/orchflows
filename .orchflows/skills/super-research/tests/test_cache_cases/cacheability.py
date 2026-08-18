from .common import *


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
        # the captive-portal caveat: an appliance answering for the origin says nothing
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
