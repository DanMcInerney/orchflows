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

import unittest

from super_research import cache, transport


DDG_ROUTE = transport.route_constant(transport.DDG_HTML_ROUTE)
ARCHIVE_ROUTE = transport.route_constant(transport.ARCTIC_SHIFT_POSTS_ROUTE)
DDG_URL = DDG_ROUTE.origin + DDG_ROUTE.path


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


if __name__ == "__main__":
    unittest.main()
