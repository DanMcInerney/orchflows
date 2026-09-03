"""GDELT DOC 2.0 artlist: offline, against the measured payload shape.

Every case here runs `gdelt.fetch_native_page` against
`helpers.offline_transport`, never a real socket — the same seam
`test_stack_exchange.py` and `test_github_rest_window.py` already use. What
is proven: the happy parse (`seendate` to instant, `domain`/`language`/
`sourcecountry` as attributes, no native id and no engagement), the window
carried as `startdatetime`/`enddatetime` in the origin's own
`YYYYMMDDHHMMSS`, the origin's own "nothing matched" shape (a bare `{}`,
read as `empty` and never `schema_drift`), the typed drift and malformed-json
pages, and one call per fetch.
"""

from __future__ import annotations

import unittest
import urllib.parse

from super_research import transport
from super_research.adapters import AdapterRequest, gdelt
from tests import helpers

ROUTE = transport.GDELT_DOC_ROUTE
JSON_CONTENT_TYPE = "application/json; charset=utf-8"


def query_param(url, name):
    pairs = urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query, keep_blank_values=True)
    values = [value for key, value in pairs if key == name]
    return values[0] if values else None


def fetch(body, request, status=200, content_type=JSON_CONTENT_TYPE):
    clock = helpers.FakeClock()
    carrier, opener = helpers.offline_transport(clock, {ROUTE: (status, body, content_type)})
    page = gdelt.fetch_native_page(carrier, request)
    return page, opener


ONE_ARTICLE = """
{
  "articles": [
    {
      "url": "https://example.com/climate-piece",
      "url_mobile": "",
      "title": "A Climate Piece",
      "seendate": "20260829T064500Z",
      "socialimage": "",
      "domain": "example.com",
      "language": "English",
      "sourcecountry": "United States"
    }
  ]
}
"""

TWO_ARTICLES = """
{
  "articles": [
    {"url": "https://a.example/1", "title": "One", "seendate": "20260829T064500Z",
     "domain": "a.example", "language": "English", "sourcecountry": "United States"},
    {"url": "https://b.example/2", "title": "Two", "seendate": "20260830T123000Z",
     "domain": "b.example", "language": "German", "sourcecountry": "Switzerland"}
  ]
}
"""

NO_MATCH_OBJECT = "{}"
EMPTY_ARTICLES_LIST = '{"articles": []}'
ARTICLES_NOT_A_LIST = '{"articles": "not-a-list"}'
NO_URL_ON_ANY_ROW = '{"articles": [{"title": "no url here"}]}'
MIXED_IDENTIFIABLE = """
{
  "articles": [
    {"title": "no url here"},
    {"url": "https://a.example/1", "title": "One", "seendate": "20260829T064500Z",
     "domain": "a.example"}
  ]
}
"""
TOP_LEVEL_NOT_AN_OBJECT = "[]"
INVALID_START_DATE_TEXT = "Invalid query start date."
INVALID_MODE_TEXT = (
    "Content-type: text/html; charset=utf-8\n"
    "Server: GDELT API Server 2.0\n\n"
    "Invalid mode."
)


class HappyParseTest(unittest.TestCase):
    def test_an_article_carries_the_roster_field_set(self):
        page, _ = fetch(ONE_ARTICLE, AdapterRequest(step_id="s1", query="climate"))

        self.assertEqual(page.outcome, "ok")
        self.assertEqual(len(page.records), 1)
        record = page.records[0]
        self.assertEqual(record.canonical_content_kind, "web_hit")
        self.assertEqual(record.canonical_locator, "https://example.com/climate-piece")
        self.assertEqual(record.title, "A Climate Piece")
        self.assertEqual(record.published_at, "2026-08-29T06:45:00Z")
        self.assertIn(("domain", "example.com"), record.attributes)
        self.assertIn(("language", "English"), record.attributes)
        self.assertIn(("sourcecountry", "United States"), record.attributes)

    def test_the_record_names_no_native_id_and_no_engagement(self):
        page, _ = fetch(ONE_ARTICLE, AdapterRequest(step_id="s1", query="climate"))

        record = page.records[0]
        self.assertEqual(record.native_item_id, "")
        self.assertEqual(record.engagement, ())

    def test_the_standing_losses_are_exactly_the_three_gdelt_deserves(self):
        page, _ = fetch(ONE_ARTICLE, AdapterRequest(step_id="s1", query="climate"))

        record = page.records[0]
        self.assertIn(gdelt.NATIVE_IDENTITY_UNKNOWN, record.loss)
        self.assertIn(gdelt.ENGAGEMENT_UNAVAILABLE, record.loss)
        self.assertIn(gdelt.TARGET_NOT_HYDRATED, record.loss)
        self.assertNotIn("unknown_publication_time", record.loss)

    def test_a_row_missing_an_optional_attribute_omits_it_rather_than_blanking_it(self):
        body = ONE_ARTICLE.replace('"language": "English",\n      ', "")
        page, _ = fetch(body, AdapterRequest(step_id="s1", query="climate"))

        names = {name for name, _ in page.records[0].attributes}
        self.assertNotIn("language", names)
        self.assertIn("domain", names)

    def test_two_articles_keep_their_own_positions(self):
        page, _ = fetch(TWO_ARTICLES, AdapterRequest(step_id="s1", query="climate"))

        self.assertEqual(len(page.records), 2)
        self.assertEqual(page.records[0].native_position, 0)
        self.assertEqual(page.records[1].native_position, 1)
        self.assertEqual(page.records[1].published_at, "2026-08-30T12:30:00Z")


