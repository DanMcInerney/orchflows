from tests.test_adapters_cases.instagram_behavior import *  # noqa: F401,F403

class InnerTubeSearchTest(unittest.TestCase):
    """Criterion 1, search: the platform's own results, keyless.

    The prior spec priced YouTube search behind an API key. Measured, one
    request under the web key youtube.com embeds in its own page source
    answers with the results themselves.
    """

    def setUp(self):
        self.page, self.opener = youtube_page(
            "search_results.json", target_id=YOUTUBE_SEARCH_TARGET
        )

    def test_one_page_carries_the_results_the_section_listed(self):
        self.assertEqual(self.page.outcome, "ok")
        self.assertEqual(self.page.loss, ())
        self.assertEqual(len(self.page.records), 5)
        self.assertEqual(len(self.opener.opened), 1)

    def test_a_result_names_the_video_its_channel_and_the_address_youtube_published(self):
        first = self.page.records[0]

        self.assertEqual(first.canonical_content_kind, "video")
        self.assertEqual(first.native_item_id, YOUTUBE_VIDEO_ID)
        self.assertEqual(first.title, "Running a 70B locally on two consumer GPUs")
        self.assertEqual(first.author, "Harbourlight Optics")
        # The address the payload published, resolved against the origin that
        # published it. YouTube writes it relative, so it is resolved where
        # hosts are spelled rather than composed here.
        self.assertEqual(
            first.canonical_locator, "https://www.youtube.com/watch?v=" + YOUTUBE_VIDEO_ID
        )
        self.assertEqual(first.native_position, 0)

    def test_a_row_that_is_not_a_video_is_not_read_as_one(self):
        # The section carries a shelf between the results. A parser that took
        # every row would report a heading as a video.
        self.assertEqual(
            [record.canonical_content_kind for record in self.page.records],
            ["video"] * 5,
        )
        self.assertEqual(
            [record.native_position for record in self.page.records], [0, 1, 2, 3, 4]
        )

    def test_a_count_the_route_wrote_for_a_reader_is_carried_and_never_parsed(self):
        # "1,284,553 views" and "2 weeks ago" are strings YouTube formatted for
        # a person. Turning either into a number or an instant would be this
        # package inventing a fact: the separators are locale-shaped, "1.2M" is
        # lossy, and "2 weeks ago" is only an instant if you read a clock. So
        # they travel verbatim, under the route's own names, and the record
        # states no engagement and no publication time at all.
        first = self.page.records[0]
        named = attributes_of(first)

        self.assertEqual(named[youtube_innertube.VIEW_COUNT_TEXT_KEY], ["1,284,553 views"])
        self.assertEqual(named[youtube_innertube.PUBLISHED_TIME_TEXT_KEY], ["2 weeks ago"])
        self.assertEqual(first.engagement, ())
        self.assertEqual(first.published_at, "")

    def test_the_continuation_is_surfaced_for_the_core_and_never_followed(self):
        self.assertEqual(
            self.page.cursor_out, "EpcDEgxsb2NhbCBtb2RlbHMaggNTQlNDQVE"
        )
        self.assertEqual(len(self.opener.opened), 1)

    def test_a_result_the_payload_left_incomplete_is_marked_and_never_filled(self):
        page, _ = youtube_page(
            "search_partial_result.json", target_id=YOUTUBE_SEARCH_TARGET
        )
        complete, partial = page.records

        self.assertEqual(page.outcome, "ok")
        self.assertEqual(complete.loss, ())
        self.assertEqual(partial.loss, ("field_omitted",))
        self.assertEqual(partial.author, "")
        self.assertEqual(attributes_of(partial), {})

    def test_a_row_the_payload_gave_no_video_id_is_not_a_result_at_all(self):
        # The third row of that fixture has a title and a channel and no id, so
        # it can be neither identified nor addressed. Keeping it would put a
        # record in the artifact that names nothing.
        page, _ = youtube_page(
            "search_partial_result.json", target_id=YOUTUBE_SEARCH_TARGET
        )

        self.assertEqual(len(page.records), 2)
        self.assertTrue(all(record.native_item_id for record in page.records))

    def test_the_query_is_read_from_the_target_or_from_the_step_that_searched(self):
        # A step naming a target is hydrating one; a step naming only a query
        # is searching. Neither is inferred from the argument's characters.
        for request in (
            adapters.AdapterRequest(step_id="s1-yt", target_ids=(YOUTUBE_SEARCH_TARGET,)),
            adapters.AdapterRequest(step_id="s1-yt", query="local models"),
        ):
            with self.subTest(request=request):
                page, opener = adapter_page(
                    youtube_innertube,
                    200,
                    read_youtube("search_results.json"),
                    content_type="application/json",
                    request=request,
                )

                self.assertTrue(opener.opened[0].url.endswith("/search"), opener.opened[0].url)
                self.assertEqual(
                    json.loads(opener.opened[0].body)["query"], "local models"
                )
                self.assertEqual(len(page.records), 5)


