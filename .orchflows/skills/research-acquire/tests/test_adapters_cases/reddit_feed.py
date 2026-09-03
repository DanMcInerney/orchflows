from tests.test_adapters_cases.feed_page_routes import *  # noqa: F401,F403

REDDIT_FEED_FIXTURE_DIR = TEST_DIR / "fixtures" / "reddit_feed"
REDDIT_PERMALINK = (
    "https://www.reddit.com/r/LocalLLaMA/comments/1abc234/"
    "what_is_the_best_local_model_right_now/"
)
REDDIT_POST_ID = "t3_1abc234"


def read_reddit_feed(name):
    return REDDIT_FEED_FIXTURE_DIR.joinpath(name).read_text(encoding="utf-8")


def reddit_feed_cases():
    return tuple(json.loads(read_reddit_feed("feed_cases.json"))["cases"])


def feed_request(subreddit=REDDIT_SUBREDDIT):
    return adapters.AdapterRequest(step_id="s1-feed", target_ids=(subreddit,))


def feed_page(fixture, status=200, subreddit=REDDIT_SUBREDDIT, module=None):
    """Run the feed adapter over one canned answer; return its page and the opener."""

    reader = reddit_feed if module is None else module
    clock = helpers.FakeClock()
    carrier, opener = helpers.offline_transport(
        clock,
        {
            transport.REDDIT_FEED_ROUTE: (
                status,
                read_reddit_feed(fixture),
                "application/atom+xml",
            )
        },
    )
    return (reader.fetch_native_page(carrier, feed_request(subreddit)), opener)


def feed_roster_row(record):
    """One entry's roster row, named as the 2026-08-10 probes name it."""

    return {
        "title": record.title,
        "link": record.canonical_locator,
        "author": record.author,
        "updated": record.published_at,
    }


