"""K0 Wikimedia per-article pageviews: window-in-the-path, offline.

Nothing here reaches a network: every carrier is `helpers.offline_transport`
over the measured fixture (`tests/fixtures/wikimedia_pageviews/
per_article_daily.json`, captured live 2026-09-01), or over a small synthetic
body built to exercise one failure shape at a time.
"""

from __future__ import annotations

import json
import unittest
import urllib.parse
from pathlib import Path

from super_research import transport
from super_research.adapters import AdapterRequest, wikimedia_pageviews
from tests import helpers

ROUTE = transport.WIKIMEDIA_PAGEVIEWS_ROUTE
FIXTURE_PATH = (
    Path(__file__).resolve().parent / "fixtures" / "wikimedia_pageviews" / "per_article_daily.json"
)
FIXTURE_BODY = FIXTURE_PATH.read_text(encoding="utf-8")
FIXTURE_ITEM_COUNT = len(json.loads(FIXTURE_BODY)["items"])

TARGET = "Python_(programming_language)"
WINDOW_START = "2026-08-21T00:00:00Z"
WINDOW_END = "2026-08-31T00:00:00Z"


def fetch(request, body=FIXTURE_BODY, status=200, content_type="application/json"):
    clock = helpers.FakeClock()
    carrier, opener = helpers.offline_transport(clock, {ROUTE: (status, body, content_type)})
    page = wikimedia_pageviews.fetch_native_page(carrier, request)
    return page, opener


def path_of(url):
    return urllib.parse.urlsplit(url).path


class TargetGrammarTest(unittest.TestCase):
    """`<article>` reads the default project; `<project>:<article>` names one."""

    def test_a_bare_article_reads_the_default_project(self):
        self.assertEqual(
            wikimedia_pageviews.target_grammar(TARGET),
            (wikimedia_pageviews.DEFAULT_PROJECT, TARGET),
        )

    def test_a_project_prefixed_article_names_its_own_project(self):
        self.assertEqual(
            wikimedia_pageviews.target_grammar("de.wikipedia:Berlin"),
            ("de.wikipedia", "Berlin"),
        )

    def test_an_empty_target_names_no_article(self):
        self.assertEqual(wikimedia_pageviews.target_grammar(""), ("", ""))
        self.assertEqual(wikimedia_pageviews.target_grammar("   "), ("", ""))

    def test_a_prefix_with_nothing_on_one_side_names_no_article(self):
        self.assertEqual(wikimedia_pageviews.target_grammar(":Berlin"), ("", ""))
        self.assertEqual(wikimedia_pageviews.target_grammar("de.wikipedia:"), ("", ""))


class HappyParseTest(unittest.TestCase):
    """The measured fixture, hydrated: one record per day, the roster's own fields."""

    def test_one_call_one_record_per_day(self):
        page, opener = fetch(
            AdapterRequest(
                step_id="s1",
                target_ids=(TARGET,),
                window_start=WINDOW_START,
                window_end=WINDOW_END,
            )
        )

        self.assertEqual(len(opener.opened), 1)
        self.assertEqual(page.outcome, "ok")
        self.assertEqual(len(page.records), FIXTURE_ITEM_COUNT)

    def test_every_record_carries_the_roster_row(self):
        page, _ = fetch(
            AdapterRequest(
                step_id="s1",
                target_ids=(TARGET,),
                window_start=WINDOW_START,
                window_end=WINDOW_END,
            )
        )

        first = page.records[0]
        self.assertEqual(first.canonical_content_kind, "pageview_count")
        self.assertEqual(first.native_item_id, "en.wikipedia/" + TARGET + "/2026082100")
        self.assertEqual(
            first.canonical_locator, "https://en.wikipedia.org/wiki/" + TARGET
        )
        self.assertEqual(first.published_at, "2026-08-21T00:00:00Z")
        self.assertEqual(dict(first.engagement)["views"], 6625)
        self.assertIn(("granularity", "daily"), first.attributes)
        self.assertIn(("access", "all-access"), first.attributes)
        self.assertIn(("agent", "all-agents"), first.attributes)

    def test_every_record_carries_date_precision_only(self):
        page, _ = fetch(
            AdapterRequest(
                step_id="s1",
                target_ids=(TARGET,),
                window_start=WINDOW_START,
                window_end=WINDOW_END,
            )
        )

        for record in page.records:
            with self.subTest(native_item_id=record.native_item_id):
                self.assertIn("date_precision_only", record.loss)

    def test_the_project_and_article_path_segments_are_sent(self):
        _, opener = fetch(
            AdapterRequest(
                step_id="s1",
                target_ids=(TARGET,),
                window_start=WINDOW_START,
                window_end=WINDOW_END,
            )
        )

        self.assertEqual(
            path_of(opener.opened[0].url),
            "/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/"
            "all-agents/Python_%28programming_language%29/daily/2026082100/2026083100",
        )


