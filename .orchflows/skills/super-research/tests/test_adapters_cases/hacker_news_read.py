from tests.test_adapters_cases.hacker_news_github_routes import *  # noqa: F401,F403

HN_FIXTURE_DIR = TEST_DIR / "fixtures" / "hacker_news"

# The 2026-08-10 probes (carry-over routes): the three fields the evidence names the
# Firebase item route returning, named as the evidence names them rather than
# as a record spells them.
HN_ITEM_ROSTER_FIELDS = ("by", "descendants", "kids")
HN_COMMENT_ID = "44831402"
HN_ABSENT_ID = "44899999"
HN_PERMALINK = "https://news.ycombinator.com/item?id="


def read_hacker_news(name):
    """Read one offline Hacker News fixture."""

    return HN_FIXTURE_DIR.joinpath(name).read_text(encoding="utf-8")


def hacker_news_cases():
    """The measured case table: a request, a status, a body, and what it means."""

    return tuple(json.loads(read_hacker_news("item_cases.json"))["cases"])


def hn_request(query="", target_id="", cursor=""):
    return adapters.AdapterRequest(
        step_id="s1-hn",
        query=query,
        target_ids=(target_id,) if target_id else (),
        cursor=cursor,
    )


def hn_page(
    fixture,
    status=200,
    query="",
    target_id="",
    cursor="",
    content_type="application/json",
    module=None,
):
    """Run the adapter over one canned answer, with both surfaces seeded.

    Both routes answer, so a call that reached the wrong one is a wrong url
    rather than a missing fixture, and a call that reached both is two entries
    in one opener — which is what "two surfaces, never fused" is checked
    against.
    """

    clock = helpers.FakeClock()
    answer = (status, read_hacker_news(fixture), content_type)
    carrier, opener = helpers.offline_transport(
        clock,
        {
            transport.HN_ALGOLIA_SEARCH_ROUTE: answer,
            transport.HN_FIREBASE_ITEM_ROUTE: answer,
        },
    )
    reading = hacker_news if module is None else module
    return (
        reading.fetch_native_page(carrier, hn_request(query, target_id, cursor)),
        opener,
    )


def attribute_pairs(record, name):
    """Every value one record carries under one attribute name, in its own order."""

    return tuple(value for carried, value in record.attributes if carried == name)