class RedditFeedTest(unittest.TestCase):
    """The freshness probe, and the four fields it is allowed to have.

    The 2026-08-10 probes recorded `www.reddit.com/r/<sub>.rss` at 200, 32 KB, 1.4 s,
    returning title, link, author and updated — and nothing else. Reddit's own
    `.json` surfaces answered 403 to three unrelated User-Agents from three
    hosts, which is IP-class blocking rather than a header problem, so this is
    the only Reddit surface in the package and there is nothing to fall back to.

    What this half exists to prevent is an engagement number nobody reported.
    Every other Reddit route in the roster carries `score`, `num_comments` and
    `upvote_ratio`, and this one carries none: a caller ranking a feed entry on
    a zero would be ranking on a fact this package made up, which is the defect
    T07's craft pass caught in the other direction.
    """

    def test_one_page_carries_the_entries_the_feed_listed(self):
        page, opener = feed_page("subreddit_new.xml")

        self.assertEqual(len(page.records), 3)
        self.assertEqual(page.outcome, "ok")
        self.assertEqual(len(opener.opened), 1)

    def test_every_entry_carries_every_field_its_roster_row_names(self):
        page, _ = feed_page("subreddit_new.xml")

        for record in page.records:
            with self.subTest(entry=record.native_item_id):
                row = feed_roster_row(record)

                for name in REDDIT_FEED_FIELDS:
                    self.assertNotEqual(row[name], "", name)

    def test_an_entry_names_the_post_its_author_and_the_moment_reddit_reported(self):
        page, _ = feed_page("subreddit_new.xml")
        first = page.records[0]

        self.assertEqual(first.title, "What is the best local model right now?")
        self.assertEqual(first.canonical_locator, REDDIT_PERMALINK)
        # The handle, not the path fragment Reddit writes it inside. The `/u/`
        # prefix addresses a page; the handle is who wrote the post, and it is
        # what Reddit's other surface in this roster reports.
        self.assertEqual(first.author, "harbourlight")
        self.assertEqual(first.published_at, "2026-08-10T08:41:03Z")
        self.assertEqual(first.canonical_content_kind, "post")
        self.assertEqual(first.native_position, 0)

    def test_a_post_keeps_the_fullname_reddit_identifies_it_by(self):
        # wrong_merge_law rule 6: the `t3_` prefix is part of platform
        # identity, so it stays where the `/u/` prefix goes — one is an
        # identifier and the other is a path. This is also the exact spelling
        # the archive adapter produces, which is what lets a caller tie a
        # freshness hit to a hydration of the same post.
        page, _ = feed_page("subreddit_new.xml")

        self.assertEqual(
            [record.native_item_id for record in page.records],
            [REDDIT_POST_ID, "t3_1abc999", "t3_1abd001"],
        )
        self.assertEqual(
            page.native_identity_namespace, reddit_archive.DESCRIPTOR.native_identity_namespace
        )

    def test_the_entries_arrive_in_the_order_the_feed_listed_them(self):
        page, _ = feed_page("subreddit_new.xml")

        self.assertEqual(
            [record.native_position for record in page.records], [0, 1, 2]
        )
        self.assertEqual(
            [record.published_at for record in page.records],
            ["2026-08-10T08:41:03Z", "2026-08-10T07:12:44Z", "2026-08-09T23:05:00Z"],
        )

    def test_no_entry_carries_an_engagement_number_of_any_kind(self):
        # The roster row is four fields and this route publishes no fifth. A
        # zero here would be indistinguishable from a post nobody has voted on,
        # which is a different and checkable thing on the archive route.
        page, _ = feed_page("subreddit_new.xml")

        for record in page.records:
            with self.subTest(entry=record.native_item_id):
                self.assertEqual(record.engagement, ())
        self.assertEqual(reddit_feed.DESCRIPTOR.comment_count_metric, "")
        self.assertEqual(reddit_feed.DESCRIPTOR.reply_count_metric, "")
        self.assertIn("engagement_unavailable", reddit_feed.DESCRIPTOR.standing_loss)

    def test_the_absence_of_a_count_is_stated_on_every_record_it_is_true_of(self):
        # Standing rather than per-record, because it is true of every entry
        # this route will ever return.
        page, _ = feed_page("subreddit_new.xml")

        for record in page.records:
            with self.subTest(entry=record.native_item_id):
                self.assertIn("engagement_unavailable", record.loss)

    def test_a_subreddit_that_published_nothing_is_empty_and_not_a_feed_that_moved(self):
        page, _ = feed_page("subreddit_empty.xml", subreddit="EmptyPlaceHolder")

        self.assertEqual(page.records, ())
        self.assertEqual(page.outcome, "empty")
        self.assertEqual(page.loss, ())
        self.assertIn("no entry", " ".join(page.warnings))

    def test_a_body_carrying_no_feed_at_all_is_drift_and_not_a_quiet_subreddit(self):
        page, _ = feed_page("subreddit_reshaped.xml")

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.loss, ("schema_drift",))
        self.assertEqual(page.records, ())

    def test_an_entry_short_of_a_roster_field_says_so_and_is_never_dated_from_the_read(self):
        page, _ = feed_page("entry_missing_updated.xml")
        complete, short = page.records

        self.assertEqual(short.published_at, "")
        self.assertIn("field_omitted", short.loss)
        self.assertNotIn("field_omitted", complete.loss)
        # And the moment it was read is not quietly promoted into the moment it
        # was published: an entry with no time has no time.
        self.assertNotEqual(short.published_at, page.observed_at)

    def test_the_subreddit_is_read_from_the_target_or_from_the_query(self):
        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(
            clock,
            {
                transport.REDDIT_FEED_ROUTE: (
                    200,
                    read_reddit_feed("subreddit_new.xml"),
                    "application/atom+xml",
                )
            },
        )

        reddit_feed.fetch_native_page(
            carrier, adapters.AdapterRequest(step_id="s1", query=REDDIT_SUBREDDIT)
        )

        self.assertEqual(
            opener.opened[0].url,
            "https://www.reddit.com/r/" + REDDIT_SUBREDDIT + ".rss",
        )

    def test_the_page_speaks_for_reddit_at_the_class_the_ladder_gives_it(self):
        page, _ = feed_page("subreddit_new.xml")

        self.assertEqual(page.adapter_id, "reddit_feed")
        self.assertEqual(page.access_class, "K0")
        self.assertEqual(page.platform, "reddit")
        self.assertEqual(page.operator_identity, "reddit")
        # A syndication feed is its own representation. It is not the platform's
        # full native record — it carries four fields and no engagement — and
        # `REPRESENTATION_KINDS` has had a name for that all along.
        self.assertEqual(page.representation_kind, "feed")
        self.assertEqual(page.route_id, transport.REDDIT_FEED_ROUTE)


