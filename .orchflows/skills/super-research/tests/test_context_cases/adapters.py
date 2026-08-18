"""Adapter implementation and declaration boundary cases."""

from .support import *  # noqa: F403

class WebSearchDiscoveryTest(unittest.TestCase):
    """The K4 discovery adapter: one page in, one NativePage out, nothing else."""

    def setUp(self):
        self.html = read_fixture("ddg_html_results.html")
        self.request = adapters.AdapterRequest(
            step_id="s1-discover", query="site:reddit.com best local model"
        )

    def test_ddg_html_yields_one_native_page_of_index_hits(self):
        carrier, opener = tracer_transport({"ddg_html": (200, self.html, "text/html")})

        page = web_search.fetch_native_page(carrier, self.request)

        self.assertEqual(page.adapter_id, "web_search")
        self.assertEqual(page.route_id, "ddg_html")
        self.assertEqual(page.outcome, "ok")
        self.assertEqual(len(page.records), 6)
        self.assertEqual(len(opener.opened), 1)
        self.assertEqual([call.route_id for call in carrier.calls], ["ddg_html"])

        first = page.records[0]
        self.assertEqual(first.canonical_content_kind, "web_hit")
        self.assertEqual(first.canonical_locator, REDDIT_THREAD_LOCATOR)
        self.assertEqual(first.title, "What is the best local model right now? : r/LocalLLaMA")
        self.assertIn("24GB of VRAM", first.body)
        self.assertEqual(first.native_position, 0)
        self.assertEqual(first.engagement, ())

        self.assertEqual(page.records[1].canonical_locator, X_POST_LOCATOR)

        snippetless = page.records[5]
        self.assertEqual(snippetless.canonical_locator, "https://example.net/empty")
        self.assertEqual(snippetless.body, "")
        self.assertIn("field_omitted", snippetless.loss)

    def test_index_hit_snippet_never_becomes_native_engagement(self):
        carrier, _ = tracer_transport({"ddg_html": (200, self.html, "text/html")})

        page = web_search.fetch_native_page(carrier, self.request)

        # The first snippet literally reads "120 votes, 88 comments"; a K4 index
        # hit reports it as prose and claims no native metric from it.
        self.assertEqual(page.records[0].engagement, ())
        self.assertIn("engagement_unavailable", page.records[0].loss)
        self.assertIn("target_not_hydrated", page.records[0].loss)

    def test_next_page_cursor_is_surfaced_but_never_followed(self):
        carrier, opener = tracer_transport({"ddg_html": (200, self.html, "text/html")})

        page = web_search.fetch_native_page(carrier, self.request)

        self.assertEqual(page.cursor_out, "30")
        self.assertEqual(len(opener.opened), 1)

    def test_non_success_status_is_typed_and_never_a_silent_empty(self):
        carrier, _ = tracer_transport({"ddg_html": (503, "<html>Service Unavailable</html>", "text/html")})

        page = web_search.fetch_native_page(carrier, self.request)

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.records, ())
        self.assertIn("http_status", page.loss)
        self.assertIn("503", " ".join(page.warnings))

    def test_two_nav_forms_leave_the_last_offset_and_nobody_spends_it(self):
        # A paginated page carries an `s` input in the "< Previous" form and
        # another in "Next", and this parser takes the last. Whether the last
        # is the forward one is not in the evidence — page one, which is what
        # The 2026-08-10 probes recorded, has only the forward form. Recorded here
        # rather than guarded, because nothing reads the value:
        # `runner.planned_calls` sets no cursor, which
        # `NothingOverlapsAndNothingPagesTest` pins.
        backwards = self.html.replace(
            '<div class="nav-link">',
            '<div class="nav-link"><form action="/html/" method="post">'
            '<input type="hidden" name="s" value="0" /></form></div>'
            '<div class="nav-link">',
            1,
        )
        carrier, _ = tracer_transport({"ddg_html": (200, backwards, "text/html")})

        page = web_search.fetch_native_page(carrier, self.request)

        self.assertEqual(page.cursor_out, "30")
        self.assertEqual(backwards.count('name="s"'), 2)

    def test_a_parsed_page_with_no_results_is_empty_not_failed(self):
        carrier, _ = tracer_transport(
            {"ddg_html": (200, "<html><body><div class='results'></div></body></html>", "text/html")}
        )

        page = web_search.fetch_native_page(carrier, self.request)

        self.assertEqual(page.outcome, "empty")
        self.assertEqual(page.records, ())
        self.assertNotIn("http_status", page.loss)


