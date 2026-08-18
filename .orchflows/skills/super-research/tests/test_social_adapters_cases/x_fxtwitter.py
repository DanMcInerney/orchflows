"""FxTwitter behavioral cases re-exported by tests.test_social_adapters."""

from tests.test_social_adapters_cases._support import *  # noqa: F401,F403


class XFxtwitterDescriptorTest(unittest.TestCase):
    """What this adapter declares: an operator's identity, and the platform's namespace."""

    def test_the_descriptor_speaks_for_x_through_an_operator_that_is_not_x(self):
        descriptor = x_fxtwitter.DESCRIPTOR

        self.assertEqual(descriptor.adapter_id, "x_fxtwitter")
        self.assertEqual(descriptor.route_id, FXTWITTER_ROUTE)
        self.assertEqual(descriptor.platform, "x")
        self.assertEqual(descriptor.representation_kind, "native")
        self.assertEqual(descriptor.operator_identity, "fxtwitter")
        self.assertEqual(descriptor.min_interval_ms, 1000)
        self.assertEqual(descriptor.burst, 5)
        self.assertEqual(descriptor.page_size, 20)
        self.assertEqual(descriptor.reply_count_metric, "replies")
        self.assertEqual(descriptor.comment_count_metric, "")

    def test_the_class_is_the_routes_own_and_it_is_the_archive_class(self):
        self.assertEqual(x_fxtwitter.DESCRIPTOR.access_class, "K3")
        self.assertEqual(
            x_fxtwitter.DESCRIPTOR.access_class,
            transport.ROUTE_CONSTANTS[FXTWITTER_ROUTE].access_class,
        )

    def test_the_namespace_is_the_platforms_so_one_tweet_read_twice_is_one_tweet(self):
        # Read here and read off the syndication timeline, a status must group
        # by strong identity. A namespace naming the operator would make two
        # readings of one status two different things.
        self.assertEqual(x_fxtwitter.DESCRIPTOR.native_identity_namespace, "x")

    def test_the_standing_loss_is_declared_on_the_descriptor(self):
        self.assertEqual(x_fxtwitter.DESCRIPTOR.standing_loss, ("third_party_archive",))


class XFxtwitterStandingLossTest(unittest.TestCase):
    """`third_party_archive` on every record of every answer, never the page alone."""

    def test_every_record_of_every_answering_operation_carries_it(self):
        for name, request in (
            ("search.json", discovery("spacex")),
            ("statuses.json", discovery("timeline:" + X_HANDLE)),
            ("profile.json", discovery("user:" + X_HANDLE)),
            ("conversation.json", hydration(X_ROOT_ID)),
        ):
            page, _ = fxtwitter_page(name, request)
            with self.subTest(fixture=name):
                self.assertEqual(page.outcome, "ok")
                self.assertTrue(page.records)
                for record in page.records:
                    self.assertIn("third_party_archive", record.loss)

    def test_the_fact_rides_on_the_record_rather_than_on_the_page(self):
        # A caller holding one row cannot correlate it back to a page to learn
        # where it came from, which is the whole reason the loss is standing.
        page, _ = fxtwitter_page("search.json", discovery("spacex"))

        self.assertEqual(page.loss, ())
        self.assertEqual(
            [record.loss for record in page.records],
            [("third_party_archive",), ("third_party_archive",)],
        )


