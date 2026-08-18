"""Partial-result, oracle-discrimination, and adapter-branch cases."""

from tests.test_pipeline_cases.common import *
from tests.test_pipeline_cases.artifact import (
    assert_cache_hit_reaches_the_record,
    assert_fused_collapses_latency_and_not_lineage,
    fused_run,
    real_governor,
    run_on,
    staged_pair,
    tracer_governor,
)


IDENTITY_ROTATION_NAMES = (
    "ProxyHandler", "build_opener", "install_opener", "set_proxy",
    "proxies", "user_agents", "USER_AGENTS",
)


def unreachable_run():
    clock = helpers.FakeClock()
    responses = dict(tracer_responses())
    responses[transport.ARCTIC_SHIFT_POSTS_ROUTE] = transport.TransportError(
        "transport failed for " + transport.ARCTIC_SHIFT_POSTS_ROUTE
    )
    carrier, opener = helpers.offline_transport(
        clock, responses, latencies=ROUTE_LATENCIES
    )
    governor = real_governor(carrier, None, clock)
    return run_on(clock, governor, TWO_STEP_MANIFEST), opener, governor


class AStepThatGotNoAnswerIsTypedTest(unittest.TestCase):
    def test_the_steps_before_it_keep_their_records_and_their_results(self):
        run, _, _ = unreachable_run()
        kept = [
            record for record in run.artifact.records if record.step_id == "s1-discover"
        ]
        self.assertTrue(kept, "the discovery step's records went with the exception")
        self.assertEqual(run.artifact.steps[0].outcome, "ok")
        self.assertEqual(run.artifact.steps[0].records_kept, len(kept))

    def test_the_step_that_got_no_answer_says_so(self):
        run, _, _ = unreachable_run()
        failed = run.artifact.steps[1]
        self.assertEqual(failed.step_id, "s2-hydrate")
        self.assertEqual(failed.outcome, "failed")
        self.assertIn("unreachable", failed.loss)
        self.assertIn("unreachable", run.artifact.loss)
        self.assertEqual(failed.records_kept, 0)

    def test_the_error_text_rides_along_as_that_steps_warning(self):
        run, _, _ = unreachable_run()
        self.assertTrue(
            any(
                transport.ARCTIC_SHIFT_POSTS_ROUTE in warning
                for warning in run.artifact.steps[1].warnings
            ),
            "the step names no route for the read that never completed",
        )

    def test_the_run_reaches_its_ledger_and_bills_no_call_for_the_read_nobody_took(self):
        run, opener, governor = unreachable_run()
        sums = runner.ledger_sums(run.ledger)
        self.assertEqual(sums["calls"], len(governor.log))
        self.assertEqual(len(opener.opened), len(governor.log) + 1)
        self.assertNotIn(
            transport.ARCTIC_SHIFT_POSTS_ROUTE, governor._route_arrival_us
        )
        self.assertEqual(sums["pages"], sum(step.pages for step in run.artifact.steps))
        self.assertEqual(
            sums["items"], sum(step.records_received for step in run.artifact.steps)
        )

    def test_the_oracle_rejects_the_run_that_answered(self):
        governor, _, clock = tracer_governor()
        healthy = run_on(clock, governor, TWO_STEP_MANIFEST)
        self.assertNotIn("unreachable", healthy.artifact.loss)
        self.assertNotEqual(healthy.artifact.steps[1].outcome, "failed")


class OracleCanFailTest(unittest.TestCase):
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
        with self.assertRaisesRegex(
            AssertionError, "outran its route's declared budget"
        ):
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
        assert_cache_hit_reaches_the_record(self, self.wrong.correct)

    def test_nothing_in_the_package_can_reach_a_wrong_pipeline(self):
        self.assertEqual(
            sources_naming(
                (
                    "wrong_pipelines", "UnpacedGovernor", "RotatingGovernor",
                    "RestampingGovernor", "UnmarkedGovernor",
                ),
                package_sources(),
            ),
            [],
        )


class AdapterBranchTest(unittest.TestCase):
    def test_every_listed_adapter_id_resolves_to_a_descriptor_and_to_a_call(self):
        for adapter_id in runner.ADAPTER_IDS:
            with self.subTest(adapter=adapter_id):
                descriptor = runner.descriptor_for(adapter_id)
                self.assertIsNotNone(descriptor)
                self.assertEqual(descriptor.adapter_id, adapter_id)
                clock = helpers.FakeClock()
                carrier, opener = helpers.offline_transport(
                    clock,
                    {
                        surface.route_id: EMPTY_PAGE_BODY
                        for surface in runner.surface_descriptors(adapter_id)
                    },
                )
                page = runner.call_adapter(
                    adapter_id, carrier, probe_request_for(adapter_id)
                )
                self.assertIn(
                    page.route_id,
                    {
                        surface.route_id
                        for surface in runner.surface_descriptors(adapter_id)
                    },
                )
                self.assertEqual(len(opener.opened), 1)

    def test_an_adapter_the_core_does_not_list_is_refused_rather_than_guessed(self):
        clock = helpers.FakeClock()
        carrier, _ = helpers.offline_transport(clock, {})
        self.assertNotIn("not_an_adapter", runner.ADAPTER_IDS)
        self.assertIsNone(runner.descriptor_for("not_an_adapter"))
        with self.assertRaises(runner.RunnerError):
            runner.call_adapter("not_an_adapter", carrier, PROBE_REQUEST)
