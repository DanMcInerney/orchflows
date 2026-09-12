"""Depth-planning checks for the coverage seam."""

from __future__ import annotations

import unittest

from super_research import adapters, coverage, runner
from super_research.adapters import hacker_news
from tests.test_coverage_cases.common import record


class DepthPlanTest(unittest.TestCase):
    def test_native_items_share_one_hydration_step_and_never_spend_continuations(self):
        rows = [record("h1", "hacker_news", native_item_id="101"),
                record("h2", "hacker_news", native_item_id="202")]
        planned = coverage.plan_depth(rows, "hacker_news", "tree", "trees", 40)
        self.assertEqual(len(planned.steps), 1)
        self.assertEqual([hit.target_id for hit in planned.steps[0].selected_hits], ["tree:101", "tree:202"])
        self.assertEqual(planned.skipped, ())
        offering = adapters.build_native_page(hacker_news.DESCRIPTOR, (), cursor_out="next")
        self.assertFalse(runner._offers_another_page(planned.steps[0], offering, 1))

    def test_a_reddit_permalink_is_the_target_and_is_not_taken_apart(self):
        """Reddit's comments grammar takes the permalink a row carried.

        Re-deriving `<subreddit>/<post id>` here would be this module parsing
        an address the adapter already parses, and a second parser is a second
        thing to get wrong.
        """

        permalink = "https://www.reddit.com/r/Bitcoin/comments/1vos2t2/just_sold_it_all"
        plan = coverage.plan_depth(
            [record("r1", "reddit_shreddit", locator=permalink)],
            "reddit_shreddit",
            "comments",
            "cm",
            max_items=40,
        )

        self.assertEqual(plan.steps[0].kind, "hydration")
        self.assertEqual(plan.steps[0].adapter_id, "reddit_shreddit")
        self.assertEqual(len(plan.steps[0].selected_hits), 1)
        self.assertEqual(plan.steps[0].selected_hits[0].target_id, "comments:" + permalink)
        # The locator is what ties the hydration back to its discovery, so it
        # rides verbatim and is never recomposed.
        self.assertEqual(plan.steps[0].selected_hits[0].discovery_locator, permalink)
        self.assertEqual(plan.skipped, ())


    def test_records_off_the_adapter_are_listed_and_never_silently_dropped(self):
        """The leftovers are returned.

        A selection whose leftovers were never listed is a silent drop wearing
        a plan's clothes.
        """

        plan = coverage.plan_depth(
            [record("a", "reddit_shreddit"), record("b", "hacker_news")],
            "reddit_shreddit",
            "comments",
            "cm",
            max_items=40,
        )

        self.assertEqual(len(plan.steps[0].selected_hits), 1)
        self.assertEqual([held.record_id for held in plan.skipped], ["b"])
        self.assertIn("off adapter hacker_news", plan.skipped[0].reason)

    def test_feed_carried_reddit_permalink_is_accepted_without_relaxing_identity_checks(self):
        permalink = "https://www.reddit.com/r/BitcoinMarkets/comments/abc/daily"
        source = record("feed1", "rss_atom", locator=permalink, representation_kind="feed")
        planned = coverage.plan_depth([source], "reddit_shreddit", "comments", "depth", 10)
        hit, = planned.steps[0].selected_hits
        self.assertEqual(hit.discovery_locator, permalink)
        self.assertEqual(hit.target_id, "comments:" + permalink)
        for locator in ("http://www.reddit.com/r/BitcoinMarkets/comments/abc/daily",
                        "https://www.reddit.com.evil.example/r/BitcoinMarkets/comments/abc/daily",
                        "https://user@www.reddit.com/r/BitcoinMarkets/comments/abc/daily",
                        "https://www.reddit.com:8443/r/BitcoinMarkets/comments/abc/daily",
                        permalink + "?other=post", permalink + "#other", "https://www.reddit.com/r/BitcoinMarkets"):
            with self.subTest(locator=locator):
                row = record("feed1", "rss_atom", locator=locator, representation_kind="feed")
                refused = coverage.plan_depth([row], "reddit_shreddit", "comments", "depth", 10)
                self.assertFalse(refused.steps[0].selected_hits)
                self.assertEqual([item.record_id for item in refused.skipped], ["feed1"])

    def test_the_callers_own_limit_is_reported_as_the_reason_it_stopped(self):
        rows = [record("r%d" % index, "reddit_shreddit", locator="u%d" % index) for index in range(5)]

        plan = coverage.plan_depth(rows, "reddit_shreddit", "comments", "cm", 40, limit=2)

        self.assertEqual(len(plan.steps[0].selected_hits), 2)
        self.assertEqual(len(plan.skipped), 3)
        self.assertTrue(all("limit" in held.reason for held in plan.skipped))

    def test_a_record_already_hydrated_is_not_hydrated_again(self):
        plan = coverage.plan_depth(
            [
                record(
                    "h1",
                    "reddit_shreddit",
                    discovery_locator="https://example.invalid/parent",
                    representation_kind="native",
                )
            ],
            "reddit_shreddit",
            "comments",
            "cm",
            max_items=40,
        )

        self.assertEqual(plan.steps[0].selected_hits, ())
        self.assertEqual(plan.skipped[0].reason, "already hydrated")

    def test_missing_native_id_never_falls_back_to_a_url(self):
        planned = coverage.plan_depth([record("h1", "hacker_news", native_item_id="")],
                                      "hacker_news", "tree", "trees", 40)
        self.assertEqual(planned.steps[0].selected_hits, ())
        self.assertIn("native item id", planned.skipped[0].reason)

    def test_missing_locator_cannot_create_unlinkable_hydration(self):
        planned = coverage.plan_depth([record("h1", "hacker_news", locator="")],
                                      "hacker_news", "tree", "trees", 40)
        self.assertEqual(planned.steps[0].selected_hits, ())
        self.assertIn("normalized locator", planned.skipped[0].reason)

    def test_undeclared_depth_route_or_operation_is_refused(self):
        for adapter, operation in (("github_rest", "comments"), ("hacker_news", "captions"),
                                   ("x_fxtwitter", "user")):
            with self.subTest(adapter=adapter, operation=operation), self.assertRaises(coverage.CoverageError):
                coverage.plan_depth([], adapter, operation, "depth", 10)

    def test_invalid_cap_or_limit_is_refused(self):
        for cap, limit in ((0, 0), (-1, 0), (1, -1), (True, 0), (1.5, 0), (1, True), (1, 0.5)):
            with self.subTest(cap=cap, limit=limit), self.assertRaises(coverage.CoverageError):
                coverage.plan_depth([], "hacker_news", "tree", "depth", cap, limit)