class XFxtwitterSearchTest(unittest.TestCase):
    """The one keyless X search in the roster, read as the operator answers it."""

    def setUp(self):
        self.page, self.opener = fxtwitter_page("search.json", discovery("spacex"))

    def test_the_page_speaks_for_the_route_that_answered(self):
        self.assertEqual(self.page.outcome, "ok")
        self.assertEqual(self.page.route_id, FXTWITTER_ROUTE)
        self.assertEqual(self.page.access_class, "K3")
        self.assertEqual(self.page.operator_identity, "fxtwitter")
        self.assertEqual(self.page.native_order, "fxtwitter_search_latest_order")
        self.assertEqual(len(self.page.records), 2)

    def test_a_status_is_addressed_by_the_url_the_payload_published(self):
        reply = self.page.records[0]

        self.assertEqual(reply.canonical_content_kind, "post")
        self.assertEqual(reply.native_item_id, X_SEARCH_REPLY_ID)
        self.assertEqual(
            reply.canonical_locator,
            "https://x.com/Pre_Consensus/status/" + X_SEARCH_REPLY_ID,
        )
        self.assertEqual(reply.author, "Pre_Consensus")
        self.assertEqual(reply.published_at, "2026-08-17T14:38:22Z")
        self.assertEqual(reply.native_position, 0)

    def test_a_reply_names_the_status_it_answers(self):
        self.assertEqual(self.page.records[0].native_parent_id, X_SEARCH_PARENT_ID)
        self.assertEqual(self.page.records[1].native_parent_id, "")

    def test_a_view_count_nobody_reported_is_absent_and_never_zero(self):
        # `views` is `null` on the first row and an integer on the second. A
        # zero written for the first would be a number nobody reported.
        first = dict(self.page.records[0].engagement)
        second = dict(self.page.records[1].engagement)

        self.assertNotIn("views", first)
        self.assertEqual(second["views"], 20)

    def test_the_counts_are_the_operators_own_names_and_exact_integers(self):
        self.assertEqual(
            self.page.records[0].engagement,
            (("likes", 0), ("reposts", 0), ("replies", 0), ("quotes", 0), ("bookmarks", 0)),
        )

    def test_a_status_carries_the_operators_own_named_facts(self):
        carried = named(self.page.records[0])

        self.assertEqual(carried["lang"], "en")
        self.assertEqual(carried["source"], "Twitter for iPhone")
        # The platform's own spelling of the moment, beside the exact epoch the
        # record's instant was read from.
        self.assertEqual(carried["created_at"], "Mon Aug 17 14:38:22 +0000 2026")
        self.assertEqual(carried["is_note_tweet"], "true")
        self.assertEqual(carried["provider"], "twitter")
        self.assertEqual(carried["author.id"], "2073814671727968256")
        self.assertEqual(
            carried["replying_to.url"],
            "https://x.com/capybaraReborn/status/" + X_SEARCH_PARENT_ID,
        )

    def test_the_continuation_is_the_token_the_operator_published(self):
        self.assertEqual(
            self.page.cursor_out, payload_of(FXTWITTER_DIR, "search.json")["cursor"]["bottom"]
        )

    def test_the_two_rankings_are_two_operations_on_one_endpoint(self):
        top, opener = fxtwitter_page("search.json", discovery("search_top:spacex"))

        self.assertEqual(top.native_order, "fxtwitter_search_top_order")
        self.assertEqual(
            opener.opened[0].url,
            built_url(FXTWITTER_ROUTE, {"endpoint": "search", "q": "spacex", "feed": "top"}),
        )
        self.assertEqual(
            self.opener.opened[0].url,
            built_url(FXTWITTER_ROUTE, {"endpoint": "search", "q": "spacex", "feed": "latest"}),
        )


class XFxtwitterTimelineAndProfileTest(unittest.TestCase):
    """One handle's statuses, and the account itself."""

    def test_a_timeline_reads_the_profiles_statuses_collection(self):
        page, opener = fxtwitter_page("statuses.json", discovery("timeline:" + X_HANDLE))

        self.assertEqual(page.outcome, "ok")
        self.assertEqual(page.native_order, "fxtwitter_timeline_order")
        self.assertEqual(len(page.records), 2)
        self.assertEqual(page.records[0].native_item_id, X_ROOT_ID)
        self.assertEqual(page.records[1].native_parent_id, X_ROOT_ID)
        self.assertEqual(dict(page.records[0].engagement)["views"], 1169817)
        self.assertEqual(
            opener.opened[0].url,
            built_url(
                FXTWITTER_ROUTE,
                {"endpoint": "profile", "subject": X_HANDLE, "collection": "statuses"},
            ),
        )

    def test_a_timeline_surfaces_the_operators_own_continuation(self):
        page, _ = fxtwitter_page("statuses.json", discovery("timeline:" + X_HANDLE))

        self.assertEqual(
            page.cursor_out, payload_of(FXTWITTER_DIR, "statuses.json")["cursor"]["bottom"]
        )

    def test_an_account_is_a_profile_record_with_the_accounts_own_counts(self):
        page, opener = fxtwitter_page("profile.json", discovery("user:" + X_HANDLE))

        self.assertEqual(page.outcome, "ok")
        self.assertEqual(page.native_order, "fxtwitter_profile_order")
        self.assertEqual(len(page.records), 1)
        record = page.records[0]
        self.assertEqual(record.canonical_content_kind, "profile")
        self.assertEqual(record.native_item_id, X_PROFILE_ID)
        self.assertEqual(record.canonical_locator, "https://x.com/" + X_HANDLE)
        self.assertEqual(record.author, X_HANDLE)
        self.assertEqual(record.title, X_HANDLE)
        self.assertEqual(
            record.engagement,
            (
                ("followers", 41906741),
                ("following", 127),
                ("likes", 528),
                ("media_count", 4593),
                ("statuses", 11649),
            ),
        )
        self.assertEqual(
            opener.opened[0].url,
            built_url(FXTWITTER_ROUTE, {"endpoint": "profile", "subject": X_HANDLE}),
        )

    def test_an_account_states_one_moment_and_it_is_read_without_a_locale(self):
        # `Thu Apr 23 21:53:30 +0000 2009` — the month is numbered before the
        # format is read, so a process that set `LC_TIME` still gets the time.
        page, _ = fxtwitter_page("profile.json", discovery("user:" + X_HANDLE))

        self.assertEqual(page.records[0].published_at, "2009-04-23T21:53:30Z")
        self.assertEqual(
            named(page.records[0])["joined"], "Thu Apr 23 21:53:30 +0000 2009"
        )

    def test_an_account_carries_its_own_named_facts_under_their_key_paths(self):
        page, _ = fxtwitter_page("profile.json", discovery("user:" + X_HANDLE))
        carried = named(page.records[0])

        self.assertEqual(carried["location"], "Earth")
        self.assertEqual(carried["protected"], "false")
        self.assertEqual(carried["website.url"], "http://spacex.com")
        self.assertEqual(carried["verification.verified"], "true")
        self.assertEqual(carried["verification.type"], "organization")


