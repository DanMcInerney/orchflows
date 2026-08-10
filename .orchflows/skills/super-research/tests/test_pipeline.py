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
import importlib.util
import unittest
from pathlib import Path

from super_research import adapters, runner, schema, transport
from super_research.adapters import fake, reddit_archive, web_search
from tests import helpers


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "pipeline"
PACKAGE_DIR = Path(__file__).resolve().parent.parent / "scripts" / "super_research"
# T02b's adapter written beside the tree, read rather than copied: it writes no
# failure handling of any kind, which is what makes it proof that a later
# adapter inherits the protocol's typing rather than repeating it.
LATER_ADAPTER = Path(__file__).resolve().parent / "fixtures" / "transport" / "minimal_adapter.py"

SHIPPED_ADAPTERS = (web_search, reddit_archive, fake)

# Names a package that rotates identity to outrun a limit would have to spell.
# None of them is a judgment call: each one is a way to become a different
# client, and this package has exactly one client.
IDENTITY_ROTATION_NAMES = (
    "ProxyHandler",
    "build_opener",
    "install_opener",
    "set_proxy",
    "proxies",
    "user_agents",
    "USER_AGENTS",
)

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
RATE_LIMITED_ANSWER = (transport.RATE_LIMITED_STATUS, "slow down", "text/plain")
US_PER_MS = 1000

# One body every shipped adapter can parse into an empty page: no result
# anchors for the HTML index, a data array for the archive, a records array for
# the offline fixture. It lets the core's two literal branches be exercised for
# every adapter id without seeding three route-specific payloads.
EMPTY_PAGE_BODY = (200, '{"data": [], "records": []}', "application/json")
PROBE_REQUEST = adapters.AdapterRequest(
    step_id="s-probe", query="probe", target_ids=("1abc234",)
)

# T01's tracer fixtures, read rather than copied: the strongest fused-versus-
# staged claim is over the run's own end-to-end path on the run's own data, and
# a copy would drift away from the path it claims to describe.
TRACER_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "tracer"
REDDIT_THREAD_LOCATOR = (
    "https://www.reddit.com/r/LocalLLaMA/comments/1abc234/"
    "what_is_the_best_local_model_right_now/"
)
DISCOVERY_STEP = {
    "step_id": "s1-discover",
    "kind": "discovery",
    "adapter_id": "web_search",
    "query": "site:reddit.com best local model",
    "max_items": 6,
}
HYDRATION_STEP = {
    "step_id": "s2-hydrate",
    "kind": "hydration",
    "adapter_id": "reddit_archive",
    "prior_step_id": "s1-discover",
    "selected_hits": [{"discovery_locator": REDDIT_THREAD_LOCATOR, "target_id": "1abc234"}],
    "max_items": 6,
}
DISCOVERY_MANIFEST = {
    "schema_version": 2,
    "manifest_id": "pipeline-discover",
    "mode": "staged",
    "as_of": "2026-08-10T00:00:00Z",
    "steps": [DISCOVERY_STEP],
}


def tracer_responses():
    """One canned origin answer per route the tracer manifests read."""

    return {
        transport.DDG_HTML_ROUTE: (
            200,
            TRACER_FIXTURE_DIR.joinpath("ddg_html_results.html").read_text(encoding="utf-8"),
            "text/html",
        ),
        transport.ARCTIC_SHIFT_POSTS_ROUTE: (
            200,
            TRACER_FIXTURE_DIR.joinpath("arctic_shift_posts_ids.json").read_text(
                encoding="utf-8"
            ),
            "application/json",
        ),
    }


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


