"""Public acquisition behaviors added by the September source review."""
import json
import unittest
from urllib.parse import parse_qs, urlsplit

from super_research import coverage, runner, schema, transport


TWEET = '''<div class="timeline"><div class="timeline-item">
<a class="tweet-link" href="/alice/status/123#m"></a>
<a class="username">@alice</a><span class="tweet-date">
<a href="/alice/status/123#m" title="Sep 9, 2026 · 12:00 PM UTC">1d</a></span>
<div class="tweet-content media-body">A public <b>Python</b> post.</div>
<div class="quote"><div class="tweet-content">Another author's quotation</div></div>
<span class="tweet-stat"><span class="icon-comment"></span>1,234</span>
<span class="tweet-stat"><span class="icon-heart"></span>2.1K</span>
</div></div>'''
POST = {"id": "abc", "title": "Python release", "selftext": "Details",
        "author": "alice", "subreddit": "python", "permalink": "/r/python/comments/abc/topic/",
        "created_utc": 1788955200, "score": 0, "num_comments": 2}
ATOM = '''<feed><entry><id>t3_abc</id><title>Python release</title>
<link href="https://www.reddit.com/r/python/comments/abc/topic/"/>
<author><name>/u/alice</name></author><updated>2026-09-09T12:00:00Z</updated>
</entry></feed>'''


def acquire(adapter, query, body, *, status=200, kind="discovery", target=None, window=False):
    step = dict(step_id="read", kind=kind, adapter_id=adapter, max_items=5)
    if target is not None:
        step["selected_hits"] = [{"discovery_locator": "https://x.com/alice/status/123", "target_id": target}]
    else:
        step["query"] = query
    if window:
        step.update(window_start="2026-09-08T00:00:00Z", window_end="2026-09-10T00:00:00Z")
    manifest = schema.parse_manifest(dict(schema_version=2, manifest_id="recent-routes", mode="staged",
                                          as_of="2026-09-10T23:00:00Z", steps=[step]))
    carrier = transport.Transport(opener=lambda request: (status, body, "text/html"),
                                  now=lambda: "2026-09-10T12:00:00Z")
    return runner.run_acquisition(manifest, carrier=carrier), carrier