class XFxtwitterConversationTest(unittest.TestCase):
    """One status and everything under it, with the root read exactly once."""

    def setUp(self):
        self.page, self.opener = fxtwitter_page("conversation.json", hydration(X_ROOT_ID))

    def test_the_root_is_carried_once_though_the_payload_states_it_twice(self):
        # The payload puts the root under `status` and again at the head of its
        # own `thread`. Reading both would emit one status twice under one id.
        self.assertEqual(self.page.outcome, "ok")
        self.assertEqual(len(self.page.records), 3)
        self.assertEqual(
            [record.native_item_id for record in self.page.records].count(X_ROOT_ID), 1
        )
        self.assertEqual(self.page.records[0].native_item_id, X_ROOT_ID)

    def test_every_reply_names_the_root_it_answers_and_keeps_its_own_counts(self):
        replies = self.page.records[1:]

        for reply in replies:
            with self.subTest(status=reply.native_item_id):
                self.assertEqual(reply.native_parent_id, X_ROOT_ID)
        # A reply never inherits the root's counts.
        self.assertEqual(dict(self.page.records[0].engagement)["likes"], 8505)
        self.assertEqual(dict(replies[0].engagement)["likes"], 27)
        self.assertEqual(dict(replies[1].engagement)["likes"], 26)

    def test_a_conversation_surfaces_no_continuation_and_spends_none(self):
        # The payload states a `cursor.bottom` here too, and spending it under
        # the name the two listing operations take answered 404 three times out
        # of three on 2026-08-17. A token whose spelling nobody proved is not
        # surfaced, so the core never spends a call of its own on a refusal.
        self.assertEqual(self.page.cursor_out, "")

        carried = adapters.AdapterRequest(
            step_id="s1-social", target_ids=(X_ROOT_ID,), cursor="whatever-the-payload-said"
        )
        _, opener = fxtwitter_page("conversation.json", carried)

        self.assertEqual(
            opener.opened[0].url,
            built_url(FXTWITTER_ROUTE, {"endpoint": "conversation", "subject": X_ROOT_ID}),
        )

    def test_a_conversation_with_no_thread_is_read_from_its_status_alone(self):
        payload = payload_of(FXTWITTER_DIR, "conversation.json")
        payload["thread"] = None
        page, _ = answered(
            x_fxtwitter, FXTWITTER_ROUTE, json.dumps(payload), hydration(X_ROOT_ID)
        )

        self.assertEqual(len(page.records), 3)
        self.assertEqual(page.records[0].native_item_id, X_ROOT_ID)