class InnerTubeCommentThreadTest(unittest.TestCase):
    """Criterion 1, next: comment threads, and the token that reaches them.

    The first call names a video and comes back with the watch page, whose
    comment section holds a token and no thread yet. The token is surfaced for
    the core to spend, exactly as a timeline cursor is: following it here would
    make one adapter call two reads.
    """

    def test_the_threads_are_read_when_the_header_arrives_as_its_own_command(self):
        """One answer carries the comment section in more than one piece.

        The header — the comment count and the sort control — is its own
        `reloadContinuationItemsCommand` and arrives *before* the one holding
        the threads. Reading only the first command found returned a one-row
        header and typed a video with 1,292 comments as having none. Measured
        2026-08-17 on `next:4jZjM0Zs_LY`: entry 0 held one
        `commentsHeaderRenderer`, entry 1 held fourteen threads.
        """

        page, _ = youtube_page(
            "next_header_then_threads.json",
            target_id="next:" + YOUTUBE_VIDEO_ID,
            cursor=YOUTUBE_COMMENT_CURSOR,
        )

        self.assertEqual(page.outcome, "ok")
        self.assertEqual(len(page.records), 2)
        self.assertEqual(
            [record.body for record in page.records],
            ["bottom signal", "charting is astrology for men"],
        )
        # The token still comes off the row that carries it, whichever command
        # that row arrived under.
        self.assertEqual(page.cursor_out, "COMMENTS_PAGE_TWO")

    def test_a_page_past_the_second_arrives_under_the_append_action(self):
        """The third page's own container name, which paging stopped at.

        Page two arrives under `reloadContinuationItemsCommand`; the page after
        it arrives under `appendContinuationItemsAction`, the same spelling the
        `search` route uses. Measured 2026-08-17 on `next:__tEElLKowI`: page
        three answered 200 carrying
        `onResponseReceivedEndpoints[0].appendContinuationItemsAction` and
        nothing else, while this module scanned for
        `appendContinuationItemsCommand` — a spelling no route was measured
        sending — so a page holding real threads came back as no list at all and
        `_comments_page` typed it `schema_drift`. Depth ran to page two and then
        reported a platform failure that had not happened.
        """

        page, _ = youtube_page(
            "next_append_action_page.json",
            target_id="next:" + YOUTUBE_VIDEO_ID,
            cursor=YOUTUBE_COMMENT_CURSOR,
        )

        self.assertEqual(page.outcome, "ok")
        self.assertEqual(page.loss, ())
        self.assertEqual(
            [record.body for record in page.records],
            ["third page, still reading", "and the page after this one is still offered"],
        )
        # The token off the row this page carried, so page four is reachable the
        # same way page three was.
        self.assertEqual(page.cursor_out, "COMMENTS_PAGE_FOUR")

    def test_a_page_under_an_undeclared_container_name_is_typed_drift(self):
        """The scan admits the names measured and not whatever looks like a list.

        Built beside the tree rather than by editing the fixture: the same
        payload twice, once under the container name page three was measured
        arriving in and once under a spelling no route sends. A parser that
        matched any key holding `continuationItems` would read the second and
        report a page the platform never served in that shape, which is the
        failure the per-route tuple guards and the reason it lists measured
        names only.

        Both halves are asserted because either alone proves little. The
        measured half is what makes this a can-fail — one key name is the whole
        difference between an `ok` page of two records and a refusal — and the
        renamed half is asserted at the page the caller receives rather than at
        the item scan under it, so a change that let an unread list conclude
        `ok` with no records would fail here instead of passing under a name
        promising the opposite.
        """

        renamed = json.loads(read_youtube("next_append_action_page.json"))
        endpoint = renamed[youtube_innertube.RECEIVED_ENDPOINTS_KEY][0]
        endpoint["appendContinuationItemsCommand"] = endpoint.pop(
            "appendContinuationItemsAction"
        )

        measured, _ = youtube_comments_page(
            json.loads(read_youtube("next_append_action_page.json"))
        )
        drifted, _ = youtube_comments_page(renamed)

        self.assertEqual(measured.outcome, "ok")
        self.assertEqual(len(measured.records), 2)

        self.assertEqual(drifted.outcome, "failed")
        self.assertEqual(drifted.loss, ("schema_drift",))
        self.assertEqual(drifted.records, ())

    def test_a_call_spending_the_token_carries_the_threads_it_returned(self):
        page, opener = youtube_page(
            "next_comment_threads.json",
            target_id="next:" + YOUTUBE_VIDEO_ID,
            cursor=YOUTUBE_COMMENT_CURSOR,
        )

        self.assertEqual(page.outcome, "ok")
        self.assertEqual(page.loss, ())
        self.assertEqual(len(page.records), 3)
        self.assertEqual(len(opener.opened), 1)
        self.assertEqual(
            json.loads(opener.opened[0].body)["continuation"], YOUTUBE_COMMENT_CURSOR
        )

    def test_a_comment_names_itself_its_author_the_video_and_its_reply_count(self):
        page, _ = youtube_page(
            "next_comment_threads.json",
            target_id="next:" + YOUTUBE_VIDEO_ID,
            cursor=YOUTUBE_COMMENT_CURSOR,
        )
        first = page.records[0]

        self.assertEqual(first.canonical_content_kind, "comment")
        self.assertEqual(first.native_item_id, "UgxK1rTn9pQwLmXaZ4h4AaABAg")
        self.assertEqual(first.native_parent_id, YOUTUBE_VIDEO_ID)
        self.assertEqual(first.author, "@northsea.dev")
        # The runs are one text the route split at its own formatting, so they
        # join back into the comment rather than into a list of fragments.
        self.assertEqual(
            first.body,
            "The two settings were n_batch and rope scaling, not the quantisation.",
        )
        self.assertEqual(dict(first.engagement), {youtube_innertube.REPLY_COUNT_METRIC: 14})
        self.assertEqual(first.native_position, 0)

    def test_a_vote_count_the_route_abbreviated_is_carried_and_never_parsed(self):
        # "1.2K" is not a number this route reported; it is a number it
        # rounded for a reader. Reading 1200 off it would be a count nobody
        # published, and the record would rank against exact ones.
        page, _ = youtube_page(
            "next_comment_threads.json",
            target_id="next:" + YOUTUBE_VIDEO_ID,
            cursor=YOUTUBE_COMMENT_CURSOR,
        )
        named = attributes_of(page.records[0])

        self.assertEqual(named[youtube_innertube.VOTE_COUNT_TEXT_KEY], ["1.2K"])
        self.assertEqual(named[youtube_innertube.PUBLISHED_TIME_TEXT_KEY], ["3 days ago"])
        self.assertNotIn(
            youtube_innertube.VOTE_COUNT_TEXT_KEY, dict(page.records[0].engagement)
        )

    def test_a_comment_carries_no_publication_time_because_the_route_states_none(self):
        # "3 days ago" is an interval from a moment this package did not
        # observe. Turning it into an instant needs a wall clock, and a record
        # dated from the read would look exactly as fresh as the read.
        page, _ = youtube_page(
            "next_comment_threads.json",
            target_id="next:" + YOUTUBE_VIDEO_ID,
            cursor=YOUTUBE_COMMENT_CURSOR,
        )

        for record in page.records:
            with self.subTest(item=record.native_item_id):
                self.assertEqual(record.published_at, "")

    def test_a_comment_carries_no_address_because_the_payload_publishes_none(self):
        page, _ = youtube_page(
            "next_comment_threads.json",
            target_id="next:" + YOUTUBE_VIDEO_ID,
            cursor=YOUTUBE_COMMENT_CURSOR,
        )

        self.assertEqual([record.canonical_locator for record in page.records], [""] * 3)

    def test_the_next_continuation_is_surfaced_for_the_core(self):
        page, _ = youtube_page(
            "next_comment_threads.json",
            target_id="next:" + YOUTUBE_VIDEO_ID,
            cursor=YOUTUBE_COMMENT_CURSOR,
        )

        self.assertEqual(page.cursor_out, YOUTUBE_COMMENT_CURSOR)

    def test_the_first_call_names_the_video_and_comes_back_holding_only_the_token(self):
        page, opener = youtube_page(
            "next_watch_page.json", target_id="next:" + YOUTUBE_VIDEO_ID
        )

        self.assertEqual(page.outcome, "empty")
        self.assertEqual(page.loss, ())
        self.assertEqual(page.records, ())
        self.assertEqual(page.cursor_out, YOUTUBE_COMMENT_CURSOR)
        self.assertIn("comment", " ".join(page.warnings))
        self.assertEqual(json.loads(opener.opened[0].body)["videoId"], YOUTUBE_VIDEO_ID)
        self.assertEqual(len(opener.opened), 1)


