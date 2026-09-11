"""Stack Exchange search/advanced: offline, against the measured payload shape.

Every case here runs `stack_exchange.fetch_native_page` against
`helpers.offline_transport`, never a real socket — the same seam
`test_github_rest_window.py` and `test_transport_gzip.py` already use for
this route. What is proven: the happy parse (epoch to instant, HTML-entity
title, tags and `is_answered` as attributes), the window carried as
`fromdate`/`todate`, the `site:<name> ` grammar, page-number cursor
discipline (surfaced, never followed), the four typed non-happy pages, one
call per fetch, and the exact-integer engagement law.
"""

from __future__ import annotations

import unittest
import urllib.parse

from super_research import transport
from super_research.adapters import AdapterRequest, stack_exchange
from tests import helpers

ROUTE = transport.STACKEXCHANGE_SEARCH_ROUTE
JSON_CONTENT_TYPE = "application/json; charset=utf-8"


def query_param(url, name):
    values = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query).get(name, [])
    return values[0] if values else None


def fetch(body, request, status=200, content_type=JSON_CONTENT_TYPE):
    clock = helpers.FakeClock()
    carrier, opener = helpers.offline_transport(clock, {ROUTE: (status, body, content_type)})
    page = stack_exchange.fetch_native_page(carrier, request)
    return page, opener


ONE_QUESTION = """
{
  "items": [
    {
      "tags": ["python", "asyncio"],
      "owner": {"display_name": "Ada L."},
      "is_answered": true,
      "view_count": 145,
      "answer_count": 2,
      "score": 7,
      "creation_date": 1735689600,
      "question_id": 79999908,
      "link": "https://stackoverflow.com/questions/79999908/example",
      "title": "Can&#39;t get virtual environment to activate"
    }
  ],
  "has_more": false,
  "quota_max": 300,
  "quota_remaining": 293
}
"""

TWO_QUESTIONS_MORE = """
{
  "items": [
    {"owner": {"display_name": "a"}, "question_id": 1,
     "link": "https://stackoverflow.com/questions/1/x", "title": "One",
     "creation_date": 1735689600},
    {"owner": {"display_name": "b"}, "question_id": 2,
     "link": "https://stackoverflow.com/questions/2/y", "title": "Two",
     "creation_date": 1735689700}
  ],
  "has_more": true,
  "quota_max": 300,
  "quota_remaining": 290
}
"""

EMPTY_ITEMS = '{"items": [], "has_more": false, "quota_max": 300, "quota_remaining": 300}'
NO_ITEMS_KEY = '{"has_more": false, "quota_max": 300, "quota_remaining": 300}'
UNIDENTIFIABLE_ITEMS = '{"items": [{"title": "no id here"}], "has_more": false}'
MIXED_IDENTIFIABLE = """
{
  "items": [
    {"title": "no id here"},
    {"owner": {"display_name": "a"}, "question_id": 1,
     "link": "https://stackoverflow.com/questions/1/x", "title": "One",
     "creation_date": 1735689600}
  ],
  "has_more": false
}
"""
NOT_JSON = "<html>not json</html>"


class HappyParseTest(unittest.TestCase):
    def test_a_question_carries_the_roster_field_set(self):
        page, _ = fetch(ONE_QUESTION, AdapterRequest(step_id="s1", query="python"))

        self.assertEqual(page.outcome, "ok")
        self.assertEqual(len(page.records), 1)
        record = page.records[0]
        self.assertEqual(record.canonical_content_kind, "question")
        self.assertEqual(record.native_item_id, "79999908")
        self.assertEqual(record.title, "Can't get virtual environment to activate")
        self.assertEqual(record.author, "Ada L.")
        self.assertEqual(
            record.canonical_locator, "https://stackoverflow.com/questions/79999908/example"
        )
        self.assertEqual(record.published_at, "2025-01-01T00:00:00Z")
        self.assertEqual(
            dict(record.engagement),
            {"score": 7, "answer_count": 2, "view_count": 145},
        )
        self.assertIn(("tag", "python"), record.attributes)
        self.assertIn(("tag", "asyncio"), record.attributes)
        self.assertIn(("is_answered", "true"), record.attributes)

    def test_a_false_is_answered_carries_its_own_exact_spelling(self):
        body = ONE_QUESTION.replace('"is_answered": true', '"is_answered": false')
        page, _ = fetch(body, AdapterRequest(step_id="s1", query="python"))

        self.assertIn(("is_answered", "false"), page.records[0].attributes)


