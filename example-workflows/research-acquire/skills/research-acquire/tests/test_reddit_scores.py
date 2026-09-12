"""Signed native Reddit scores survive acquisition without admitting bad counts."""

import json
import tempfile
import unittest
from pathlib import Path

import acquire
from acquire_fixture import fixture_plan, fixture_runtime
from super_research import normalize, schema, transport


class RedditScoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / "evidence"
        self.plan = fixture_plan()
        self.plan["allowed_adapters"] = ["reddit_archive", "reddit_shreddit"]
        self.plan["discovery"] = self.plan["discovery"][:1]
        self.plan["depth"] = self.plan["depth"][:1]
        self.runtime, self.opened = fixture_runtime()

    def test_downvoted_archive_post_and_live_comment_survive_selection_and_resume(self):
        opener = self.runtime["opener"]

        def signed(request):
            status, body, content_type, url, headers = opener(request)
            if request.route_id == transport.ARCTIC_SHIFT_SEARCH_ROUTE:
                source = json.loads(body)["data"][0]
                zero = dict(source, id="zero", score=0, num_comments=0,
                            permalink="/r/BitcoinMarkets/comments/zero/daily/")
                missing = dict(source, id="missing", permalink="/r/BitcoinMarkets/comments/missing/daily/")
                missing.pop("score")
                missing.pop("num_comments")
                body = json.dumps({"data": [dict(source, score=-4), zero, missing]})
            elif request.route_id == transport.REDDIT_SHREDDIT_COMMENTS_ROUTE:
                body = body.replace('score="2"', 'score="-7"')
            return status, body, content_type, url, headers

        self.runtime["opener"] = signed
        first = acquire.execute(self.plan, self.output, **self.runtime)
        candidates = json.loads((self.output / "candidates.json").read_text())["candidates"]
        by_id = {row["native_item_id"]: row for row in candidates}
        metrics = lambda row: {item["metric_name"]: item["value"] for item in row["engagement"]}
        self.assertEqual(metrics(by_id["t3_abc"]), {"score": -4, "num_comments": 5})
        self.assertEqual(metrics(by_id["t3_zero"]), {"score": 0, "num_comments": 0})
        self.assertEqual(metrics(by_id["t3_missing"]), {})
        selected = {"candidate_id": first["candidate_id"], "choices": [{
            "record_id": by_id["t3_abc"]["record_id"], "depth_id": "comments",
            "reason": "Inspect the discussion under this downvoted post."}],
            "omission_reason": "The zero and missing-score posts do not need depth for this check."}
        result = acquire.execute(self.plan, self.output, selected, **self.runtime)
        self.assertEqual(result["phase"], "complete")
        packet = (self.output / "packet.json").read_bytes()
        artifact = json.loads(packet)
        comment = next(row for row in artifact["records"] if row["canonical_content_kind"] == "comment")
        self.assertEqual(comment["platform"], "reddit")
        self.assertEqual(metrics(comment), {"score": -7})
        self.assertEqual(artifact["edges"][0]["from_record_id"], by_id["t3_abc"]["record_id"])
        self.assertEqual(artifact["edges"][0]["to_record_id"], comment["record_id"])
        self.assertEqual(acquire.execute(self.plan, self.output, **self.runtime)["requests_this_invocation"], 0)
        self.assertEqual(packet, (self.output / "packet.json").read_bytes())
        self.assertEqual(len(self.opened), 2)

    def test_shreddit_listing_preserves_signed_zero_missing_and_refuses_bad_numbers(self):
        self.plan["discovery"] = [{"step_id": "listing", "adapter_id": "reddit_shreddit",
                                   "query": "listing:BitcoinMarkets", "max_items": 9}]
        self.plan["depth"] = []
        scores = ("-9", "0", None, "1.5", "-1k", "True", "²", "--2", "+2")
        posts = []
        for index, score in enumerate(scores):
            score_attr = '' if score is None else 'score="' + score + '"'
            posts.append('<shreddit-post id="t3_post{0}" post-title="A discussion" author="reader" '
                         'created-timestamp="2026-09-09T12:00:00Z" subreddit-prefixed-name="r/BitcoinMarkets" '
                         'permalink="/r/BitcoinMarkets/comments/post{0}/daily/" {1} '
                         'comment-count="{2}"></shreddit-post>'.format(index, score_attr, "0" if index == 0 else "-1"))

        def opener(request):
            self.opened.append(request)
            self.assertEqual(request.route_id, transport.REDDIT_SHREDDIT_LISTING_ROUTE)
            return 200, "".join(posts), "text/html", request.url, ()

        self.runtime["opener"] = opener
        result = acquire.execute(self.plan, self.output, **self.runtime)
        self.assertEqual(result["phase"], "complete")
        rows = json.loads((self.output / "packet.json").read_text())["records"]
        self.assertEqual(len(rows), len(scores))
        metrics = [{item["metric_name"]: item["value"] for item in row["engagement"]} for row in rows]
        self.assertEqual(metrics[0], {"score": -9, "comment-count": 0})
        self.assertEqual(metrics[1], {"score": 0})
        self.assertEqual(metrics[2:], [{}] * 7)

    def test_negative_archive_comment_count_is_still_refused(self):
        opener = self.runtime["opener"]

        def negative_count(request):
            status, body, content_type, url, headers = opener(request)
            payload = json.loads(body)
            payload["data"][0].update(score=-4, num_comments=-1)
            return status, json.dumps(payload), content_type, url, headers

        self.runtime["opener"] = negative_count
        with self.assertRaisesRegex(normalize.NormalizeError, "num_comments is out of range"):
            acquire.execute(self.plan, self.output, **self.runtime)
        self.assertEqual(len(self.opened), 1)

    def test_only_reddit_score_accepts_signed_integers_within_bounds(self):
        observed = "2026-09-10T12:00:00Z"
        minimum = -schema.MAX_ENGAGEMENT_VALUE - 1
        accepted = normalize.engagement_snapshots((("score", minimum),), observed, platform="reddit")
        self.assertEqual(accepted[0].value, minimum)
        for platform, name, value in (("reddit", "num_comments", -1), ("reddit", "comment-count", -1),
                                      ("hacker_news", "score", -1), ("", "score", -1),
                                      ("reddit", "score", True), ("reddit", "score", -1.5),
                                      ("reddit", "score", "-1"), ("reddit", "score", minimum - 1),
                                      ("reddit", "score", schema.MAX_ENGAGEMENT_VALUE + 1),
                                      ("reddit", "num_comments", True), ("reddit", "num_comments", 1.5),
                                      ("reddit", "num_comments", "1")):
            with self.subTest(platform=platform, name=name, value=value), self.assertRaises(normalize.NormalizeError):
                normalize.engagement_snapshots(((name, value),), observed, platform=platform)


if __name__ == "__main__":
    unittest.main()
