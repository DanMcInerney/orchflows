"""F4's repair: an unmeasured surface reads apart from a measured-unable one.

`x_guest`'s `UserTweets` and `x_fxtwitter`'s one operation both have a live
measurement Details prescribed, and both were blocked before it could run — a
stale guest bearer on the one, an origin answering 404 to every attempt on
the other, both recorded in R.02's own report. Declaring either `False` reads
at the seam exactly like `github_rest`'s `releases`, which R.02 did measure
unable: `runner.run_step` would append the same `WINDOW_NOT_HONORED` for a
measured fact and for a capability nobody has ever checked. This file proves
the two are typed apart, from the table through to `StepResult.loss`.

Nothing here reaches a network: the one seam-level read is
`helpers.offline_transport` over a canned fixture, proving what the step's
own `loss` carries rather than what a live origin answers.
"""

from __future__ import annotations

import unittest

from super_research import runner, schema, transport
from super_research._support import window_reach
from tests import helpers
from tests.test_social_adapters_cases._support import FXTWITTER_DIR, read_fixture

FXTWITTER_ROUTE = transport.FXTWITTER_API_ROUTE
GITHUB_REST_ROUTE = transport.GITHUB_REST_ROUTE
RECENT_WINDOW = ("2026-08-10T00:00:00Z", "2026-08-11T00:00:00Z")


class TheTableDeclaresThreeReadingsTest(unittest.TestCase):
    """Not two: `True`/`False` are measured, `None` is a declaration nobody proved."""

    def test_x_guest_user_tweets_is_unmeasured_not_measured_unable(self):
        self.assertIsNone(window_reach.can_bound_at_origin("x_guest", "UserTweets"))
        self.assertIsNone(window_reach.reach_for("x_guest", target_ids=("user_tweets:someone",)))

    def test_x_fxtwitters_one_operation_is_unmeasured_not_measured_unable(self):
        self.assertIsNone(window_reach.can_bound_at_origin("x_fxtwitter", ""))
        self.assertIsNone(window_reach.reach_for("x_fxtwitter", query="spacex"))

    def test_x_guests_two_settled_operations_stay_measured_false(self):
        # The contrast that makes the point: two operations on the same
        # adapter, both single-item hydrations with no ordering, both
        # genuinely measured unable — unlike their sibling above.
        self.assertFalse(window_reach.can_bound_at_origin("x_guest", "TweetResultByRestId"))
        self.assertFalse(window_reach.can_bound_at_origin("x_guest", "UserByScreenName"))

    def test_github_rests_releases_stays_measured_false(self):
        # R.02's own measured-unable fact, unchanged by this repair: a
        # `since=` set minutes in the future answered the identical
        # unfiltered page. This is what F4 says a caller could not tell
        # apart from the two unmeasured rows above before this fix.
        self.assertFalse(window_reach.can_bound_at_origin("github_rest", "releases"))


class TheLossCodeMappingIsThreeWayTest(unittest.TestCase):
    """`window_loss_code`: the one place the three readings become two codes."""

    def test_unmeasured_gets_its_own_code(self):
        self.assertEqual(
            window_reach.window_loss_code(None), window_reach.WINDOW_CAPABILITY_UNMEASURED
        )

    def test_measured_unable_gets_the_pre_existing_code(self):
        self.assertEqual(
            window_reach.window_loss_code(False), window_reach.WINDOW_NOT_HONORED
        )

    def test_measured_able_gets_no_code_at_all(self):
        self.assertIsNone(window_reach.window_loss_code(True))

    def test_the_two_codes_are_distinct(self):
        self.assertNotEqual(
            window_reach.WINDOW_CAPABILITY_UNMEASURED, window_reach.WINDOW_NOT_HONORED
        )


class TypedReadingAtTheSeamTest(unittest.TestCase):
    """Goal 2's oracle, extended: a caller reads three distinct `loss` shapes.

    Same mechanism `test_window_reach.TypedReadingDistinguishesEmptyFromUnhonoredTest`
    already proves for the can/cannot pair, now proving the third state
    through the real `runner.run_step` seam rather than only at the table.
    """

    def _run_fxtwitter_step(self, window_start=""):
        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(
            clock,
            {FXTWITTER_ROUTE: (200, read_fixture(FXTWITTER_DIR, "search.json"), "application/json")},
        )
        step = schema.AcquisitionStep(
            step_id="s1",
            kind="discovery",
            adapter_id="x_fxtwitter",
            query="spacex",
            max_items=50,
            max_pages=1,
            window_start=window_start,
        )
        result, records, _ = runner.run_step(
            step, carrier, "artifact:1", "manifest:1", clock=clock.monotonic
        )
        return result, records, opener

    def _run_github_releases_step(self, window_start=""):
        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(
            clock, {GITHUB_REST_ROUTE: (200, "[]", "application/json")}
        )
        step = schema.AcquisitionStep(
            step_id="s1",
            kind="hydration",
            adapter_id="github_rest",
            selected_hits=(
                schema.SelectedHit(target_id="releases:owner/repo", discovery_locator=""),
            ),
            max_items=50,
            max_pages=1,
            window_start=window_start,
        )
        result, records, _ = runner.run_step(
            step, carrier, "artifact:1", "manifest:1", clock=clock.monotonic
        )
        return result, records, opener

    def test_a_windowed_fxtwitter_step_carries_unmeasured_and_not_unhonored(self):
        start, end = RECENT_WINDOW
        result, _, _ = self._run_fxtwitter_step(window_start=start)

        self.assertIn(window_reach.WINDOW_CAPABILITY_UNMEASURED, result.loss)
        self.assertNotIn(window_reach.WINDOW_NOT_HONORED, result.loss)

    def test_an_unwindowed_fxtwitter_step_carries_neither(self):
        result, _, _ = self._run_fxtwitter_step()

        self.assertNotIn(window_reach.WINDOW_CAPABILITY_UNMEASURED, result.loss)
        self.assertNotIn(window_reach.WINDOW_NOT_HONORED, result.loss)

    def test_a_windowed_github_releases_step_still_carries_unhonored_and_not_unmeasured(self):
        # The direct contrast F4 names: before this repair the two steps
        # above and this one were byte-identical on `loss`. A measured fact
        # is not an unmeasured one, and this is the seam that now says so.
        result, _, _ = self._run_github_releases_step(window_start="2026-08-10T00:00:00Z")

        self.assertIn(window_reach.WINDOW_NOT_HONORED, result.loss)
        self.assertNotIn(window_reach.WINDOW_CAPABILITY_UNMEASURED, result.loss)


if __name__ == "__main__":
    unittest.main()