class WindowTest(unittest.TestCase):
    def test_an_unwindowed_call_sends_no_date_bounds(self):
        _, opener = fetch(ONE_ARTICLE, AdapterRequest(step_id="s1", query="climate"))

        url = opener.opened[0].url
        self.assertIsNone(query_param(url, "startdatetime"))
        self.assertIsNone(query_param(url, "enddatetime"))

    def test_a_windowed_call_sends_both_bounds_in_the_origins_own_shape(self):
        request = AdapterRequest(
            step_id="s1",
            query="climate",
            window_start="2026-08-29T00:00:00Z",
            window_end="2026-09-01T00:00:00Z",
        )
        _, opener = fetch(ONE_ARTICLE, request)

        url = opener.opened[0].url
        self.assertEqual(query_param(url, "startdatetime"), "20260829000000")
        self.assertEqual(query_param(url, "enddatetime"), "20260901000000")

    def test_only_one_edge_sends_only_that_bound(self):
        request = AdapterRequest(
            step_id="s1", query="climate", window_start="2026-08-29T00:00:00Z"
        )
        _, opener = fetch(ONE_ARTICLE, request)

        url = opener.opened[0].url
        self.assertEqual(query_param(url, "startdatetime"), "20260829000000")
        self.assertIsNone(query_param(url, "enddatetime"))

    def test_the_windowed_and_unwindowed_requests_genuinely_differ(self):
        _, unwindowed = fetch(ONE_ARTICLE, AdapterRequest(step_id="s1", query="climate"))
        _, windowed = fetch(
            ONE_ARTICLE,
            AdapterRequest(
                step_id="s1", query="climate", window_start="2026-08-29T00:00:00Z"
            ),
        )

        self.assertNotEqual(unwindowed.opened[0].url, windowed.opened[0].url)


class FixedShapeAndQueryTest(unittest.TestCase):
    def test_the_fixed_shape_is_sent_every_time(self):
        _, opener = fetch(ONE_ARTICLE, AdapterRequest(step_id="s1", query="climate"))

        url = opener.opened[0].url
        self.assertEqual(query_param(url, "mode"), "artlist")
        self.assertEqual(query_param(url, "format"), "json")
        self.assertEqual(query_param(url, "maxrecords"), "75")
        self.assertEqual(query_param(url, "query"), "climate")

    def test_a_hydration_shaped_request_is_served_as_its_own_empty_query(self):
        # This module reads `request.query` alone, the same way `web_search`
        # reads its own: `target_ids` is never consulted, so a hydration
        # step's request (query empty, target_ids populated) is served, not
        # specially refused. An empty-string param is never sent at all
        # (`_support.transport_request.build_transport_request` drops it),
        # so the origin sees no `query` key rather than a blank one.
        request = AdapterRequest(step_id="s1", target_ids=("some-hit",))
        page, opener = fetch(NO_MATCH_OBJECT, request)

        self.assertIsNone(query_param(opener.opened[0].url, "query"))
        self.assertEqual(len(opener.opened), 1)
        self.assertEqual(page.outcome, "empty")


