"""Reddit RSS surfaces share a budget through the default acquisition path."""
import threading
import unittest
from unittest import mock

from super_research import pacing, runner, schema, transport
from tests.helpers import FakeClock
from tests.test_recent_routes import ATOM


def manifest(queries, mode="staged", extra=()):
    steps = [dict(step_id="rss-{0}".format(index), kind="discovery",
                  adapter_id="reddit_feed", query=query, max_items=1)
             for index, query in enumerate(queries)]
    return schema.parse_manifest(dict(
        schema_version=2, manifest_id="rss-origin-budget", mode=mode,
        as_of="2026-09-10T23:00:00Z", steps=steps + list(extra)))


class RecentRssPacingTests(unittest.TestCase):
    def test_both_route_orders_share_spacing_and_keep_distinct_cache_entries(self):
        for queries in (("python", "search:python"), ("search:python", "python")):
            with self.subTest(queries=queries):
                clock, calls = FakeClock(), []

                def opener(request):
                    calls.append((request.route_id, clock.seconds))
                    return 200, ATOM, "application/atom+xml"

                with mock.patch.object(transport, "urlopen_read", side_effect=opener), \
                        mock.patch.object(pacing.time, "sleep", side_effect=clock.sleep):
                    artifact = runner.run_acquisition(
                        manifest(queries + queries), clock=clock.monotonic)
                self.assertEqual(artifact.outcome, "ok")
                self.assertEqual(len(calls), 2)
                self.assertEqual({route for route, _ in calls},
                                 {transport.REDDIT_FEED_ROUTE, transport.REDDIT_SEARCH_FEED_ROUTE})
                self.assertEqual([at for _, at in calls], [0, 30])
                self.assertEqual([step.route_id for step in artifact.steps],
                                 [calls[0][0], calls[1][0]] * 2)

    def test_refusal_cooldown_survives_either_explicit_route_change(self):
        for queries in (("python", "search:python"), ("search:python", "python")):
            with self.subTest(queries=queries):
                clock, calls = FakeClock(), []

                def opener(request):
                    calls.append(clock.seconds)
                    if len(calls) == 1:
                        return 429, "slow down", "text/plain", request.url, (("Retry-After", "90"),)
                    return 200, ATOM, "application/atom+xml"

                with mock.patch.object(transport, "urlopen_read", side_effect=opener), \
                        mock.patch.object(pacing.time, "sleep", side_effect=clock.sleep):
                    artifact = runner.run_acquisition(manifest(queries), clock=clock.monotonic)
                self.assertEqual(calls, [0, 90])
                self.assertIn("rate_limited", artifact.steps[0].loss)
                self.assertEqual(artifact.steps[1].outcome, "ok")
                self.assertEqual(artifact.outcome, "partial")

    def test_an_unrelated_origin_can_finish_while_reddit_is_waiting(self):
        clock = FakeClock()
        waiting, other_finished = threading.Event(), threading.Event()

        def sleep(seconds):
            waiting.set()
            self.assertTrue(other_finished.wait(5), "another origin waited on Reddit's budget")
            clock.sleep(seconds)

        def opener(request):
            if request.route_id == transport.XCANCEL_SEARCH_ROUTE:
                self.assertTrue(waiting.wait(5), "the RSS surfaces never shared a wait")
                other_finished.set()
                return 200, '<div class="timeline"><div class="timeline-none">No items</div></div>', "text/html"
            return 200, ATOM, "application/atom+xml"

        extra = (dict(step_id="other", kind="discovery", adapter_id="x_xcancel",
                      query="search:python", max_items=1),)
        with mock.patch.object(transport, "urlopen_read", side_effect=opener), \
                mock.patch.object(pacing.time, "sleep", side_effect=sleep):
            artifact = runner.run_acquisition(
                manifest(("python", "search:python"), mode="fused", extra=extra),
                clock=clock.monotonic)
        self.assertTrue(other_finished.is_set())
        self.assertEqual(artifact.outcome, "ok")


if __name__ == "__main__":
    unittest.main()
