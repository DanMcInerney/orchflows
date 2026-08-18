"""Bluesky behavioral cases re-exported by tests.test_social_adapters."""

from tests.test_social_adapters_cases._support import *  # noqa: F401,F403


class BlueskyDescriptorTest(unittest.TestCase):
    """What this adapter declares about itself, against the routes it declares it for."""

    def test_two_surfaces_are_declared_and_the_search_is_the_primary(self):
        self.assertEqual(
            bluesky.SURFACE_DESCRIPTORS, (bluesky.DESCRIPTOR, bluesky.AUTHOR_FEED_DESCRIPTOR)
        )
        self.assertEqual(bluesky.DESCRIPTOR.route_id, SEARCH_ROUTE)
        self.assertEqual(bluesky.AUTHOR_FEED_DESCRIPTOR.route_id, AUTHOR_ROUTE)

    def test_every_surface_speaks_for_bluesky_at_the_class_its_route_declares(self):
        for descriptor in bluesky.SURFACE_DESCRIPTORS:
            with self.subTest(route=descriptor.route_id):
                self.assertEqual(descriptor.adapter_id, "bluesky")
                self.assertEqual(descriptor.platform, "bluesky")
                self.assertEqual(descriptor.native_identity_namespace, "bluesky")
                self.assertEqual(descriptor.representation_kind, "native")
                self.assertEqual(descriptor.operator_identity, "bluesky")
                self.assertEqual(descriptor.standing_loss, ())
                self.assertEqual(descriptor.min_interval_ms, 1000)
                self.assertEqual(descriptor.burst, 5)
                self.assertEqual(descriptor.page_size, 100)
                # The class is the route's, not this module's opinion of it.
                self.assertEqual(
                    descriptor.access_class,
                    transport.ROUTE_CONSTANTS[descriptor.route_id].access_class,
                )

    def test_the_one_counted_metric_is_the_appviews_own_name_for_replies(self):
        # A name aliased across platforms would be this package inventing a
        # vocabulary; `replyCount` is what the payload calls it.
        for descriptor in bluesky.SURFACE_DESCRIPTORS:
            with self.subTest(route=descriptor.route_id):
                self.assertEqual(descriptor.reply_count_metric, "replyCount")
                self.assertEqual(descriptor.comment_count_metric, "")


class BlueskySearchTest(unittest.TestCase):
    """The search surface reading the shape the method documents and returns."""

    def setUp(self):
        self.page, self.opener = bluesky_page("search_posts.json", discovery("spacex"))

    def test_the_page_speaks_for_the_route_that_answered(self):
        self.assertEqual(self.page.outcome, "ok")
        self.assertEqual(self.page.loss, ())
        self.assertEqual(self.page.route_id, SEARCH_ROUTE)
        self.assertEqual(self.page.access_class, "K0")
        self.assertEqual(self.page.native_order, "bluesky_search_latest_order")
        self.assertEqual(len(self.page.records), 2)

    def test_a_post_is_addressed_by_its_handle_and_its_record_key(self):
        first = self.page.records[0]

        self.assertEqual(first.canonical_content_kind, "post")
        # The identity is the `at://` URI; the address is composed from the
        # handle beside it and the URI's last segment, because the payload
        # publishes no web address at all.
        self.assertEqual(first.native_item_id, BSKY_ROOT_URI)
        self.assertEqual(
            first.canonical_locator,
            "https://bsky.app/profile/" + BSKY_HANDLE + "/post/3msqpuobiwk2t",
        )
        self.assertEqual(first.author, BSKY_HANDLE)
        self.assertEqual(first.published_at, "2026-08-10T18:23:59Z")
        self.assertEqual(first.native_position, 0)
        self.assertEqual(first.loss, ())
        self.assertTrue(first.body.startswith("v1.130 is live!"))

    def test_the_four_declared_counts_are_the_payloads_own_exact_integers(self):
        self.assertEqual(
            self.page.records[0].engagement,
            (
                ("likeCount", 9487),
                ("repostCount", 2388),
                ("replyCount", 494),
                ("quoteCount", 2368),
            ),
        )

    def test_a_count_this_module_does_not_declare_is_carried_nowhere(self):
        # The payload states `bookmarkCount: 600` on this row. It is not one of
        # the four declared metrics, so it is neither an engagement figure nor
        # an attribute: a name this module does not declare is a name it does
        # not carry.
        record = self.page.records[0]

        self.assertNotIn("bookmarkCount", dict(record.engagement))
        self.assertNotIn("bookmarkCount", named(record))

    def test_a_post_carries_the_appviews_own_named_facts(self):
        self.assertEqual(
            self.page.records[0].attributes,
            (
                ("did", BSKY_DID),
                ("cid", "bafyreia5giteuhei7im66w7yn3pldm7h7npkmuy73fvakrpsjsz5oejdgu"),
                ("indexedAt", "2026-08-10T18:24:05.869Z"),
            ),
        )

    def test_a_reply_names_the_post_it_answers_and_carries_its_root_apart(self):
        reply = self.page.records[1]

        self.assertEqual(reply.native_item_id, BSKY_REPLY_URI)
        self.assertEqual(reply.native_parent_id, BSKY_ROOT_URI)
        # The thread's root is a separate fact and never `native_parent_id`.
        self.assertEqual(named(reply)["root_uri"], BSKY_ROOT_URI)
        # And a reply never inherits the parent's counts.
        self.assertEqual(dict(reply.engagement)["likeCount"], 2378)

    def test_a_post_answering_nothing_names_no_parent_and_no_root(self):
        first = self.page.records[0]

        self.assertEqual(first.native_parent_id, "")
        self.assertNotIn("root_uri", named(first))

    def test_the_continuation_is_the_one_the_appview_published(self):
        self.assertEqual(
            self.page.cursor_out, payload_of(BLUESKY_DIR, "search_posts.json")["cursor"]
        )


