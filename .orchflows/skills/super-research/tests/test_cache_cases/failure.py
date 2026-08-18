from .common import *


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

