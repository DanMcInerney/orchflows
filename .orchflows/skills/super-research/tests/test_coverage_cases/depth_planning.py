"""Depth-planning checks for the coverage seam."""

from __future__ import annotations

import unittest

from super_research import adapters, coverage, runner
from super_research.adapters import youtube_innertube
from tests.test_coverage_cases.common import record


class DepthPlanTest(unittest.TestCase):
    def test_a_paging_operation_gives_discovery_steps(self):
        """`next` is a step per video, addressed in the query and not in a hit.

        A discovery step forbids `selected_hits`, so the target rides in the
        query under the operation's own name — which is where
        `youtube_innertube.operation_for` reads it from on a step that names no
        target — and one video per step is what keeps each step's cap its own.
        """

        rows = [
            record("y1", "youtube_innertube", native_item_id="a", locator="https://x.invalid/a"),
            record("y2", "youtube_innertube", native_item_id="b", locator="https://x.invalid/b"),
        ]

        plan = coverage.plan_depth(rows, "youtube_innertube", "next", "nx", max_items=50)

        self.assertEqual([held.query for held in plan.steps], ["next:a", "next:b"])
        self.assertEqual([held.selected_hits for held in plan.steps], [(), ()])
        self.assertEqual(len({held.step_id for held in plan.steps}), 2)
        self.assertEqual(plan.skipped, ())

    def test_a_single_call_operation_gives_a_hydration_step(self):
        """`player` answers in one call, so the older shape is still the right one."""

        rows = [
            record("y1", "youtube_innertube", native_item_id="a", locator="https://x.invalid/a"),
            record("y2", "youtube_innertube", native_item_id="b", locator="https://x.invalid/b"),
        ]

        plan = coverage.plan_depth(rows, "youtube_innertube", "player", "pl", max_items=5)

        self.assertEqual(len(plan.steps), 1)
        self.assertEqual(
            [hit.target_id for hit in plan.steps[0].selected_hits], ["player:a", "player:b"]
        )

    def test_the_kind_is_the_one_the_core_pages(self):
        """The criterion is the core's own predicate, not the string it returns.

        `runner._offers_another_page` is what decides whether a continuation is
        ever spent, so a step planned for a paging operation is one that
        function answers `True` for. Asserting `kind == "discovery"` here would
        pin this module's spelling against itself and prove nothing about
        whether page two is reached.
        """

        rows = [record("y1", "youtube_innertube", native_item_id="a")]
        paging = coverage.plan_depth(rows, "youtube_innertube", "next", "nx", 50).steps[0]
        single = coverage.plan_depth(rows, "youtube_innertube", "player", "pl", 50).steps[0]
        offering = adapters.build_native_page(
            youtube_innertube.DESCRIPTOR, (), cursor_out="A_CONTINUATION_TOKEN"
        )

        self.assertTrue(runner._offers_another_page(paging, offering, 1, 1))
        self.assertFalse(runner._offers_another_page(single, offering, 1, 1))

    def test_a_transcript_cap_under_two_is_refused(self):
        """Page one is the video's own record; the cues are on page two.

        `kept < max_items` is the clause that buys the second page, so a
        transcript step capped at one reaches no cue and reports success.
        """

        rows = [record("y1", "youtube_innertube", native_item_id="a")]

        with self.assertRaises(coverage.CoverageError) as raised:
            coverage.plan_depth(rows, "youtube_innertube", "transcript", "tx", 1)

        self.assertIn("page two", str(raised.exception))
        self.assertEqual(len(coverage.plan_depth(rows, "youtube_innertube", "transcript", "tx", 2).steps), 1)

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

    def test_youtube_targets_the_native_id_under_the_named_operation(self):
        plan = coverage.plan_depth(
            [record("y1", "youtube_innertube", native_item_id="4jZjM0Zs_LY")],
            "youtube_innertube",
            "transcript",
            "tx",
            max_items=400,
        )

        self.assertEqual(plan.steps[0].query, "transcript:4jZjM0Zs_LY")

    def test_records_off_the_adapter_are_listed_and_never_silently_dropped(self):
        """The leftovers are returned, for `relevance.partition`'s reason.

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

    def test_an_unaddressable_record_is_skipped_rather_than_addressed_by_the_other_id(self):
        """A missing native id is never quietly replaced by the locator.

        Guessing which id a route meant is how a hydration lands on the wrong
        item and still looks authorized.
        """

        plan = coverage.plan_depth(
            [record("y1", "youtube_innertube", native_item_id="")],
            "youtube_innertube",
            "player",
            "pl",
            max_items=5,
        )

        self.assertEqual(plan.steps[0].selected_hits, ())
        self.assertIn("native item id", plan.skipped[0].reason)

    def test_an_undeclared_adapter_or_operation_is_refused(self):
        with self.assertRaises(coverage.CoverageError):
            coverage.plan_depth([], "stocktwits", "comments", "s", 10)
        with self.assertRaises(coverage.CoverageError):
            coverage.plan_depth([], "youtube_innertube", "captions", "s", 10)

    def test_a_cap_that_is_not_a_positive_integer_is_refused(self):
        with self.assertRaises(coverage.CoverageError):
            coverage.plan_depth([], "youtube_innertube", "player", "s", 0)