class RecentRoutesTests(unittest.TestCase):
    def test_xcancel_empty_requires_a_closed_timeline_with_no_unread_rows(self):
        empty = '<div class="timeline-none">No items found</div>'
        cases = (
            ('<div class="timeline">' + empty + '</div>', "empty", ()),
            ('<div class="timeline"></div><footer class="timeline-none">Footer</footer>', "failed", ("schema_drift",)),
            ('<div class="timeline">' + empty + '<div class="timeline-item"><div class="tweet-content">Unfinished', "failed", ("schema_drift",)),
            ('<div class="timeline">' + empty, "failed", ("schema_drift",)),
            (TWEET.removeprefix('<div class="timeline">').removesuffix('</div>'), "failed", ("schema_drift",)),
        )
        for body, outcome, loss in cases:
            with self.subTest(body=body):
                artifact, _ = acquire("x_xcancel", "search:python", body)
                self.assertEqual(artifact.outcome, outcome)
                self.assertEqual(artifact.loss, loss)
                self.assertFalse(artifact.records)

    def test_xcancel_keeps_readable_rows_and_reports_unreadable_siblings(self):
        for sibling in ('<div class="timeline-item"><div class="tweet-content">Missing identity</div></div>',
                        '<div class="timeline-item"><a class="tweet-link" href="/alice/status/456"></a>'):
            body = TWEET.removesuffix('</div>') + sibling
            if sibling.endswith('</div>'):
                body += '</div>'
            with self.subTest(sibling=sibling):
                artifact, _ = acquire("x_xcancel", "search:python", body)
                self.assertEqual(artifact.outcome, "partial")
                self.assertIn("schema_drift", artifact.loss)
                self.assertEqual([record.native_item_id for record in artifact.records], ["123"])

    def test_xcancel_selected_status_ignores_other_readable_statuses(self):
        body = TWEET.removesuffix('</div>') + TWEET.replace('/123', '/456').removeprefix('<div class="timeline">')
        artifact, _ = acquire("x_xcancel", "", body, kind="hydration", target="status:alice/123")
        self.assertEqual([record.native_item_id for record in artifact.records], ["123"])
        self.assertEqual(artifact.outcome, "ok")

    def test_xcancel_nested_rows_are_lost_without_contaminating_valid_siblings(self):
        row = TWEET.removeprefix('<div class="timeline">').removesuffix('</div>')
        child = row.replace('/123', '/789')
        outer = '<div class="timeline-item"><a class="tweet-link" href="/alice/status/456"></a>'
        malformed = (
            outer + '<div class="tweet-content">Outer text. </div>' + child + '</div>',
            outer + '<div class="tweet-content">Outer text. ' + child + '</div></div>',
            outer + '<span class="tweet-stat"><span class="icon-comment"></span>42' + child + '</span></div>',
        )
        for placement, nested in zip(("sibling", "body", "count"), malformed):
            for following in ('', row.replace('/123', '/987')):
                with self.subTest(placement=placement, following=bool(following)):
                    artifact, _ = acquire("x_xcancel", "search:python",
                                          '<div class="timeline">' + row + nested + following + '</div>')
                    self.assertEqual(artifact.outcome, "partial")
                    self.assertEqual(artifact.loss, ("schema_drift",))
                    self.assertEqual([record.native_item_id for record in artifact.records],
                                     ["123", "987"] if following else ["123"])
                    for record in artifact.records:
                        self.assertEqual(record.body, "A public Python post.")
                        self.assertEqual(record.author, "alice")
                        self.assertEqual(record.published_at, "2026-09-09T12:00:00Z")
                        self.assertEqual({s.metric_name: s.value for s in record.engagement}, {"icon-comment": 1234})

    def test_xcancel_nested_rows_cannot_supply_a_selected_status(self):
        row = TWEET.removeprefix('<div class="timeline">').removesuffix('</div>')
        malformed = row.replace('/123', '/456').removesuffix('</div>') + row.replace('/123', '/789') + '</div>'
        for target in ("status:alice/456", "status:alice/789"):
            with self.subTest(target=target):
                artifact, _ = acquire("x_xcancel", "", '<div class="timeline">' + row + malformed + '</div>',
                                      kind="hydration", target=target)
                self.assertFalse(artifact.records)
                self.assertEqual(artifact.outcome, "failed")
                self.assertEqual(artifact.loss, ("schema_drift",))

    def test_xcancel_quote_cards_isolate_nested_rows_without_malformed_loss(self):
        row = TWEET.removeprefix('<div class="timeline">').removesuffix('</div>')
        child = (row.replace('/123', '/789').replace('alice', 'bob').replace('2026', '2001')
                 .replace('A public', 'Quoted').replace('1,234', '99'))
        for quote_class in ("quote", "quote-big", "quote-link"):
            for direct in (False, True):
                with self.subTest(quote_class=quote_class, direct=direct):
                    quote = (child.replace('class="timeline-item"', 'class="timeline-item ' + quote_class + '"', 1)
                             if direct else '<div class="' + quote_class + '">' + child + '</div>')
                    body = TWEET.replace('<div class="quote"><div class="tweet-content">Another author\'s quotation</div></div>', quote)
                    artifact, _ = acquire("x_xcancel", "search:python", body)
                    self.assertEqual(artifact.outcome, "ok")
                    self.assertEqual(artifact.loss, ())
                    record, = artifact.records
                    self.assertEqual(record.native_item_id, "123")
                    self.assertEqual(record.body, "A public Python post.")
                    self.assertEqual(record.author, "alice")
                    self.assertEqual(record.published_at, "2026-09-09T12:00:00Z")
                    self.assertEqual({s.metric_name: s.value for s in record.engagement}, {"icon-comment": 1234})

    def test_xcancel_search_reads_only_the_post_and_exact_counts(self):
        artifact, carrier = acquire("x_xcancel", "search:python", TWEET, window=True)
        self.assertEqual(len(carrier.calls), 1)
        record, = artifact.records
        self.assertEqual(record.normalized_locator, "https://x.com/alice/status/123")
        self.assertEqual(record.body, "A public Python post.")
        self.assertEqual(record.author, "alice")
        self.assertEqual(record.published_at, "2026-09-09T12:00:00Z")
        self.assertEqual({s.metric_name: s.value for s in record.engagement}, {"icon-comment": 1234})
        self.assertIn("third_party_archive", record.loss)
        self.assertIn("window_capability_unmeasured", artifact.steps[0].loss)

    def test_xcancel_status_is_selected_and_unsafe_targets_make_no_request(self):
        artifact, carrier = acquire("x_xcancel", "", TWEET, kind="hydration", target="status:alice/123")
        self.assertEqual(len(artifact.records), 1)
        self.assertEqual(urlsplit(carrier.calls[0].url).path, "/alice/status/123")
        refused, carrier = acquire("x_xcancel", "", TWEET, kind="hydration", target="status:../123")
        self.assertEqual(len(carrier.calls), 0)
        self.assertIn("unselected_target", refused.loss)

    def test_discovered_xcancel_locator_plans_only_its_selected_status(self):
        discovery, _ = acquire("x_xcancel", "search:python", TWEET)
        plan = coverage.plan_depth(discovery.records, "x_xcancel", "status", "selected", 1)
        hit, = plan.steps[0].selected_hits
        self.assertEqual(hit.target_id, "status:https://x.com/alice/status/123")
        hydrated, carrier = acquire("x_xcancel", "", TWEET, kind="hydration", target=hit.target_id)
        self.assertEqual(hydrated.records[0].normalized_locator, hit.discovery_locator)
        self.assertEqual(urlsplit(carrier.calls[0].url).path, "/alice/status/123")
        for target in ("status:https://x.com.evil/alice/status/123", "status:https://alice@x.com/alice/status/123",
                       "status:https://x.com/alice/status/123?next=evil"):
            refused, carrier = acquire("x_xcancel", "", TWEET, kind="hydration", target=target)
            self.assertFalse(carrier.calls)
            self.assertIn("unselected_target", refused.loss)

    def test_xcancel_challenge_rate_limit_and_drift_never_become_empty(self):
        for status, body, loss in [(200, '<title>Verifying your browser…</title><script>captcha</script>', 'attestation_required'),
                                   (429, 'slow down', 'rate_limited'), (200, '<html>changed</html>', 'schema_drift')]:
            with self.subTest(loss=loss):
                artifact, carrier = acquire("x_xcancel", "python", body, status=status)
                self.assertEqual(len(carrier.calls), 1)
                self.assertFalse(artifact.records)
                self.assertIn(loss, artifact.loss)
                self.assertNotEqual(artifact.outcome, "empty")

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

    def test_reddit_rss_search_preserves_feed_identity_without_invented_counts(self):
        artifact, carrier = acquire("reddit_feed", "search:python", ATOM, window=True)
        self.assertEqual(urlsplit(carrier.calls[0].url).path, "/search.rss")
        query = parse_qs(urlsplit(carrier.calls[0].url).query)
        self.assertEqual(query["q"], ["python"])
        self.assertEqual(query["sort"], ["new"])
        record, = artifact.records
        self.assertEqual(record.native_item_id, "t3_abc")
        self.assertFalse(record.engagement)
        self.assertIn("engagement_unavailable", record.loss)


if __name__ == "__main__":
    unittest.main()