class RedditFeedDescriptorTest(unittest.TestCase):
    """The tightest ceiling in the roster, declared where the scheduler reads it."""

    def test_the_route_declares_the_ceiling_the_evidence_measured(self):
        budget = runner.route_budgets()[transport.REDDIT_FEED_ROUTE]

        # The 2026-08-10 probes: four requests back to back answered 1x 200 then
        # 3x 429; after a thirty-second cooldown, paced one per six seconds, it
        # answered 2x 200 and then 429ed again; a custom UA changed nothing.
        # The effective ceiling is 1–2 per ~30 s per IP, and a client that
        # respects a limit takes the floor of a measured range.
        self.assertEqual(budget.min_interval_ms, 30000)
        self.assertEqual(budget.burst, 1)
        self.assertEqual(budget.cooldown_ms, 30000)
        # T04 seeded these three numbers as a replay constant before this route
        # existed. Asserting the identity rather than the values a second time
        # is what stops the seed and the shipped descriptor drifting apart.
        self.assertEqual(budget, test_pipeline.REDDIT_FEED_BUDGET)

    def test_it_admits_fewer_reads_in_a_minute_than_any_other_route_in_the_roster(self):
        # "Tightest ceiling" is not the longest interval — GitHub's is twice as
        # long — it is how few reads a route admits at all. GitHub spends its
        # hour as one bucket of sixty, so a minute buys sixty-one reads there
        # and three here. That factor of twenty is the whole reason the cache
        # is a correctness requirement rather than an optimization, and it is
        # what a budget of 30 s at a burst of one actually means.
        budgets = runner.route_budgets()
        admitted = {
            route_id: budget.burst + 60000 // budget.min_interval_ms
            for route_id, budget in budgets.items()
        }
        ranked = sorted(admitted.items(), key=lambda pair: (pair[1], pair[0]))

        self.assertEqual(ranked[0], (transport.REDDIT_FEED_ROUTE, 3))
        # Unique, and not merely equal-lowest: the runner-up admits at least
        # four times as many reads in the same minute. It was seven until
        # 2026-09-01, when GDELT joined with the origin's own stated ceiling
        # of one read per five seconds — thirteen a minute — and became the
        # runner-up this margin is measured against.
        self.assertGreaterEqual(ranked[1][1], ranked[0][1] * 4)
        self.assertGreater(ranked[1][1], ranked[0][1])

    def test_it_declares_neither_engagement_metric_because_the_route_reports_none(self):
        self.assertEqual(reddit_feed.DESCRIPTOR.comment_count_metric, "")
        self.assertEqual(reddit_feed.DESCRIPTOR.reply_count_metric, "")

    def test_it_declares_no_rotating_identifier_because_it_depends_on_none(self):
        self.assertEqual(reddit_feed.DESCRIPTOR.volatile_identifiers, ())

    def test_the_core_can_reach_it_by_both_of_its_literal_branches(self):
        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(
            clock,
            {
                transport.REDDIT_FEED_ROUTE: (
                    200,
                    read_reddit_feed("subreddit_new.xml"),
                    "application/atom+xml",
                )
            },
        )

        self.assertIn("reddit_feed", runner.ADAPTER_IDS)
        self.assertIs(runner.descriptor_for("reddit_feed"), reddit_feed.DESCRIPTOR)
        page = runner.call_adapter("reddit_feed", carrier, feed_request())

        self.assertEqual(len(page.records), 3)
        self.assertEqual(len(opener.opened), 1)

    def test_the_only_reddit_surface_this_adapter_can_reach_is_the_feed(self):
        # There is no `.json` branch to find, because there is no `.json`
        # route: the one route this adapter names is the measured one, and a
        # refusal on it is never answered by asking somewhere else.
        self.assertEqual(
            [descriptor.route_id for descriptor in runner.surface_descriptors("reddit_feed")],
            [transport.REDDIT_FEED_ROUTE],
        )
        # Code strings, not prose: this module's docstring says out loud that
        # `.json` is blocked and why, and a paragraph cannot be put on a wire.
        # What matters is that no string constant here could become one.
        spelled = sorted(
            blocked
            for blocked in (".json", "old.reddit", "api.reddit")
            for spelling in code_strings(ADAPTER_DIR / "reddit_feed.py")
            if blocked in spelling
        )

        self.assertEqual(spelled, [])

    def test_the_code_for_a_missing_credential_is_declared_and_never_produced(self):
        # A 403 from a private community is Reddit declining this read, and
        # waiting or asking about a public community clears it. Typing it as a
        # missing credential would report a documented keyless route as one
        # this package cannot use without an account.
        self.assertEqual(reddit_feed.AUTH_REQUIRED, "auth_required")
        self.assertEqual(names_read(ADAPTER_DIR / "reddit_feed.py", "AUTH_REQUIRED"), 0)


