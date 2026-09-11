"""Run-local caches written beside the tree, each wrong in exactly one way.

This file is not part of the package. Nothing imports it, no discovery pattern
matches it, and ``tests/test_cache.py`` loads it by path.

:class:`CorrectCache` satisfies the whole contract. Every other class here is
that same cache with one method overridden, so the oracle's rejection of each
is attributable to that one override and to nothing else. Together they show
the oracle discriminates between the four ways this cache can be wrong, rather
than accepting whatever it is handed.
"""

from dataclasses import replace

from super_research import cache


class CorrectCache:
    """A correct run-local cache. Every wrong one below overrides one method."""

    def __init__(self, clock):
        self._clock = clock
        self._entries = {}

    def fresh(self, stored_at, route_id):
        return self._clock() - stored_at < cache.ttl_seconds(route_id)

    def hit(self, response):
        return cache.CacheServe(response=response, cache_hit=True)

    def serve(self, request, fetch):
        key = cache.cache_key(request)
        entry = self._entries.get(key)
        if entry is not None:
            stored_at, response = entry
            if self.fresh(stored_at, request.route_id):
                return self.hit(response)
            del self._entries[key]
        response = fetch(request)
        self._entries[key] = (self._clock(), response)
        return cache.CacheServe(response=response, cache_hit=False)

    def close(self):
        self._entries = {}


class RestampingCache(CorrectCache):
    """Wrong one way: it stamps the serve time as the moment of observation.

    This is the failure the ``observed_at`` clause exists for. Everything else
    it serves is correct, so a caller sees a plausible moment that is fresher
    than any read ever was, and nothing on the record says it was invented.
    """

    def __init__(self, clock, wall):
        CorrectCache.__init__(self, clock)
        self._wall = wall

    def hit(self, response):
        return cache.CacheServe(
            response=replace(response, observed_at=self._wall()), cache_hit=True
        )


class UnmarkedCache(CorrectCache):
    """Wrong one way: it serves from memory without saying so."""

    def hit(self, response):
        return cache.CacheServe(response=response, cache_hit=False)


class NeverExpiringCache(CorrectCache):
    """Wrong one way: an entry it stored is fresh forever."""

    def fresh(self, stored_at, route_id):
        return True


class PassThroughCache(CorrectCache):
    """Wrong one way: it stores but never serves, so every read hits the origin."""

    def fresh(self, stored_at, route_id):
        return False
