"""GitHub REST's window-carrying: two more of R.02's five live measurements.

Measured live 2026-08-31 (recorded in `origin_created_qualifier`'s and
`origin_since_param`'s own docstrings): `search`'s `created:` qualifier moved
`total_count` from 1,244,282 to 6,725 and put every returned `created_at`
inside the named span; `issues`' `since=` set a few minutes in the future
answered zero rows where the bare call answered a full page. `releases` was
measured the same way as `issues` and does not honor it: a future `since=`
answered the identical unfiltered page. `WINDOW_REACH["github_rest"]` now
reads `{"repo": False, "issues": True, "releases": False, "search": True}`.

Nothing here reaches a network: every carrier is `helpers.offline_transport`
over a synthetic empty answer, because this file proves what reaches the
origin, not what a real page parses into.
"""

from __future__ import annotations

import unittest
import urllib.parse
from datetime import datetime, timedelta, timezone

from super_research import runner, schema, transport
from super_research._support import window_reach
from super_research.adapters import AdapterRequest, github_rest
from tests import helpers

REST_ROUTE = transport.GITHUB_REST_ROUTE
SEARCH_ROUTE = transport.GITHUB_SEARCH_ROUTE
EMPTY_LIST = "[]"
EMPTY_SEARCH = '{"total_count":0,"items":[]}'


def iso(age_seconds):
    moment = datetime.now(timezone.utc) - timedelta(seconds=age_seconds)
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def day(age_seconds):
    return iso(age_seconds)[:10]


def fetch(route, body, request):
    clock = helpers.FakeClock()
    carrier, opener = helpers.offline_transport(clock, {route: (200, body, "application/json")})
    page = github_rest.fetch_native_page(carrier, request)
    return page, opener


def query_param(url, name):
    values = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query).get(name, [])
    return values[0] if values else ""


class PureQualifierDerivationTest(unittest.TestCase):
    """`origin_created_qualifier` alone: day-precision, both edges independent."""

    def test_only_a_start_gives_the_open_ended_form(self):
        self.assertEqual(
            github_rest.origin_created_qualifier(iso(7 * 86400), ""),
            "created:>=" + day(7 * 86400),
        )

    def test_only_an_end_gives_the_other_open_ended_form(self):
        self.assertEqual(
            github_rest.origin_created_qualifier("", iso(7 * 86400)),
            "created:<=" + day(7 * 86400),
        )

    def test_both_edges_give_the_range_form(self):
        self.assertEqual(
            github_rest.origin_created_qualifier(iso(30 * 86400), iso(7 * 86400)),
            "created:" + day(30 * 86400) + ".." + day(7 * 86400),
        )

    def test_no_window_at_all_sends_nothing_new(self):
        self.assertEqual(github_rest.origin_created_qualifier("", ""), "")

    def test_an_unparseable_instant_is_treated_as_absent(self):
        self.assertEqual(github_rest.origin_created_qualifier("not-a-date", ""), "")


class PureSinceDerivationTest(unittest.TestCase):
    """`origin_since_param` alone: `window_start`, verbatim, or nothing."""

    def test_a_window_start_is_carried_verbatim(self):
        start = iso(3600)
        self.assertEqual(github_rest.origin_since_param(start), start)

    def test_no_window_start_sends_nothing(self):
        self.assertEqual(github_rest.origin_since_param(""), "")


class WindowedStepReachesTheOriginTest(unittest.TestCase):
    """Goal 1/2: a windowed step's bound reaches the origin on `search` and `issues`."""

    def test_a_windowed_search_call_sends_the_created_qualifier(self):
        _, opener = fetch(
            SEARCH_ROUTE,
            EMPTY_SEARCH,
            AdapterRequest(step_id="s1", query="search:machine learning", window_start=iso(7 * 86400)),
        )

        self.assertIn("created:>=" + day(7 * 86400), query_param(opener.opened[0].url, "q"))

    def test_a_windowed_issues_call_sends_since(self):
        start = iso(3600)
        _, opener = fetch(
            REST_ROUTE,
            EMPTY_LIST,
            AdapterRequest(step_id="s1", query="issues:owner/repo", window_start=start),
        )

        self.assertEqual(query_param(opener.opened[0].url, "since"), start)

    def test_a_windowed_releases_call_sends_no_since_at_all(self):
        # Measured cannot: `releases` ignores `since=` at the origin, so
        # nothing new is sent even when the step carries a window.
        _, opener = fetch(
            REST_ROUTE,
            EMPTY_LIST,
            AdapterRequest(step_id="s1", query="releases:owner/repo", window_start=iso(3600)),
        )

        self.assertEqual(query_param(opener.opened[0].url, "since"), "")

    def test_a_windowed_repo_call_carries_no_window_either(self):
        # `repo` is a single hydration by name: no ordering, no bound.
        _, opener = fetch(
            REST_ROUTE, EMPTY_LIST, AdapterRequest(step_id="s1", target_ids=("owner/repo",), window_start=iso(3600))
        )

        self.assertEqual(query_param(opener.opened[0].url, "since"), "")

    def test_declaration_matches_behavior(self):
        from super_research._support import window_reach

        self.assertTrue(window_reach.reach_for("github_rest", query="search:x"))
        self.assertTrue(window_reach.reach_for("github_rest", query="issues:owner/repo"))
        self.assertFalse(window_reach.reach_for("github_rest", query="releases:owner/repo"))
        self.assertFalse(window_reach.reach_for("github_rest", target_ids=("owner/repo",)))


