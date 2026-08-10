"""Pipeline suite: a measured ceiling is respected, and fused collapses only latency.

Four claims are defended here, and they fail in different directions.

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

The fourth is smaller and holds the other three up: a record served from a
run's own memory says so, and still states the moment the origin was really
read. A mark that goes missing under-reports cache use; a moment that moves
fabricates freshness, and every recency judgment downstream then rests on a
time nothing ever observed.
"""

from __future__ import annotations

import dataclasses
import importlib.util
import json
import unittest
from pathlib import Path
from unittest import mock

from super_research import adapters, cache, normalize, runner, schema, transport
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
# Adapters whose roster row names a vendor identifier that rotates. Every other
# listed adapter declares none, and one declaring a rotating id without being on
# this list is declaring a dependency it does not have. In `ADAPTER_IDS` order,
# because that is the order the check below collects them in.
ADAPTERS_WITH_ROTATING_IDENTIFIERS = ("x_guest", "youtube_innertube")

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
TWO_STEP_MANIFEST = {
    "schema_version": 2,
    "manifest_id": "pipeline-two-step",
    "mode": "staged",
    "as_of": "2026-08-10T00:00:00Z",
    "steps": [DISCOVERY_STEP, HYDRATION_STEP],
}
FUSED_MANIFEST = dict(TWO_STEP_MANIFEST, manifest_id="pipeline-fused", mode="fused")
# The staged half of the pair. It names no `prior_step_id`, because the step it
# followed is in a different manifest — which is the point: what ties a
# hydration record to the hit that found it is the locator the caller froze,
# never an execution graph.
STAGED_HYDRATION_MANIFEST = {
    "schema_version": 2,
    "manifest_id": "pipeline-hydrate",
    "mode": "staged",
    "as_of": "2026-08-10T00:00:00Z",
    "steps": [dict(HYDRATION_STEP, prior_step_id="")],
}
REPEAT_ROUTES = (transport.DDG_HTML_ROUTE, transport.ARCTIC_SHIFT_POSTS_ROUTE)