class WindowTest(unittest.TestCase):
    def test_an_unwindowed_call_sends_no_date_bounds(self):
        _, opener = fetch(ONE_QUESTION, AdapterRequest(step_id="s1", query="python"))

        url = opener.opened[0].url
        self.assertIsNone(query_param(url, "fromdate"))
        self.assertIsNone(query_param(url, "todate"))

    def test_a_windowed_call_sends_fromdate_and_todate_as_unix_seconds(self):
        request = AdapterRequest(
            step_id="s1",
            query="python",
            window_start="2025-01-01T00:00:00Z",
            window_end="2025-02-01T00:00:00Z",
        )
        _, opener = fetch(ONE_QUESTION, request)

        url = opener.opened[0].url
        self.assertEqual(query_param(url, "fromdate"), "1735689600")
        self.assertEqual(query_param(url, "todate"), "1738368000")

    def test_only_one_edge_sends_only_that_bound(self):
        request = AdapterRequest(
            step_id="s1", query="python", window_start="2025-01-01T00:00:00Z"
        )
        _, opener = fetch(ONE_QUESTION, request)

        url = opener.opened[0].url
        self.assertEqual(query_param(url, "fromdate"), "1735689600")
        self.assertIsNone(query_param(url, "todate"))

    def test_the_windowed_and_unwindowed_requests_genuinely_differ(self):
        _, unwindowed = fetch(ONE_QUESTION, AdapterRequest(step_id="s1", query="python"))
        _, windowed = fetch(
            ONE_QUESTION,
            AdapterRequest(
                step_id="s1", query="python", window_start="2025-01-01T00:00:00Z"
            ),
        )

        self.assertNotEqual(unwindowed.opened[0].url, windowed.opened[0].url)


class SiteGrammarTest(unittest.TestCase):
    def test_the_pure_function_splits_a_prefixed_argument(self):
        self.assertEqual(
            stack_exchange.site_and_query("site:serverfault reverse proxy"),
            ("serverfault", "reverse proxy"),
        )

    def test_the_pure_function_defaults_an_unprefixed_argument(self):
        self.assertEqual(
            stack_exchange.site_and_query("reverse proxy"),
            (stack_exchange.DEFAULT_SITE, "reverse proxy"),
        )

    def test_a_bare_prefix_with_no_space_is_read_as_an_ordinary_query(self):
        self.assertEqual(
            stack_exchange.site_and_query("site:serverfault"),
            (stack_exchange.DEFAULT_SITE, "site:serverfault"),
        )

    def test_a_named_site_reaches_the_wire(self):
        _, opener = fetch(
            ONE_QUESTION, AdapterRequest(step_id="s1", query="site:serverfault reverse proxy")
        )

        url = opener.opened[0].url
        self.assertEqual(query_param(url, "site"), "serverfault")
        self.assertEqual(query_param(url, "q"), "reverse proxy")

    def test_an_unprefixed_query_reaches_the_wire_under_the_default_site(self):
        _, opener = fetch(ONE_QUESTION, AdapterRequest(step_id="s1", query="python"))

        url = opener.opened[0].url
        self.assertEqual(query_param(url, "site"), stack_exchange.DEFAULT_SITE)
        self.assertEqual(query_param(url, "q"), "python")

    def test_the_fixed_shape_is_sent_every_time(self):
        _, opener = fetch(ONE_QUESTION, AdapterRequest(step_id="s1", query="python"))

        url = opener.opened[0].url
        self.assertEqual(query_param(url, "pagesize"), "30")
        self.assertEqual(query_param(url, "order"), "desc")
        self.assertEqual(query_param(url, "sort"), "creation")


class CursorTest(unittest.TestCase):
    def test_has_more_surfaces_the_next_page_number(self):
        page, opener = fetch(TWO_QUESTIONS_MORE, AdapterRequest(step_id="s1", query="python"))

        self.assertEqual(page.cursor_out, "2")
        # Never followed by this module itself: one call, one page.
        self.assertEqual(len(opener.opened), 1)

    def test_no_has_more_surfaces_no_cursor(self):
        page, _ = fetch(ONE_QUESTION, AdapterRequest(step_id="s1", query="python"))

        self.assertEqual(page.cursor_out, "")

    def test_an_inbound_cursor_is_sent_as_the_page_to_read(self):
        _, opener = fetch(
            TWO_QUESTIONS_MORE, AdapterRequest(step_id="s1", query="python", cursor="2")
        )

        self.assertEqual(query_param(opener.opened[0].url, "page"), "2")

    def test_the_next_cursor_advances_past_whichever_page_was_sent(self):
        page, _ = fetch(
            TWO_QUESTIONS_MORE, AdapterRequest(step_id="s1", query="python", cursor="4")
        )

        self.assertEqual(page.cursor_out, "5")

    def test_an_unset_cursor_sends_no_page_parameter_at_all(self):
        _, opener = fetch(ONE_QUESTION, AdapterRequest(step_id="s1", query="python"))

        self.assertIsNone(query_param(opener.opened[0].url, "page"))