class EmptyTest(unittest.TestCase):
    def test_the_origins_own_no_match_shape_is_a_typed_empty_outcome(self):
        page, _ = fetch(NO_MATCH_OBJECT, AdapterRequest(step_id="s1", query="zzzznothing"))

        self.assertEqual(page.outcome, "empty")
        self.assertEqual(page.records, ())
        self.assertTrue(page.warnings)
        self.assertEqual(page.loss, ())

    def test_a_no_match_answer_is_never_schema_drift(self):
        page, _ = fetch(NO_MATCH_OBJECT, AdapterRequest(step_id="s1", query="zzzznothing"))

        self.assertNotIn(gdelt.SCHEMA_DRIFT, page.loss)

    def test_an_explicit_empty_articles_list_is_also_a_typed_empty_outcome(self):
        page, _ = fetch(EMPTY_ARTICLES_LIST, AdapterRequest(step_id="s1", query="zzzz"))

        self.assertEqual(page.outcome, "empty")
        self.assertEqual(page.records, ())
        self.assertNotIn(gdelt.SCHEMA_DRIFT, page.loss)


class DriftTest(unittest.TestCase):
    def test_a_non_list_articles_is_schema_drift(self):
        page, _ = fetch(ARTICLES_NOT_A_LIST, AdapterRequest(step_id="s1", query="climate"))

        self.assertEqual(page.outcome, "failed")
        self.assertIn(gdelt.SCHEMA_DRIFT, page.loss)

    def test_rows_present_but_none_carrying_a_url_is_schema_drift(self):
        page, _ = fetch(NO_URL_ON_ANY_ROW, AdapterRequest(step_id="s1", query="climate"))

        self.assertEqual(page.outcome, "failed")
        self.assertIn(gdelt.SCHEMA_DRIFT, page.loss)

    def test_a_top_level_payload_that_is_not_an_object_is_schema_drift(self):
        page, _ = fetch(TOP_LEVEL_NOT_AN_OBJECT, AdapterRequest(step_id="s1", query="climate"))

        self.assertEqual(page.outcome, "failed")
        self.assertIn(gdelt.SCHEMA_DRIFT, page.loss)

    def test_a_mix_of_identified_and_not_keeps_the_good_row_and_warns(self):
        page, _ = fetch(MIXED_IDENTIFIABLE, AdapterRequest(step_id="s1", query="climate"))

        self.assertEqual(page.outcome, "ok")
        self.assertEqual(len(page.records), 1)
        self.assertTrue(page.warnings)
        self.assertIn("url", page.warnings[0])


class HttpAndJsonFailureTest(unittest.TestCase):
    def test_a_non_200_status_is_http_status(self):
        # 429 is intercepted by `fetch_one_page` itself, ahead of this
        # module's own parse, and typed `rate_limited` rather than
        # `http_status` — a status this parser types is any other refusal.
        page, _ = fetch(
            "internal error",
            AdapterRequest(step_id="s1", query="climate"),
            status=503,
            content_type="text/plain",
        )

        self.assertEqual(page.outcome, "failed")
        self.assertIn(gdelt.HTTP_STATUS, page.loss)
        self.assertEqual(page.records, ())

    def test_a_200_plain_text_rejection_is_malformed_json(self):
        # Measured 2026-09-01: a `startdatetime` outside the origin's
        # retained span answers 200 with this exact plain-text line, never
        # JSON.
        page, _ = fetch(
            INVALID_START_DATE_TEXT,
            AdapterRequest(step_id="s1", query="climate"),
            content_type="text/html; charset=utf-8",
        )

        self.assertEqual(page.outcome, "failed")
        self.assertIn(gdelt.MALFORMED_JSON, page.loss)
        self.assertEqual(page.records, ())

    def test_a_200_echoed_headers_rejection_is_also_malformed_json(self):
        # Measured 2026-09-01: `mode=badmode` answers 200 with its own
        # response headers echoed into the body ahead of the plain-text
        # complaint.
        page, _ = fetch(
            INVALID_MODE_TEXT,
            AdapterRequest(step_id="s1", query="climate"),
            content_type="text/html; charset=utf-8",
        )

        self.assertEqual(page.outcome, "failed")
        self.assertIn(gdelt.MALFORMED_JSON, page.loss)


class OneCallTest(unittest.TestCase):
    def test_one_fetch_spends_exactly_one_call_on_the_declared_route(self):
        _, opener = fetch(ONE_ARTICLE, AdapterRequest(step_id="s1", query="climate"))

        self.assertEqual(len(opener.opened), 1)
        self.assertEqual(opener.opened[0].route_id, ROUTE)


class NoCursorTest(unittest.TestCase):
    def test_artlist_offers_no_cursor(self):
        page, _ = fetch(TWO_ARTICLES, AdapterRequest(step_id="s1", query="climate"))

        self.assertEqual(page.cursor_out, "")


if __name__ == "__main__":
    unittest.main()
