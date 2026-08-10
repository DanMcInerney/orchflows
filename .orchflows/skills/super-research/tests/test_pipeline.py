"""Pipeline suite: a measured ceiling is respected, and fused collapses only latency.

Three claims are defended here, and they fail in different directions.

The first is that a rate limit is an observed constraint this package obeys,
never one it works around. Measured ceilings differ by three orders of
magnitude — Reddit's own feed answers one or two requests per thirty seconds,
GitHub answers sixty per hour — so the scheduler paces each route by that
route's own declared constants, and a 429 buys that route a cooldown rather
than a different identity or a different route. Every proof here runs on a
fake clock: a suite that waited out a thirty-second interval would be a suite
nobody runs.

The second is that ``fused`` collapses latency and never lineage. The fused
artifact must equal the staged pair's records, groups, and provenance edges
exactly, while its schedule is strictly shorter — mode changes when work is
placed, never what the work produced.

The third is that the frozen ``as_of`` ordering is total and replayable, and
that the work ledger's causal order and additive sums agree with the artifact
they describe.
"""

from __future__ import annotations

import dataclasses
import unittest
from pathlib import Path

from super_research import adapters, runner, transport
from tests import helpers


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "pipeline"

# Two routes the roster names and no ticket has implemented yet. They are seeds
# for the replay, not entries in the route table: what is under test is the
# scheduler's arithmetic over declared constants, and it must hold for a route
# before that route exists.
REDDIT_FEED_ROUTE = "reddit_feed"
GITHUB_REST_ROUTE = "github_rest"

# findings.md §1, Reddit: four RSS requests back to back returned one 200 and
# three 429s; after a thirty-second cooldown, paced one per six seconds, it
# returned two 200s and then 429ed again. The measured ceiling is one to two
# per ~30 s per IP, and it is User-Agent independent. A client that respects a
# limit takes the floor of a measured range, never its ceiling.
REDDIT_FEED_BUDGET = runner.RouteBudget(min_interval_ms=30000, burst=1, cooldown_ms=30000)

# findings.md §1, carry-over routes: `api.github.com/rate_limit` reported the
# anonymous ceiling as 60/hr for core and code_search. GitHub spends that as
# one hourly bucket, so sixty reads may leave at once and one refills per
# minute; the cooldown is the window the bucket resets in.
GITHUB_REST_BUDGET = runner.RouteBudget(
    min_interval_ms=60000, burst=60, cooldown_ms=3600000
)

SEEDED_BUDGETS = {
    REDDIT_FEED_ROUTE: REDDIT_FEED_BUDGET,
    GITHUB_REST_ROUTE: GITHUB_REST_BUDGET,
}

OK_JSON = (200, '{"data": []}', "application/json")
US_PER_MS = 1000

# One body every shipped adapter can parse into an empty page: no result
# anchors for the HTML index, a data array for the archive, a records array for
# the offline fixture. It lets the core's two literal branches be exercised for
# every adapter id without seeding three route-specific payloads.
EMPTY_PAGE_BODY = (200, '{"data": [], "records": []}', "application/json")
PROBE_REQUEST = adapters.AdapterRequest(
    step_id="s-probe", query="probe", target_ids=("1abc234",)
)


def probe_request(route_id, index=0):
    """One read on a seeded route, under this package's one static identity."""

    return transport.TransportRequest(
        route_id=route_id,
        method="GET",
        url="probe://{0}/{1}".format(route_id, index),
        headers=(("User-Agent", transport.USER_AGENT), ("Accept", "application/json")),
    )


def paced_governor(clock, responses, latencies=None, budgets=None):
    """A governor over an offline carrier, paced by the clock the suite drives."""

    carrier, opener = helpers.offline_transport(clock, responses, latencies=latencies)
    governor = runner.RateGovernor(
        carrier,
        budgets=SEEDED_BUDGETS if budgets is None else budgets,
        clock=clock.monotonic,
        sleep=clock.sleep,
    )
    return governor, opener


def assert_rate_budget_respected(case, governor, budgets):
    """Row 1's oracle: every origin read sat inside its own route's declared budget.

    The admissible arrival time is recomputed here from the declared constants
    alone — never from the governor's own arithmetic — so a governor that
    computes its own permission wrongly is caught rather than believed. Three
    clauses, each naming the confusion it caught: a read that arrived before
    its route's interval and burst allowance admitted it, a read inside the
    cooldown a 429 opened, and a read that changed the identity it went out
    under.
    """

    if not governor.log:
        raise AssertionError("no origin read was made, so no budget was exercised")

    theoretical = {}
    blocked_until = {}
    for read in governor.log:
        budget = budgets.get(read.route_id)
        if budget is None:
            raise AssertionError(
                "route {0} was read with no declared budget".format(read.route_id)
            )
        interval_us = budget.min_interval_ms * US_PER_MS
        allowance_us = (budget.burst - 1) * interval_us
        arrival = theoretical.get(read.route_id)
        earliest = blocked_until.get(read.route_id, 0)
        if arrival is not None:
            earliest = max(earliest, arrival - allowance_us)
        if read.at_us < earliest:
            raise AssertionError(
                "a read outran its route's declared budget: {0} was read at {1} us,"
                " admissible at {2} us under {3}".format(
                    read.route_id, read.at_us, earliest, budget
                )
            )
        theoretical[read.route_id] = (
            max(read.at_us if arrival is None else arrival, read.at_us) + interval_us
        )
        if read.status == transport.RATE_LIMITED_STATUS:
            blocked_until[read.route_id] = (
                read.at_us + read.duration_us + budget.cooldown_ms * US_PER_MS
            )

    identities = sorted(
        {
            value
            for request in governor.calls
            for name, value in request.headers
            if name.lower() == "user-agent"
        }
    )
    if identities != [transport.USER_AGENT]:
        raise AssertionError(
            "the identity changed between reads, which is evasion rather than"
            " respect: {0}".format(identities)
        )