def load_module_beside_the_tree(path):
    """Load one module written beside the tree, by path.

    These are not package modules: nothing in the package imports them and no
    discovery pattern matches them. They exist so an oracle can be shown to
    reject a wrong result — or a bare adapter shown to inherit a right one —
    without mutating the tree under test.
    """

    spec = importlib.util.spec_from_file_location("pipeline_fixture_" + path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def adapter_page(module, clock, answers):
    """Run one adapter over one canned answer; return its page and the opener."""

    carrier, opener = helpers.offline_transport(clock, {module.DESCRIPTOR.route_id: answers})
    return module.fetch_native_page(carrier, PROBE_REQUEST), opener


def package_sources():
    """Every source file the package ships."""

    return sorted(PACKAGE_DIR.rglob("*.py"))


def sources_naming(names, paths):
    """Every (file name, name) pair where a source spells something it must not."""

    return sorted(
        (path.name, name)
        for path in paths
        for name in names
        if name in path.read_text(encoding="utf-8")
    )


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


class BurstAndCooldownTest(unittest.TestCase):
    """Criterion 1, the other two constants: a burst is spendable, a 429 is waited out."""

    def test_a_declared_burst_leaves_at_once_and_then_paces(self):
        # GitHub spends its anonymous hour as one bucket, so sixty reads may
        # leave together and the sixty-first waits a refill. A scheduler that
        # only knew an interval would take an hour to do what the origin
        # permits in an instant.
        clock = helpers.FakeClock()
        governor, opener = paced_governor(
            clock, {GITHUB_REST_ROUTE: OK_JSON}, latencies={GITHUB_REST_ROUTE: 0.0}
        )

        for index in range(GITHUB_REST_BUDGET.burst + 1):
            governor.fetch(probe_request(GITHUB_REST_ROUTE, index))

        assert_rate_budget_respected(self, governor, SEEDED_BUDGETS)
        arrivals = [read.at_us for read in governor.log]
        self.assertEqual(arrivals[: GITHUB_REST_BUDGET.burst], [0] * GITHUB_REST_BUDGET.burst)
        self.assertEqual(
            arrivals[GITHUB_REST_BUDGET.burst],
            GITHUB_REST_BUDGET.min_interval_ms * US_PER_MS,
        )
        self.assertEqual(len(opener.opened), GITHUB_REST_BUDGET.burst + 1)

    def test_a_429_holds_that_route_for_its_declared_cooldown(self):
        clock = helpers.FakeClock()
        governor, _ = paced_governor(
            clock,
            {REDDIT_FEED_ROUTE: [OK_JSON, RATE_LIMITED_ANSWER, OK_JSON]},
            latencies={REDDIT_FEED_ROUTE: 0.5},
        )

        for index in range(3):
            governor.fetch(probe_request(REDDIT_FEED_ROUTE, index))

        assert_rate_budget_respected(self, governor, SEEDED_BUDGETS)
        self.assertEqual([read.status for read in governor.log], [200, 429, 200])
        # The refusal ends at the moment it landed plus the declared cooldown,
        # which is strictly later than the interval alone would have allowed.
        refusal = governor.log[1]
        self.assertEqual(
            governor.log[2].at_us,
            refusal.at_us + refusal.duration_us + REDDIT_FEED_BUDGET.cooldown_ms * US_PER_MS,
        )
        self.assertGreater(
            governor.log[2].at_us - refusal.at_us,
            REDDIT_FEED_BUDGET.min_interval_ms * US_PER_MS,
        )

    def test_the_whole_of_the_governors_answer_to_a_429_is_to_wait(self):
        clock = helpers.FakeClock()
        governor, opener = paced_governor(
            clock,
            {REDDIT_FEED_ROUTE: [RATE_LIMITED_ANSWER, OK_JSON]},
            latencies={REDDIT_FEED_ROUTE: 0.5},
        )

        governor.fetch(probe_request(REDDIT_FEED_ROUTE, 0))
        governor.fetch(probe_request(REDDIT_FEED_ROUTE, 1))

        assert_rate_budget_respected(self, governor, SEEDED_BUDGETS)
        self.assertEqual(
            governor.log[1].waited_us, REDDIT_FEED_BUDGET.cooldown_ms * US_PER_MS
        )
        self.assertEqual({request.route_id for request in opener.opened}, {REDDIT_FEED_ROUTE})

    def test_a_rate_limited_response_is_typed_rather_than_substituted(self):
        # Including on an adapter that writes no failure handling at all: the
        # branch lives in the protocol, so no adapter has to remember it and
        # none can quietly report a refusal as a result.
        later = load_module_beside_the_tree(LATER_ADAPTER)

        for module in SHIPPED_ADAPTERS + (later,):
            with self.subTest(adapter=module.DESCRIPTOR.adapter_id):
                page, opener = adapter_page(module, helpers.FakeClock(), RATE_LIMITED_ANSWER)

                self.assertEqual(page.loss, (transport.RATE_LIMITED,))
                self.assertEqual(page.outcome, "failed")
                self.assertEqual(page.records, ())
                self.assertEqual(page.route_id, module.DESCRIPTOR.route_id)
                self.assertEqual(len(opener.opened), 1)

    def test_a_rate_limited_step_keeps_its_own_route_and_substitutes_nothing(self):
        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(
            clock, {transport.DDG_HTML_ROUTE: RATE_LIMITED_ANSWER}
        )
        governor = runner.RateGovernor(carrier, clock=clock.monotonic, sleep=clock.sleep)

        artifact = runner.run_acquisition(schema.parse_manifest(DISCOVERY_MANIFEST), governor)

        self.assertEqual(artifact.steps[0].route_id, transport.DDG_HTML_ROUTE)
        self.assertEqual(artifact.steps[0].loss, (transport.RATE_LIMITED,))
        self.assertEqual(artifact.steps[0].outcome, "failed")
        self.assertEqual(artifact.loss, (transport.RATE_LIMITED,))
        self.assertEqual(artifact.records, ())
        self.assertEqual({request.route_id for request in opener.opened}, {transport.DDG_HTML_ROUTE})

    def test_no_package_module_can_become_a_different_client(self):
        # The structural half of "respected, never evaded": the package holds
        # one static identity and one channel, and nothing in it spells a way
        # to acquire a second of either.
        self.assertEqual(sources_naming(IDENTITY_ROTATION_NAMES, package_sources()), [])

        identities = {
            value
            for route_id in transport.ROUTE_CONSTANTS
            for name, value in transport.build_transport_request(route_id).headers
            if name.lower() == "user-agent"
        }
        self.assertEqual(identities, {transport.USER_AGENT})


class VolatileIdentifierTest(unittest.TestCase):
    """Spec item 4's declaration half: a rotating identifier names its way back."""

    def test_a_volatile_identifier_declared_without_a_recovery_is_refused(self):
        descriptor = runner.descriptor_for("web_search")

        with self.assertRaises(adapters.AdapterError):
            dataclasses.replace(
                descriptor,
                volatile_identifiers=(
                    adapters.VolatileIdentifier(name="ddg_result_class", recovery=""),
                ),
            )
        with self.assertRaises(adapters.AdapterError):
            dataclasses.replace(
                descriptor,
                volatile_identifiers=(
                    adapters.VolatileIdentifier(name="", recovery="re-read one saved page"),
                ),
            )

    def test_an_adapter_that_depends_on_no_rotating_identifier_declares_none(self):
        for adapter_id in runner.ADAPTER_IDS:
            with self.subTest(adapter=adapter_id):
                self.assertEqual(runner.descriptor_for(adapter_id).volatile_identifiers, ())


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