class RedditArchiveHydrationTest(unittest.TestCase):
    """The K3 hydration adapter: the archive's own fields, labelled as the archive."""

    def setUp(self):
        self.payload = read_fixture("arctic_shift_posts_ids.json")
        self.request = adapters.AdapterRequest(step_id="s2-hydrate", target_ids=("1abc234",))

    def _page(self, response):
        carrier, opener = tracer_transport({"arctic_shift_posts_ids": response})
        return reddit_archive.fetch_native_page(carrier, self.request), carrier, opener

    def test_arctic_shift_post_yields_one_native_page_with_platform_engagement(self):
        page, carrier, opener = self._page((200, self.payload, "application/json"))

        self.assertEqual(page.adapter_id, "reddit_archive")
        self.assertEqual(page.representation_kind, "native")
        self.assertEqual(page.platform, "reddit")
        self.assertEqual(page.outcome, "ok")
        self.assertEqual(len(page.records), 1)
        self.assertEqual(len(opener.opened), 1)
        self.assertEqual([call.route_id for call in carrier.calls], ["arctic_shift_posts_ids"])

        post = page.records[0]
        self.assertEqual(post.canonical_content_kind, "post")
        self.assertEqual(post.canonical_locator, REDDIT_THREAD_LOCATOR)
        self.assertEqual(post.title, "What is the best local model right now?")
        self.assertIn("prompt-processing time", post.body)
        self.assertEqual(post.author, "vram_hoarder")
        self.assertEqual(post.community, "LocalLLaMA")
        self.assertEqual(post.published_at, "2026-08-09T13:20:00Z")
        self.assertEqual(dict(post.engagement), {"score": 120, "num_comments": 88})

    def test_reddit_native_identity_carries_the_fullname_prefix(self):
        page, _, _ = self._page((200, self.payload, "application/json"))

        self.assertEqual(page.records[0].native_item_id, "t3_1abc234")

    def test_third_party_archive_records_name_their_operator(self):
        page, _, _ = self._page((200, self.payload, "application/json"))

        self.assertEqual(page.operator_identity, "arctic-shift")
        self.assertEqual(page.access_class, "K3")
        self.assertIn("third_party_archive", page.records[0].loss)

    def test_malformed_json_is_typed_and_never_a_silent_empty(self):
        page, _, opener = self._page((200, "{not json", "application/json"))

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.records, ())
        self.assertIn("malformed_json", page.loss)
        self.assertEqual(len(opener.opened), 1)

    def test_non_success_status_is_typed_and_never_retried(self):
        page, _, opener = self._page((502, "bad gateway", "text/plain"))

        self.assertEqual(page.outcome, "failed")
        self.assertIn("http_status", page.loss)
        self.assertEqual(len(opener.opened), 1)

    def test_a_submission_the_archive_named_no_id_for_carries_no_identity(self):
        # wrong_merge_law rule 1: the prefix alone is not an identity. Two
        # submissions the archive answered without an `id` would otherwise both
        # be `t3_`, present one strong identity, and be folded into one group —
        # a merge of two distinct threads on a key neither of them has.
        payload = json.dumps(
            {
                "data": [
                    {"title": "first", "permalink": "/r/a/comments/x1/first/"},
                    {"title": "second", "permalink": "/r/a/comments/x2/second/"},
                ]
            }
        )
        page, _, _ = self._page((200, payload, "application/json"))

        self.assertEqual([record.native_item_id for record in page.records], ["", ""])
        for record in page.records:
            self.assertIn("field_omitted", record.loss)
            self.assertIn("third_party_archive", record.loss)

        step = schema.AcquisitionStep(
            step_id="s2-hydrate", kind="discovery", adapter_id="reddit_archive", max_items=8
        )
        records = normalize.normalize_page(page, step, "artifact:x", "x")
        for record in records:
            self.assertIsNone(normalize.strong_identity(record))
        self.assertEqual(len(normalize.group_records(records)), 2)


