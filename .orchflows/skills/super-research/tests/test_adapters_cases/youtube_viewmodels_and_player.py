from tests.test_adapters_cases.youtube_search_and_comments import *  # noqa: F401,F403

VIEW_MODEL_FIXTURE = "next_comment_view_models.json"


def assert_the_old_shape_reads(case, page):
    """The preservation oracle's own body, so a wrong adapter can meet it too.

    Held apart from the test that runs it because a criterion which passes
    before the change it guards has to be shown rejecting something, and the
    only honest way to show that is to run these same assertions over a result
    built beside the tree.
    """

    case.assertEqual(page.outcome, "ok")
    case.assertEqual(
        [record.body for record in page.records],
        ["bottom signal", "charting is astrology for men"],
    )
    case.assertEqual(
        [dict(record.engagement) for record in page.records],
        [
            {youtube_innertube.REPLY_COUNT_METRIC: 4},
            {youtube_innertube.REPLY_COUNT_METRIC: 0},
        ],
    )
    case.assertEqual(
        attributes_of(page.records[0])[youtube_innertube.VOTE_COUNT_TEXT_KEY], ["272"]
    )


def view_model_page(fixture=VIEW_MODEL_FIXTURE):
    """One `next` answer in the shape the platform now serves, read as comments."""

    return youtube_page(
        fixture, target_id="next:" + YOUTUBE_VIDEO_ID, cursor=YOUTUBE_COMMENT_CURSOR
    )[0]


