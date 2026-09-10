"""Window-reach seam: per-operation capability, and the typed reading it buys.

Goal 2's two halves, proven at the seam this member owns. The declaration
half: every live probe's own operation resolves through
`_support.window_reach`, and a declaration nothing names fails loudly rather
than reading as either answer. The typed-reading half: a windowed step
against an operation declared unable to bound time at its origin carries
`window_reach.WINDOW_NOT_HONORED` in its `StepResult.loss`, distinct from the
same step against a declared-can operation whose window happens to keep
nothing — proven at a narrow, recent window and again at an old one, so
"any width, any age" is an oracle here rather than a claim. `bluesky` is the
measured case: its search method sends `since`/`until` and its author feed
sends neither, off the same fixtures `test_social_adapters` reads.

Nothing here reaches a network: every carrier is `helpers.offline_transport`
over the same canned fixtures the adapter suite already trusts.
"""

from __future__ import annotations

import unittest

from super_research import probes, runner, schema, transport
from super_research._support import window_reach
from tests import helpers
from tests.test_social_adapters_cases._support import (
    BLUESKY_DIR,
    BSKY_HANDLE,
    read_fixture,
)

SEARCH_ROUTE = transport.BLUESKY_SEARCH_POSTS_ROUTE
AUTHOR_ROUTE = transport.BLUESKY_AUTHOR_FEED_ROUTE

# A window narrow enough to be "one minute" and recent enough to bracket the
# fixtures' own timestamps (`2026-08-10T18:23:59Z`), so a can-honor surface
# keeps rows inside it.
RECENT_WINDOW = ("2026-08-10T18:23:00Z", "2026-08-10T18:24:00Z")
# A window old enough that none of the fixtures' rows fall inside it, so
# every surface reports zero kept — the case a green suite could still miss,
# because "zero kept" alone cannot tell a caller which of the two happened.
DECADE_OLD_WINDOW = ("2016-01-01T00:00:00Z", "2016-02-01T00:00:00Z")


def run_bluesky_step(query, route_id, fixture_name, window_start="", window_end=""):
    clock = helpers.FakeClock()
    carrier, opener = helpers.offline_transport(
        clock, {route_id: (200, read_fixture(BLUESKY_DIR, fixture_name), "application/json")}
    )
    step = schema.AcquisitionStep(
        step_id="s1",
        kind="discovery",
        adapter_id="bluesky",
        query=query,
        max_items=50,
        max_pages=1,
        window_start=window_start,
        window_end=window_end,
    )
    result, records, _ = runner.run_step(
        step, carrier, "artifact:1", "manifest:1", clock=clock.monotonic
    )
    return result, records, opener


class DeclarationCoversTheLiveRosterTest(unittest.TestCase):
    """Every probe `cli.py smoke` can be asked for resolves through this table."""

    def test_every_live_probe_adapter_is_declared(self):
        self.assertEqual(
            {probe.adapter_id for probe in probes.SMOKE_PROBES},
            set(window_reach.WINDOW_REACH) - {"fake"},
        )

    def test_an_unnamed_adapter_fails_loudly_rather_than_reading_either_way(self):
        with self.assertRaises(window_reach.WindowReachError):
            window_reach.can_bound_at_origin("not_a_real_adapter", "")

    def test_an_unnamed_operation_on_a_named_adapter_fails_loudly_too(self):
        with self.assertRaises(window_reach.WindowReachError):
            window_reach.can_bound_at_origin("bluesky", "not_a_real_operation")


class BlueskyOperationsDisagreeTest(unittest.TestCase):
    """The measured case Goal 1 forces: one adapter, two answers.

    `bluesky.py:478-481` sends `since`/`until` on search only; `:463-465`
    states the author feed takes none. A tuple of adapter ids could not say
    both were true of one adapter, which is why the table is keyed by
    operation and not by adapter alone.
    """

    def test_search_can_bound_and_the_author_feed_cannot(self):
        self.assertEqual(window_reach.WINDOW_REACH["bluesky"], {"search": True, "author": False})

    def test_reach_for_resolves_each_query_to_its_own_operations_answer(self):
        self.assertTrue(window_reach.reach_for("bluesky", query="spacex"))
        self.assertTrue(window_reach.reach_for("bluesky", query="search:spacex"))
        self.assertFalse(window_reach.reach_for("bluesky", query="author:" + BSKY_HANDLE))


class TypedReadingDistinguishesEmptyFromUnhonoredTest(unittest.TestCase):
    """Goal 2's oracle: same empty answer, two different `loss` readings.

    Both surfaces read the same fixtures under the same decade-old window and
    both keep nothing — the shape a caller cannot tell apart from records
    alone. Only the declared-cannot surface's `StepResult.loss` says why.
    """

    def test_at_a_decade_old_window_both_surfaces_answer_empty_but_only_one_is_typed(self):
        start, end = DECADE_OLD_WINDOW
        can_result, can_records, _ = run_bluesky_step(
            "spacex", SEARCH_ROUTE, "search_posts.json", start, end
        )
        cannot_result, cannot_records, _ = run_bluesky_step(
            "author:" + BSKY_HANDLE, AUTHOR_ROUTE, "author_feed.json", start, end
        )

        self.assertEqual(len(can_records), 0)
        self.assertEqual(len(cannot_records), 0)
        self.assertNotIn(window_reach.WINDOW_NOT_HONORED, can_result.loss)
        self.assertIn(window_reach.WINDOW_NOT_HONORED, cannot_result.loss)

    def test_at_a_one_minute_recent_window_the_same_two_readings_hold(self):
        # Width and age are independent: a narrow, recent window that keeps
        # rows on both surfaces still types only the one that could not have
        # asked the origin to keep them.
        start, end = RECENT_WINDOW
        can_result, can_records, _ = run_bluesky_step(
            "spacex", SEARCH_ROUTE, "search_posts.json", start, end
        )
        cannot_result, cannot_records, _ = run_bluesky_step(
            "author:" + BSKY_HANDLE, AUTHOR_ROUTE, "author_feed.json", start, end
        )

        self.assertGreater(len(can_records), 0)
        self.assertGreater(len(cannot_records), 0)
        self.assertNotIn(window_reach.WINDOW_NOT_HONORED, can_result.loss)
        self.assertIn(window_reach.WINDOW_NOT_HONORED, cannot_result.loss)


class UnwindowedStepIsUnchangedTest(unittest.TestCase):
    """Goal 3: a step carrying no window is the baseline step, byte for byte."""

    def test_an_unwindowed_step_never_carries_the_new_code_even_on_a_cannot_surface(self):
        result, records, opener = run_bluesky_step("author:" + BSKY_HANDLE, AUTHOR_ROUTE, "author_feed.json")

        self.assertNotIn(window_reach.WINDOW_NOT_HONORED, result.loss)
        self.assertEqual(len(records), 3)

    def test_the_wire_request_the_author_feed_sends_does_not_change_when_windowed(self):
        _, _, unwindowed_opener = run_bluesky_step(
            "author:" + BSKY_HANDLE, AUTHOR_ROUTE, "author_feed.json"
        )
        start, end = RECENT_WINDOW
        _, _, windowed_opener = run_bluesky_step(
            "author:" + BSKY_HANDLE, AUTHOR_ROUTE, "author_feed.json", start, end
        )

        self.assertEqual(unwindowed_opener.opened[0].url, windowed_opener.opened[0].url)


if __name__ == "__main__":
    unittest.main()