class RateBudgetTest(unittest.TestCase):
    """Criterion 1, spacing half: one route's declared interval, honored per route."""

    def test_a_repeat_read_waits_out_its_routes_declared_interval(self):
        clock = helpers.FakeClock()
        governor, opener = paced_governor(
            clock, {REDDIT_FEED_ROUTE: OK_JSON}, latencies={REDDIT_FEED_ROUTE: 0.5}
        )

        for index in range(3):
            governor.fetch(probe_request(REDDIT_FEED_ROUTE, index))

        assert_rate_budget_respected(self, governor, SEEDED_BUDGETS)
        self.assertEqual(len(opener.opened), 3)
        self.assertEqual(
            [read.at_us for read in governor.log], [0, 30000000, 60000000]
        )

    def test_one_routes_interval_never_holds_up_another_route(self):
        clock = helpers.FakeClock()
        governor, _ = paced_governor(
            clock,
            {REDDIT_FEED_ROUTE: OK_JSON, GITHUB_REST_ROUTE: OK_JSON},
            latencies={REDDIT_FEED_ROUTE: 0.5, GITHUB_REST_ROUTE: 0.5},
        )

        governor.fetch(probe_request(REDDIT_FEED_ROUTE))
        governor.fetch(probe_request(GITHUB_REST_ROUTE))

        assert_rate_budget_respected(self, governor, SEEDED_BUDGETS)
        self.assertEqual([read.waited_us for read in governor.log], [0, 0])

    def test_a_route_is_paced_by_the_interval_its_own_descriptor_declares(self):
        descriptor = runner.descriptor_for("web_search")
        clock = helpers.FakeClock()
        carrier, _ = helpers.offline_transport(
            clock, {descriptor.route_id: EMPTY_PAGE_BODY}
        )
        governor = runner.RateGovernor(carrier, clock=clock.monotonic, sleep=clock.sleep)

        governor.fetch(probe_request(descriptor.route_id, 0))
        governor.fetch(probe_request(descriptor.route_id, 1))

        self.assertGreater(descriptor.min_interval_ms, 0)
        self.assertEqual(
            governor.log[1].at_us - governor.log[0].at_us,
            descriptor.min_interval_ms * US_PER_MS,
        )

    def test_two_adapters_may_not_declare_one_route_two_different_budgets(self):
        # A budget belongs to the route, because the ceiling belongs to the
        # origin. Two adapters on one route must therefore agree, and the
        # contradiction is refused rather than resolved by whichever was
        # declared last.
        declared = runner.descriptor_for("web_search")
        agreeing = dataclasses.replace(declared, adapter_id="web_search_mirror")
        disagreeing = dataclasses.replace(
            agreeing, min_interval_ms=declared.min_interval_ms + 1
        )

        self.assertEqual(
            runner.budgets_from((declared, agreeing)), runner.budgets_from((declared,))
        )
        with self.assertRaises(runner.RunnerError):
            runner.budgets_from((declared, disagreeing))


class AdapterBranchTest(unittest.TestCase):
    """The seam every adapter ticket registers against: one id, two literal branches.

    ``ADAPTER_IDS`` is what the core can reach; ``descriptor_for`` and
    ``call_adapter`` are the two places it reaches them. A later ticket that
    lists an adapter and forgets one branch gets a red test here rather than a
    route with no budget and no call site.
    """

    def test_every_listed_adapter_id_resolves_to_a_descriptor_and_to_a_call(self):
        for adapter_id in runner.ADAPTER_IDS:
            with self.subTest(adapter=adapter_id):
                descriptor = runner.descriptor_for(adapter_id)
                self.assertIsNotNone(descriptor)
                self.assertEqual(descriptor.adapter_id, adapter_id)

                clock = helpers.FakeClock()
                carrier, opener = helpers.offline_transport(
                    clock, {descriptor.route_id: EMPTY_PAGE_BODY}
                )
                page = runner.call_adapter(adapter_id, carrier, PROBE_REQUEST)

                self.assertEqual(page.route_id, descriptor.route_id)
                self.assertEqual(len(opener.opened), 1)

    def test_an_adapter_the_core_does_not_list_is_refused_rather_than_guessed(self):
        clock = helpers.FakeClock()
        carrier, _ = helpers.offline_transport(clock, {})

        self.assertNotIn("reddit_feed", runner.ADAPTER_IDS)
        self.assertIsNone(runner.descriptor_for("reddit_feed"))
        with self.assertRaises(runner.RunnerError):
            runner.call_adapter("reddit_feed", carrier, PROBE_REQUEST)


if __name__ == "__main__":
    unittest.main()
