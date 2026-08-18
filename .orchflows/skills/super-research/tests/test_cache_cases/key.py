from .common import *


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