class YoutubeCommentsOffTest(unittest.TestCase):
    """A video nobody may comment on, which is an answer and not a broken read.

    Measured 2026-08-17, side by side, through this package's own transport.
    `next:DPhzzkjiD9s` answered 200 with four watch-next renderers whose last
    is an `itemSectionRenderer` carrying `comment-item-section` and the token.
    `next:yLY0LGmBTt8` answered 200 with three renderers —
    `videoPrimaryInfoRenderer`, `videoSecondaryInfoRenderer`,
    `compositeVideoPrimaryInfoRenderer` — and no `itemSectionRenderer` at all.
    Both well formed. The second was typed `schema_drift`, so a three-video
    depth read returned `yt-comments-1 failed loss ('schema_drift',)` and
    `coverage.review_artifact` reported `step_carried_loss`, obliging the
    calling lane to state a payload change that had not happened.

    `protocol.md` reserves `schema_drift` for a payload arriving in a shape
    this parser does not know, so that an empty result would have been a lie.
    Here the empty is the truth, and the shape this parser does not know is
    the other absence: the watch-next container itself gone.
    """

    def test_a_video_with_comments_off_answers_empty(self):
        page, _ = youtube_page(
            "next_comments_off.json", target_id="next:" + YOUTUBE_VIDEO_ID
        )

        self.assertEqual(page.outcome, "empty")
        self.assertEqual(page.loss, ())
        self.assertEqual(page.records, ())
        # No section, so no token: there is no second call to make, and
        # surfacing one would send the core after a page nobody offered.
        self.assertEqual(page.cursor_out, "")

    def test_the_warning_states_what_was_absent(self):
        """An empty carries its own news, and the news is the video's.

        The page below and the first call on a video with comments both answer
        empty with no loss, so the warning is the only place a reader learns
        which one this was. Naming the `comment-item-section` here would name
        a container the answer did not carry, and `_drifted`'s sentence would
        say the payload moved when it did not.
        """

        page, _ = youtube_page(
            "next_comments_off.json", target_id="next:" + YOUTUBE_VIDEO_ID
        )
        with_a_token, _ = youtube_page(
            "next_watch_page.json", target_id="next:" + YOUTUBE_VIDEO_ID
        )
        said = " ".join(page.warnings)

        self.assertIn("lists no comment", said)
        # `_drifted`'s own sentence, which no page answering `empty` may carry.
        self.assertNotIn("changed shape", said)
        self.assertNotIn(youtube_innertube.COMMENT_SECTION_IDENTIFIER, said)
        # The other empty still says what it is, so the two stay tellable
        # apart by the one thing either of them returns.
        self.assertIn(
            youtube_innertube.COMMENT_SECTION_IDENTIFIER, " ".join(with_a_token.warnings)
        )

    def test_a_missing_container_is_still_drift(self):
        """The absence that is not the video's, which the branch above widens past.

        Both payloads are built beside the fixture rather than by editing it,
        because what is asserted is the difference between them and the page
        that reads whole: the same watch page with the container this module
        walks removed, and a continuation call answering with an endpoint list
        and no container either. Neither states anything about comments, so
        neither can be read as a video that has none — calling either empty
        would report a comment section nobody looked in as one nobody wrote
        in, which is the reading `schema_drift` exists to prevent.
        """

        no_container = json.loads(read_youtube("next_comments_off.json"))
        del no_container[youtube_innertube.WATCH_NEXT_PATH[0]]

        gone, _ = youtube_comments_page(no_container)
        neither, _ = youtube_comments_page(
            {youtube_innertube.RECEIVED_ENDPOINTS_KEY: []}
        )

        for page in (gone, neither):
            with self.subTest(warning=page.warnings):
                self.assertEqual(page.outcome, "failed")
                self.assertEqual(page.loss, ("schema_drift",))
                self.assertEqual(page.records, ())
