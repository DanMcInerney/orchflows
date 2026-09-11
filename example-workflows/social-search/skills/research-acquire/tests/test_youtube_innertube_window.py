"""YouTube InnerTube's window-carrying: the fifth and last of R.02's live measurements.

Measured live 2026-08-31 (recorded in `origin_upload_date_filter`'s own
docstring): a query returning results as old as nine years, filtered with
each of five candidate upload-date values, put every returned
`publishedTimeText` inside the named span (hour/today/week/month/year) in
every case. `WINDOW_REACH["youtube_innertube"]` now splits by operation:
`search` is `True`, the other three (single-video reads with no ordering)
stay `False`. Honoring the bound cost more than an adapter edit, per
Details: the POST body is rendered only from `YOUTUBE_INNERTUBE_ROUTE`'s
closed `body_params` list, so a `params` entry was added there too.

Nothing here reaches a network: every carrier is `helpers.offline_transport`
over a synthetic empty JSON body, because this file proves what reaches the
origin, not what a real page parses into.
"""

from __future__ import annotations

import json
import unittest
from datetime import datetime, timedelta, timezone

from super_research import transport
from super_research.adapters import AdapterRequest, youtube_innertube
from tests import helpers

ROUTE = transport.YOUTUBE_INNERTUBE_ROUTE
EMPTY_BODY = "{}"


def iso(age_seconds):
    moment = datetime.now(timezone.utc) - timedelta(seconds=age_seconds)
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch(request):
    clock = helpers.FakeClock()
    carrier, opener = helpers.offline_transport(clock, {ROUTE: (200, EMPTY_BODY, "application/json")})
    page = youtube_innertube.fetch_native_page(carrier, request)
    return page, opener


def body_params_field(url_or_body, name):
    return json.loads(url_or_body).get(name, "")


class PureFilterDerivationTest(unittest.TestCase):
    """`origin_upload_date_filter` alone: the smallest covering span's value."""

    def test_each_age_resolves_to_the_smallest_covering_span(self):
        cases = (
            (30 * 60, "EgIIAQ=="),
            (12 * 3600, "EgIIAg=="),
            (3 * 86400, "EgIIAw=="),
            (20 * 86400, "EgIIBA=="),
            (200 * 86400, "EgIIBQ=="),
        )
        for age_seconds, expected in cases:
            with self.subTest(age_seconds=age_seconds):
                self.assertEqual(youtube_innertube.origin_upload_date_filter(iso(age_seconds), ""), expected)

    def test_a_window_older_than_a_year_sends_no_filter_at_all(self):
        # The ladder's widest rung is "This year"; sending nothing already
        # reaches further than that, so nothing new is the honest answer.
        self.assertEqual(youtube_innertube.origin_upload_date_filter(iso(400 * 86400), ""), "")

    def test_no_window_start_sends_nothing_new_regardless_of_window_end(self):
        self.assertEqual(youtube_innertube.origin_upload_date_filter("", ""), "")
        self.assertEqual(youtube_innertube.origin_upload_date_filter("", iso(3600)), "")

    def test_an_unparseable_window_start_sends_nothing_new(self):
        self.assertEqual(youtube_innertube.origin_upload_date_filter("not-a-date", ""), "")

    def test_window_end_never_changes_the_answer(self):
        start = iso(3 * 86400)
        baseline = youtube_innertube.origin_upload_date_filter(start, "")
        self.assertEqual(youtube_innertube.origin_upload_date_filter(start, iso(0)), baseline)
        self.assertEqual(youtube_innertube.origin_upload_date_filter(start, "2016-01-01T00:00:00Z"), baseline)


class WindowedStepReachesTheOriginTest(unittest.TestCase):
    """Goal 1/2: a windowed `search` step's bound reaches the POST body."""

    def test_a_windowed_search_sends_the_derived_filter_in_the_body(self):
        _, opener = fetch(
            AdapterRequest(step_id="s1", query="search:python tutorial", window_start=iso(3 * 86400))
        )

        self.assertEqual(body_params_field(opener.opened[0].body, "params"), "EgIIAw==")

    def test_a_windowed_player_hydration_never_carries_the_filter(self):
        # `player` is a single-video read with no ordering: `operation_for`
        # resolves a bare target id (no operation prefix) to `player`.
        _, opener = fetch(AdapterRequest(step_id="s1", target_ids=("dQw4w9WgXcQ",), window_start=iso(3600)))

        self.assertEqual(body_params_field(opener.opened[0].body, "params"), "")

    def test_declaration_matches_behavior(self):
        from super_research._support import window_reach

        self.assertTrue(window_reach.reach_for("youtube_innertube", query="search:x"))
        self.assertFalse(window_reach.reach_for("youtube_innertube", target_ids=("dQw4w9WgXcQ",)))


class UnwindowedStepIsUnchangedTest(unittest.TestCase):
    """Goal 4: a step carrying no window is the baseline request, byte for byte."""

    def test_the_search_body_is_exactly_the_pre_existing_shape(self):
        _, opener = fetch(AdapterRequest(step_id="s1", query="search:python tutorial"))

        self.assertNotIn("params", json.loads(opener.opened[0].body))

    def test_a_window_end_with_no_window_start_never_triggers_the_new_path(self):
        _, baseline = fetch(AdapterRequest(step_id="s1", query="search:python tutorial"))
        _, end_only = fetch(AdapterRequest(step_id="s1", query="search:python tutorial", window_end=iso(0)))

        self.assertEqual(baseline.opened[0].body, end_only.opened[0].body)

    def test_a_continuation_call_never_carries_the_filter_either(self):
        # `query` itself is not resent on a continuation call; the filter
        # follows the same rule, matching the pre-existing idiom.
        _, opener = fetch(
            AdapterRequest(step_id="s1", query="search:python tutorial", cursor="c1", window_start=iso(3 * 86400))
        )

        self.assertNotIn("params", json.loads(opener.opened[0].body))


if __name__ == "__main__":
    unittest.main()