class XFxtwitterAnswersWithNoStatusTest(unittest.TestCase):
    """The six ways this operator answers with nothing, told apart.

    Two of them arrive at HTTP 200 with a code of the operator's own inside
    the body. A 404 there is a subject it holds nothing for, which is an
    absence; anything else there is the status the read got, one layer in.
    Neither is drift: the envelope is the shape this module declares.
    """

    def test_an_empty_results_list_is_an_absence_and_says_so(self):
        page, _ = fxtwitter_page("search_empty.json", discovery("nothing matches this"))

        self.assertEqual(page.outcome, "empty")
        self.assertEqual(page.loss, ())
        self.assertEqual(page.records, ())
        self.assertIn("results", " ".join(page.warnings))

    def test_an_empty_answer_surfaces_no_continuation_it_did_not_earn(self):
        # This envelope states a token on every answer and states no "there is
        # more" of its own, so relaying one off an answer with nothing in it
        # would be this module claiming a next page the operator never claimed.
        page, _ = fxtwitter_page("search_empty.json", discovery("nothing matches this"))

        self.assertTrue(payload_of(FXTWITTER_DIR, "search_empty.json")["cursor"]["bottom"])
        self.assertEqual(page.cursor_out, "")

    def test_every_container_that_moved_is_drift_and_never_an_absence(self):
        for name, request, spoken in (
            ("search_reshaped.json", discovery("spacex"), "results"),
            ("profile_reshaped.json", discovery("user:" + X_HANDLE), "user"),
            ("conversation_reshaped.json", hydration(X_ROOT_ID), "status"),
        ):
            with self.subTest(fixture=name):
                page, _ = fxtwitter_page(name, request)

                self.assertEqual(page.outcome, "failed")
                self.assertEqual(page.loss, ("schema_drift",))
                self.assertEqual(page.records, ())
                self.assertIn(spoken, " ".join(page.warnings))
                self.assertIn("changed shape", " ".join(page.warnings))

    def test_rows_that_name_no_id_are_drift_and_never_an_empty_search(self):
        page, _ = fxtwitter_page("search_unidentified.json", discovery("spacex"))

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.loss, ("schema_drift",))
        self.assertIn("no id on any of them", " ".join(page.warnings))

    def test_a_body_that_is_not_json_at_two_hundred_is_malformed(self):
        page, _ = answered(x_fxtwitter, FXTWITTER_ROUTE, "<html>nope", discovery("spacex"))

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.loss, ("malformed_json",))

    def test_a_status_line_that_is_not_two_hundred_is_the_status_it_is(self):
        for name, status, request in (
            ("bad_request_400.json", 400, hydration("abc")),
            ("not_found_404.json", 404, discovery("user:nobody")),
            ("statuses_not_found_404.json", 404, discovery("timeline:nobody")),
            ("conversation_not_found_404.json", 404, hydration(X_ROOT_ID)),
        ):
            with self.subTest(fixture=name):
                page, _ = fxtwitter_page(name, request, status=status)

                self.assertEqual(page.outcome, "failed")
                self.assertEqual(page.loss, ("http_status",))
                self.assertIn(str(status), " ".join(page.warnings))

    def test_a_not_found_inside_a_two_hundred_is_an_absence_in_the_operators_words(self):
        page, _ = fxtwitter_page("code_404_in_200.json", discovery("user:nobody"))

        self.assertEqual(page.outcome, "empty")
        self.assertEqual(page.loss, ())
        self.assertEqual(page.records, ())
        self.assertIn("code 404", " ".join(page.warnings))
        self.assertIn("User not found", " ".join(page.warnings))

    def test_any_other_code_inside_a_two_hundred_is_the_status_it_names(self):
        page, _ = fxtwitter_page("code_500_in_200.json", discovery("spacex"))

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.loss, ("http_status",))
        self.assertIn("code 500", " ".join(page.warnings))
        self.assertIn("Upstream error", " ".join(page.warnings))

    def test_the_same_body_at_two_layers_is_typed_the_same_way_twice(self):
        # `not_found_404.json` and `code_404_in_200.json` are the same bytes.
        # At HTTP 404 the read never arrived, and at HTTP 200 the operator
        # answered about a subject it holds nothing for. Both are honest
        # readings, and neither is drift.
        outer, _ = fxtwitter_page("not_found_404.json", discovery("user:nobody"), status=404)
        inner, _ = fxtwitter_page("code_404_in_200.json", discovery("user:nobody"))

        self.assertEqual(outer.loss, ("http_status",))
        self.assertEqual(inner.outcome, "empty")
        self.assertNotIn("schema_drift", outer.loss + inner.loss)