class YoutubeCommentViewModelTest(unittest.TestCase):
    """The second shape a `next` answer serves its threads in.

    Measured 2026-08-17 on `next:4jZjM0Zs_LY`, page two: 13
    `commentThreadRenderer`s and **zero** carrying `comment.commentRenderer`,
    the path the old reader walks. The thread now carries a view model whose
    `commentKey` addresses that thread's `commentEntityPayload` among the 66
    entity-store mutations beside it, and the fields — author, body, id, counts
    — live on that entity. `next_comment_view_models.json` is that answer
    trimmed to three of those threads: the `28`/`29` row, the `6`/`7` row whose
    `replyCount` states `"3"`, and the `" "`/`1` row of a comment nobody liked.
    """

    def test_one_record_per_thread(self):
        # Four rows, three of them threads: the filter-context row the platform
        # ships beside them costs a loop iteration and never a record.
        page = view_model_page()

        self.assertEqual(page.outcome, "ok")
        self.assertEqual(len(page.records), 3)
        self.assertEqual([record.native_position for record in page.records], [0, 1, 2])
        self.assertEqual(
            [record.canonical_content_kind for record in page.records], ["comment"] * 3
        )
        self.assertEqual(
            [record.native_parent_id for record in page.records], [YOUTUBE_VIDEO_ID] * 3
        )

    def test_fields_come_from_the_named_entity(self):
        # The view model states a key and nothing else worth carrying; every
        # field is read off the entity that key addresses, in the order the
        # threads arrived rather than the order the mutations did.
        page = view_model_page()

        self.assertEqual(
            [record.author for record in page.records],
            ["@DeltaLumineux", "@ErikTheGrateful", "@BertoClipper"],
        )
        # `properties.content.content` is a plain string, not a runs holder:
        # a reader that went through `route_text` would carry every body empty.
        self.assertEqual(page.records[0].body, "Nicd")
        self.assertEqual(page.records[1].body, "Crypto channel is back?")
        self.assertEqual(
            [record.native_item_id for record in page.records],
            [
                "UgyyGmQFMmFbbTn5MfN4AaABAg",
                "UgyralckDuyMxNLY-7h4AaABAg",
                "UgyUiK-OZOBU_EFG0cp4AaABAg",
            ],
        )
        self.assertEqual(page.loss, ())
        self.assertEqual([record.loss for record in page.records], [()] * 3)
        # A reply count only where the field states digits. `""` is what this
        # route writes for a thread with no replies, and zero-filling it would
        # publish a count the origin never stated.
        self.assertEqual(
            [dict(record.engagement) for record in page.records],
            [{}, {youtube_innertube.REPLY_COUNT_METRIC: 3}, {}],
        )
        self.assertEqual(
            [
                attributes_of(record)[youtube_innertube.PUBLISHED_TIME_KEY]
                for record in page.records
            ],
            [["1 day ago"], ["3 days ago"], ["2 days ago"]],
        )

    def test_the_count_is_never_the_liked_one(self):
        # `likeCountLiked` is the count *if you liked it* — every row's
        # `likeCountNotliked` plus one. Reading it inflates all thirteen
        # measured rows by exactly one, and turns a comment nobody liked into
        # one with a like. The signed-out count rides verbatim, `" "` included:
        # it is what the origin wrote for zero, and it is not parsed into one.
        page = view_model_page()
        carried = [
            attributes_of(record)[youtube_innertube.LIKE_COUNT_NOTLIKED_KEY]
            for record in page.records
        ]

        self.assertEqual(carried, [[" "], ["6"], ["28"]])
        for record in page.records:
            with self.subTest(item=record.native_item_id):
                named = attributes_of(record)
                self.assertNotIn("likeCountLiked", named)
                self.assertNotIn("likeCountA11y", named)
                self.assertNotIn(
                    youtube_innertube.LIKE_COUNT_NOTLIKED_KEY, dict(record.engagement)
                )

    def test_an_unresolved_thread_is_marked(self):
        # A key addressing nothing in the store this answer carried is a thread
        # whose fields did not arrive, not a thread that is not there. Dropping
        # it would report fewer comments than the platform listed, so it stays
        # a record and says what it is short of.
        page = view_model_page("next_view_model_without_entity.json")

        self.assertEqual(page.outcome, "ok")
        self.assertEqual(len(page.records), 2)
        self.assertEqual(page.records[0].loss, ())
        self.assertEqual(page.records[1].loss, ("field_omitted",))
        self.assertEqual(page.records[1].body, "")
        self.assertEqual(page.records[1].engagement, ())
        self.assertEqual(page.records[1].attributes, ())

    def test_an_answer_with_no_mutation_list_is_drift(self):
        # The threads arrived and the store they point into did not: that is
        # the payload having moved, and typing it as an empty page would report
        # a video with comments as having none.
        page = view_model_page("next_view_models_no_entity_store.json")

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.loss, ("schema_drift",))
        self.assertEqual(page.records, ())

    def test_the_old_shape_still_reads(self):
        # `comment.commentRenderer` is still what the header-then-threads
        # capture carries, and this change is additive: the old walk is
        # unchanged and its fixture is untouched.
        assert_the_old_shape_reads(self, view_model_page("next_header_then_threads.json"))

    def test_the_old_shape_oracle_rejects_an_adapter_that_dropped_it(self):
        """And the reading above is worth something, which needs showing.

        This is the one criterion here that passed before the change it guards
        — a preservation oracle that failed at the baseline would be guarding
        nothing — so its discrimination comes from a wrong adapter kept beside
        the tree rather than from the executor's own red. `old_shape_dropped`
        believes a comment's fields live in the entity store only; the same
        assertions run over its page, and reject it.
        """

        wrong = load_adapter_fixture("old_shape_dropped_adapter", YOUTUBE_FIXTURE_DIR)
        page, _ = adapter_page(
            wrong,
            200,
            read_youtube("next_header_then_threads.json"),
            content_type="application/json",
            request=youtube_request(
                "next:" + YOUTUBE_VIDEO_ID, cursor=YOUTUBE_COMMENT_CURSOR
            ),
        )

        self.assertEqual(page.records, ())
        with self.assertRaises(AssertionError):
            assert_the_old_shape_reads(self, page)
        # And the same adapter leaves the shape this item added alone, so the
        # rejection above is the older shape's loss and nothing else.
        page, _ = adapter_page(
            wrong,
            200,
            read_youtube(VIEW_MODEL_FIXTURE),
            content_type="application/json",
            request=youtube_request(
                "next:" + YOUTUBE_VIDEO_ID, cursor=YOUTUBE_COMMENT_CURSOR
            ),
        )

        self.assertEqual(len(page.records), 3)


