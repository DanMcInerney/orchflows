"""Fused lanes: overlap across origins, one read at a time per origin.

`test_pipeline` proves the accounting of a run on a fake clock and one lane.
This suite proves the other half of what `fused` now means, and it needs a
real clock to do it: an opener that blocks lets two lanes on two origins be
caught inside their reads at the same moment, and an opener that sleeps lets
two lanes on one origin be shown never to be. Both proofs are made on the
recorded intervals of the reads themselves, so a governor that stopped taking
its origin lock, or a runner that stopped overlapping lanes, fails here rather
than at the first live run.

Nothing here reaches a socket: every opener is offline, and every fixture
route is the `fake` adapter's or a real adapter's with a canned answer.
"""

from __future__ import annotations

import json
import threading
import time
import unittest

from super_research import cache, runner, schema, transport
from tests import helpers

# Two adapters on two origins with the cheapest canned answers in the suite:
# the fixture adapter's own page, and Firebase's `null` for an item HN does
# not hold, which `hacker_news` reads as an ordinary empty answer.
FIXTURE_PAGE = json.dumps({"platform": "fixture", "records": [], "cursor_out": ""})
TWO_ORIGINS = {
    "schema_version": 2,
    "manifest_id": "lanes-two-origins",
    "mode": "fused",
    "as_of": "2026-08-17T12:00:00Z",
    "steps": [
        {"step_id": "s1-fixture", "kind": "discovery", "adapter_id": "fake", "query": "a", "max_items": 3},
        {"step_id": "s2-hn", "kind": "discovery", "adapter_id": "hacker_news", "query": "item:1", "max_items": 3},
    ],
}
# Two adapters on ONE origin: InnerTube and the channel feed both live on
# www.youtube.com, and are declared as two routes with two budgets.
ONE_ORIGIN = {
    "schema_version": 2,
    "manifest_id": "lanes-one-origin",
    "mode": "fused",
    "as_of": "2026-08-17T12:00:00Z",
    "steps": [
        {"step_id": "s1-feed", "kind": "discovery", "adapter_id": "rss_atom", "query": "UCabc", "max_items": 3},
        {"step_id": "s2-search", "kind": "discovery", "adapter_id": "youtube_innertube", "query": "search:x", "max_items": 3},
    ],
}
EMPTY_FEED = '<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><title>t</title></feed>'
EMPTY_SEARCH = json.dumps({"contents": {"twoColumnSearchResultsRenderer": {"primaryContents": {"sectionListRenderer": {"contents": []}}}}})


class IntervalOpener:
    """An offline opener that records when each read began and ended, on a real clock.

    ``hold`` is what every read waits inside the opener: a barrier makes two
    reads prove they were in flight together, and a sleep makes two reads
    show whether they ever were.
    """

    def __init__(self, answers, hold):
        self.answers = answers
        self.hold = hold
        self.intervals = []
        self.lock = threading.Lock()

    def __call__(self, request):
        began = time.monotonic()
        self.hold(request)
        answer = self.answers[request.route_id]
        ended = time.monotonic()
        with self.lock:
            self.intervals.append((request.route_id, transport.origin_key(request), began, ended))
        return answer


def governor_over(opener):
    carrier = transport.Transport(opener=opener)
    return runner.RateGovernor(carrier, run_cache=cache.RunCache())


