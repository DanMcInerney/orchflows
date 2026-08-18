"""Artifact, cache, lineage, and ledger cases."""

from tests.test_pipeline_cases.common import *


def real_governor(carrier, run_cache, clock):
    return runner.RateGovernor(
        carrier, run_cache=run_cache, clock=clock.monotonic, sleep=clock.sleep
    )


def tracer_governor(make_governor=real_governor, clock=None, run_cache=None):
    clock = helpers.FakeClock() if clock is None else clock
    carrier, opener = helpers.offline_transport(
        clock, tracer_responses(), latencies=ROUTE_LATENCIES
    )
    return make_governor(carrier, run_cache, clock), opener, clock


def cached_run(make_governor, clock=None):
    clock = helpers.FakeClock() if clock is None else clock
    return tracer_governor(
        make_governor, clock=clock, run_cache=cache.RunCache(clock=clock.monotonic)
    )


def run_on(clock, governor, payload, dispatch_ordinal=0, start_tick_us=0):
    return runner.run_scheduled(
        schema.parse_manifest(payload),
        governor,
        clock=clock.monotonic,
        dispatch_ordinal=dispatch_ordinal,
        start_tick_us=start_tick_us,
        lanes=1,
    )


def assert_cache_hit_reaches_the_record(case, make_governor):
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
    def test_a_served_record_carries_the_mark_and_the_moment_it_was_read(self):
        assert_cache_hit_reaches_the_record(self, real_governor)

    def test_the_mark_is_installed_once_and_no_adapter_writes_it(self):
        self.assertEqual(sources_naming([cache.CACHE_HIT], adapter_sources()), [])

    def test_a_cache_hit_costs_the_routes_rate_budget_nothing(self):
        governor, opener, clock = cached_run(real_governor)
        manifest = schema.parse_manifest(TWO_STEP_MANIFEST)
        runner.run_acquisition(manifest, governor, clock=clock.monotonic)
        origin_reads = len(governor.log)
        runner.run_acquisition(manifest, governor, clock=clock.monotonic)
        self.assertEqual(len(governor.log), origin_reads)
        self.assertEqual(len(opener.opened), origin_reads)
        self.assertEqual(
            [serve.cache_hit for serve in governor.serves[origin_reads:]],
            [True] * origin_reads,
        )


def fused_run(run_fused=None):
    governor, _, clock = tracer_governor()
    if run_fused is None:
        return run_on(clock, governor, FUSED_MANIFEST)
    return run_fused(schema.parse_manifest(FUSED_MANIFEST), governor, clock)


def staged_pair(case):
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
    return dataclasses.replace(record, artifact_id="", manifest_id="")


def assert_linked_and_never_merged(case, records, edges, label):
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
            "{0} has no single discovery record for the locator its hydration names: {1}".format(
                label, hydrated.discovery_locator
            )
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
            "fused grouped its records differently from the staged pair: {0} against {1}".format(
                fused.artifact.groups, staged_groups
            )
        )
    staged_edges = normalize.link_discovery_hydration(staged_records)
    if not staged_edges:
        raise AssertionError("the staged pair reconstructed no lineage: nothing to compare")
    if fused.artifact.edges != staged_edges:
        raise AssertionError(
            "fused linked its records differently from the staged pair: {0} against {1}".format(
                fused.artifact.edges, staged_edges
            )
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
    def test_a_fused_manifest_matches_the_staged_pair_and_finishes_sooner(self):
        assert_fused_collapses_latency_and_not_lineage(self, fused_run(), staged_pair(self))

    def test_a_hydration_steps_calls_come_from_the_frozen_manifest_alone(self):
        fused = schema.parse_manifest(FUSED_MANIFEST)
        staged = schema.parse_manifest(STAGED_HYDRATION_MANIFEST)
        self.assertEqual(fused.steps[1].prior_step_id, "s1-discover")
        self.assertEqual(staged.steps[0].prior_step_id, "")
        self.assertEqual(
            runner.planned_calls(fused.steps[1]), runner.planned_calls(staged.steps[0])
        )

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
        self.assertLess(span, durations)
        self.assertEqual(
            span,
            max(event.stop_tick_us for event in fused.ledger if event.metric != "stop"),
        )