class BlueskyAuthorFeedTest(unittest.TestCase):
    """One actor's feed: the same post view, wrapped one level deeper."""

    def setUp(self):
        self.page, self.opener = bluesky_page(
            "author_feed.json", discovery("author:" + BSKY_HANDLE), route_id=AUTHOR_ROUTE
        )

    def test_every_feed_entry_is_read_through_its_own_post(self):
        self.assertEqual(self.page.outcome, "ok")
        self.assertEqual(self.page.route_id, AUTHOR_ROUTE)
        self.assertEqual(self.page.native_order, "bluesky_author_feed_order")
        self.assertEqual(len(self.page.records), 3)
        self.assertEqual([record.native_position for record in self.page.records], [0, 1, 2])

    def test_a_reposted_row_is_authored_by_whoever_wrote_it(self):
        # A repost is somebody else's post carried in this actor's feed. Its
        # author is the account that wrote it, and its address is under that
        # account's handle — attributing it to the reposter would be this
        # module inventing an authorship the payload does not state.
        passed_on = self.page.records[2]

        self.assertEqual(passed_on.author, BSKY_REPOSTED_HANDLE)
        self.assertTrue(
            passed_on.canonical_locator.startswith(
                "https://bsky.app/profile/" + BSKY_REPOSTED_HANDLE + "/post/"
            ),
            passed_on.canonical_locator,
        )
        self.assertEqual(passed_on.published_at, "2026-08-01T20:08:00Z")
        self.assertEqual(dict(passed_on.engagement)["likeCount"], 574)

    def test_the_continuation_is_the_one_the_appview_published(self):
        self.assertEqual(
            self.page.cursor_out, payload_of(BLUESKY_DIR, "author_feed.json")["cursor"]
        )


