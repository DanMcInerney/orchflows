"""Reddit Shreddit's window-carrying: R.02's half of Goal clause 2.

`reddit_shreddit`'s `listing` and `search` operations already declare `True`
in `_support.window_reach.WINDOW_REACH` (R.01); this file proves the origin
side actually gets asked. `_fetch_listing`/`_fetch_search`
(`adapters/reddit_shreddit.py`) now derive the origin's own `t=` bucket from
a windowed step's `window_start`/`window_end`
(`_support/reddit_shreddit_contract.origin_time_bucket`) instead of only from
the caller's target string, so a windowed discovery step spends its cap
in-window at the origin rather than trimming it after the fact, client-side.
`_fetch_comments` stays unsent, per Details.

Reddit's `t=` is a span measured back from *now*, never from an explicit
endpoint, so `origin_time_bucket` reads the real wall clock
(`transport.utc_now_iso`) exactly as its exemplar,
`_support/web_search_feeds.google_when_days`, already does when its own
`window_end` is absent. The pure-function tests below build `window_start`
from the same wall clock at call time and land each case a full bucket away
from its nearest boundary (30 minutes inside "hour", not 55; 10 days inside
"month", not 29), so test execution time can never cross one.

Nothing here reaches a network: every carrier is `helpers.offline_transport`
over the fixtures `tests/fixtures/reddit_shreddit/` already carries.
"""

from __future__ import annotations

import unittest
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

from super_research import runner, schema, transport
from super_research.adapters import AdapterRequest, reddit_shreddit
from super_research.adapters._support.reddit_shreddit_contract import origin_time_bucket
from tests import helpers

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "reddit_shreddit"
LISTING_ROUTE = transport.REDDIT_SHREDDIT_LISTING_ROUTE
SEARCH_ROUTE = transport.REDDIT_SHREDDIT_SEARCH_ROUTE
COMMENTS_ROUTE = transport.REDDIT_SHREDDIT_COMMENTS_ROUTE


def read_fixture(name):
    return FIXTURE_DIR.joinpath(name).read_text(encoding="utf-8")


def iso(age_seconds):
    """One instant this many seconds before the real wall clock, in manifest form."""

    moment = datetime.now(timezone.utc) - timedelta(seconds=age_seconds)
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch(route_id, fixture_name, request):
    """One offline `fetch_native_page` call, and the request it actually sent."""

    clock = helpers.FakeClock()
    carrier, opener = helpers.offline_transport(
        clock, {route_id: (200, read_fixture(fixture_name), "text/html")}
    )
    page = reddit_shreddit.fetch_native_page(carrier, request)
    return page, opener


def t_param(url):
    """The exact ``t`` query parameter one sent URL carries, or nothing.

    A substring check on ``"t="`` is not this route's grammar: `sort=top`
    contains the same two characters. Parsed rather than guessed.
    """

    query = urllib.parse.urlsplit(url).query
    values = urllib.parse.parse_qs(query).get("t", [])
    return values[0] if values else ""


class PureBucketDerivationTest(unittest.TestCase):
    """`origin_time_bucket` alone: the coarsest bucket that still reaches `window_start`."""

    def test_each_age_resolves_to_the_smallest_covering_bucket(self):
        cases = (
            (30 * 60, "hour"),
            (3 * 3600, "day"),
            (2 * 86400, "week"),
            (10 * 86400, "month"),
            (180 * 86400, "year"),
            (3 * 365 * 86400, "all"),
        )
        for age_seconds, expected in cases:
            with self.subTest(age_seconds=age_seconds):
                self.assertEqual(origin_time_bucket(iso(age_seconds), ""), expected)

    def test_a_window_start_in_the_future_still_answers_the_smallest_bucket(self):
        self.assertEqual(origin_time_bucket(iso(-3600), ""), "hour")

    def test_no_window_start_sends_nothing_new_regardless_of_window_end(self):
        self.assertEqual(origin_time_bucket("", ""), "")
        self.assertEqual(origin_time_bucket("", iso(3600)), "")

    def test_an_unparseable_window_start_sends_nothing_new(self):
        self.assertEqual(origin_time_bucket("not-a-date", ""), "")

    def test_window_end_never_changes_the_answer(self):
        # Reddit's own bucket is always measured from "now", never from an
        # explicit endpoint: `window_end` before now, after now, or absent
        # all change nothing the request sends.
        start = iso(10 * 86400)
        baseline = origin_time_bucket(start, "")
        self.assertEqual(origin_time_bucket(start, iso(0)), baseline)
        self.assertEqual(origin_time_bucket(start, "2016-01-01T00:00:00Z"), baseline)