class EmptyTest(unittest.TestCase):
    def test_an_empty_items_list_is_a_typed_empty_outcome(self):
        page, _ = fetch(EMPTY_ITEMS, AdapterRequest(step_id="s1", query="zzzznothing"))

        self.assertEqual(page.outcome, "empty")
        self.assertEqual(page.records, ())
        self.assertTrue(page.warnings)


class DriftTest(unittest.TestCase):
    def test_a_missing_items_list_is_schema_drift(self):
        page, _ = fetch(NO_ITEMS_KEY, AdapterRequest(step_id="s1", query="python"))

        self.assertEqual(page.outcome, "failed")
        self.assertIn(stack_exchange.SCHEMA_DRIFT, page.loss)

    def test_items_present_but_none_identified_is_schema_drift(self):
        page, _ = fetch(UNIDENTIFIABLE_ITEMS, AdapterRequest(step_id="s1", query="python"))

        self.assertEqual(page.outcome, "failed")
        self.assertIn(stack_exchange.SCHEMA_DRIFT, page.loss)

    def test_a_mix_of_identified_and_not_keeps_the_good_rows_and_warns(self):
        page, _ = fetch(MIXED_IDENTIFIABLE, AdapterRequest(step_id="s1", query="python"))

        self.assertEqual(page.outcome, "ok")
        self.assertEqual(len(page.records), 1)
        self.assertTrue(page.warnings)
        self.assertIn("question_id", page.warnings[0])


class HttpAndJsonFailureTest(unittest.TestCase):
    def test_a_non_200_status_is_http_status(self):
        page, _ = fetch(
            '{"error_message": "throttle_violation"}',
            AdapterRequest(step_id="s1", query="python"),
            status=400,
        )

        self.assertEqual(page.outcome, "failed")
        self.assertIn(stack_exchange.HTTP_STATUS, page.loss)
        self.assertEqual(page.records, ())

    def test_a_200_that_is_not_json_is_malformed_json(self):
        page, _ = fetch(
            NOT_JSON, AdapterRequest(step_id="s1", query="python"), content_type="text/html"
        )

        self.assertEqual(page.outcome, "failed")
        self.assertIn(stack_exchange.MALFORMED_JSON, page.loss)
        self.assertEqual(page.records, ())


class OneCallTest(unittest.TestCase):
    def test_one_fetch_spends_exactly_one_call_on_the_declared_route(self):
        _, opener = fetch(ONE_QUESTION, AdapterRequest(step_id="s1", query="python"))

        self.assertEqual(len(opener.opened), 1)
        self.assertEqual(opener.opened[0].route_id, ROUTE)


class EngagementExactIntegerLawTest(unittest.TestCase):
    def test_a_bool_score_is_never_engagement(self):
        body = ONE_QUESTION.replace('"score": 7', '"score": true')
        page, _ = fetch(body, AdapterRequest(step_id="s1", query="python"))

        names = dict(page.records[0].engagement)
        self.assertNotIn("score", names)
        self.assertIn("answer_count", names)
        self.assertIn("view_count", names)

    def test_a_float_answer_count_is_never_engagement(self):
        body = ONE_QUESTION.replace('"answer_count": 2', '"answer_count": 2.5')
        page, _ = fetch(body, AdapterRequest(step_id="s1", query="python"))

        names = dict(page.records[0].engagement)
        self.assertNotIn("answer_count", names)
        self.assertIn("score", names)
        self.assertIn("view_count", names)

    def test_a_missing_count_is_absent_rather_than_zero(self):
        body = ONE_QUESTION.replace('"view_count": 145,', "")
        page, _ = fetch(body, AdapterRequest(step_id="s1", query="python"))

        names = dict(page.records[0].engagement)
        self.assertNotIn("view_count", names)

    def test_a_negative_score_is_never_engagement(self):
        # Measured on the live route: several items answer with a score of
        # -3 through -10. The artifact's engagement family admits only
        # non-negative exact integers, so this is a count the adapter cannot
        # report rather than one carried past the ladder unsigned.
        body = ONE_QUESTION.replace('"score": 7', '"score": -3')
        page, _ = fetch(body, AdapterRequest(step_id="s1", query="python"))

        names = dict(page.records[0].engagement)
        self.assertNotIn("score", names)
        self.assertIn("answer_count", names)
        self.assertIn("view_count", names)


if __name__ == "__main__":
    unittest.main()