class HackerNewsSearchTest(unittest.TestCase):
    """The half the prior spec did not have: HN, searchable.

    Firebase v0 lists and hydrates and cannot search at all, which is why the
    superseded spec's `hacker_news` adapter could only walk ids it was already
    given. Algolia is HN's own index of itself, and it is what makes a query
    answerable — so these checks read a query's answer, row by row, in the
    order the index listed them.
    """

    def test_a_step_naming_only_a_query_asks_the_endpoint_the_evidence_measured(self):
        _, opener = hn_page("algolia_search_by_date.json", query="local models")

        # The 2026-08-10 probes: `hn.algolia.com/api/v1/search_by_date` answered 200
        # with full-text HN search. A caller wanting relevance names `search:`.
        self.assertEqual(len(opener.opened), 1)
        self.assertEqual(opener.opened[0].route_id, transport.HN_ALGOLIA_SEARCH_ROUTE)
        self.assertEqual(
            urllib.parse.urlsplit(opener.opened[0].url).path, "/api/v1/search_by_date"
        )

    def test_comment_search_is_that_endpoint_asked_under_the_tag_that_selects_them(self):
        _, opener = hn_page("algolia_comment_search.json", query="comments:kv cache")
        asked = urllib.parse.urlsplit(opener.opened[0].url)

        # The 2026-08-10 probes: `.../search?tags=comment` answered 200 for comments.
        # `typoTolerance=false` rides on every search since 2026-08-17: the index
        # reaches `space` from `SpaceX` otherwise, and answered 849,432 hits to
        # that query where the exact one answers 67,207.
        self.assertEqual(asked.path, "/api/v1/search")
        self.assertEqual(
            sorted(urllib.parse.parse_qsl(asked.query)),
            [("query", "kv cache"), ("tags", "comment"), ("typoTolerance", "false")],
        )

    def test_the_index_rows_arrive_in_the_order_the_index_listed_them(self):
        page, _ = hn_page("algolia_search_by_date.json", query="local models")

        self.assertEqual(page.outcome, "ok")
        self.assertEqual(
            [record.native_item_id for record in page.records],
            ["44831234", "44830011", "44829903", "44829502"],
        )
        self.assertEqual(
            [record.canonical_content_kind for record in page.records],
            ["story", "story", "comment", "story"],
        )
        self.assertEqual([record.native_position for record in page.records], [0, 1, 2, 3])

    def test_a_story_hit_carries_its_own_address_and_the_link_it_points_at(self):
        page, _ = hn_page("algolia_search_by_date.json", query="local models")
        story = page.records[0]

        # Two different things, and conflating them would merge every story
        # that ever linked to one article: the item's address is on HN, and the
        # link it points at is the story's own reported field.
        self.assertEqual(story.canonical_locator, HN_PERMALINK + "44831234")
        self.assertEqual(
            attribute_pairs(story, "url"), ("https://harbourlight.example/70b-two-gpus",)
        )
        self.assertEqual(story.title, "Running a 70B locally on two consumer GPUs")
        self.assertEqual(story.author, "kessel_run")
        self.assertEqual(story.published_at, "2026-08-09T16:41:52Z")

    def test_a_story_that_links_to_nothing_carries_its_own_text_and_no_link(self):
        page, _ = hn_page("algolia_search_by_date.json", query="local models")
        ask = page.records[1]

        self.assertEqual(attribute_pairs(ask, "url"), ())
        self.assertEqual(
            ask.body, "Mine was a cache key that stopped including the lockfile."
        )

    def test_a_comment_hit_names_the_parent_it_answers_and_no_title_of_its_own(self):
        page, _ = hn_page("algolia_search_by_date.json", query="local models")
        comment = page.records[2]

        self.assertEqual(comment.native_parent_id, "44829870")
        self.assertEqual(
            comment.body,
            "The two settings that mattered were batch size and the KV cache dtype.",
        )
        # Algolia reports the parent story's title on a comment. It is a fact
        # about the story, so it is not this record's title.
        self.assertEqual(comment.title, "")
        self.assertEqual(comment.engagement, ())

    def test_the_counts_a_hit_reports_travel_under_algolias_own_names(self):
        page, _ = hn_page("algolia_search_by_date.json", query="local models")

        self.assertEqual(counts_of(page.records[0]), {"points": 412, "num_comments": 233})
        self.assertEqual(counts_of(page.records[3]), {"points": 58, "num_comments": 12})

    def test_the_next_page_is_surfaced_for_the_core_and_never_followed(self):
        page, opener = hn_page("algolia_search_by_date.json", query="local models")

        # The index states how many pages it has, so the next one is its claim
        # and not this adapter's arithmetic about whether more exist.
        self.assertEqual(page.cursor_out, "1")
        self.assertEqual(len(opener.opened), 1)

    def test_the_last_page_the_index_states_surfaces_no_next_one(self):
        page, _ = hn_page("algolia_comment_search.json", query="comments:kv cache")

        self.assertEqual(page.cursor_out, "")
        self.assertEqual(len(page.records), 2)
        self.assertEqual(
            [record.canonical_content_kind for record in page.records],
            ["comment", "comment"],
        )

    def test_a_reply_names_the_comment_it_answers_and_the_story_it_sits_under(self):
        # Two different facts, and only one of them is `native_parent_id`: this
        # reply hangs off another comment, and the story it belongs to is the
        # index's own separate field.
        page, _ = hn_page("algolia_comment_search.json", query="comments:kv cache")
        reply = page.records[0]

        self.assertEqual(reply.native_parent_id, HN_COMMENT_ID)
        self.assertEqual(attribute_pairs(reply, "story_id"), (HN_STORY_ID,))

    def test_a_cursor_the_core_hands_back_is_spent_as_the_index_own_page(self):
        _, opener = hn_page(
            "algolia_search_by_date.json", query="local models", cursor="3"
        )

        self.assertEqual(len(opener.opened), 1)
        self.assertIn(("page", "3"), urllib.parse.parse_qsl(opener.opened[0].url.split("?")[1]))

    def test_rows_this_adapter_cannot_type_are_not_a_query_that_matched_nothing(self):
        # Two answers with no records and two different reasons. An index that
        # returned nothing matched nothing; an index that returned rows this
        # adapter cannot identify matched something it could not read, and
        # saying "matched nothing" there would hide a shape this package does
        # not handle behind an ordinary empty.
        unreadable, _ = hn_page("algolia_untypable_only.json", query="front page")
        matched, _ = hn_page("algolia_no_matches.json", query="a phrase")

        self.assertEqual(unreadable.outcome, "empty")
        self.assertEqual(unreadable.records, ())
        self.assertIn("2", " ".join(unreadable.warnings))
        self.assertNotIn("matched nothing", " ".join(unreadable.warnings))
        self.assertIn("matched nothing", " ".join(matched.warnings))

    def test_a_row_short_of_its_fields_says_so_and_a_row_of_no_type_is_not_a_row(self):
        page, _ = hn_page("algolia_partial_hit.json", query="short row")

        self.assertEqual(len(page.records), 1)
        self.assertEqual(page.records[0].loss, ("field_omitted",))
        # Zero is a count the index reported, not a field it left out.
        self.assertEqual(counts_of(page.records[0]), {"points": 0, "num_comments": 0})
        self.assertEqual(page.outcome, "ok")
        self.assertIn("1", " ".join(page.warnings))
        self.assertIn("no item type", " ".join(page.warnings))