class WindowedStepReachesTheOriginTest(unittest.TestCase):
    """Goal 1: a windowed step's bound reaches Reddit's own `t=` on the wire."""

    def test_a_windowed_listing_call_sends_the_derived_t(self):
        _, opener = fetch(
            LISTING_ROUTE,
            "listing.html",
            AdapterRequest(step_id="s1", query="listing:programming", window_start=iso(10 * 86400)),
        )

        self.assertEqual(t_param(opener.opened[0].url), "month")

    def test_a_windowed_search_call_sends_the_derived_t(self):
        _, opener = fetch(
            SEARCH_ROUTE,
            "search.html",
            AdapterRequest(step_id="s1", query="search:python", window_start=iso(3 * 3600)),
        )

        self.assertEqual(t_param(opener.opened[0].url), "day")

    def test_the_step_level_window_overrides_an_explicit_query_grammar_window(self):
        # `listing:<sub>:<sort>:<window>` still parses; the step's own bound
        # is what actually reaches the origin when both are present.
        _, opener = fetch(
            LISTING_ROUTE,
            "listing.html",
            AdapterRequest(
                step_id="s1",
                query="listing:programming:new:hour",
                window_start=iso(180 * 86400),
            ),
        )
        self.assertEqual(t_param(opener.opened[0].url), "year")

    def test_an_end_to_end_windowed_discovery_step_spends_its_cap_in_window(self):
        # Goal's own phrasing, proven through the real step/runner seam rather
        # than by calling the adapter function directly, as every test above
        # does.
        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(
            clock, {LISTING_ROUTE: (200, read_fixture("listing.html"), "text/html")}
        )
        step = schema.AcquisitionStep(
            step_id="s1",
            kind="discovery",
            adapter_id="reddit_shreddit",
            query="listing:programming",
            max_items=50,
            max_pages=1,
            window_start=iso(2 * 86400),
        )

        runner.run_step(step, carrier, "artifact:1", "manifest:1", clock=clock.monotonic)

        self.assertEqual(t_param(opener.opened[0].url), "week")


class UnwindowedStepIsUnchangedTest(unittest.TestCase):
    """Goal 4: a step carrying no `window_start` is the baseline request, byte for byte."""

    def test_the_wire_request_is_exactly_the_pre_existing_shape_with_no_window(self):
        # Pinned literally, not by comparing a call to itself: `t` is absent
        # and the params sent are exactly `listing_target`'s own two.
        _, opener = fetch(
            LISTING_ROUTE, "listing.html", AdapterRequest(step_id="s1", query="listing:programming")
        )

        self.assertEqual(
            opener.opened[0].url,
            "https://www.reddit.com/svc/shreddit/community-more-posts/new/?name=programming",
        )

    def test_a_window_end_with_no_window_start_never_triggers_the_new_path(self):
        # `origin_time_bucket` cannot honor an upper-only bound (there is no
        # second parameter this route reads to narrow the near edge), so the
        # request stays exactly what an unwindowed step would have sent.
        _, baseline = fetch(
            LISTING_ROUTE, "listing.html", AdapterRequest(step_id="s1", query="listing:programming")
        )
        _, end_only = fetch(
            LISTING_ROUTE,
            "listing.html",
            AdapterRequest(step_id="s1", query="listing:programming", window_end=iso(0)),
        )

        self.assertEqual(baseline.opened[0].url, end_only.opened[0].url)

    def test_the_query_grammar_window_still_works_with_no_step_level_window(self):
        _, opener = fetch(
            LISTING_ROUTE, "listing.html", AdapterRequest(step_id="s1", query="listing:programming:new:week")
        )

        self.assertEqual(t_param(opener.opened[0].url), "week")


class CommentsNeverCarriesAWindowTest(unittest.TestCase):
    """Details: `_fetch_comments` is the hydration surface and stays unsent."""

    def test_a_windowed_comments_call_sends_no_t_at_all(self):
        page, opener = fetch(
            COMMENTS_ROUTE,
            "comments.html",
            AdapterRequest(step_id="s1", target_ids=("programming/1vqukkf",), window_start=iso(3600)),
        )

        self.assertEqual(page.outcome, "ok")
        self.assertEqual(t_param(opener.opened[0].url), "")


if __name__ == "__main__":
    unittest.main()