class UnwindowedStepIsUnchangedTest(unittest.TestCase):
    """Goal 4: a step carrying no window at all is the baseline request, byte for byte.

    `index` is a path segment (`route_catalog`'s own `path_params`), not a
    query parameter, so the baseline query string is `q` alone.
    """

    def test_the_search_request_is_exactly_the_pre_existing_shape(self):
        _, opener = fetch(SEARCH_ROUTE, EMPTY_SEARCH, AdapterRequest(step_id="s1", query="search:python"))

        self.assertEqual(opener.opened[0].url, "https://api.github.com/search/repositories?q=python")

    def test_a_window_end_alone_leaves_issues_unwindowed(self):
        # Unlike `search`, `issues` has no measured far-edge parameter
        # (Details: no `until` was found, none was invented), so a
        # `window_end`-only step stays exactly the unwindowed request.
        _, baseline = fetch(REST_ROUTE, EMPTY_LIST, AdapterRequest(step_id="s1", query="issues:owner/repo"))
        _, end_only = fetch(
            REST_ROUTE, EMPTY_LIST, AdapterRequest(step_id="s1", query="issues:owner/repo", window_end=iso(0))
        )

        self.assertEqual(baseline.opened[0].url, end_only.opened[0].url)


class SearchHonorsAnEndOnlyWindowTooTest(unittest.TestCase):
    """`search`'s `created:` qualifier genuinely takes an end with no start.

    Not a byte-for-byte-unchanged case: GitHub's own qualifier grammar
    supports `<=` independent of `>=` (measured: the range form put both
    edges exactly where asked), so a step naming only `window_end` is a
    real bound this route can honor, and Goal says a surface that can bound
    time should — this is that surface exercising its far edge alone.
    """

    def test_a_window_end_only_step_sends_the_open_ended_upper_bound(self):
        _, opener = fetch(
            SEARCH_ROUTE, EMPTY_SEARCH, AdapterRequest(step_id="s1", query="search:python", window_end=iso(7 * 86400))
        )

        self.assertIn("created:<=" + day(7 * 86400), query_param(opener.opened[0].url, "q"))


class ReleasesTypedStatementTest(unittest.TestCase):
    """The measured-none surface: `releases` earns its own typed reading.

    Not a claim about the wire alone: a windowed step against `releases`
    must carry `window_reach.WINDOW_NOT_HONORED` in its own `StepResult.loss`
    through the real `runner.run_step` seam — the same mechanism R.01 proved
    generically on `bluesky`'s author feed, now proven on the one operation
    this ticket measured `False` rather than left conservative.
    """

    def _run_releases_step(self, window_start=""):
        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(clock, {REST_ROUTE: (200, EMPTY_LIST, "application/json")})
        step = schema.AcquisitionStep(
            step_id="s1",
            kind="hydration",
            adapter_id="github_rest",
            selected_hits=(schema.SelectedHit(target_id="releases:owner/repo", discovery_locator=""),),
            max_items=50,
            max_pages=1,
            window_start=window_start,
        )
        result, records, _ = runner.run_step(
            step, carrier, "artifact:1", "manifest:1", clock=clock.monotonic
        )
        return result, records, opener

    def test_a_windowed_releases_step_carries_the_typed_unhonored_reading(self):
        result, _, opener = self._run_releases_step(iso(3600))

        self.assertIn(window_reach.WINDOW_NOT_HONORED, result.loss)
        self.assertEqual(query_param(opener.opened[0].url, "since"), "")

    def test_an_unwindowed_releases_step_never_carries_it(self):
        result, _, _ = self._run_releases_step()

        self.assertNotIn(window_reach.WINDOW_NOT_HONORED, result.loss)


if __name__ == "__main__":
    unittest.main()
