"""Acquisition preserves pacing debt and the exact semantic selection on resume."""

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import acquire
import acquire_checkpoint
from acquire_fixture import fixture_plan, fixture_runtime, choose
from super_research import transport
from tests.helpers import FakeClock


class AcquisitionRepairTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.output = Path(temporary.name)
        self.clock = FakeClock(start="2026-09-10T12:00:00Z")
        self.opened = []
        self.plan = fixture_plan()
        self.plan.update(allowed_adapters=["github_rest"], depth=[], window=None)
        self.runtime = dict(opener=self.opener, now=self.clock.stamp,
                            clock=self.clock.monotonic, sleep=self.clock.sleep, lanes=1)
        # Restarted governors use different monotonic epochs but the same wall
        # timeline. Pin that external clock without introducing real waits.
        self.wall = patch.object(acquire_checkpoint.time, "time", self.clock.monotonic)
        self.wall.start()
        self.addCleanup(self.wall.stop)
        transport.GUEST_TOKENS.clear()
        self.addCleanup(transport.GUEST_TOKENS.clear)

    def opener(self, request):
        self.opened.append((request.route_id, self.clock.seconds))
        body = '{"total_count": 0, "items": []}' if request.route_id == transport.GITHUB_SEARCH_ROUTE else "[]"
        return 200, body, "application/json", request.url, ()

    def searches(self, count, seconds=180):
        self.plan["discovery"] = [dict(step_id="s" + str(i), adapter_id="github_rest",
                                       query="search:q" + str(i), max_items=1) for i in range(count)]
        self.plan["limits"] = dict(max_steps=count, max_requests=count,
                                   max_records=count, max_seconds=seconds)

    def execute(self, **kwargs):
        return acquire.execute(self.plan, self.output, **self.runtime, **kwargs)

    def test_two_github_reads_fit_thirty_second_bound(self):
        self.searches(2, seconds=30)
        self.execute()
        self.assertEqual(len(self.opened), 2)
        packet = json.loads((self.output / "packet.json").read_text())
        self.assertEqual([row["outcome"] for row in packet["steps"]], ["empty", "empty"])
        self.assertEqual(self.clock.seconds, 0)

    def test_burst_refill_and_separate_github_route_survive_repeated_resume(self):
        self.searches(63)
        self.plan["discovery"][60]["query"] = "issues:octocat/Hello-World"
        def stop_after_receipt(step_id):
            raise KeyboardInterrupt()
        for index in range(63):
            with self.assertRaises(KeyboardInterrupt):
                self.execute(after_checkpoint=stop_after_receipt)
            self.assertEqual(len(self.opened), index + 1)
            if index == 60:
                self.clock.advance(30)  # Idle wall time refills across restarts.
        self.assertEqual([at for route, at in self.opened[:60]], [0] * 60)
        self.assertEqual(self.opened[60], (transport.GITHUB_REST_ROUTE, 0))
        self.assertEqual(self.opened[61:], [(transport.GITHUB_SEARCH_ROUTE, 60),
                                           (transport.GITHUB_SEARCH_ROUTE, 120)])
        self.assertEqual(self.execute()["requests_this_invocation"], 0)

    def test_uncertain_read_spends_burst(self):
        self.searches(61)
        original = self.runtime["opener"]
        def crash(request):
            original(request)
            raise KeyboardInterrupt()
        self.runtime["opener"] = crash
        with self.assertRaises(KeyboardInterrupt):
            self.execute()
        self.runtime["opener"] = original
        result = self.execute()
        self.assertEqual(result["uncertain_requests"], 1)
        self.assertEqual(len(self.opened), 61)
        self.assertEqual(self.opened[-1][1], 60)
        self.assertEqual(result["phase"], "incomplete")

    def test_refusal_blocks_all_origin_routes_after_resume(self):
        self.searches(3)
        self.plan["discovery"][2]["query"] = "issues:octocat/Hello-World"
        def refuse(request):
            self.opener(request)
            return 403, "Forbidden", "text/plain", request.url, ()
        self.runtime["opener"] = refuse
        def interrupt(step_id):
            raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            self.execute(after_checkpoint=interrupt)
        result = self.execute()
        self.assertEqual(len(self.opened), 1)
        self.assertEqual(result["requests_total"], 1)

    def test_a_refused_activation_keeps_its_loss_and_spends_no_interval_after_resume(self):
        self.check_refused_activation(401, "unauthorized", "auth_required")

    def test_a_rate_limited_activation_keeps_the_same_loss_in_receipts_and_checkpoint(self):
        self.check_refused_activation(429, "Too Many Requests", "rate_limited")

    def test_a_secondary_rate_limit_on_activation_stays_rate_limited_after_resume(self):
        self.check_refused_activation(403, "secondary rate limit", "rate_limited")

    def check_refused_activation(self, status, body, loss):
        self.plan.update(allowed_adapters=["x_guest"])
        self.plan["discovery"] = [dict(step_id="s0", adapter_id="x_guest", query="user:a", max_items=1),
                                  dict(step_id="s1", adapter_id="x_guest", query="user:b", max_items=1)]
        self.plan["limits"] = dict(max_steps=2, max_requests=4, max_records=2, max_seconds=180)
        def refuse_activation(request):
            self.opened.append((request.route_id, self.clock.seconds))
            if request.route_id == transport.X_GUEST_ACTIVATE_ROUTE:
                return status, body, "application/json", request.url, ()
            return 200, "{}", "application/json", request.url, ()
        self.runtime["opener"] = refuse_activation
        def interrupt(step_id):
            raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            self.execute(after_checkpoint=interrupt)
        pacing_before = json.loads((self.output / "checkpoint.json").read_text())["pacing"]
        # A new process holds no token memory: the refusal it knows is the checkpoint's.
        transport.GUEST_TOKENS.clear()
        result = self.execute()
        checkpoint = json.loads((self.output / "checkpoint.json").read_text())
        packet = json.loads((self.output / "packet.json").read_text())
        self.assertEqual(self.opened, [(transport.X_GUEST_ACTIVATE_ROUTE, 0)])
        self.assertEqual([row["loss"] for row in packet["steps"]], [[loss], [loss]])
        self.assertEqual(packet["loss"], [loss])
        self.assertEqual(checkpoint["refused_origins"], {"api.twitter.com": loss})
        self.assertEqual(checkpoint["pacing"], pacing_before)
        self.assertEqual(transport.GUEST_TOKENS._tokens, {})
        self.assertEqual(result["requests_this_invocation"], 0)

    def test_second_observation_and_cross_source_selection_keep_exact_edges(self):
        for cross_source in (False, True):
            with self.subTest(cross_source=cross_source):
                plan = fixture_plan()
                runtime, opened = fixture_runtime()
                original = runtime["opener"]
                if cross_source:
                    plan["depth"][0]["from_steps"].append("index")
                def duplicates(request):
                    status, body, content_type, url, headers = original(request)
                    if not cross_source and request.route_id == transport.ARCTIC_SHIFT_SEARCH_ROUTE:
                        payload = json.loads(body)
                        second = copy.deepcopy(payload["data"][0])
                        second.update(title="Second observation", score=97,
                                      created_utc=second["created_utc"] + 3600)
                        payload["data"].insert(1, second)
                        body = json.dumps(payload)
                    elif cross_source and request.route_id == "bing_rss":
                        body = body.replace("https://example.net/outlook",
                                            "https://www.reddit.com/r/BitcoinMarkets/comments/abc/daily/")
                    return status, body, content_type, url, headers
                runtime["opener"] = duplicates
                output = self.output / str(cross_source)
                acquire.execute(plan, output, **runtime)
                batch = json.loads((output / "candidates.json").read_text())
                selected = next(row for row in batch["candidates"] if (
                    row["adapter_id"] == "web_search" if cross_source else row["title"] == "Second observation"))
                selection = choose(output)
                selection["choices"] = [dict(record_id=selected["record_id"], depth_id="comments",
                                              reason="Inspect this exact observation.")]
                acquire.execute(plan, output, selection, **runtime)
                packet = (output / "packet.json").read_bytes()
                artifact = json.loads(packet)
                comment = next(row for row in artifact["records"] if row["body"] == "A conditional case, not a prediction.")
                edge = next(row for row in artifact["edges"] if row["to_record_id"] == comment["record_id"])
                self.assertEqual(edge["from_record_id"], selected["record_id"])
                observations = [row for row in artifact["records"] if row["normalized_locator"] == selected["normalized_locator"]]
                self.assertEqual(len(observations), 2)
                self.assertEqual(acquire.execute(plan, output, **runtime)["requests_this_invocation"], 0)
                self.assertEqual(packet, (output / "packet.json").read_bytes())


if __name__ == "__main__":
    unittest.main()