class InnerTubePlayerTest(unittest.TestCase):
    """Criterion 1, player: the three fields the evidence measured, and no fourth."""

    def setUp(self):
        self.page, self.opener = youtube_page("player_metadata.json")

    def test_one_page_carries_the_one_video_this_operation_asks_for(self):
        self.assertEqual(self.page.outcome, "ok")
        self.assertEqual(len(self.page.records), 1)
        self.assertEqual(len(self.opener.opened), 1)

    def test_the_record_carries_every_field_its_roster_row_names(self):
        record = self.page.records[0]
        carried = {
            "title": record.title,
            "viewCount": dict(record.engagement).get(youtube_innertube.VIEW_COUNT_METRIC),
            "publishDate": record.published_at,
        }

        self.assertEqual(sorted(carried), sorted(YOUTUBE_PLAYER_ROSTER_FIELDS))
        for name in YOUTUBE_PLAYER_ROSTER_FIELDS:
            self.assertTrue(carried[name], name)
        self.assertEqual(carried["title"], "Running a 70B locally on two consumer GPUs")
        # An exact count the route published as digits, read as the integer it
        # is. "1,284,553 views" on the search row is a different thing and
        # stays a string.
        self.assertEqual(carried["viewCount"], 1284553)
        self.assertIsInstance(carried["viewCount"], int)
        self.assertEqual(carried["publishDate"], "2026-07-26T00:00:00Z")

    def test_a_video_nobody_has_watched_reported_a_count_and_it_is_zero(self):
        # The other direction of `field_omitted`, and the whole reason the mark
        # exists: the route reported the view count and it is zero. Marking
        # that omitted would say the payload was short when it was complete.
        # The same answer carries a full instant rather than a bare day, so
        # this record claims no precision it does not have and says nothing
        # about precision it does.
        page, _ = youtube_page("player_zero_views.json", target_id="player:Zk5xD1nQ9pL")
        record = page.records[0]

        self.assertEqual(dict(record.engagement), {youtube_innertube.VIEW_COUNT_METRIC: 0})
        self.assertEqual(record.published_at, "2026-08-10T08:55:00Z")
        self.assertEqual(record.loss, (youtube_innertube.ATTESTATION_REQUIRED,))

    def test_a_day_the_route_reported_is_a_day_and_the_record_says_so(self):
        # The route states a date and the artifact's instant carries seconds,
        # so the record reads midnight UTC and carries the precision it has
        # rather than letting a reader assume a video appeared at 00:00.
        record = self.page.records[0]

        self.assertIn("date_precision_only", record.loss)

    def test_the_record_names_the_video_and_the_address_the_payload_published(self):
        record = self.page.records[0]

        self.assertEqual(record.canonical_content_kind, "video")
        self.assertEqual(record.native_item_id, YOUTUBE_VIDEO_ID)
        self.assertEqual(record.author, "Harbourlight Optics")
        # The player payload publishes one address for the video and it is
        # already absolute, so it is carried as published rather than rebuilt.
        self.assertEqual(
            record.canonical_locator, "https://www.youtube.com/embed/" + YOUTUBE_VIDEO_ID
        )
        self.assertIn("benchmarks", record.body)

    def test_the_page_speaks_for_youtube_at_the_class_the_ladder_gives_it(self):
        self.assertEqual(self.page.adapter_id, "youtube_innertube")
        self.assertEqual(self.page.platform, "youtube")
        self.assertEqual(self.page.native_identity_namespace, "youtube")
        self.assertEqual(self.page.access_class, "K1")
        self.assertEqual(self.page.representation_kind, "native")
        self.assertEqual(self.page.route_id, transport.YOUTUBE_INNERTUBE_ROUTE)

    def test_a_bare_target_id_names_a_video_and_never_a_guess_at_its_shape(self):
        _, opener = youtube_page("player_metadata.json", target_id=YOUTUBE_VIDEO_ID)

        self.assertTrue(opener.opened[0].url.endswith("/player"), opener.opened[0].url)
        self.assertEqual(json.loads(opener.opened[0].body)["videoId"], YOUTUBE_VIDEO_ID)


class InnerTubeOperationSelectorTest(unittest.TestCase):
    """What the colon means here, which the docstring used to have backwards.

    It said a query containing a colon stays a query. It does not, when its
    first word is one of the three operation names — `player: sonata no. 14`
    reads as a `player` hydration of ` sonata no. 14`. What is true is the
    narrower rule, and both halves of it are pinned here so the sentence and
    the branch cannot part company again.
    """

    def test_a_colon_after_the_first_word_is_text(self):
        for query in ("ratio 16:9", "a plain query", "note: this is not an operation"):
            with self.subTest(query=query):
                self.assertEqual(
                    youtube_innertube.operation_for(
                        adapters.AdapterRequest(step_id="s1-yt", query=query)
                    ),
                    (youtube_innertube.SEARCH_OPERATION, query),
                )

    def test_one_of_the_three_names_before_the_first_colon_is_the_selector(self):
        for name in youtube_innertube.INNERTUBE_OPERATIONS:
            with self.subTest(operation=name):
                self.assertEqual(
                    youtube_innertube.operation_for(
                        adapters.AdapterRequest(
                            step_id="s1-yt", query=name + ": sonata no. 14"
                        )
                    ),
                    (name, " sonata no. 14"),
                )