class BlueskyAnswersWithNoPostsTest(unittest.TestCase):
    """The five ways these methods answer with no post, told apart.

    The one that matters is the 403. It is a refusal about who is asking,
    arriving from the party in front of the AppView, on a method the platform
    documents as keyless — and the 400 beside it, whose body also declines to
    serve, is an ordinary status. Only the status line may decide.
    """

    def test_an_empty_container_is_an_absence_and_says_so(self):
        for name, route_id, request, spoken in (
            ("search_posts_empty.json", SEARCH_ROUTE, discovery("nothing here"), "posts"),
            ("author_feed_empty.json", AUTHOR_ROUTE, discovery("author:nobody"), "feed"),
        ):
            with self.subTest(fixture=name):
                page, _ = bluesky_page(name, request, route_id=route_id)

                self.assertEqual(page.outcome, "empty")
                self.assertEqual(page.loss, ())
                self.assertEqual(page.records, ())
                self.assertIn(spoken, " ".join(page.warnings))

    def test_a_payload_whose_container_moved_is_drift_and_never_an_absence(self):
        for name, route_id, request in (
            ("search_posts_reshaped.json", SEARCH_ROUTE, discovery("spacex")),
            ("author_feed_reshaped.json", AUTHOR_ROUTE, discovery("author:" + BSKY_HANDLE)),
        ):
            with self.subTest(fixture=name):
                page, _ = bluesky_page(name, request, route_id=route_id)

                self.assertEqual(page.outcome, "failed")
                self.assertEqual(page.loss, ("schema_drift",))
                self.assertEqual(page.records, ())
                self.assertIn("changed shape", " ".join(page.warnings))

    def test_rows_that_name_no_post_are_drift_and_never_an_empty_feed(self):
        # The container is there and holds two entries, and neither of them
        # carries a post this adapter can identify. Reporting that as "this
        # actor has posted nothing" is the one thing a caller cannot tell from
        # a real absence.
        page, _ = bluesky_page(
            "author_feed_no_posts.json", discovery("author:" + BSKY_HANDLE), route_id=AUTHOR_ROUTE
        )

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.loss, ("schema_drift",))
        self.assertIn("no uri on any of them", " ".join(page.warnings))

    def test_a_body_that_is_not_json_at_two_hundred_is_malformed_and_not_a_refusal(self):
        page, _ = answered(bluesky, SEARCH_ROUTE, "<html>not json", discovery("spacex"))

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.loss, ("malformed_json",))
        self.assertNotIn(bluesky.AUTH_REQUIRED, page.loss)

    def test_the_cdns_own_refusal_is_typed_as_one_and_quoted(self):
        page, _ = bluesky_page(
            "forbidden_403.html", discovery("spacex"), status=403, content_type=HTML_TYPE
        )

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.loss, ("auth_required",))
        self.assertEqual(page.records, ())
        spoken = " ".join(page.warnings)
        self.assertIn("403", spoken)
        self.assertIn("who is asking", spoken)
        # The refusing party's own first readable sentence, so an operator
        # reads the CDN rather than this module's guess at it.
        self.assertIn("403 Forbidden", spoken)

    def test_the_same_body_at_two_statuses_is_two_different_answers(self):
        # The sharpest form of the rule. One body, twice: at 403 it is the
        # origin declining over who is asking, at 400 it is an ordinary status.
        # Nothing in the body moved, so nothing in the body decided.
        refused, _ = bluesky_page(
            "forbidden_403.html", discovery("spacex"), status=403, content_type=HTML_TYPE
        )
        ordinary, _ = bluesky_page(
            "forbidden_403.html", discovery("spacex"), status=400, content_type=HTML_TYPE
        )

        self.assertEqual(refused.loss, ("auth_required",))
        self.assertEqual(ordinary.loss, ("http_status",))

    def test_an_unauthorized_status_is_the_same_refusal_as_a_forbidden_one(self):
        page, _ = bluesky_page("forbidden_403.html", discovery("spacex"), status=401,
                              content_type=HTML_TYPE)

        self.assertEqual(page.loss, ("auth_required",))

    def test_an_appview_error_body_is_quoted_from_its_own_message(self):
        page, _ = bluesky_page(
            "profile_not_found_400.json",
            discovery("author:nobody"),
            route_id=AUTHOR_ROUTE,
            status=400,
        )

        self.assertEqual(page.loss, ("http_status",))
        self.assertIn("Profile not found", " ".join(page.warnings))


class BlueskyGrammarTest(unittest.TestCase):
    """Which method a step reaches, and what a step that names none means."""

    def test_a_caller_names_the_operation_and_the_argument_survives_it(self):
        for named_step, expected in (
            ("search:spacex", (bluesky.SEARCH_OPERATION, "spacex")),
            ("author:" + BSKY_HANDLE, (bluesky.AUTHOR_OPERATION, BSKY_HANDLE)),
            # A decentralised identifier is full of colons and travels whole.
            ("author:" + BSKY_DID, (bluesky.AUTHOR_OPERATION, BSKY_DID)),
        ):
            with self.subTest(step=named_step):
                self.assertEqual(bluesky.operation_for(discovery(named_step)), expected)

    def test_absent_a_prefix_both_shapes_of_step_search(self):
        # An actor is a thing a caller names, never a thing inferred from the
        # characters in an argument.
        self.assertEqual(
            bluesky.operation_for(discovery("spacex")), (bluesky.SEARCH_OPERATION, "spacex")
        )
        self.assertEqual(
            bluesky.operation_for(hydration(BSKY_HANDLE)),
            (bluesky.SEARCH_OPERATION, BSKY_HANDLE),
        )

    def test_a_query_carrying_a_colon_this_module_does_not_name_stays_a_query(self):
        self.assertEqual(
            bluesky.operation_for(discovery("from:someone spacex")),
            (bluesky.SEARCH_OPERATION, "from:someone spacex"),
        )

    def test_a_search_asks_for_the_latest_and_states_the_page_it_wants(self):
        _, opener = bluesky_page("search_posts.json", discovery("spacex"))

        self.assertEqual(
            opener.opened[0].url,
            built_url(SEARCH_ROUTE, {"q": "spacex", "sort": "latest", "limit": "100"}),
        )

    def test_an_author_step_names_the_actor_and_no_sort_at_all(self):
        _, opener = bluesky_page(
            "author_feed.json", discovery("author:" + BSKY_DID), route_id=AUTHOR_ROUTE
        )

        self.assertEqual(
            opener.opened[0].url,
            built_url(AUTHOR_ROUTE, {"actor": BSKY_DID, "limit": "100"}),
        )

    def test_one_call_reads_one_page_and_nothing_else(self):
        _, opener = bluesky_page("search_posts.json", discovery("spacex"))

        self.assertEqual(len(opener.opened), 1)