class HackerNewsItemTest(unittest.TestCase):
    """The other surface: one item, its counts, and the tree under it.

    Firebase v0 is where a story's comment tree lives — `kids` is the only
    field in either surface that says which items hang off this one. The
    traversal itself is the core's: this adapter reads one item per call and
    hands back the ids, because walking them here would make one call a crawl.
    """

    def test_an_item_answer_carries_every_field_the_evidence_names(self):
        page, opener = hn_page("firebase_story.json", target_id=HN_STORY_ID)
        story = page.records[0]

        # The 2026-08-10 probes: `by`, `descendants`, and the `kids` tree.
        self.assertEqual(len(page.records), 1)
        self.assertEqual(story.author, "kessel_run")
        self.assertEqual(counts_of(story)["descendants"], 233)
        self.assertEqual(
            attribute_pairs(story, hacker_news.KIDS_KEY),
            ("44831402", "44831377", "44831301"),
        )
        self.assertEqual(len(opener.opened), 1)

    def test_the_item_is_asked_for_on_the_route_that_has_the_tree(self):
        _, opener = hn_page("firebase_story.json", target_id=HN_STORY_ID)

        self.assertEqual(opener.opened[0].route_id, transport.HN_FIREBASE_ITEM_ROUTE)
        self.assertEqual(
            urllib.parse.urlsplit(opener.opened[0].url).path,
            "/v0/item/" + HN_STORY_ID + ".json",
        )

    def test_an_item_states_its_kind_its_time_and_its_own_address(self):
        page, _ = hn_page("firebase_story.json", target_id=HN_STORY_ID)
        story = page.records[0]

        self.assertEqual(story.canonical_content_kind, "story")
        self.assertEqual(story.native_item_id, HN_STORY_ID)
        self.assertEqual(story.published_at, "2026-08-09T16:41:52Z")
        self.assertEqual(story.canonical_locator, HN_PERMALINK + HN_STORY_ID)
        self.assertEqual(counts_of(story)["score"], 412)

    def test_a_kid_read_by_its_own_id_names_the_item_it_hangs_off(self):
        page, _ = hn_page("firebase_comment.json", target_id="item:" + HN_COMMENT_ID)
        comment = page.records[0]

        self.assertEqual(comment.canonical_content_kind, "comment")
        self.assertEqual(comment.native_item_id, HN_COMMENT_ID)
        self.assertEqual(comment.native_parent_id, HN_STORY_ID)
        self.assertEqual(attribute_pairs(comment, hacker_news.KIDS_KEY), ("44831500",))
        # A comment reports no score and no descendant count, and neither is
        # invented as a zero here.
        self.assertEqual(counts_of(comment), {})

    def test_a_stamp_no_clock_can_hold_is_a_missing_time_and_not_a_crash(self):
        # Every wrong shape this route can send has to arrive as an answer,
        # because an adapter that raised would cost the core its one page and
        # the run its typed outcome. An epoch second past what a clock can
        # represent is the one value here that is not a string to be parsed.
        page, _ = hn_page("firebase_absurd_time.json", target_id="44831999")

        self.assertEqual(len(page.records), 1)
        self.assertEqual(page.records[0].published_at, "")
        self.assertEqual(page.records[0].loss, ("field_omitted",))
        self.assertEqual(page.outcome, "ok")

    def test_one_story_seen_on_both_surfaces_states_one_identity(self):
        # What makes the two surfaces one adapter: Algolia's `objectID` is HN's
        # own item id, so a search hit and an item read name the same thing and
        # will group on it rather than being two unrelated rows.
        found, _ = hn_page("algolia_search_by_date.json", query="local models")
        read, _ = hn_page("firebase_story.json", target_id=HN_STORY_ID)

        self.assertEqual(found.records[0].native_item_id, read.records[0].native_item_id)
        self.assertEqual(
            found.records[0].canonical_content_kind, read.records[0].canonical_content_kind
        )
        self.assertEqual(
            found.records[0].canonical_locator, read.records[0].canonical_locator
        )
        self.assertNotEqual(found.route_id, read.route_id)