class InnerTubeDescriptorTest(unittest.TestCase):
    """The descriptor T04's seam reads, and the identifier that rotates under it."""

    def test_the_route_is_paced_by_the_interval_the_evidence_measured(self):
        # The 2026-08-10 probes (YouTube): 1.4 s for search, which is the roster row's
        # declared ceiling. `next` at 2.2 s and `player` at 0.3 s are those
        # operations' latencies and not second ceilings: one route, one budget.
        descriptor = youtube_innertube.DESCRIPTOR

        self.assertEqual(descriptor.min_interval_ms, 1400)
        self.assertEqual(descriptor.burst, adapters.DEFAULT_BURST)
        self.assertEqual(descriptor.cooldown_ms, adapters.DEFAULT_COOLDOWN_MS)
        self.assertEqual(
            runner.route_budgets()[transport.YOUTUBE_INNERTUBE_ROUTE],
            runner.RouteBudget(min_interval_ms=1400, burst=1, cooldown_ms=60000),
        )

    def test_the_client_version_is_declared_rotating_with_a_way_back_to_a_current_one(self):
        declared = youtube_innertube.DESCRIPTOR.volatile_identifiers

        # Two clients rotate on this route since 2026-08-17: the web one every
        # operation but `player` presents, and the Android one `player` and the
        # transcript operation present because it is the one served caption
        # tracks. Each is a separate identifier with a separate procedure —
        # they rotate on separate schedules and are recovered from separate
        # places.
        self.assertEqual(len(declared), 2)
        self.assertIn(youtube_innertube.CLIENT_VERSION, declared[0].name)
        self.assertIn(youtube_innertube.CLIENT_NAME, declared[0].name)
        self.assertIn(youtube_innertube.PLAYER_CLIENT_VERSION, declared[1].name)
        self.assertIn(youtube_innertube.PLAYER_CLIENT_NAME, declared[1].name)
        # The procedure travels with the identifier rather than living
        # somewhere a reader would have to already know to look.
        recovery = declared[0].recovery
        self.assertIn("ytcfg", recovery)
        self.assertIn("INNERTUBE_CLIENT_VERSION", recovery)
        self.assertIn("_INNERTUBE_CLIENTS", declared[1].recovery)

    def test_the_client_version_goes_out_in_the_body_the_route_shapes(self):
        # `player` presents the Android client, which is the one served caption
        # tracks; `search` presents the web client whose key the route carries.
        # Both go out in the body the route shapes, and neither is anywhere a
        # caller could set.
        _, player_opener = youtube_page("player_metadata.json")
        played = json.loads(player_opener.opened[0].body)["context"]["client"]
        _, search_opener = youtube_page(
            "search_results.json", target_id=YOUTUBE_SEARCH_TARGET
        )
        searched = json.loads(search_opener.opened[0].body)["context"]["client"]

        self.assertEqual(played["clientName"], youtube_innertube.PLAYER_CLIENT_NAME)
        self.assertEqual(played["clientVersion"], youtube_innertube.PLAYER_CLIENT_VERSION)
        self.assertEqual(searched["clientName"], youtube_innertube.CLIENT_NAME)
        self.assertEqual(searched["clientVersion"], youtube_innertube.CLIENT_VERSION)

    def test_it_declares_the_reply_metric_it_reports_and_no_comment_metric(self):
        # A comment carries a count of its replies; nothing in these three
        # operations reports a count of comments on a video. Declaring the one
        # under both names would make two of the five views identical.
        self.assertEqual(
            youtube_innertube.DESCRIPTOR.reply_count_metric,
            youtube_innertube.REPLY_COUNT_METRIC,
        )
        self.assertEqual(youtube_innertube.DESCRIPTOR.comment_count_metric, "")

    def test_the_core_can_reach_it_by_both_of_its_literal_branches(self):
        self.assertIn("youtube_innertube", runner.ADAPTER_IDS)
        self.assertIs(
            runner.descriptor_for("youtube_innertube"), youtube_innertube.DESCRIPTOR
        )

        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(
            clock,
            {
                transport.YOUTUBE_INNERTUBE_ROUTE: (
                    200,
                    read_youtube("player_metadata.json"),
                    "application/json",
                )
            },
        )
        page = runner.call_adapter(
            "youtube_innertube", carrier, youtube_request("player:" + YOUTUBE_VIDEO_ID)
        )

        self.assertEqual(len(page.records), 1)
        self.assertEqual(len(opener.opened), 1)
