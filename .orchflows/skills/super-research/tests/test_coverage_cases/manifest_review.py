"""Manifest-review checks for the coverage seam."""

from __future__ import annotations

import unittest

from super_research import coverage, schema
from tests.test_coverage_cases.common import codes, manifest, step, subjects


class ReviewManifestTest(unittest.TestCase):
    def test_discovery_with_no_hydration_names_what_the_run_will_not_carry(self):
        """The 2026-08-17 YouTube case, caught before the run.

        `search:` was called and the report said "no transcripts, no view
        counts". The manifest was valid; the depth was never asked for.
        """

        found = coverage.review_manifest(
            manifest(step("yt", "discovery", "youtube_innertube", query="search:btc"))
        )

        self.assertEqual(subjects(found, coverage.DEPTH_NOT_PLANNED), ["youtube_innertube"])
        self.assertIn("transcripts", found[0].message)

    def test_planning_the_hydration_silences_it(self):
        found = coverage.review_manifest(
            manifest(
                step("yt", "discovery", "youtube_innertube", query="search:btc"),
                step(
                    "tx",
                    "hydration",
                    "youtube_innertube",
                    query="transcript",
                    selected_hits=(schema.SelectedHit("https://example.invalid/a", "transcript:a"),),
                ),
            )
        )

        self.assertNotIn(coverage.DEPTH_NOT_PLANNED, codes(found))

    def test_an_unwindowed_step_is_named_only_where_the_origin_would_have_bounded_it(self):
        """The 2026-08-17 news case, and the false positive it used to carry.

        `web_search` pushes Google News `when:` server-side, so omitting the
        window there is strictly wasteful. `prediction_markets` does not, and
        an unwindowed markets step is ordinarily deliberate — open markets
        closing next year are the point. Warning about both trained a reader
        to skip the line that mattered.
        """

        found = coverage.review_manifest(
            manifest(
                step("rd", "discovery", "reddit_shreddit", query="search:btc",
                     window_start="2026-07-18T00:00:00Z"),
                step("web", "discovery", "web_search", query="gnews:btc"),
                step("pm", "discovery", "prediction_markets", query="polymarket:btc"),
            )
        )

        self.assertEqual(subjects(found, coverage.WINDOW_ABSENT), ["web"])

    def test_no_window_anywhere_is_a_choice_and_draws_nothing(self):
        """An all-evergreen manifest is a legitimate shape, not an oversight.

        Windowing is per step and optional; a run that bounds nothing has
        decided that, and this check only fires on the inconsistency.
        """

        found = coverage.review_manifest(
            manifest(step("web", "discovery", "web_search", query="gnews:btc"))
        )

        self.assertNotIn(coverage.WINDOW_ABSENT, codes(found))

    def test_a_cap_under_the_page_size_is_named_before_the_read_not_during_it(self):
        found = coverage.review_manifest(
            manifest(step("bs", "discovery", "bluesky", query="search:btc", max_items=50))
        )

        self.assertIn(coverage.CAP_BELOW_PAGE_SIZE, codes(found))

    def test_a_depth_cap_under_the_floor_is_named_at_review_time_as_well(self):
        """The plan refuses this cap, and a hand-written manifest never met the plan.

        `evidence.md` §2, exactly: a `transcript:` step at max_items 1 is valid,
        passes review, runs, reaches no cue and reports success. `plan_depth`
        refuses it — but a manifest written by hand, or amended after planning,
        arrives at the review having never been through the plan, and the review
        already reads the row that carries the floor.
        """

        floor = coverage.DEPTH_TARGETS["youtube_innertube"]["transcript"].min_items
        under = coverage.review_manifest(
            manifest(
                step(
                    "tx", "discovery", "youtube_innertube",
                    query="transcript:vid", max_items=floor - 1,
                )
            )
        )

        self.assertEqual(codes(under), [coverage.CAP_BELOW_DEPTH_FLOOR])
        self.assertEqual(subjects(under, coverage.CAP_BELOW_DEPTH_FLOOR), ["tx"])
        # And silence at the floor itself, or the check would fire on every
        # lawful depth step the planner builds.
        self.assertEqual(
            coverage.review_manifest(
                manifest(
                    step(
                        "tx", "discovery", "youtube_innertube",
                        query="transcript:vid", max_items=floor,
                    )
                )
            ),
            (),
        )

    def test_an_ordinary_discovery_step_is_not_measured_against_a_depth_floor(self):
        """`search:` names no depth operation, so no row and no floor apply."""

        found = coverage.review_manifest(
            manifest(step("yt", "discovery", "youtube_innertube", query="search:btc", max_items=1))
        )

        self.assertNotIn(coverage.CAP_BELOW_DEPTH_FLOOR, codes(found))

    def test_a_clean_manifest_draws_nothing(self):
        """The check that keeps the others honest: silence is reachable."""

        found = coverage.review_manifest(
            manifest(
                step("hn", "discovery", "hacker_news", query="search:btc", max_items=1000,
                     window_start="2026-07-18T00:00:00Z"),
                step(
                    "tree",
                    "hydration",
                    "hacker_news",
                    query="tree",
                    selected_hits=(schema.SelectedHit("https://example.invalid/a", "tree:1"),),
                ),
            )
        )

        self.assertEqual(found, ())
