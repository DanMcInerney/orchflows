"""Original paper reads and source-qualified dates across the real checkpoints."""

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from xml.sax.saxutils import escape

import acquire
import acquire_plan
from super_research import normalize, schema, transport
from super_research.adapters import NativeRecord, build_native_page, fake
from tests.helpers import FakeClock


STAMP = "2026-09-09T12:00:00Z"


def plan_for(adapter, query, max_items=4, depth=True):
    return {
        "version": 1, "plan_id": "source-dates", "question": "Inspect original evidence and its publication date.",
        "as_of": "2026-09-10T23:59:59Z",
        "window": {"start": "2026-09-08T00:00:00Z", "end": "2026-09-10T00:00:00Z"},
        "allowed_adapters": [adapter, "open_page"],
        "limits": {"max_steps": 2, "max_requests": 2, "max_records": max_items + 1, "max_seconds": 30},
        "discovery": [{"step_id": "source", "adapter_id": adapter, "query": query, "max_items": max_items}],
        "depth": [{"depth_id": "document", "adapter_id": "open_page", "operation": "",
                   "from_steps": ["source"], "max_items": 1, "max_targets": 1}] if depth else [],
    }


def crossref_item(url, index=0):
    return {"DOI": "10.1234/paper" + str(index), "URL": url, "title": ["A source paper"],
            "type": "journal-article", "author": [{"given": "Ada", "family": "Researcher"}],
            "published": {"date-parts": [[2026, 9, 9]]}, "is-referenced-by-count": 2,
            "abstract": "<jats:p>The original abstract and its limits.</jats:p>"}


def publisher_feed(url, published="Wed, 09 Sep 2026 12:00:00 GMT"):
    return ("<rss><channel><item><title>A source paper</title><link>" + escape(url) +
            "</link><description>A publisher's summary.</description><pubDate>" + published +
            "</pubDate></item></channel></rss>")


class PaperDateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def runtime(self, discovery_route, discovery_body, document="", document_url=None, discovery_url=None):
        opened = []
        clock = FakeClock()

        def opener(request):
            opened.append(request)
            if request.route_id == discovery_route and (discovery_url is None or request.url == discovery_url):
                return 200, discovery_body, "application/xml" if discovery_body.startswith("<") else "application/json", request.url, ()
            if request.route_id == transport.WEB_PAGE_OPEN_ROUTE:
                return 200, document, "text/html", document_url or request.url, ()
            raise AssertionError("Unexpected route: " + request.route_id)

        return {"opener": opener, "now": lambda: "2026-09-10T12:00:00Z",
                "clock": clock.monotonic, "sleep": clock.sleep}, opened

    def select_document(self, plan, output, runtime, row):
        batch = json.loads((output / "candidates.json").read_text())
        selection = {"candidate_id": batch["candidate_id"], "choices": [
            {"record_id": row["record_id"], "depth_id": "document",
             "reason": "Read this original document to inspect its evidence and date."}],
            "omission_reason": "Only this original document is needed for the bounded comparison."}
        result = acquire.execute(plan, output, selection, **runtime)
        self.assertEqual(result["phase"], "complete")
        before = (output / "packet.json").read_bytes()
        resumed = acquire.execute(plan, output, **runtime)
        self.assertEqual(resumed["requests_this_invocation"], 0)
        self.assertEqual(before, (output / "packet.json").read_bytes())
        return json.loads(before)

    def test_native_papers_offer_exact_document_and_keep_linked_metadata_on_resume(self):
        crossref_url = "https://papers.example.net/article/?version=1#abstract"
        arxiv_url = "https://arxiv.org/abs/2609.01234v1"
        arxiv = '''<feed xmlns="http://www.w3.org/2005/Atom"><entry>
            <id>http://arxiv.org/abs/2609.01234v1</id><title>A source paper</title>
            <published>2026-09-09T12:00:00Z</published><updated>2026-09-10T00:00:00Z</updated>
            <author><name>Ada Researcher</name></author><summary>The original abstract and its limits.</summary>
            <link href="https://arxiv.org/abs/2609.01234v1" rel="alternate" type="text/html"/>
            </entry></feed>'''
        cases = (
            ("crossref", transport.CROSSREF_WORKS_ROUTE,
             json.dumps({"message": {"items": [crossref_item(crossref_url)]}}), crossref_url),
            ("arxiv", transport.ARXIV_QUERY_ROUTE, arxiv, arxiv_url),
        )
        # A readable destination may omit author/date. No metadata is borrowed
        # into it: the exact selected source record supplies those via the edge.
        document = "<html><head><title>Paper evidence</title></head><body><article><p>" + (
            "Full document evidence and explicit limitations. " * 1200) + "</p></article></body></html>"
        for operation, route, payload, locator in cases:
            with self.subTest(operation=operation):
                output = self.root / operation
                plan = plan_for("scholarly", operation + ":source paper")
                runtime, opened = self.runtime(route, payload, document)
                first = acquire.execute(plan, output, **runtime)
                self.assertEqual(first["phase"], "selection_required")
                rows = json.loads((output / "candidates.json").read_text())["candidates"]
                self.assertEqual(len(rows), 1)
                row = rows[0]
                self.assertEqual(row["representation_kind"], "native")
                self.assertEqual(row["options"], ["document"])
                self.assertEqual(row["canonical_locator"], locator)
                packet = self.select_document(plan, output, runtime, row)
                original, child = packet["records"]
                self.assertEqual(original["author"], "Ada Researcher")
                self.assertTrue(original["published_at"].startswith("2026-09-09"))
                self.assertIn("original abstract", original["body"])
                self.assertEqual(dict(original["attributes"])["body_representation"], "abstract")
                self.assertEqual(child["author"], "")
                self.assertEqual(child["published_at"], "")
                self.assertEqual(child["usable_basis_time"], "")
                self.assertEqual(child["time_confidence"], "unknown")
                self.assertGreater(len(child["body"]), 54000)
                self.assertNotIn("published_at_basis", dict(child["attributes"]))
                self.assertEqual(packet["edges"], [{"edge_kind": "discovery_hydration",
                    "from_record_id": original["record_id"], "to_record_id": child["record_id"]}])
                self.assertEqual(child["discovery_locator"], original["normalized_locator"])
                self.assertEqual([request.route_id for request in opened], [route, transport.WEB_PAGE_OPEN_ROUTE])
                self.assertEqual(opened[1].url, locator)
                self.assertEqual(dict(child["attributes"])["requested_url"], locator)

    def test_new_publisher_feed_date_does_not_hide_old_original_publication(self):
        locator = "https://papers.example.net/article/?version=1#methods"
        feed_url = "https://publisher.example.net/feed.xml"
        plan = plan_for("rss_atom", feed_url)
        document = '''<html><head><title>Original publication</title>
            <meta property="article:published_time" content="1998-04-01T00:00:00Z">
            <meta name="author" content="Original Author"></head>
            <body><article><p>The older source's actual evidence.</p></article></body></html>'''
        runtime, opened = self.runtime(transport.WEB_PAGE_OPEN_ROUTE, publisher_feed(locator), document,
                                       discovery_url=feed_url)
        output = self.root / "old-original"
        acquire.execute(plan, output, **runtime)
        row = json.loads((output / "candidates.json").read_text())["candidates"][0]
        self.assertEqual(row["published_at"], STAMP)
        self.assertEqual(row["time_confidence"], "reported")
        self.assertEqual(dict(row["attributes"])["published_at_basis"], "publisher_reported")
        self.assertEqual(row["date_eligibility"], "reported_in_window")
        self.assertIn("check the original source", row["date_qualification"])
        packet = self.select_document(plan, output, runtime, row)
        original, child = packet["records"]
        self.assertEqual(original["published_at"], STAMP)
        self.assertEqual(child["published_at"], "1998-04-01T00:00:00Z")
        self.assertEqual(child["author"], "Original Author")
        self.assertEqual(child["time_confidence"], "authoritative")
        self.assertEqual(acquire_plan.candidates(plan, [acquire.record_from(child)])[0]["date_eligibility"], "outside_window")
        self.assertEqual(packet["edges"][0]["from_record_id"], original["record_id"])
        self.assertEqual(packet["edges"][0]["to_record_id"], child["record_id"])
        self.assertEqual(opened[1].url, locator)
        self.assertEqual(len(opened), 2)

    def test_unsafe_or_platform_paper_locators_never_offer_document_depth(self):
        locators = ["http://papers.example.net/paper", "https://localhost/paper", "https://127.0.0.1/paper",
                    "https://10.0.0.1/paper", "https://user:secret@papers.example.net/paper",
                    "https://papers.example.net:8443/paper", "https://papers.example.net:bad/paper",
                    "https://export.arxiv.org/api/query", "https://www.reddit.com/r/test/comments/abc/paper",
                    "https://api.crossref.org/works/10.1234/paper", "https://example.net/paper\n", ""]
        plan = plan_for("scholarly", "crossref:source paper", len(locators) + 1)
        payload = json.dumps({"message": {"items": [crossref_item(url, index) for index, url in enumerate(locators)]}})
        runtime, opened = self.runtime(transport.CROSSREF_WORKS_ROUTE, payload)
        output = self.root / "refused-locators"
        first = acquire.execute(plan, output, **runtime)
        rows = json.loads((output / "candidates.json").read_text())["candidates"]
        self.assertEqual(len(rows), len(locators))
        for row in rows:
            with self.subTest(locator=row["canonical_locator"]):
                self.assertEqual(row["options"], [])
                selection = {"candidate_id": first["candidate_id"], "choices": [{
                    "record_id": row["record_id"], "depth_id": "document", "reason": "Try this exact carrier."}],
                    "omission_reason": "Other records omitted."}
                with self.assertRaises(acquire_plan.PlanError):
                    acquire.execute(plan, output, selection, **runtime)
        self.assertEqual(len(opened), 1)

    def test_missing_publisher_feed_date_remains_unknown(self):
        feed_url = "https://publisher.example.net/feed.xml"
        plan = plan_for("rss_atom", feed_url, depth=False)
        runtime, opened = self.runtime(transport.WEB_PAGE_OPEN_ROUTE,
            publisher_feed("https://publisher.example.net/article", published=""), discovery_url=feed_url)
        output = self.root / "undated-feed"
        acquire.execute(plan, output, **runtime)
        row = json.loads((output / "candidates.json").read_text())["candidates"][0]
        self.assertEqual(row["time_confidence"], "unknown")
        self.assertEqual(row["date_eligibility"], "unknown")
        self.assertNotIn("published_at_basis", dict(row["attributes"]))
        self.assertEqual(len(opened), 1)

    def test_index_representation_dates_are_provisional_even_in_offline_records(self):
        plan = plan_for("rss_atom", "https://publisher.example.net/feed.xml", depth=False)
        descriptor = replace(fake.DESCRIPTOR, representation_kind="index")
        page = build_native_page(descriptor, tuple(
            NativeRecord(canonical_content_kind="page", canonical_locator="https://example.net/" + name,
                         title="An index entry", body="An index summary.", published_at=stamp)
            for name, stamp in (("dated", STAMP), ("undated", ""))), observed_at=STAMP)
        step = schema.AcquisitionStep(step_id="source", adapter_id="fake", kind="discovery", max_items=2)
        records = normalize.normalize_page(page, step, "artifact", "manifest")
        dated, undated = acquire_plan.candidates(plan, records)
        self.assertEqual(dated["time_confidence"], "reported")
        self.assertEqual(dict(dated["attributes"])["published_at_basis"], "index_reported")
        self.assertEqual(dated["date_eligibility"], "reported_in_window")
        self.assertIn("requires verification", dated["date_qualification"])
        self.assertEqual(undated["published_at"], "")
        self.assertEqual(undated["time_confidence"], "unknown")
        self.assertEqual(undated["date_eligibility"], "unknown")


if __name__ == "__main__":
    unittest.main()