class XFxtwitterGrammarTest(unittest.TestCase):
    """Which of five operations a step reaches, and what a step naming none means."""

    def test_a_caller_names_the_operation_and_the_argument_survives_it(self):
        for named_step, expected in (
            ("search:spacex", (x_fxtwitter.SEARCH_OPERATION, "spacex")),
            ("search_top:spacex", (x_fxtwitter.SEARCH_TOP_OPERATION, "spacex")),
            ("timeline:" + X_HANDLE, (x_fxtwitter.TIMELINE_OPERATION, X_HANDLE)),
            ("user:" + X_HANDLE, (x_fxtwitter.USER_OPERATION, X_HANDLE)),
            ("conversation:" + X_ROOT_ID, (x_fxtwitter.CONVERSATION_OPERATION, X_ROOT_ID)),
        ):
            with self.subTest(step=named_step):
                self.assertEqual(x_fxtwitter.operation_for(discovery(named_step)), expected)
                # A conversation is reachable from either shape of step, which
                # is what freezing a hit and asking for it again means.
                self.assertEqual(x_fxtwitter.operation_for(hydration(named_step)), expected)

    def test_absent_a_prefix_the_steps_own_shape_decides(self):
        self.assertEqual(
            x_fxtwitter.operation_for(discovery("spacex")),
            (x_fxtwitter.SEARCH_OPERATION, "spacex"),
        )
        self.assertEqual(
            x_fxtwitter.operation_for(hydration(X_ROOT_ID)),
            (x_fxtwitter.CONVERSATION_OPERATION, X_ROOT_ID),
        )

    def test_nothing_is_inferred_from_the_characters_in_an_argument(self):
        # A query of digits is a query, not a status id; a handle written as a
        # query is a query, not a timeline.
        self.assertEqual(
            x_fxtwitter.operation_for(discovery(X_ROOT_ID)),
            (x_fxtwitter.SEARCH_OPERATION, X_ROOT_ID),
        )
        self.assertEqual(
            x_fxtwitter.operation_for(discovery("https://x.com/SpaceX")),
            (x_fxtwitter.SEARCH_OPERATION, "https://x.com/SpaceX"),
        )

    def test_a_cursor_is_spent_only_on_the_operations_that_proved_one(self):
        for step, params in (
            (
                "search:spacex",
                {"endpoint": "search", "q": "spacex", "feed": "latest", "cursor": "NEXT"},
            ),
            (
                "search_top:spacex",
                {"endpoint": "search", "q": "spacex", "feed": "top", "cursor": "NEXT"},
            ),
            (
                "timeline:" + X_HANDLE,
                {
                    "endpoint": "profile",
                    "subject": X_HANDLE,
                    "collection": "statuses",
                    "cursor": "NEXT",
                },
            ),
            ("user:" + X_HANDLE, {"endpoint": "profile", "subject": X_HANDLE}),
        ):
            with self.subTest(step=step):
                request = adapters.AdapterRequest(
                    step_id="s1-social", query=step, cursor="NEXT"
                )
                _, opener = fxtwitter_page("search_empty.json", request)

                self.assertEqual(opener.opened[0].url, built_url(FXTWITTER_ROUTE, params))

    def test_one_call_reads_one_page_and_nothing_else(self):
        _, opener = fxtwitter_page("search.json", discovery("spacex"))

        self.assertEqual(len(opener.opened), 1)


class XFxtwitterFieldOmittedTest(unittest.TestCase):
    """A row short of what this adapter declares says so, beside its standing loss."""

    def test_a_status_with_no_stamp_carries_both_losses(self):
        payload = payload_of(FXTWITTER_DIR, "search.json")
        del payload["results"][0]["created_timestamp"]
        page, _ = answered(
            x_fxtwitter, FXTWITTER_ROUTE, json.dumps(payload), discovery("spacex")
        )

        self.assertEqual(page.outcome, "ok")
        self.assertEqual(page.records[0].published_at, "")
        self.assertEqual(page.records[0].loss, ("third_party_archive", "field_omitted"))
        # The standing half never depends on what the row carried.
        self.assertEqual(page.records[1].loss, ("third_party_archive",))

    def test_a_profile_with_no_join_stamp_carries_both_losses(self):
        payload = payload_of(FXTWITTER_DIR, "profile.json")
        payload["user"]["joined"] = "some time in 2009"
        page, _ = answered(
            x_fxtwitter, FXTWITTER_ROUTE, json.dumps(payload), discovery("user:" + X_HANDLE)
        )

        self.assertEqual(page.records[0].published_at, "")
        self.assertEqual(page.records[0].loss, ("third_party_archive", "field_omitted"))

