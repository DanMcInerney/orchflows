"""Scoped Reddit archive search retains bounds and typed origin failures."""
import json
import unittest
from urllib.parse import parse_qs, urlsplit

from super_research import runner, schema, transport


POST = {"id": "abc", "title": "Python release", "selftext": "Details",
        "author": "alice", "subreddit": "python", "permalink": "/r/python/comments/abc/topic/",
        "created_utc": 1788955200, "score": 0, "num_comments": 2}


def acquire(adapter, query, body, *, status=200, window=False):
    step = dict(step_id="read", kind="discovery", adapter_id=adapter, max_items=5, query=query)
    if window:
        step.update(window_start="2026-09-08T00:00:00Z", window_end="2026-09-10T00:00:00Z")
    manifest = schema.parse_manifest(dict(manifest_id="recent-routes", as_of="2026-09-10T23:00:00Z", steps=[step]))
    carrier = transport.Transport(opener=lambda request: (status, body, "text/html", request.url, ()),
                                  now=lambda: "2026-09-10T12:00:00Z")
    return runner.run_acquisition(manifest, carrier=carrier), carrier


class RecentRoutesTests(unittest.TestCase):


    def test_archive_search_requires_scope_and_sends_the_declared_window(self):
        artifact, carrier = acquire("reddit_archive", "search:subreddit=python&title=release", json.dumps({"data": [POST]}), window=True)
        self.assertEqual(len(artifact.records), 1)
        query = parse_qs(urlsplit(carrier.calls[0].url).query)
        self.assertEqual(query["subreddit"], ["python"])
        self.assertIn("after", query)
        self.assertIn("before", query)
        self.assertIn("third_party_archive", artifact.records[0].loss)
        refused, carrier = acquire("reddit_archive", "search:title=release", '{}')
        self.assertFalse(carrier.calls)
        self.assertIn("scope_required", refused.loss)

    def test_archive_422_throttle_and_malformed_search_are_typed(self):
        artifact, _ = acquire("reddit_archive", "search:subreddit=python", '{"error":"slow down"}', status=422)
        self.assertIn("rate_limited", artifact.loss)
        refused, carrier = acquire("reddit_archive", "search:subreddit=python&limit=100000", '{}')
        self.assertFalse(carrier.calls)
        self.assertIn("unselected_target", refused.loss)


if __name__ == "__main__":
    unittest.main()