def typed_reddit_feed_pages(module):
    return {
        row["case_name"]: feed_page(
            row["body_fixture"],
            status=row["status"],
            subreddit=row["subreddit"],
            module=module,
        )[0]
        for row in reddit_feed_cases()
    }


def assert_a_freshness_probe_reports_only_freshness(case, adapter_id, pages):
    """Row 3's oracle: four fields, no fifth, and no route but the measured one.

    Three confusions, each a different wrong thing to believe. An engagement
    number on a feed entry is a fact nobody reported. A refusal read as a
    missing credential turns the roster's tightest budget into a capability
    this package does not have. And an answer typed as anything other than
    what its own evidence names sends a reader to the wrong place entirely.
    """

    for row in reddit_feed_cases():
        name = row["case_name"]
        case.assertIn(name, pages, "{0} produced no page for case {1}".format(adapter_id, name))
        page = pages[name]
        loss = tuple(page.loss)
        detail = " {0} typed case {1} as outcome {2} loss {3}".format(
            adapter_id, name, page.outcome, loss
        )

        for record in page.records:
            if record.engagement:
                case.fail(
                    "a freshness probe reported engagement {0} the route does not"
                    " publish:{1}".format(record.engagement, detail)
                )
        if reddit_feed.AUTH_REQUIRED in loss:
            case.fail("a documented keyless route was called credentialed:" + detail)
        case.assertEqual(
            page.outcome,
            row["expected_outcome"],
            "case {0} came back {1}, its evidence says {2}".format(
                name, page.outcome, row["expected_outcome"]
            ),
        )
        case.assertEqual(
            loss, (row["expected_loss"],) if row["expected_loss"] else (), detail
        )


class RedditFeedIsOnlyAFreshnessProbeTest(unittest.TestCase):
    """Row 3, over every answer this route can give."""

    def test_every_measured_case_is_typed_as_its_evidence_says(self):
        assert_a_freshness_probe_reports_only_freshness(
            self, "reddit_feed", typed_reddit_feed_pages(None)
        )

    def test_the_two_rows_the_evidence_measured_are_marked_as_measured(self):
        # The case table mixes a measurement with this adapter's own declared
        # handling, and which is which has to survive being read later.
        measured = sorted(row["case_name"] for row in reddit_feed_cases() if row["measured"])

        self.assertEqual(measured, ["asked_for_fewer_requests", "newest_entries"])

    def test_a_refusal_to_slow_down_is_typed_and_never_substituted(self):
        # The measurement that made the run-local cache a correctness
        # requirement. An origin asking for fewer requests is an outcome, not
        # an invitation to ask a different Reddit host — and there is no other
        # Reddit host here to ask.
        page, opener = feed_page(
            "too_many_requests.txt", status=transport.RATE_LIMITED_STATUS
        )

        self.assertEqual(page.loss, (transport.RATE_LIMITED,))
        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.records, ())
        self.assertEqual(
            [call.route_id for call in opener.opened], [transport.REDDIT_FEED_ROUTE]
        )