class FusedLanesOverlapTest(unittest.TestCase):
    def test_two_lanes_on_two_origins_are_in_flight_at_the_same_moment(self):
        # A barrier both reads must reach before either returns: a serial
        # runner never gets both there and the wait times out; an overlapping
        # one gets both there at once. The timeout is the proof's own bound,
        # so a regression fails in seconds rather than hanging.
        barrier = threading.Barrier(2, timeout=5)
        arrived = []

        def hold(request):
            try:
                barrier.wait()
                arrived.append(request.route_id)
            except threading.BrokenBarrierError:
                arrived.append("timeout:" + request.route_id)

        opener = IntervalOpener(
            {
                transport.FAKE_OFFLINE_ROUTE: (200, FIXTURE_PAGE, "application/json"),
                transport.HN_FIREBASE_ITEM_ROUTE: (200, "null", "application/json"),
            },
            hold,
        )
        artifact = runner.run_acquisition(schema.parse_manifest(TWO_ORIGINS), governor_over(opener))

        self.assertEqual(sorted(arrived), sorted([transport.FAKE_OFFLINE_ROUTE, transport.HN_FIREBASE_ITEM_ROUTE]))
        self.assertEqual([step.step_id for step in artifact.steps], ["s1-fixture", "s2-hn"])
        # The barrier is the proof; the intervals corroborate it. Windows'
        # monotonic clock ticks at ~15 ms, so two reads caught inside one
        # tick begin and end at the same reading — hence "at or before".
        (_, _, began_a, ended_a), (_, _, began_b, ended_b) = opener.intervals
        self.assertLessEqual(max(began_a, began_b), min(ended_a, ended_b))

    def test_two_lanes_on_one_origin_never_overlap(self):
        # Two lanes, one host, each read sleeping long enough that an overlap
        # would be visible: the governor's origin lock keeps the two intervals
        # disjoint however the pool schedules them.
        def hold(request):
            time.sleep(0.05)

        opener = IntervalOpener(
            {
                transport.YOUTUBE_CHANNEL_FEED_ROUTE: (200, EMPTY_FEED, "application/atom+xml"),
                transport.YOUTUBE_INNERTUBE_ROUTE: (200, EMPTY_SEARCH, "application/json"),
            },
            hold,
        )
        runner.run_acquisition(schema.parse_manifest(ONE_ORIGIN), governor_over(opener))

        self.assertEqual(len(opener.intervals), 2)
        self.assertEqual(len({origin for _, origin, _, _ in opener.intervals}), 1)
        (_, _, began_a, ended_a), (_, _, began_b, ended_b) = sorted(
            opener.intervals, key=lambda interval: interval[2]
        )
        self.assertLessEqual(ended_a, began_b)

    def test_one_lane_asked_for_runs_the_fused_manifest_serially(self):
        # `lanes=1` is the serial line, whatever the mode says: no read can be
        # inside the opener while another is.
        barrier = threading.Barrier(2, timeout=0.5)
        outcomes = []

        def hold(request):
            try:
                barrier.wait()
                outcomes.append("both")
            except threading.BrokenBarrierError:
                outcomes.append("alone")

        opener = IntervalOpener(
            {
                transport.FAKE_OFFLINE_ROUTE: (200, FIXTURE_PAGE, "application/json"),
                transport.HN_FIREBASE_ITEM_ROUTE: (200, "null", "application/json"),
            },
            hold,
        )
        runner.run_acquisition(
            schema.parse_manifest(TWO_ORIGINS), governor_over(opener), lanes=1
        )

        self.assertEqual(outcomes, ["alone", "alone"])

    def test_the_artifact_is_assembled_in_declared_step_order_whatever_finished_first(self):
        # The fixture lane sleeps and the HN lane does not, so the HN read
        # finishes first; the artifact still lists steps and records in the
        # order the manifest declared them.
        def hold(request):
            if request.route_id == transport.FAKE_OFFLINE_ROUTE:
                time.sleep(0.05)

        opener = IntervalOpener(
            {
                transport.FAKE_OFFLINE_ROUTE: (200, FIXTURE_PAGE, "application/json"),
                transport.HN_FIREBASE_ITEM_ROUTE: (200, "null", "application/json"),
            },
            hold,
        )
        artifact = runner.run_acquisition(schema.parse_manifest(TWO_ORIGINS), governor_over(opener))

        self.assertEqual([interval[0] for interval in opener.intervals][0], transport.HN_FIREBASE_ITEM_ROUTE)
        self.assertEqual([step.step_id for step in artifact.steps], ["s1-fixture", "s2-hn"])


class LanesAreByAdapterTest(unittest.TestCase):
    def test_lanes_group_steps_by_adapter_in_declared_order(self):
        manifest = schema.parse_manifest(
            {
                "schema_version": 2,
                "manifest_id": "lanes-grouping",
                "mode": "fused",
                "as_of": "2026-08-17T12:00:00Z",
                "steps": [
                    {"step_id": "a1", "kind": "discovery", "adapter_id": "fake", "query": "a", "max_items": 1},
                    {"step_id": "b1", "kind": "discovery", "adapter_id": "hacker_news", "query": "item:1", "max_items": 1},
                    {"step_id": "a2", "kind": "discovery", "adapter_id": "fake", "query": "b", "max_items": 1},
                ],
            }
        )
        lanes = runner.lanes_of(manifest.steps)

        self.assertEqual(list(lanes), ["fake", "hacker_news"])
        self.assertEqual([step.step_id for step in lanes["fake"]], ["a1", "a2"])
        self.assertEqual([step.step_id for step in lanes["hacker_news"]], ["b1"])

    def test_the_lane_ceiling_is_the_declared_constant(self):
        self.assertEqual(runner.MAX_CONCURRENT_LANES, 8)


class ForbiddenIoStillHoldsUnderLanesTest(unittest.TestCase):
    def test_a_fused_multi_lane_run_reaches_no_socket_and_no_file(self):
        opener = IntervalOpener(
            {
                transport.FAKE_OFFLINE_ROUTE: (200, FIXTURE_PAGE, "application/json"),
                transport.HN_FIREBASE_ITEM_ROUTE: (200, "null", "application/json"),
            },
            lambda request: None,
        )
        with helpers.forbid_io():
            artifact = runner.run_acquisition(schema.parse_manifest(TWO_ORIGINS), governor_over(opener))

        self.assertEqual(len(artifact.steps), 2)


if __name__ == "__main__":
    unittest.main()
