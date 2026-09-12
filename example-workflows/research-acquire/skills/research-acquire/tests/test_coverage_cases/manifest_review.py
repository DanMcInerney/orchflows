"""Manifest-review checks for the coverage seam."""

from __future__ import annotations

import unittest

from super_research import coverage, schema
from tests.test_coverage_cases.common import codes, manifest, step, subjects


class ReviewManifestTest(unittest.TestCase):


    def test_an_unwindowed_step_is_named_only_where_the_origin_would_have_bounded_it(self):
        """Native search can bound its results; a supplied feed cannot bound its entries."""

        found = coverage.review_manifest(
            manifest(
                step("rd", "discovery", "reddit_shreddit", query="search:btc",
                     window_start="2026-07-18T00:00:00Z"),
                step("hn", "discovery", "hacker_news", query="search:btc"),
                step("feed", "discovery", "rss_atom", query="https://example.net/feed.xml"),
            )
        )

        self.assertEqual(subjects(found, coverage.WINDOW_ABSENT), ["hn"])



    def test_no_window_anywhere_is_a_choice_and_draws_nothing(self):
        """An all-evergreen manifest is a legitimate shape, not an oversight.

        Windowing is per step and optional; a run that bounds nothing has
        decided that, and this check only fires on the inconsistency.
        """

        found = coverage.review_manifest(
            manifest(step("hn", "discovery", "hacker_news", query="search:btc"))
        )

        self.assertNotIn(coverage.WINDOW_ABSENT, codes(found))




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
