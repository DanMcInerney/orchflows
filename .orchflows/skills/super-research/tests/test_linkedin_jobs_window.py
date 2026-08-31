"""LinkedIn Jobs' window-carrying: one of R.02's five live measurements.

Measured live 2026-08-31 (recorded in `origin_recency_term`'s own docstring):
the same ``keywords`` read bare and with a candidate ``f_TPR=r<seconds>``
moved the oldest posting's date forward and, on a rarer keyword, dropped the
row count too — the pair Details asked for. `WINDOW_REACH["linkedin_jobs"]`
now declares ``True``, and `fetch_native_page` carries the derived term when
a windowed step names one.

Nothing here reaches a network: every carrier is `helpers.offline_transport`
over a synthetic empty results fragment, because this file proves what
reaches the origin, not what a real page parses into.
"""

from __future__ import annotations

import unittest
import urllib.parse
from datetime import datetime, timedelta, timezone

from super_research import transport
from super_research.adapters import AdapterRequest, linkedin_jobs
from tests import helpers

ROUTE = transport.LINKEDIN_JOBS_GUEST_SEARCH_ROUTE
EMPTY_RESULTS = '<ul class="jobs-search__results-list"></ul>'


def iso(age_seconds):
    moment = datetime.now(timezone.utc) - timedelta(seconds=age_seconds)
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch(request):
    clock = helpers.FakeClock()
    carrier, opener = helpers.offline_transport(clock, {ROUTE: (200, EMPTY_RESULTS, "text/html")})
    page = linkedin_jobs.fetch_native_page(carrier, request)
    return page, opener


def f_tpr(url):
    values = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query).get("f_TPR", [])
    return values[0] if values else ""


class PureRecencyDerivationTest(unittest.TestCase):
    """`origin_recency_term` alone: the age in whole seconds, as `r<seconds>`."""

    def test_the_answer_is_the_exact_age_in_seconds(self):
        self.assertEqual(linkedin_jobs.origin_recency_term(iso(3600), ""), "r3600")
        self.assertEqual(linkedin_jobs.origin_recency_term(iso(86400), ""), "r86400")

    def test_a_window_start_in_the_future_still_answers_a_positive_span(self):
        self.assertEqual(linkedin_jobs.origin_recency_term(iso(-60), ""), "r1")

    def test_no_window_start_sends_nothing_new_regardless_of_window_end(self):
        self.assertEqual(linkedin_jobs.origin_recency_term("", ""), "")
        self.assertEqual(linkedin_jobs.origin_recency_term("", iso(3600)), "")

    def test_an_unparseable_window_start_sends_nothing_new(self):
        self.assertEqual(linkedin_jobs.origin_recency_term("not-a-date", ""), "")

    def test_window_end_never_changes_the_answer(self):
        start = iso(10 * 86400)
        baseline = linkedin_jobs.origin_recency_term(start, "")
        self.assertEqual(linkedin_jobs.origin_recency_term(start, iso(0)), baseline)
        self.assertEqual(linkedin_jobs.origin_recency_term(start, "2016-01-01T00:00:00Z"), baseline)


class WindowedStepReachesTheOriginTest(unittest.TestCase):
    """Goal 1/2: a windowed step's bound reaches `f_TPR` on the wire."""

    def test_a_windowed_search_sends_the_derived_f_tpr(self):
        _, opener = fetch(AdapterRequest(step_id="s1", query="python", window_start=iso(3600)))

        self.assertEqual(f_tpr(opener.opened[0].url), "r3600")

    def test_declaration_matches_behavior(self):
        from super_research._support import window_reach

        self.assertTrue(window_reach.reach_for("linkedin_jobs", query="python"))


class UnwindowedStepIsUnchangedTest(unittest.TestCase):
    """Goal 4: a step carrying no window is the baseline request, byte for byte."""

    def test_the_wire_request_is_exactly_the_pre_existing_shape(self):
        _, opener = fetch(AdapterRequest(step_id="s1", query="python", cursor="0"))

        self.assertEqual(
            opener.opened[0].url,
            "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=python&start=0",
        )

    def test_a_window_end_with_no_window_start_never_triggers_the_new_path(self):
        _, baseline = fetch(AdapterRequest(step_id="s1", query="python"))
        _, end_only = fetch(AdapterRequest(step_id="s1", query="python", window_end=iso(0)))

        self.assertEqual(baseline.opened[0].url, end_only.opened[0].url)


if __name__ == "__main__":
    unittest.main()
