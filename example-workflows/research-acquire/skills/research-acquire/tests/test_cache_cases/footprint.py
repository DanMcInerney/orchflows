from .common import *


class BoundedCacheTest(unittest.TestCase):
    """Criterion 3, bound half: the cache is bounded and eviction is observable.

    A cache with no bound is a memory leak that lives as long as the run. The
    entry a run keeps asking for is the last one worth dropping, so the entry
    dropped at the bound is the one least recently served.
    """

    def filled_cache(self, count):
        clock = FakeClock()
        carrier, opener = offline_transport(
            clock, {transport.FAKE_OFFLINE_ROUTE: (200, "<html></html>", "text/html")}
        )
        run_cache = cache.RunCache(clock=clock.monotonic)
        requests = tuple(
            transport.build_transport_request(
                transport.FAKE_OFFLINE_ROUTE, {"q": "query {0}".format(index)}
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


class BodySizeBoundaryTest(unittest.TestCase):
    """The byte cap admits its boundary and serves oversized bodies through."""

    def held(self, body):
        clock = FakeClock()
        carrier, opener = offline_transport(
            clock, {transport.FAKE_OFFLINE_ROUTE: (200, body, "application/xml")}
        )
        run_cache = cache.RunCache(clock=clock.monotonic)
        request = transport.build_transport_request(
            transport.FAKE_OFFLINE_ROUTE, {"q": "local model"}
        )
        first = run_cache.serve(request, carrier.fetch)
        second = run_cache.serve(request, carrier.fetch)
        self.assertEqual(first.response.body, body)
        self.assertEqual(second.response.body, body)
        return second.cache_hit

    def test_body_at_the_byte_cap_is_held(self):
        self.assertTrue(self.held("x" * cache.MAX_ENTRY_BYTES))

    def test_body_one_byte_above_cap_is_served_through(self):
        self.assertFalse(self.held("x" * (cache.MAX_ENTRY_BYTES + 1)))

    def test_cap_counts_encoded_bytes_not_characters(self):
        self.assertFalse(self.held("é" * (cache.MAX_ENTRY_BYTES // 2 + 1)))


if __name__ == "__main__":
    unittest.main()