class BlueskyWindowAndCursorTest(unittest.TestCase):
    """The step's bounds, in the method's own terms, and the page after this one."""

    def test_the_steps_window_reaches_the_search_as_since_and_until(self):
        _, opener = bluesky_page(
            "search_posts.json",
            discovery(
                "spacex",
                window_start="2026-08-01T00:00:00Z",
                window_end="2026-08-17T00:00:00Z",
            ),
        )

        self.assertEqual(
            opener.opened[0].url,
            built_url(
                SEARCH_ROUTE,
                {
                    "q": "spacex",
                    "sort": "latest",
                    "limit": "100",
                    "since": "2026-08-01T00:00:00Z",
                    "until": "2026-08-17T00:00:00Z",
                },
            ),
        )

    def test_a_half_open_window_sends_only_the_bound_it_has(self):
        _, opener = bluesky_page(
            "search_posts.json", discovery("spacex", window_start="2026-08-01T00:00:00Z")
        )

        self.assertIn("since=2026-08-01T00%3A00%3A00Z", opener.opened[0].url)
        self.assertNotIn("until", opener.opened[0].url)

    def test_the_author_feed_takes_no_bound_on_time_and_is_sent_none(self):
        # The method publishes no term for one, so the core's own filter is the
        # whole window there. Sending a parameter the method does not declare
        # would be this module inventing the origin's vocabulary.
        _, opener = bluesky_page(
            "author_feed.json",
            discovery(
                "author:" + BSKY_HANDLE,
                window_start="2026-08-01T00:00:00Z",
                window_end="2026-08-17T00:00:00Z",
            ),
            route_id=AUTHOR_ROUTE,
        )

        self.assertEqual(
            opener.opened[0].url,
            built_url(AUTHOR_ROUTE, {"actor": BSKY_HANDLE, "limit": "100"}),
        )

    def test_a_cursor_the_core_froze_is_spent_under_the_appviews_own_name(self):
        for route_id, name, request, params in (
            (
                SEARCH_ROUTE,
                "search_posts.json",
                discovery("spacex", ),
                {"q": "spacex", "sort": "latest", "limit": "100", "cursor": "25"},
            ),
            (
                AUTHOR_ROUTE,
                "author_feed.json",
                discovery("author:" + BSKY_HANDLE),
                {"actor": BSKY_HANDLE, "limit": "100", "cursor": "25"},
            ),
        ):
            with self.subTest(route=route_id):
                carried = adapters.AdapterRequest(
                    step_id=request.step_id,
                    query=request.query,
                    target_ids=request.target_ids,
                    cursor="25",
                )
                _, opener = bluesky_page(name, carried, route_id=route_id)

                self.assertEqual(opener.opened[0].url, built_url(route_id, params))


class BlueskyFieldOmittedTest(unittest.TestCase):
    """A row that arrived short of what this adapter declares says so."""

    def test_a_post_with_no_text_carries_the_loss_and_still_carries_its_counts(self):
        payload = payload_of(BLUESKY_DIR, "search_posts.json")
        del payload["posts"][0]["record"]["text"]
        page, _ = answered(bluesky, SEARCH_ROUTE, json.dumps(payload), discovery("spacex"))

        self.assertEqual(page.outcome, "ok")
        self.assertEqual(page.records[0].loss, ("field_omitted",))
        self.assertEqual(page.records[0].body, "")
        self.assertEqual(dict(page.records[0].engagement)["likeCount"], 9487)
        # And the row beside it, which arrived whole, carries no loss at all.
        self.assertEqual(page.records[1].loss, ())

    def test_a_stamp_this_module_cannot_read_is_a_missing_time_and_not_a_guess(self):
        payload = payload_of(BLUESKY_DIR, "search_posts.json")
        payload["posts"][0]["record"]["createdAt"] = "yesterday"
        page, _ = answered(bluesky, SEARCH_ROUTE, json.dumps(payload), discovery("spacex"))

        self.assertEqual(page.records[0].published_at, "")
        self.assertEqual(page.records[0].loss, ("field_omitted",))