# findings.md §1: Arctic Shift's `/api/posts/ids` was measured at 1.5 s. No
# latency was recorded for the DuckDuckGo HTML endpoint, so the helper's own
# default stands in for it; what the comparison needs is two routes that cost
# visibly different amounts, and these are the two the tracer already reads.
ROUTE_LATENCIES = {
    transport.DDG_HTML_ROUTE: helpers.DEFAULT_LATENCY_SECONDS,
    transport.ARCTIC_SHIFT_POSTS_ROUTE: 1.5,
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


def paced_governor(clock, responses, latencies=None, budgets=None, governor_class=None):
    """A governor over an offline carrier, paced by the clock the suite drives."""

    carrier, opener = helpers.offline_transport(clock, responses, latencies=latencies)
    governor = (runner.RateGovernor if governor_class is None else governor_class)(
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


def adapter_sources():
    """Every adapter module the package ships, the shared protocol excluded."""

    return sorted(
        path for path in (PACKAGE_DIR / "adapters").glob("*.py") if path.name != "__init__.py"
    )


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


CONCURRENCY_MODULES = ("asyncio", "concurrent", "multiprocessing", "threading", "_thread")


class NothingOverlapsAndNothingPagesTest(unittest.TestCase):
    """Two mechanisms the documents called core-owned, pinned to what ships.

    `protocol.md` said `fused` lets two steps overlap and `adapters/__init__.py`
    said the core owns pagination and concurrency. Neither exists: the package
    imports no concurrency primitive at all, and `runner.planned_calls` is the
    only production constructor of an `AdapterRequest` and never sets a cursor.
    What `fused` really collapses is the round-trip — discovery and bounded
    hydration in one invocation — and `fake_makespan_us` is the span of a
    modeled placement rather than a wall clock. Both claims are now written down
    as what they are, and pinned here so the next edit cannot quietly restore
    the stronger one.
    """

    def test_the_package_imports_no_concurrency_primitive(self):
        # By import rather than by spelling: this file's own prose says the
        # word, and a scan that could not tell an import from a sentence would
        # make writing the truth down impossible.
        taken = sorted(
            (path.name, name)
            for path in package_sources()
            for name in helpers.imported_names(path)
            if name.split(".")[0] in CONCURRENCY_MODULES
        )

        self.assertEqual(taken, [])

    def test_the_only_request_the_core_builds_carries_no_cursor(self):
        for payload in (DISCOVERY_MANIFEST, TWO_STEP_MANIFEST, FUSED_MANIFEST):
            for step in schema.parse_manifest(payload).steps:
                with self.subTest(manifest=payload["manifest_id"], step=step.step_id):
                    planned = runner.planned_calls(step)

                    self.assertEqual([request.cursor for request, _ in planned], [""] * len(planned))
                    if step.kind == "discovery":
                        self.assertEqual(len(planned), 1)

    def test_a_fused_run_makes_the_same_calls_in_the_same_order_as_a_staged_one(self):
        # The execution half: the mode reaches the ledger's placement and
        # nothing else. If `fused` overlapped anything, this is where the two
        # would stop agreeing.
        staged_governor, staged_opener, staged_clock = tracer_governor()
        fused_governor, fused_opener, fused_clock = tracer_governor()

        staged = run_on(staged_clock, staged_governor, TWO_STEP_MANIFEST)
        fused = run_on(fused_clock, fused_governor, FUSED_MANIFEST)

        self.assertEqual(
            [request.route_id for request in staged_opener.opened],
            [request.route_id for request in fused_opener.opened],
        )
        self.assertEqual(len(staged.artifact.records), len(fused.artifact.records))


class TheDocumentedPathPacesAndRemembersTest(unittest.TestCase):
    """Criterion 4's other half: the governor is on the path, not only in a fixture.

    Every pacing proof below runs against a governor the test itself built.
    That proves the class and says nothing about the delivery: until this seam
    existed, `RateGovernor` and `RunCache` were constructed nowhere outside
    `tests/`, `smoke.observe` made its one live read through a bare
    `transport.Transport`, and a caller following `SKILL.md` to
    `run_acquisition` paced nothing and remembered nothing. Spec change 1 calls
    the cache mandatory and the binding constraint says a rate limit is
    respected, never evaded — neither of which a green unit test on an
    unreachable class delivers.
    """

    def test_the_composed_carrier_is_a_governor_over_a_run_cache(self):
        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(
            clock, tracer_responses(), latencies=ROUTE_LATENCIES
        )

        composed = runner.paced_carrier(carrier, clock=clock.monotonic, sleep=clock.sleep)

        self.assertIsInstance(composed, runner.RateGovernor)
        composed.fetch(probe_request(transport.DDG_HTML_ROUTE))
        composed.fetch(probe_request(transport.DDG_HTML_ROUTE))
        # One origin read behind two identical asks is the cache; the governor
        # is what the second ask went through to find it.
        self.assertEqual(len(opener.opened), 1)
        self.assertEqual([serve.cache_hit for serve in composed.serves], [False, True])

    def test_a_run_that_names_no_carrier_is_paced_and_remembers(self):
        # The whole point: this is the call `SKILL.md` documents, made the way
        # it is documented, with nothing composed by the caller.
        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(
            clock, tracer_responses(), latencies=ROUTE_LATENCIES
        )
        manifest = schema.parse_manifest(TWO_STEP_MANIFEST)

        with mock.patch.object(transport, "Transport", lambda *a, **k: carrier):
            artifact = runner.run_acquisition(manifest, clock=clock.monotonic)
            reads = len(opener.opened)
            clock.advance(min(cache.ttl_seconds(route) for route in REPEAT_ROUTES) / 2.0)
            repeat = runner.run_acquisition(manifest, clock=clock.monotonic)

        self.assertTrue(artifact.records)
        self.assertGreater(reads, 0)
        # A second run makes a second cache, so it reaches the origin again —
        # the cache is run-local and never crosses runs. What this pins is that
        # the composed carrier is what a carrier-less run gets at all.
        self.assertEqual(len(opener.opened), reads * 2)
        self.assertEqual(len(repeat.records), len(artifact.records))

    def test_no_module_but_the_composition_builds_its_own_carrier(self):
        # A second `transport.Transport()` anywhere in the package is a second
        # unpaced door, and the last one was `smoke.observe`'s. Stated as the
        # set of modules that build one, for the same reason the wall-clock
        # wait above is: naming one path would not notice a new one.
        building = sorted(
            path.name
            for path in PACKAGE_DIR.rglob("*.py")
            if "transport.Transport(" in path.read_text(encoding="utf-8")
        )

        self.assertEqual(building, ["pacing.py"])


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


def real_governor(carrier, run_cache, clock):
    """The governor under test, built the way every caller of it should."""

    return runner.RateGovernor(
        carrier, run_cache=run_cache, clock=clock.monotonic, sleep=clock.sleep
    )


def tracer_governor(make_governor=real_governor, clock=None, run_cache=None):
    """A governor over the tracer's two routes, on one clock at the frozen start.

    The clock comes back with it because the governor and the run it paces must
    read the same one: a run reading a different clock would measure real time
    while the governor spends fake time, and every duration in its ledger would
    be an artefact of how fast this suite happens to execute.
    """

    clock = helpers.FakeClock() if clock is None else clock
    carrier, opener = helpers.offline_transport(
        clock, tracer_responses(), latencies=ROUTE_LATENCIES
    )
    return make_governor(carrier, run_cache, clock), opener, clock


def cached_run(make_governor, clock=None):
    """One run cache behind one governor, over the tracer's own two routes."""

    clock = helpers.FakeClock() if clock is None else clock
    return tracer_governor(
        make_governor, clock=clock, run_cache=cache.RunCache(clock=clock.monotonic)
    )


def run_on(clock, governor, payload, dispatch_ordinal=0, start_tick_us=0):
    """One dispatch of one manifest, on the clock its governor is paced by."""

    return runner.run_scheduled(
        schema.parse_manifest(payload),
        governor,
        clock=clock.monotonic,
        dispatch_ordinal=dispatch_ordinal,
        start_tick_us=start_tick_us,
    )


def assert_cache_hit_reaches_the_record(case, make_governor):
    """Row 9's oracle: a served record says it was served, and when it was read.

    Both halves fail in opposite directions and both are checked on the
    ``AcquisitionRecord`` a caller keeps, never on the response behind it. A
    record that loses the mark under-reports cache use; a record restamped
    with the serve time fabricates freshness, and every later recency and
    staleness judgment then rests on a moment nothing ever observed.
    """

    governor, opener, clock = cached_run(make_governor)
    manifest = schema.parse_manifest(TWO_STEP_MANIFEST)

    first = runner.run_acquisition(manifest, governor, clock=clock.monotonic)
    reads = len(opener.opened)
    if reads == 0 or not first.records:
        raise AssertionError("the first read never reached the origin: nothing to serve later")
    premarked = [record.record_id for record in first.records if cache.CACHE_HIT in record.loss]
    if premarked:
        raise AssertionError(
            "a record read from the origin was marked cache_hit: {0}".format(premarked)
        )

    clock.advance(min(cache.ttl_seconds(route) for route in REPEAT_ROUTES) / 2.0)
    second = runner.run_acquisition(manifest, governor, clock=clock.monotonic)

    if len(opener.opened) != reads:
        raise AssertionError(
            "the cache did not serve a repeat read inside its TTL: {0} origin reads"
            " repeating {1}".format(len(opener.opened) - reads, reads)
        )
    if len(second.records) != len(first.records):
        raise AssertionError("a repeat run yielded a different number of records")
    unmarked = [
        record.record_id for record in second.records if cache.CACHE_HIT not in record.loss
    ]
    if unmarked:
        raise AssertionError(
            "a served-from-cache record carries no cache_hit mark: {0} of {1} records,"
            " starting at {2}".format(len(unmarked), len(second.records), unmarked[0])
        )
    restamped = [
        (before.record_id, before.observed_at, after.observed_at)
        for before, after in zip(first.records, second.records)
        if before.observed_at != after.observed_at
    ]
    if restamped:
        raise AssertionError(
            "a served-from-cache record was restamped with the serve time:"
            " record {0} observed at {1} came back observed at {2}".format(*restamped[0])
        )
    if clock.stamp() == first.records[0].observed_at:
        raise AssertionError("the clock never moved, so the unrestamped clause proves nothing")


class CacheHitOnTheRecordTest(unittest.TestCase):
    """Criterion 9: the mark and the moment both survive as far as a caller reads."""

    def test_a_served_record_carries_the_mark_and_the_moment_it_was_read(self):
        assert_cache_hit_reaches_the_record(self, real_governor)

    def test_the_mark_is_installed_once_and_no_adapter_writes_it(self):
        # The same inheritance claim T02b made for the channel verdict: every
        # adapter gets this for free, and an adapter that spelled it for itself
        # would be the beginning of the drift.
        self.assertEqual(sources_naming([cache.CACHE_HIT], adapter_sources()), [])

    def test_a_cache_hit_costs_the_routes_rate_budget_nothing(self):
        # Pacing lives inside the callable a hit never invokes, so a run that
        # remembers what it read never pays a wait for reading it again.
        governor, opener, clock = cached_run(real_governor)
        manifest = schema.parse_manifest(TWO_STEP_MANIFEST)

        runner.run_acquisition(manifest, governor, clock=clock.monotonic)
        origin_reads = len(governor.log)
        runner.run_acquisition(manifest, governor, clock=clock.monotonic)

        self.assertEqual(len(governor.log), origin_reads)
        self.assertEqual(len(opener.opened), origin_reads)
        self.assertEqual([serve.cache_hit for serve in governor.serves[origin_reads:]],
                         [True] * origin_reads)


def fused_run(run_fused=None):
    """One invocation carrying both steps."""

    governor, _, clock = tracer_governor()
    if run_fused is None:
        return run_on(clock, governor, FUSED_MANIFEST)
    return run_fused(schema.parse_manifest(FUSED_MANIFEST), governor, clock)


def staged_pair(case):
    """Discovery, a caller's round trip, then hydration: two invocations, two artifacts.

    The round trip is given away free — the second dispatch starts the instant
    the first one ends — so the makespan comparison is the one staged is most
    likely to win, and it still loses.
    """

    governor, _, clock = tracer_governor()
    first = run_on(clock, governor, DISCOVERY_MANIFEST)
    discovered = [record.normalized_locator for record in first.artifact.records]
    case.assertIn(
        normalize.normalized_locator(REDDIT_THREAD_LOCATOR),
        discovered,
        "the caller could not have frozen a selection it never discovered",
    )
    second = run_on(
        clock,
        governor,
        STAGED_HYDRATION_MANIFEST,
        dispatch_ordinal=1,
        start_tick_us=runner.fake_makespan_us(first.ledger),
    )
    return (first, second)


def filed_nowhere(record):
    """One record with the artifact it was filed under removed, so two runs compare."""

    return dataclasses.replace(record, artifact_id="", manifest_id="")


def assert_linked_and_never_merged(case, records, edges, label):
    """Discovery and hydration stay two records, linked, whatever mode produced them."""

    index = [record for record in records if record.representation_kind == "index"]
    native = [record for record in records if record.representation_kind == "native"]
    if not index or not native:
        raise AssertionError(
            "{0} lost one half of the pair: {1} index, {2} native".format(
                label, len(index), len(native)
            )
        )
    hydrated = native[0]
    hit = [record for record in index if record.normalized_locator == hydrated.discovery_locator]
    if len(hit) != 1:
        raise AssertionError(
            "{0} has no single discovery record for the locator its hydration"
            " names: {1}".format(label, hydrated.discovery_locator)
        )
    if hit[0].record_id == hydrated.record_id:
        raise AssertionError("{0} merged the hit into its hydrated target".format(label))
    if hit[0].access_class == hydrated.access_class:
        raise AssertionError(
            "{0} gave the pair one provenance: both records are {1}".format(
                label, hydrated.access_class
            )
        )
    links = [
        edge
        for edge in edges
        if edge.from_record_id == hit[0].record_id and edge.to_record_id == hydrated.record_id
    ]
    if len(links) != 1:
        raise AssertionError(
            "{0} produced {1} provenance edges for the pair, expected one".format(
                label, len(links)
            )
        )


def assert_fused_collapses_latency_and_not_lineage(case, fused, staged):
    """Row 3's oracle: same records, groups and edges; strictly shorter schedule.

    The staged side is a *pair* of dispatches, so its lineage has to be
    reconstructed across both artifacts — which is exactly the claim: freezing
    the same selection in one manifest yields the same records and the same
    links, and only the placement of the work changes.
    """

    staged_records = tuple(record for run in staged for record in run.artifact.records)
    fused_records = fused.artifact.records
    if not fused_records:
        raise AssertionError("the fused run produced no records: nothing to compare")

    if len(fused_records) != len(staged_records):
        raise AssertionError(
            "fused and staged yielded different numbers of records: {0} against {1}".format(
                len(fused_records), len(staged_records)
            )
        )
    for fused_record, staged_record in zip(fused_records, staged_records):
        if filed_nowhere(fused_record) != filed_nowhere(staged_record):
            raise AssertionError(
                "a fused record differs from the staged record it repeats: {0}".format(
                    fused_record.record_id
                )
            )

    staged_groups = normalize.group_records(staged_records)
    if fused.artifact.groups != staged_groups:
        raise AssertionError(
            "fused grouped its records differently from the staged pair: {0} against"
            " {1}".format(fused.artifact.groups, staged_groups)
        )
    staged_edges = normalize.link_discovery_hydration(staged_records)
    if not staged_edges:
        raise AssertionError("the staged pair reconstructed no lineage: nothing to compare")
    if fused.artifact.edges != staged_edges:
        raise AssertionError(
            "fused linked its records differently from the staged pair: {0} against"
            " {1}".format(fused.artifact.edges, staged_edges)
        )

    assert_linked_and_never_merged(case, fused_records, fused.artifact.edges, "fused")
    assert_linked_and_never_merged(case, staged_records, staged_edges, "the staged pair")

    fused_span = runner.fake_makespan_us(fused.ledger)
    staged_span = runner.fake_makespan_us(
        tuple(event for run in staged for event in run.ledger)
    )
    if fused_span >= staged_span:
        raise AssertionError(
            "fused did not collapse any latency: {0} us against staged {1} us".format(
                fused_span, staged_span
            )
        )


class FusedModeTest(unittest.TestCase):
    """Criterion 3: fused collapses latency and never lineage."""

    def test_a_fused_manifest_matches_the_staged_pair_and_finishes_sooner(self):
        assert_fused_collapses_latency_and_not_lineage(self, fused_run(), staged_pair(self))

    def test_a_hydration_steps_calls_come_from_the_frozen_manifest_alone(self):
        # Which is what makes overlapping the two steps sound: the hydration
        # step reads nothing this run produced, so `prior_step_id` records
        # where the caller's selection came from rather than a dependency the
        # scheduler has to serialize.
        fused = schema.parse_manifest(FUSED_MANIFEST)
        staged = schema.parse_manifest(STAGED_HYDRATION_MANIFEST)

        self.assertEqual(fused.steps[1].prior_step_id, "s1-discover")
        self.assertEqual(staged.steps[0].prior_step_id, "")
        self.assertEqual(runner.planned_calls(fused.steps[1]), runner.planned_calls(staged.steps[0]))

    def test_the_two_modes_place_the_same_work_differently_and_only_that(self):
        fused = fused_run()
        first, second = staged_pair(self)

        self.assertEqual(fused.artifact.mode, "fused")
        self.assertEqual(
            [operation.route_id for operation in runner.planned_operations(fused.ledger)],
            [transport.DDG_HTML_ROUTE, transport.ARCTIC_SHIFT_POSTS_ROUTE],
        )
        self.assertEqual(
            runner.ledger_sums(fused.ledger),
            runner.ledger_sums(first.ledger + second.ledger),
        )


class WorkLedgerTest(unittest.TestCase):
    """Criterion 4, ledger half: causal order is total, and the sums are the artifact's."""

    def test_the_causal_key_serializes_the_ledger_exactly_as_it_happened(self):
        fused = fused_run()

        keys = [runner.causal_key(event) for event in fused.ledger]

        self.assertEqual(keys, sorted(keys))
        self.assertEqual(len(set(keys)), len(keys))
        self.assertEqual(
            [runner.causal_key(event) for event in sorted(fused.ledger, key=runner.causal_key)],
            keys,
        )

    def test_within_one_step_the_causal_order_agrees_with_the_schedule(self):
        fused = fused_run()

        for step_id in ("s1-discover", "s2-hydrate"):
            with self.subTest(step=step_id):
                ticks = [
                    event.start_tick_us
                    for event in fused.ledger
                    if event.step_id == step_id and event.metric != "stop"
                ]

                self.assertEqual(ticks, sorted(ticks))

    def test_the_ledger_sums_are_what_the_artifact_says_it_consumed(self):
        governor, opener, clock = tracer_governor()

        run = run_on(clock, governor, FUSED_MANIFEST)
        sums = runner.ledger_sums(run.ledger)

        self.assertEqual(sums["pages"], sum(step.pages for step in run.artifact.steps))
        self.assertEqual(
            sums["items"], sum(step.records_received for step in run.artifact.steps)
        )
        self.assertEqual(sums["calls"], len(opener.opened))
        self.assertEqual(sums["calls"], len(governor.log))

    def test_a_served_read_costs_a_page_and_no_call(self):
        # The distinction the two metrics exist to draw: a run that remembers
        # what it read still produced the page, and did not spend the call.
        governor, opener, clock = cached_run(real_governor)

        first = run_on(clock, governor, FUSED_MANIFEST)
        clock.advance(min(cache.ttl_seconds(route) for route in REPEAT_ROUTES) / 2.0)
        second = run_on(clock, governor, FUSED_MANIFEST, dispatch_ordinal=1)

        self.assertEqual(runner.ledger_sums(first.ledger)["calls"], len(opener.opened))
        self.assertEqual(runner.ledger_sums(second.ledger)["calls"], 0)
        self.assertEqual(
            runner.ledger_sums(second.ledger)["pages"],
            runner.ledger_sums(first.ledger)["pages"],
        )

    def test_the_stop_marker_adds_to_nothing_and_nothing_starts_after_it(self):
        fused = fused_run()

        markers = [event for event in fused.ledger if event.metric == "stop"]
        operations = [event for event in fused.ledger if event.metric != "stop"]

        self.assertEqual(len(markers), 1)
        self.assertEqual(markers[0].delta, 0)
        self.assertNotIn("stop", runner.ADDITIVE_METRICS)
        self.assertNotIn("stop", runner.ledger_sums(fused.ledger))
        self.assertLessEqual(
            max(event.start_tick_us for event in operations), markers[0].start_tick_us
        )

    def test_the_makespan_is_derived_and_is_never_a_sum_of_deltas(self):
        fused = fused_run()

        durations = runner.ledger_sums(fused.ledger)["fake_duration"]
        span = runner.fake_makespan_us(fused.ledger)

        self.assertNotIn("fake_makespan_us", runner.METRIC_ORDINALS)
        self.assertEqual(runner.fake_makespan_us(()), 0)
        # Two routes that overlap: the schedule is shorter than the work in it.
        self.assertLess(span, durations)
        self.assertEqual(
            span,
            max(event.stop_tick_us for event in fused.ledger if event.metric != "stop"),
        )


def replay_seeds():
    """The frozen ordering seeds, as data."""

    return json.loads(
        FIXTURE_DIR.joinpath("engagement_as_of_replay.json").read_text(encoding="utf-8")
    )


def seeded_record(row):
    """One artifact record built from one frozen seed row."""

    return schema.AcquisitionRecord(
        record_id="seed#" + row["case"],
        artifact_id="artifact:ordering",
        manifest_id="ordering",
        step_id="s1-seed",
        adapter_id=row["adapter_id"],
        adapter_version="1",
        route_id="",
        access_class="",
        operator_identity="",
        platform=row["platform"],
        native_identity_namespace=row["native_identity_namespace"],
        group_scope=row["platform"],
        representation_kind=row["representation_kind"],
        canonical_content_kind=row["canonical_content_kind"],
        native_item_id=row["native_item_id"],
        native_parent_id="",
        canonical_locator="",
        normalized_locator="",
        exact_content_hash="",
        title="",
        body="",
        author="",
        community="",
        published_at=row["published_at"],
        observed_at=helpers.FROZEN_START,
        time_confidence="reported" if row["published_at"] else "unknown",
        usable_basis_time=row["published_at"],
        engagement=tuple(
            schema.EngagementSnapshot(metric_name=name, value=value, observed_at=observed)
            for name, value, observed in row["engagement"]
        ),
        page_index=0,
        list_index=0,
        native_position=row["native_position"],
        discovery_locator="",
        outcome="ok",
        loss=(),
    )


def seeded_records():
    """Every seed row, in the order the fixture declares them."""

    return tuple(seeded_record(row) for row in replay_seeds()["records"])


def cases_of(records):
    return [record.record_id.split("#", 1)[1] for record in records]


# The two metric names a Reddit route reports, declared on a descriptor rather
# than inferred from a snapshot. The shipped descriptor declares neither, which
# is what the "never inferred" case turns on.
DECLARING_DESCRIPTORS = {
    "web_search": runner.descriptor_for("web_search"),
}


def declaring_descriptors():
    return dict(
        DECLARING_DESCRIPTORS,
        reddit_archive=dataclasses.replace(
            runner.descriptor_for("reddit_archive"),
            comment_count_metric="num_comments",
            reply_count_metric="reply_count",
        ),
    )


class OrderingContractTest(unittest.TestCase):
    """Criterion 4, ordering half: five total orders over one frozen ``as_of``.

    The expected order of every view is written out case by case, so the check
    is what the contract says the answer is and not what the comparator
    happens to produce.
    """

    def setUp(self):
        self.seeds = replay_seeds()
        self.records = seeded_records()
        self.as_of = self.seeds["as_of"]
        self.native = tuple(
            record for record in self.records if record.representation_kind == "native"
        )
        self.descriptors = declaring_descriptors()

    def ordered(self, order, records=None):
        return cases_of(
            runner.order_records(
                self.native if records is None else records,
                order,
                self.as_of,
                descriptors=self.descriptors,
            )
        )

    def test_newest_ranks_by_usable_basis_time_with_the_untimed_terminal(self):
        self.assertEqual(
            self.ordered("newest"),
            ["future", "changing", "missing", "wrong_name", "stale", "equal_time", "untimed"],
        )

    def test_native_top_ranks_by_the_routes_own_ordinal_lower_first(self):
        self.assertEqual(
            self.ordered("native_top"),
            ["stale", "changing", "future", "equal_time", "missing", "wrong_name", "untimed"],
        )

    def test_most_commented_replays_engagement_against_the_frozen_as_of(self):
        # stale 120, changing 80 (not its earlier 10), equal_time 40 (the
        # earlier of two at one moment), future 5 (not the 9999 the as_of
        # cannot see), then the rows with no eligible metric at all.
        self.assertEqual(
            self.ordered("most_commented"),
            ["stale", "changing", "equal_time", "future", "missing", "wrong_name", "untimed"],
        )

    def test_two_readings_at_one_moment_resolve_to_the_earlier_position(self):
        # The `equal_time` seed has said "the tie is the smallest stable
        # snapshot id, never the larger value" since it was written, and until
        # this test nothing asserted the value it resolves to: 40 and 41 both
        # sit between `changing`'s 80 and `future`'s 5, so the rank above is
        # the same either way and the comparator returned 41 — the larger
        # reading, on the larger id, which is exactly what the rule forbids.
        equal_time = next(
            record for record, seed in zip(self.records, self.seeds["records"])
            if seed["case"] == "equal_time"
        )
        resolved = runner.eligible_snapshot(equal_time, "num_comments", self.as_of)

        self.assertEqual([snapshot.value for snapshot in equal_time.engagement], [40, 41])
        self.assertEqual(resolved.value, 40)
        self.assertEqual(resolved, equal_time.engagement[0])

    def test_a_tie_is_broken_by_position_and_never_by_how_a_position_is_spelled(self):
        # Eleven readings at one moment, so the tie spans `#e2` and `#e10`. A
        # comparator ranking a derived `record#e<position>` id as text picks
        # `#e9`; one ranking the position picks the first. Values descend, so
        # a rule that leaked value into the tie is visible here too.
        source = next(
            record for record, seed in zip(self.records, self.seeds["records"])
            if seed["case"] == "equal_time"
        )
        crowded = dataclasses.replace(
            source,
            engagement=tuple(
                schema.EngagementSnapshot(
                    metric_name="num_comments", value=100 - index,
                    observed_at="2026-08-08T00:00:00Z",
                )
                for index in range(11)
            ),
        )

        resolved = runner.eligible_snapshot(crowded, "num_comments", self.as_of)

        self.assertEqual(resolved.value, 100)
        self.assertEqual(sorted(["r#e2", "r#e10"]), ["r#e10", "r#e2"])

    def test_most_replied_uses_its_own_declared_metric_and_never_the_other(self):
        self.assertEqual(
            self.ordered("most_replied"),
            ["changing", "stale", "future", "missing", "wrong_name", "equal_time", "untimed"],
        )

    def test_cross_source_chronology_crosses_roles_and_keeps_one_total_order(self):
        self.assertEqual(
            cases_of(
                runner.order_records(
                    self.records,
                    "cross_source_chronology",
                    self.as_of,
                    descriptors=self.descriptors,
                )
            ),
            [
                "future",
                "changing",
                "missing",
                "wrong_name",
                "stale",
                "equal_time",
                "hit_reddit",
                "hit_x",
                "untimed",
            ],
        )

    def test_a_metric_name_is_never_inferred_from_the_snapshot_that_carries_it(self):
        # With nothing declared, every row's comment count is missing — even
        # the row whose snapshot is literally called `comment_count`. The order
        # collapses to the time-and-id tail, which is the whole tell.
        undeclared = cases_of(
            runner.order_records(
                self.native, "most_commented", self.as_of, descriptors=DECLARING_DESCRIPTORS
            )
        )

        self.assertEqual(
            undeclared,
            ["future", "changing", "missing", "wrong_name", "stale", "equal_time", "untimed"],
        )
        self.assertEqual(undeclared, self.ordered("newest"))

    def test_a_family_scoped_order_refuses_to_compare_across_families(self):
        for order in ("newest", "native_top", "most_commented", "most_replied"):
            with self.subTest(order=order):
                with self.assertRaises(runner.OrderingError):
                    runner.order_records(
                        self.records, order, self.as_of, descriptors=self.descriptors
                    )

    def test_an_order_the_contract_does_not_name_is_refused(self):
        self.assertEqual(
            runner.ORDERING_CONTRACT,
            (
                "newest",
                "cross_source_chronology",
                "native_top",
                "most_commented",
                "most_replied",
            ),
        )
        with self.assertRaises(runner.OrderingError):
            runner.order_records(self.native, "most_upvoted", self.as_of)

    def test_no_wall_clock_participates_and_the_replay_is_repeatable(self):
        first = self.ordered("most_commented")
        again = self.ordered("most_commented")

        self.assertEqual(first, again)
        self.assertEqual(
            sources_naming(("datetime.now", "time.time", "utcnow"), package_sources()),
            [("transport.py", "datetime.now")],
        )

    def test_the_artifacts_own_record_order_is_step_then_page_then_list(self):
        fused = fused_run()

        positions = [
            (
                [step.step_id for step in fused.artifact.steps].index(record.step_id),
                record.page_index,
                record.list_index,
            )
            for record in fused.artifact.records
        ]

        self.assertEqual(positions, sorted(positions))


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

    def test_the_page_s_own_account_of_the_read_reaches_the_artifact(self):
        # Forty-five write sites across the package and, until this seam
        # carried them, no reader anywhere: `run_step` copied `outcome` and
        # `loss` and dropped `warnings`, so every explanatory sentence an
        # adapter wrote died between the page and the artifact and a typed
        # failure arrived naming only its kind.
        clock = helpers.FakeClock()
        carrier, _ = helpers.offline_transport(
            clock, {transport.DDG_HTML_ROUTE: RATE_LIMITED_ANSWER}
        )
        governor = runner.RateGovernor(carrier, clock=clock.monotonic, sleep=clock.sleep)

        artifact = runner.run_acquisition(schema.parse_manifest(DISCOVERY_MANIFEST), governor)
        said = " ".join(artifact.steps[0].warnings)

        self.assertIn(transport.DDG_HTML_ROUTE, said)
        self.assertIn(str(transport.RATE_LIMITED_STATUS), said)

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

    def test_an_adapter_declares_a_rotating_identifier_only_when_it_depends_on_one(self):
        declaring = tuple(
            adapter_id
            for adapter_id in runner.ADAPTER_IDS
            if runner.descriptor_for(adapter_id).volatile_identifiers
        )

        self.assertEqual(declaring, ADAPTERS_WITH_ROTATING_IDENTIFIERS)


class FakeClockOnlyTest(unittest.TestCase):
    """Criterion 5: every wait here is a number, and nothing in the suite waits."""

    def test_the_whole_pacing_proof_runs_with_every_wall_clock_wait_forbidden(self):
        clock = helpers.FakeClock()
        governor, _ = paced_governor(
            clock,
            {REDDIT_FEED_ROUTE: [OK_JSON, RATE_LIMITED_ANSWER, OK_JSON]},
            latencies={REDDIT_FEED_ROUTE: 0.5},
        )

        with helpers.forbid_sleep():
            for index in range(3):
                governor.fetch(probe_request(REDDIT_FEED_ROUTE, index))

        assert_rate_budget_respected(self, governor, SEEDED_BUDGETS)
        # A minute of interval and half a minute of cooldown, none of it spent.
        self.assertGreaterEqual(clock.seconds, 60.0)
        self.assertGreater(sum(read.waited_us for read in governor.log), 0)

    def test_neither_this_suite_nor_its_helpers_reach_a_wall_clock_wait(self):
        for path in (Path(__file__).resolve(), Path(helpers.__file__).resolve()):
            with self.subTest(module=path.name):
                self.assertNotIn("time.sleep", helpers.attribute_names(path))

    def test_the_governor_still_waits_for_real_when_nobody_injects_a_clock(self):
        # The other half of the same claim, and the one a fake clock could
        # quietly destroy: deleting the production wait would make every proof
        # above pass and every rate limit in production go unrespected.
        #
        # Stated as the set of modules that wait rather than as one path. T11
        # moved the governor out of `runner.py`, and following the assertion to
        # `pacing.py` alone would say only what the original said. The set says
        # it and one more thing the path form cannot: a second module quietly
        # acquiring a real wall-clock wait is as wrong as no module having one,
        # because a wait outside the governor is paced by nothing.
        waiting = sorted(
            path.name
            for path in PACKAGE_DIR.rglob("*.py")
            if "time.sleep" in helpers.attribute_names(path)
        )

        self.assertEqual(waiting, ["pacing.py"])
        self.assertIn("time.monotonic", helpers.attribute_names(PACKAGE_DIR / "runner.py"))

    def test_the_whole_pipeline_runs_with_every_io_primitive_refused(self):
        governor, _, clock = tracer_governor()
        guarded_governor, _, guarded_clock = tracer_governor()

        expected = run_on(clock, governor, FUSED_MANIFEST)
        with helpers.forbid_io():
            guarded = run_on(guarded_clock, guarded_governor, FUSED_MANIFEST)

        self.assertTrue(expected.artifact.records)
        self.assertEqual(guarded.artifact, expected.artifact)
        self.assertEqual(guarded.ledger, expected.ledger)


class OracleCanFailTest(unittest.TestCase):
    """Criteria 6 and 10: every oracle above is shown to reject, and to accept.

    Each wrong result is a file beside the tree — the real governor with one
    method overridden, or the real fused run with one property of its output
    spoiled — so a rejection is attributable to that one difference and nothing
    under test was mutated to produce it.
    """

    def setUp(self):
        self.wrong = load_module_beside_the_tree(FIXTURE_DIR / "wrong_pipelines.py")

    def test_a_governor_that_ignores_its_declared_interval_is_rejected(self):
        clock = helpers.FakeClock()
        governor, _ = paced_governor(
            clock,
            {REDDIT_FEED_ROUTE: OK_JSON},
            latencies={REDDIT_FEED_ROUTE: 0.5},
            governor_class=self.wrong.UnpacedGovernor,
        )

        for index in range(3):
            governor.fetch(probe_request(REDDIT_FEED_ROUTE, index))

        with self.assertRaisesRegex(AssertionError, "outran its route's declared budget"):
            assert_rate_budget_respected(self, governor, SEEDED_BUDGETS)

    def test_the_same_budget_oracle_accepts_the_real_governor(self):
        clock = helpers.FakeClock()
        governor, _ = paced_governor(
            clock, {REDDIT_FEED_ROUTE: OK_JSON}, latencies={REDDIT_FEED_ROUTE: 0.5}
        )

        for index in range(3):
            governor.fetch(probe_request(REDDIT_FEED_ROUTE, index))

        assert_rate_budget_respected(self, governor, SEEDED_BUDGETS)

    def test_a_governor_that_changes_identity_between_reads_is_rejected(self):
        # The evasion case, and the one that would otherwise pass every timing
        # clause: this governor waits out every interval it is given, under a
        # different name each time.
        clock = helpers.FakeClock()
        governor, _ = paced_governor(
            clock,
            {REDDIT_FEED_ROUTE: OK_JSON},
            latencies={REDDIT_FEED_ROUTE: 0.5},
            governor_class=self.wrong.RotatingGovernor,
        )

        for index in range(2):
            governor.fetch(probe_request(REDDIT_FEED_ROUTE, index))

        with self.assertRaisesRegex(AssertionError, "the identity changed between reads"):
            assert_rate_budget_respected(self, governor, SEEDED_BUDGETS)

    def test_the_identity_rotation_scan_can_fail(self):
        # Pointed at a source that does name them — this one, which names them
        # in order to forbid them — the scan finds every one.
        found = sources_naming(IDENTITY_ROTATION_NAMES, [Path(__file__).resolve()])

        self.assertEqual([name for _, name in found], sorted(IDENTITY_ROTATION_NAMES))

    def test_a_fused_path_that_folds_the_pair_into_one_record_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, "different numbers of records"):
            assert_fused_collapses_latency_and_not_lineage(
                self, fused_run(self.wrong.merged_fused_run), staged_pair(self)
            )

    def test_a_fused_path_that_drops_the_link_between_the_pair_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, "linked its records differently"):
            assert_fused_collapses_latency_and_not_lineage(
                self, fused_run(self.wrong.unlinked_fused_run), staged_pair(self)
            )

    def test_a_fused_path_that_collapses_no_latency_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, "did not collapse any latency"):
            assert_fused_collapses_latency_and_not_lineage(
                self, fused_run(self.wrong.serialized_fused_run), staged_pair(self)
            )

    def test_a_governor_that_restamps_a_served_answer_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, "restamped with the serve time"):
            assert_cache_hit_reaches_the_record(self, self.wrong.restamping)

    def test_a_governor_that_drops_the_mark_before_the_record_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, "carries no cache_hit mark"):
            assert_cache_hit_reaches_the_record(self, self.wrong.unmarked)

    def test_the_same_record_oracle_accepts_the_fixtures_own_correct_governor(self):
        # Which is what makes the two rejections above attributable: the
        # correct fixture is the same construction with nothing overridden.
        assert_cache_hit_reaches_the_record(self, self.wrong.correct)

    def test_nothing_in_the_package_can_reach_a_wrong_pipeline(self):
        self.assertEqual(
            sources_naming(
                (
                    "wrong_pipelines",
                    "UnpacedGovernor",
                    "RotatingGovernor",
                    "RestampingGovernor",
                    "UnmarkedGovernor",
                ),
                package_sources(),
            ),
            [],
        )


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

        self.assertNotIn("not_an_adapter", runner.ADAPTER_IDS)
        self.assertIsNone(runner.descriptor_for("not_an_adapter"))
        with self.assertRaises(runner.RunnerError):
            runner.call_adapter("not_an_adapter", carrier, PROBE_REQUEST)


if __name__ == "__main__":
    unittest.main()
