"""A run-local cache that is not run-local: it keeps its entries in a file.

This file is not part of the package. Nothing imports it, no discovery pattern
matches it, and ``tests/test_cache.py`` loads it by path.

It exists so both halves of "no entry can survive a run" are shown to
discriminate rather than to match nothing: the import scan finds the modules a
cache needs in order to persist, and the zero-I/O guard stops the write this
one attempts. It is never run outside that guard, and the store it is handed
sits under a directory that does not exist, so no file is created either way.
"""

import json
import os
from pathlib import Path

from super_research import cache


class DiskBackedCache:
    """Wrong one way: its entries outlive the process that made them."""

    def __init__(self, clock, store):
        self._clock = clock
        self._store = Path(store)

    def _read(self):
        try:
            handle = open(str(self._store), "r", encoding="utf-8")
        except OSError:
            return {}
        with handle:
            return json.load(handle)

    def _write(self, entries):
        os.makedirs(str(self._store.parent), exist_ok=True)
        with open(str(self._store), "w", encoding="utf-8") as handle:
            json.dump(entries, handle)

    def serve(self, request, fetch):
        key = cache.cache_key(request)
        slot = key.route_id + "|" + key.canonical_request
        entries = self._read()
        if slot in entries:
            stored_at, body = entries[slot]
            if self._clock() - stored_at < cache.ttl_seconds(request.route_id):
                return cache.CacheServe(response=body, cache_hit=True)
        response = fetch(request)
        entries[slot] = [self._clock(), response.body]
        self._write(entries)
        return cache.CacheServe(response=response, cache_hit=False)

    def close(self):
        pass