class WindowIsThePathTest(unittest.TestCase):
    """A read with no `window_start` is refused; one with no `window_end` sends the sentinel."""

    def test_no_window_start_is_refused_without_a_call(self):
        page, opener = fetch(AdapterRequest(step_id="s1", target_ids=(TARGET,)))

        self.assertEqual(page.outcome, "refused")
        self.assertIn("unselected_target", page.loss)
        self.assertEqual(page.records, ())
        self.assertEqual(len(opener.opened), 0)

    def test_an_unparseable_window_start_is_refused_the_same_way(self):
        page, opener = fetch(
            AdapterRequest(step_id="s1", target_ids=(TARGET,), window_start="not-a-date")
        )

        self.assertEqual(page.outcome, "refused")
        self.assertIn("unselected_target", page.loss)
        self.assertEqual(len(opener.opened), 0)

    def test_no_window_end_spends_the_far_future_sentinel(self):
        _, opener = fetch(
            AdapterRequest(step_id="s1", target_ids=(TARGET,), window_start=WINDOW_START)
        )

        self.assertTrue(
            path_of(opener.opened[0].url).endswith(
                "/2026082100/" + wikimedia_pageviews.FAR_FUTURE_END
            )
        )

    def test_the_sentinel_is_deterministic_across_two_builds(self):
        _, first = fetch(
            AdapterRequest(step_id="s1", target_ids=(TARGET,), window_start=WINDOW_START)
        )
        _, second = fetch(
            AdapterRequest(step_id="s1", target_ids=(TARGET,), window_start=WINDOW_START)
        )

        self.assertEqual(first.opened[0].url, second.opened[0].url)

    def test_no_article_named_is_refused_without_a_call(self):
        page, opener = fetch(
            AdapterRequest(step_id="s1", target_ids=("",), window_start=WINDOW_START)
        )

        self.assertEqual(page.outcome, "refused")
        self.assertIn("unselected_target", page.loss)
        self.assertEqual(len(opener.opened), 0)


class EmptyTest(unittest.TestCase):
    def test_a_200_with_an_empty_items_list_is_reported_empty(self):
        page, _ = fetch(
            AdapterRequest(
                step_id="s1",
                target_ids=(TARGET,),
                window_start=WINDOW_START,
                window_end=WINDOW_END,
            ),
            body='{"items": []}',
        )

        self.assertEqual(page.outcome, "empty")
        self.assertEqual(page.records, ())
        self.assertTrue(page.warnings)


class DriftTest(unittest.TestCase):
    def test_a_200_with_no_items_field_is_schema_drift(self):
        page, _ = fetch(
            AdapterRequest(
                step_id="s1",
                target_ids=(TARGET,),
                window_start=WINDOW_START,
                window_end=WINDOW_END,
            ),
            body='{"not_items": []}',
        )

        self.assertEqual(page.outcome, "failed")
        self.assertIn("schema_drift", page.loss)

    def test_a_200_with_items_holding_no_identifiable_row_is_schema_drift(self):
        page, _ = fetch(
            AdapterRequest(
                step_id="s1",
                target_ids=(TARGET,),
                window_start=WINDOW_START,
                window_end=WINDOW_END,
            ),
            body='{"items": [{"nothing": "recognizable"}]}',
        )

        self.assertEqual(page.outcome, "failed")
        self.assertIn("schema_drift", page.loss)


class NonJsonTest(unittest.TestCase):
    def test_a_200_with_no_json_body_is_malformed_json(self):
        page, _ = fetch(
            AdapterRequest(
                step_id="s1",
                target_ids=(TARGET,),
                window_start=WINDOW_START,
                window_end=WINDOW_END,
            ),
            body="not json at all",
        )

        self.assertEqual(page.outcome, "failed")
        self.assertIn("malformed_json", page.loss)


class HttpStatusTest(unittest.TestCase):
    def test_a_404_carries_its_own_detail_sentence_as_a_warning(self):
        detail_body = json.dumps(
            {
                "detail": "The date(s) you used are valid, but we either do not"
                " have data for those date(s), or the project you asked for is"
                " not loaded yet.",
                "status": 404,
            }
        )

        page, _ = fetch(
            AdapterRequest(
                step_id="s1",
                target_ids=(TARGET,),
                window_start=WINDOW_START,
                window_end=WINDOW_END,
            ),
            body=detail_body,
            status=404,
        )

        self.assertEqual(page.outcome, "failed")
        self.assertIn("http_status", page.loss)
        self.assertIn("The date(s) you used are valid", page.warnings[0])


class OneCallOnlyTest(unittest.TestCase):
    def test_a_happy_read_costs_exactly_one_call(self):
        _, opener = fetch(
            AdapterRequest(
                step_id="s1",
                target_ids=(TARGET,),
                window_start=WINDOW_START,
                window_end=WINDOW_END,
            )
        )

        self.assertEqual(len(opener.opened), 1)
        self.assertEqual(opener.opened[0].route_id, ROUTE)


if __name__ == "__main__":
    unittest.main()
