"""A feed entry can be selected for bounded article depth and resumed intact."""
import json
from pathlib import Path
import tempfile
import unittest

import acquire
from acquire_plan import PlanError
from tests.helpers import FakeClock
from tests.test_public_feeds import ATOM, FEED_URL


class FeedAcquisitionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.output = Path(temporary.name) / "evidence"
        self.clock = FakeClock(start="2026-09-12T12:00:00Z")
        self.opened = []
        self.feed = ATOM
        self.article = '''<html><head><title>A new result</title>
          <meta property="article:published_time" content="2026-09-11T13:30:00Z"/></head>
          <body><article><p>The experiment measured its error rate over repeated trials.</p></article></body></html>'''
        self.plan = dict(version=1, plan_id="feed-article", question="What did the experiment measure?",
            as_of="2026-09-12T13:00:00Z",
            window=dict(start="2026-08-13T00:00:00Z", end="2026-09-12T12:00:00Z"),
            allowed_adapters=["rss_atom", "open_page"],
            limits=dict(max_steps=2, max_requests=2, max_records=11, max_seconds=120),
            discovery=[dict(step_id="feed", adapter_id="rss_atom", query=FEED_URL, max_items=10)],
            depth=[dict(depth_id="article", adapter_id="open_page", operation="",
                        from_steps=["feed"], max_items=1, max_targets=1)])

    def opener(self, request):
        self.opened.append(request)
        if request.url == FEED_URL:
            return 200, self.feed, "application/atom+xml", request.url, ()
        return 200, self.article, "text/html", request.url, ()

    def execute(self, **kwargs):
        return acquire.execute(self.plan, self.output, opener=self.opener, now=self.clock.stamp,
                               clock=self.clock.monotonic, sleep=self.clock.sleep, **kwargs)

    def batch(self):
        return json.loads((self.output / "candidates.json").read_text())

    def selection(self, row):
        return dict(candidate_id=self.batch()["candidate_id"],
                    choices=[dict(record_id=row["record_id"], depth_id="article",
                                  reason="Inspect the reported experiment's method and limitations.")],
                    omission_reason="Other entries do not identify a new, dated experiment.")

    def test_feed_discovery_article_selection_and_checkpoint_resume_preserve_provenance(self):
        first = self.execute()
        self.assertEqual(first["phase"], "selection_required")
        self.assertEqual(first["requests_total"], 1)
        selected = next(row for row in self.batch()["candidates"] if row["native_item_id"] == "new")
        self.assertEqual(selected["representation_kind"], "feed")
        self.assertEqual(selected["options"], ["article"])

        def interrupt_after_saved_depth(step_id):
            if step_id == "depth-1":
                raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            self.execute(selection=self.selection(selected), after_checkpoint=interrupt_after_saved_depth)
        self.assertEqual([request.url for request in self.opened],
                         [FEED_URL, selected["normalized_locator"]])
        result = self.execute()
        self.assertEqual(result["phase"], "complete")
        self.assertEqual(result["requests_total"], 2)
        self.assertEqual(result["requests_this_invocation"], 0)
        self.assertEqual(set(result["reused_steps"]), {"feed", "depth-1"})
        packet_bytes = (self.output / "packet.json").read_bytes()
        packet = json.loads(packet_bytes)
        discovery = next(row for row in packet["records"] if row["record_id"] == selected["record_id"])
        depth = next(row for row in packet["records"] if row["step_id"] == "depth-1")
        self.assertEqual(dict(discovery["attributes"])["feed_url"], FEED_URL)
        self.assertEqual(depth["body"], "The experiment measured its error rate over repeated trials.")
        self.assertEqual(depth["discovery_locator"], selected["normalized_locator"])
        self.assertEqual(packet["edges"], [dict(edge_kind="discovery_hydration",
                         from_record_id=selected["record_id"], to_record_id=depth["record_id"])])
        self.assertEqual(self.execute()["requests_this_invocation"], 0)
        self.assertEqual((self.output / "packet.json").read_bytes(), packet_bytes)
        self.assertEqual(len(self.opened), 2)

    def test_unsafe_or_platform_refused_feed_links_offer_no_article_depth(self):
        urls = ["http://publisher.example/article", "https://127.0.0.1/article",
                "https://www.reddit.com/r/python/comments/abc/topic/",
                "https://user:secret@publisher.example/article", "https://[broken"]
        self.feed = '<feed xmlns="http://www.w3.org/2005/Atom">' + "".join(
            '<entry><id>{0}</id><title>Candidate</title><published>2026-09-11T12:00:00Z</published>'
            '<link href="{1}"/></entry>'.format(index, url) for index, url in enumerate(urls)) + '</feed>'
        self.execute()
        rows = self.batch()["candidates"]
        self.assertEqual(len(rows), len(urls))
        for row in rows:
            with self.subTest(locator=row["canonical_locator"]):
                self.assertEqual(row["options"], [])
                with self.assertRaises(PlanError):
                    self.execute(selection=self.selection(row))
        self.assertEqual(len(self.opened), 1)


if __name__ == "__main__":
    unittest.main()
