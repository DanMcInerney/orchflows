from .common import *


# What the 2026-08-10 probes actually recorded, in the sizes it recorded them. The
# first two are the largest answers in the roster; the third is the smallest
# measurement above the cap, so it is the one that fixes the cap's ceiling.
MEASURED_LINKEDIN_BYTES = 577 * 1024
MEASURED_INSTAGRAM_BYTES = 455 * 1024
MEASURED_INNERTUBE_NEXT_BYTES = 1120 * 1024
MEASURED_INNERTUBE_SEARCH_BYTES = 2270 * 1024


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
        # The 2026-08-10 probes: LinkedIn's public profile, 577 KB in 1.3 s — the
        # roster's most expensive read and its longest declared window. A cap
        # below this meant that window had never once bound on a real page.
        self.assertTrue(self.held(MEASURED_LINKEDIN_BYTES))

    def test_the_second_largest_answer_the_evidence_measured_is_held(self):
        # The 2026-08-10 probes: Instagram's web profile, 455 KB in 2.9 s.
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
    `internals.md` for a reader who never opens the source — and a run's whole
    memory ceiling is the product of two numbers. Either sentence drifting from
    the constants turns a bound a caller relies on into a wrong number that
    nothing reddens to report, so both are parsed here rather than restated.
    """

    def document_sentence(self):
        stated = document_footprint_paragraphs()

        self.assertEqual(len(stated), 1, "the footprint law is stated once in internals.md")
        return stated[0]

    def test_the_source_sentence_names_both_halves_of_the_bound(self):
        stated = footprint_comment()

        self.assertIn("MAX_ENTRY_BYTES", stated)
        self.assertIn("MAX_ENTRIES", stated)

    def test_the_document_sentence_states_the_constants_the_package_holds(self):
        stated = self.document_sentence()
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
            ("internals.md", self.document_sentence()),
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
