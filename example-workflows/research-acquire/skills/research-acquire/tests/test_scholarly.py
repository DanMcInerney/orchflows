"""Crossref and arXiv reads: explicit grammar, abstract facts, bounds and typed failures."""

from __future__ import annotations

import unittest
import urllib.parse
from pathlib import Path

from super_research import transport
from super_research.adapters import AdapterRequest, scholarly
from tests import helpers

CROSSREF_ROUTE = transport.CROSSREF_WORKS_ROUTE
ARXIV_ROUTE = transport.ARXIV_QUERY_ROUTE

JSON_CONTENT_TYPE = "application/json"
ATOM_CONTENT_TYPE = "application/atom+xml; charset=utf-8"

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "scholarly"


def fetch(route, body, request, status=200, content_type=JSON_CONTENT_TYPE):
    clock = helpers.FakeClock()
    carrier, opener = helpers.offline_transport(clock, {route: (status, body, content_type)})
    page = scholarly.fetch_native_page(carrier, request)
    return page, opener


def query_param(url, name):
    values = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query).get(name, [])
    return values[0] if values else None


def read_fixture(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


# --- Hand-built bodies, one field controlled at a time ---------------------


CR_ONE_ITEM = """
{
  "message": {
    "items": [
      {
        "DOI": "10.1/abc",
        "type": "journal-article",
        "title": ["A Title"],
        "author": [{"given": "Ada", "family": "Lovelace"}],
        "published": {"date-parts": [[2021, 3, 15]]},
        "is-referenced-by-count": 7,
        "URL": "https://doi.org/10.1/abc",
        "container-title": ["Journal Of Things"],
        "publisher": "Acme Press"
      }
    ]
  }
}
"""
CR_MONTH_ONLY = """
{"message": {"items": [
  {"DOI": "10.1/month", "type": "journal-article", "title": ["Month Precision"],
   "author": [{"given": "Ada", "family": "Lovelace"}],
   "published": {"date-parts": [[2015, 9]]}, "URL": "https://doi.org/10.1/month"}
]}}
"""
CR_YEAR_ONLY = """
{"message": {"items": [
  {"DOI": "10.1/year", "type": "book-chapter", "title": ["Year Precision"],
   "published": {"date-parts": [[2015]]}, "URL": "https://doi.org/10.1/year"}
]}}
"""
CR_NO_AUTHOR = """
{"message": {"items": [
  {"DOI": "10.1/noauthor", "type": "book-chapter", "title": ["No Author"],
   "published": {"date-parts": [[2020, 1, 1]]}, "URL": "https://doi.org/10.1/noauthor"}
]}}
"""
CR_EMPTY = '{"message": {"items": []}}'
CR_NO_ITEMS_KEY = '{"message": {}}'
CR_NO_MESSAGE_KEY = '{}'
CR_UNIDENTIFIABLE = '{"message": {"items": [{"title": ["no doi here"]}]}}'
CR_MIXED = """
{"message": {"items": [
  {"title": ["no doi here"]},
  {"DOI": "10.1/x", "type": "journal-article", "title": ["One"],
   "published": {"date-parts": [[2020, 1, 1]]}, "URL": "https://doi.org/10.1/x"}
]}}
"""
CR_NOT_JSON = "<html>not json</html>"

ATOM_NS = 'xmlns="http://www.w3.org/2005/Atom"'
AX_ONE_ENTRY = """<?xml version='1.0' encoding='UTF-8'?>
<feed {ns}>
<entry>
<id>http://arxiv.org/abs/1234.5678v1</id>
<title>
  A Great Paper
  On Things
</title>
<published>2021-03-15T12:00:00Z</published>
<updated>2021-03-16T00:00:00Z</updated>
<summary>
  A summary
  spanning multiple lines.
</summary>
<author><name>Ada Lovelace</name></author>
<author><name>Alan Turing</name></author>
<link href="https://arxiv.org/abs/1234.5678v1" rel="alternate" type="text/html"/>
<link href="https://arxiv.org/pdf/1234.5678v1" rel="related" type="application/pdf" title="pdf"/>
</entry>
</feed>
""".format(ns=ATOM_NS)
AX_EMPTY = '<feed {0}></feed>'.format(ATOM_NS)
AX_NOT_ATOM = "<html><body>not atom</body></html>"
AX_UNIDENTIFIABLE = """<feed {0}>
<entry><title>no id here</title>
<link href="https://arxiv.org/abs/9v1" rel="alternate" type="text/html"/>
</entry>
</feed>""".format(ATOM_NS)
AX_MIXED = """<feed {0}>
<entry><title>no id here</title>
<link href="https://arxiv.org/abs/9v1" rel="alternate" type="text/html"/>
</entry>
<entry>
<id>http://arxiv.org/abs/1v1</id>
<title>One</title>
<published>2020-01-01T00:00:00Z</published>
<link href="https://arxiv.org/abs/1v1" rel="alternate" type="text/html"/>
</entry>
</feed>""".format(ATOM_NS)




class CrossrefHappyParseTest(unittest.TestCase):
    def test_an_item_carries_the_roster_field_set(self):
        page, _ = fetch(
            CROSSREF_ROUTE, CR_ONE_ITEM, AdapterRequest(step_id="s1", query="crossref:things")
        )

        self.assertEqual(page.outcome, "ok")
        record = page.records[0]
        self.assertEqual(record.canonical_content_kind, "journal-article")
        self.assertEqual(record.native_item_id, "10.1/abc")
        self.assertEqual(record.title, "A Title")
        self.assertEqual(record.author, "Ada Lovelace")
        self.assertEqual(record.canonical_locator, "https://doi.org/10.1/abc")
        self.assertEqual(record.published_at, "2021-03-15T00:00:00Z")
        self.assertIn("date_precision_only", record.loss)
        self.assertEqual(dict(record.engagement), {"is-referenced-by-count": 7})
        self.assertIn(("container-title", "Journal Of Things"), record.attributes)
        self.assertIn(("publisher", "Acme Press"), record.attributes)
        # Crossref does not get repeated author attributes: only OpenAlex and
        # arXiv do, per the roster's own field set.
        self.assertNotIn(("author", "Ada Lovelace"), record.attributes)

    def test_the_real_captured_fixture_parses(self):
        page, _ = fetch(
            CROSSREF_ROUTE,
            read_fixture("crossref_works.json"),
            AdapterRequest(step_id="s1", query="crossref:machine learning"),
        )

        self.assertEqual(page.outcome, "ok")
        self.assertGreater(len(page.records), 0)
        for record in page.records:
            self.assertTrue(record.native_item_id)


class CrossrefMonthPrecisionTest(unittest.TestCase):
    def test_a_month_only_date_leaves_published_at_empty(self):
        page, _ = fetch(
            CROSSREF_ROUTE, CR_MONTH_ONLY, AdapterRequest(step_id="s1", query="crossref:x")
        )

        record = page.records[0]
        self.assertEqual(record.published_at, "")
        self.assertNotIn("date_precision_only", record.loss)
        self.assertIn(("published_date_parts", "2015-9"), record.attributes)

    def test_a_year_only_date_leaves_published_at_empty_too(self):
        page, _ = fetch(
            CROSSREF_ROUTE, CR_YEAR_ONLY, AdapterRequest(step_id="s1", query="crossref:x")
        )

        record = page.records[0]
        self.assertEqual(record.published_at, "")
        self.assertNotIn("date_precision_only", record.loss)
        self.assertIn(("published_date_parts", "2015"), record.attributes)

    def test_a_full_day_carries_the_instant_and_the_precision_code(self):
        page, _ = fetch(
            CROSSREF_ROUTE, CR_ONE_ITEM, AdapterRequest(step_id="s1", query="crossref:x")
        )

        record = page.records[0]
        self.assertEqual(record.published_at, "2021-03-15T00:00:00Z")
        self.assertIn("date_precision_only", record.loss)
        self.assertNotIn("published_date_parts", dict(record.attributes))

    def test_no_day_is_ever_invented(self):
        for body in (CR_MONTH_ONLY, CR_YEAR_ONLY):
            with self.subTest(body=body):
                page, _ = fetch(
                    CROSSREF_ROUTE, body, AdapterRequest(step_id="s1", query="crossref:x")
                )
                self.assertNotIn("T", page.records[0].published_at)


class CrossrefAuthorAbsenceTest(unittest.TestCase):
    def test_an_absent_author_list_is_an_empty_author_not_a_failure(self):
        page, _ = fetch(
            CROSSREF_ROUTE, CR_NO_AUTHOR, AdapterRequest(step_id="s1", query="crossref:x")
        )

        self.assertEqual(page.outcome, "ok")
        self.assertEqual(page.records[0].author, "")


class ArxivHappyParseTest(unittest.TestCase):
    def test_an_entry_carries_the_roster_field_set(self):
        page, _ = fetch(
            ARXIV_ROUTE,
            AX_ONE_ENTRY,
            AdapterRequest(step_id="s1", query="arxiv:things"),
            content_type=ATOM_CONTENT_TYPE,
        )

        self.assertEqual(page.outcome, "ok")
        record = page.records[0]
        self.assertEqual(record.canonical_content_kind, "preprint")
        self.assertEqual(record.native_item_id, "http://arxiv.org/abs/1234.5678v1")
        self.assertEqual(record.title, "A Great Paper On Things")
        self.assertEqual(record.author, "Ada Lovelace")
        self.assertEqual(record.canonical_locator, "https://arxiv.org/abs/1234.5678v1")
        self.assertEqual(record.published_at, "2021-03-15T12:00:00Z")
        self.assertEqual(record.body, "A summary spanning multiple lines.")
        self.assertEqual(record.loss, ())
        self.assertIn(("author", "Ada Lovelace"), record.attributes)
        self.assertIn(("author", "Alan Turing"), record.attributes)
        self.assertIn(("pdf_url", "https://arxiv.org/pdf/1234.5678v1"), record.attributes)

    def test_the_real_captured_fixture_parses(self):
        page, _ = fetch(
            ARXIV_ROUTE,
            read_fixture("arxiv_query.xml"),
            AdapterRequest(step_id="s1", query="arxiv:machine learning"),
            content_type=ATOM_CONTENT_TYPE,
        )

        self.assertEqual(page.outcome, "ok")
        self.assertGreater(len(page.records), 0)
        for record in page.records:
            self.assertTrue(record.native_item_id)
            self.assertTrue(record.published_at)


class OperationGrammarTest(unittest.TestCase):


    def test_the_crossref_prefix_reaches_crossref(self):
        _, opener = fetch(
            CROSSREF_ROUTE, CR_EMPTY, AdapterRequest(step_id="s1", query="crossref:things")
        )

        self.assertEqual(opener.opened[0].route_id, CROSSREF_ROUTE)
        self.assertEqual(query_param(opener.opened[0].url, "query"), "things")

    def test_the_arxiv_prefix_reaches_arxiv(self):
        _, opener = fetch(
            ARXIV_ROUTE,
            AX_EMPTY,
            AdapterRequest(step_id="s1", query="arxiv:things"),
            content_type=ATOM_CONTENT_TYPE,
        )

        self.assertEqual(opener.opened[0].route_id, ARXIV_ROUTE)
        self.assertIn('all:"things"', query_param(opener.opened[0].url, "search_query"))


    def test_a_target_id_is_read_the_same_way_as_a_query(self):
        _, opener = fetch(
            CROSSREF_ROUTE,
            CR_EMPTY,
            AdapterRequest(step_id="s1", target_ids=("crossref:things",)),
        )

        self.assertEqual(opener.opened[0].route_id, CROSSREF_ROUTE)
        self.assertEqual(query_param(opener.opened[0].url, "query"), "things")


class WindowTest(unittest.TestCase):




    def test_crossref_unwindowed_sends_no_filter(self):
        _, opener = fetch(
            CROSSREF_ROUTE, CR_EMPTY, AdapterRequest(step_id="s1", query="crossref:things")
        )

        self.assertIsNone(query_param(opener.opened[0].url, "filter"))

    def test_crossref_windowed_sends_both_edges(self):
        request = AdapterRequest(
            step_id="s1",
            query="crossref:things",
            window_start="2020-01-01T00:00:00Z",
            window_end="2020-12-31T00:00:00Z",
        )
        _, opener = fetch(CROSSREF_ROUTE, CR_EMPTY, request)

        self.assertEqual(
            query_param(opener.opened[0].url, "filter"),
            "from-pub-date:2020-01-01,until-pub-date:2020-12-31",
        )

    def test_crossref_one_edge_sends_only_that_clause(self):
        request = AdapterRequest(
            step_id="s1", query="crossref:things", window_end="2020-12-31T00:00:00Z"
        )
        _, opener = fetch(CROSSREF_ROUTE, CR_EMPTY, request)

        self.assertEqual(
            query_param(opener.opened[0].url, "filter"), "until-pub-date:2020-12-31"
        )

    def test_arxiv_unwindowed_sends_no_submitted_date_clause(self):
        _, opener = fetch(
            ARXIV_ROUTE,
            AX_EMPTY,
            AdapterRequest(step_id="s1", query="arxiv:things"),
            content_type=ATOM_CONTENT_TYPE,
        )

        self.assertNotIn(
            "submittedDate", query_param(opener.opened[0].url, "search_query")
        )

    def test_arxiv_windowed_sends_both_edges(self):
        request = AdapterRequest(
            step_id="s1",
            query="arxiv:things",
            window_start="2020-01-01T00:00:00Z",
            window_end="2020-12-31T23:59:00Z",
        )
        _, opener = fetch(ARXIV_ROUTE, AX_EMPTY, request, content_type=ATOM_CONTENT_TYPE)

        search_query = query_param(opener.opened[0].url, "search_query")
        self.assertIn("submittedDate:[202001010000 TO 202012312359]", search_query)

    def test_arxiv_missing_end_fills_the_far_future_sentinel(self):
        request = AdapterRequest(
            step_id="s1", query="arxiv:things", window_start="2020-01-01T00:00:00Z"
        )
        _, opener = fetch(ARXIV_ROUTE, AX_EMPTY, request, content_type=ATOM_CONTENT_TYPE)

        search_query = query_param(opener.opened[0].url, "search_query")
        self.assertIn(
            "submittedDate:[202001010000 TO {0}]".format(scholarly.ARXIV_FAR_FUTURE),
            search_query,
        )

    def test_arxiv_missing_start_fills_the_far_past_sentinel(self):
        request = AdapterRequest(
            step_id="s1", query="arxiv:things", window_end="2020-12-31T23:59:00Z"
        )
        _, opener = fetch(ARXIV_ROUTE, AX_EMPTY, request, content_type=ATOM_CONTENT_TYPE)

        search_query = query_param(opener.opened[0].url, "search_query")
        self.assertIn(
            "submittedDate:[{0} TO 202012312359]".format(scholarly.ARXIV_FAR_PAST),
            search_query,
        )

    def test_arxiv_windowed_and_unwindowed_genuinely_differ(self):
        _, unwindowed = fetch(
            ARXIV_ROUTE,
            AX_EMPTY,
            AdapterRequest(step_id="s1", query="arxiv:things"),
            content_type=ATOM_CONTENT_TYPE,
        )
        _, windowed = fetch(
            ARXIV_ROUTE,
            AX_EMPTY,
            AdapterRequest(
                step_id="s1", query="arxiv:things", window_start="2020-01-01T00:00:00Z"
            ),
            content_type=ATOM_CONTENT_TYPE,
        )

        self.assertNotEqual(unwindowed.opened[0].url, windowed.opened[0].url)


class EmptyTest(unittest.TestCase):

    def test_crossref_empty_items_is_a_typed_empty_outcome(self):
        page, _ = fetch(
            CROSSREF_ROUTE, CR_EMPTY, AdapterRequest(step_id="s1", query="crossref:zzz")
        )

        self.assertEqual(page.outcome, "empty")
        self.assertEqual(page.records, ())
        self.assertTrue(page.warnings)

    def test_arxiv_empty_feed_is_a_typed_empty_outcome(self):
        page, _ = fetch(
            ARXIV_ROUTE,
            AX_EMPTY,
            AdapterRequest(step_id="s1", query="arxiv:zzz"),
            content_type=ATOM_CONTENT_TYPE,
        )

        self.assertEqual(page.outcome, "empty")
        self.assertEqual(page.records, ())
        self.assertTrue(page.warnings)


class DriftTest(unittest.TestCase):



    def test_crossref_missing_message_is_schema_drift(self):
        page, _ = fetch(
            CROSSREF_ROUTE, CR_NO_MESSAGE_KEY, AdapterRequest(step_id="s1", query="crossref:x")
        )

        self.assertEqual(page.outcome, "failed")
        self.assertIn(scholarly.SCHEMA_DRIFT, page.loss)

    def test_crossref_missing_items_is_schema_drift(self):
        page, _ = fetch(
            CROSSREF_ROUTE, CR_NO_ITEMS_KEY, AdapterRequest(step_id="s1", query="crossref:x")
        )

        self.assertEqual(page.outcome, "failed")
        self.assertIn(scholarly.SCHEMA_DRIFT, page.loss)

    def test_crossref_rows_present_but_none_identified_is_schema_drift(self):
        page, _ = fetch(
            CROSSREF_ROUTE, CR_UNIDENTIFIABLE, AdapterRequest(step_id="s1", query="crossref:x")
        )

        self.assertEqual(page.outcome, "failed")
        self.assertIn(scholarly.SCHEMA_DRIFT, page.loss)

    def test_crossref_a_mix_keeps_the_good_rows_and_warns(self):
        page, _ = fetch(CROSSREF_ROUTE, CR_MIXED, AdapterRequest(step_id="s1", query="crossref:x"))

        self.assertEqual(page.outcome, "ok")
        self.assertEqual(len(page.records), 1)
        self.assertTrue(page.warnings)

    def test_arxiv_a_document_not_rooted_in_feed_is_schema_drift(self):
        page, _ = fetch(
            ARXIV_ROUTE,
            AX_NOT_ATOM,
            AdapterRequest(step_id="s1", query="arxiv:x"),
            content_type=ATOM_CONTENT_TYPE,
        )

        self.assertEqual(page.outcome, "failed")
        self.assertIn(scholarly.SCHEMA_DRIFT, page.loss)

    def test_arxiv_entries_present_but_none_identified_is_schema_drift(self):
        page, _ = fetch(
            ARXIV_ROUTE,
            AX_UNIDENTIFIABLE,
            AdapterRequest(step_id="s1", query="arxiv:x"),
            content_type=ATOM_CONTENT_TYPE,
        )

        self.assertEqual(page.outcome, "failed")
        self.assertIn(scholarly.SCHEMA_DRIFT, page.loss)

    def test_arxiv_a_mix_keeps_the_good_rows_and_warns(self):
        page, _ = fetch(
            ARXIV_ROUTE,
            AX_MIXED,
            AdapterRequest(step_id="s1", query="arxiv:x"),
            content_type=ATOM_CONTENT_TYPE,
        )

        self.assertEqual(page.outcome, "ok")
        self.assertEqual(len(page.records), 1)
        self.assertTrue(page.warnings)


class HttpAndJsonFailureTest(unittest.TestCase):


    def test_crossref_non_200_is_http_status(self):
        page, _ = fetch(
            CROSSREF_ROUTE, "{}", AdapterRequest(step_id="s1", query="crossref:x"), status=404
        )

        self.assertEqual(page.outcome, "failed")
        self.assertIn(scholarly.HTTP_STATUS, page.loss)

    def test_crossref_200_not_json_is_malformed_json(self):
        page, _ = fetch(
            CROSSREF_ROUTE,
            CR_NOT_JSON,
            AdapterRequest(step_id="s1", query="crossref:x"),
            content_type="text/html",
        )

        self.assertEqual(page.outcome, "failed")
        self.assertIn(scholarly.MALFORMED_JSON, page.loss)

    def test_arxiv_non_200_is_http_status(self):
        page, _ = fetch(
            ARXIV_ROUTE,
            "server error",
            AdapterRequest(step_id="s1", query="arxiv:x"),
            status=500,
            content_type=ATOM_CONTENT_TYPE,
        )

        self.assertEqual(page.outcome, "failed")
        self.assertIn(scholarly.HTTP_STATUS, page.loss)


class OneCallTest(unittest.TestCase):

    def test_crossref_fetch_spends_exactly_one_call(self):
        _, opener = fetch(
            CROSSREF_ROUTE, CR_EMPTY, AdapterRequest(step_id="s1", query="crossref:things")
        )

        self.assertEqual(len(opener.opened), 1)
        self.assertEqual(opener.opened[0].route_id, CROSSREF_ROUTE)

    def test_arxiv_fetch_spends_exactly_one_call(self):
        _, opener = fetch(
            ARXIV_ROUTE,
            AX_EMPTY,
            AdapterRequest(step_id="s1", query="arxiv:things"),
            content_type=ATOM_CONTENT_TYPE,
        )

        self.assertEqual(len(opener.opened), 1)
        self.assertEqual(opener.opened[0].route_id, ARXIV_ROUTE)


class EngagementExactIntegerLawTest(unittest.TestCase):


    def test_a_float_is_referenced_by_count_is_never_engagement(self):
        body = CR_ONE_ITEM.replace('"is-referenced-by-count": 7', '"is-referenced-by-count": 7.5')
        page, _ = fetch(CROSSREF_ROUTE, body, AdapterRequest(step_id="s1", query="crossref:x"))

        self.assertNotIn("is-referenced-by-count", dict(page.records[0].engagement))

    def test_a_missing_is_referenced_by_count_is_absent_rather_than_zero(self):
        body = CR_ONE_ITEM.replace('"is-referenced-by-count": 7,', "")
        page, _ = fetch(CROSSREF_ROUTE, body, AdapterRequest(step_id="s1", query="crossref:x"))

        self.assertNotIn("is-referenced-by-count", dict(page.records[0].engagement))


if __name__ == "__main__":
    unittest.main()