class AdapterCallBoundaryTest(unittest.TestCase):
    """Completion criterion 3, for every adapter the tracer crosses.

    One call, one page, one route: no pagination, no retry, no fallback, no
    cross-adapter call, no persistence.
    """

    def _seeded(self, module, fixture, content_type):
        return tracer_transport(
            {module.DESCRIPTOR.route_id: (200, read_fixture(fixture), content_type)}
        )

    def test_one_call_yields_one_page_over_the_adapters_own_route_only(self):
        for module, request, fixture, content_type in ADAPTER_CALLS:
            with self.subTest(adapter=module.DESCRIPTOR.adapter_id):
                carrier, opener = self._seeded(module, fixture, content_type)

                page = module.fetch_native_page(carrier, request)

                self.assertEqual(len(opener.opened), 1)
                self.assertEqual(
                    {call.route_id for call in carrier.calls}, {module.DESCRIPTOR.route_id}
                )
                self.assertEqual(page.route_id, module.DESCRIPTOR.route_id)
                self.assertTrue(page.records)

    def test_a_raising_transport_is_never_retried(self):
        for module, request, _, _ in ADAPTER_CALLS:
            with self.subTest(adapter=module.DESCRIPTOR.adapter_id):
                carrier, opener = tracer_transport(
                    {module.DESCRIPTOR.route_id: transport.TransportError("connection reset")}
                )

                with self.assertRaises(transport.TransportError):
                    module.fetch_native_page(carrier, request)

                self.assertEqual(len(opener.opened), 1)
                self.assertEqual(len(carrier.calls), 1)

    def test_no_adapter_touches_the_filesystem_or_a_socket(self):
        for module, request, fixture, content_type in ADAPTER_CALLS:
            with self.subTest(adapter=module.DESCRIPTOR.adapter_id):
                carrier, _ = self._seeded(module, fixture, content_type)

                with forbid_io():
                    page = module.fetch_native_page(carrier, request)

                self.assertTrue(page.records)


class FakeAdapterTest(unittest.TestCase):
    """The offline adapter stands in for a route that does not exist yet."""

    def test_fixture_page_declares_the_platform_it_stands_in_for(self):
        carrier, opener = tracer_transport(
            {"fake_offline": (200, read_fixture("fake_x_native_page.json"), "application/json")}
        )

        page = fake.fetch_native_page(
            carrier, adapters.AdapterRequest(step_id="s2-hydrate", target_ids=("x_native_page",))
        )

        self.assertEqual(page.adapter_id, "fake")
        self.assertEqual(page.platform, "x")
        self.assertEqual(page.native_identity_namespace, "x")
        self.assertEqual(page.representation_kind, "native")
        self.assertEqual(len(page.records), 2)
        self.assertEqual(len(opener.opened), 1)

        post, reply = page.records
        self.assertEqual(post.canonical_content_kind, "post")
        self.assertEqual(post.canonical_locator, X_POST_LOCATOR)
        self.assertEqual(dict(post.engagement)["favorite_count"], 412)
        self.assertEqual(reply.canonical_content_kind, "reply")
        self.assertEqual(reply.native_parent_id, post.native_item_id)


class AdapterDeclarationTest(unittest.TestCase):
    """A live adapter's page always agrees with the descriptor it ships."""

    def test_live_pages_agree_with_their_static_descriptor(self):
        carrier, _ = tracer_transport(
            {
                "ddg_html": (200, read_fixture("ddg_html_results.html"), "text/html"),
                "arctic_shift_posts_ids": (
                    200,
                    read_fixture("arctic_shift_posts_ids.json"),
                    "application/json",
                ),
            }
        )
        pages = (
            web_search.fetch_native_page(
                carrier, adapters.AdapterRequest(step_id="s1-discover", query="q")
            ),
            reddit_archive.fetch_native_page(
                carrier, adapters.AdapterRequest(step_id="s2-hydrate", target_ids=("1abc234",))
            ),
        )
        descriptors = (web_search.DESCRIPTOR, reddit_archive.DESCRIPTOR)

        for page, descriptor in zip(pages, descriptors):
            self.assertEqual(page.adapter_id, descriptor.adapter_id)
            self.assertEqual(page.route_id, descriptor.route_id)
            self.assertEqual(page.access_class, descriptor.access_class)
            self.assertEqual(page.platform, descriptor.platform)
            self.assertEqual(page.representation_kind, descriptor.representation_kind)
            self.assertEqual(
                page.native_identity_namespace, descriptor.native_identity_namespace
            )

    def test_discovery_and_hydration_declare_different_representations(self):
        self.assertEqual(web_search.DESCRIPTOR.representation_kind, "index")
        self.assertEqual(reddit_archive.DESCRIPTOR.representation_kind, "native")


