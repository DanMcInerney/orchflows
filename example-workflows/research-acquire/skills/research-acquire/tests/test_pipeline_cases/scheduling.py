"""Pacing, cooldown, composition, and wall-clock scheduling cases."""

from tests.test_pipeline_cases.common import *
from tests.test_pipeline_cases.artifact import run_on, tracer_governor


IDENTITY_ROTATION_NAMES = (
    "ProxyHandler", "build_opener", "install_opener", "set_proxy",
    "proxies", "user_agents", "USER_AGENTS",
)


class TheDocumentedPathPacesAndRemembersTest(unittest.TestCase):
    def test_the_composed_carrier_is_a_governor_over_a_run_cache(self):
        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(
            clock, tracer_responses(), latencies=ROUTE_LATENCIES
        )
        composed = runner.paced_carrier(
            carrier, clock=clock.monotonic, sleep=clock.sleep
        )
        self.assertIsInstance(composed, runner.RateGovernor)
        composed.fetch(probe_request(transport.DDG_HTML_ROUTE))
        composed.fetch(probe_request(transport.DDG_HTML_ROUTE))
        self.assertEqual(len(opener.opened), 1)
        self.assertEqual([serve.cache_hit for serve in composed.serves], [False, True])

    def test_a_run_that_names_no_carrier_is_paced_and_remembers(self):
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
        self.assertEqual(len(opener.opened), reads * 2)
        self.assertEqual(len(repeat.records), len(artifact.records))

    def test_no_module_but_the_composition_builds_its_own_carrier(self):
        building = sorted(
            path.name
            for path in PACKAGE_DIR.rglob("*.py")
            if "transport.Transport(" in path.read_text(encoding="utf-8")
        )
        self.assertEqual(building, ["pacing.py"])


class RateBudgetTest(unittest.TestCase):
    def test_a_repeat_read_waits_out_its_routes_declared_interval(self):
        clock = helpers.FakeClock()
        governor, opener = paced_governor(
            clock, {REDDIT_FEED_ROUTE: OK_JSON}, latencies={REDDIT_FEED_ROUTE: 0.5}
        )
        for index in range(3):
            governor.fetch(probe_request(REDDIT_FEED_ROUTE, index))
        assert_rate_budget_respected(self, governor, SEEDED_BUDGETS)
        self.assertEqual(len(opener.opened), 3)
        self.assertEqual([read.at_us for read in governor.log], [0, 30000000, 60000000])

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
        governor = runner.RateGovernor(
            carrier, clock=clock.monotonic, sleep=clock.sleep
        )
        governor.fetch(probe_request(descriptor.route_id, 0))
        governor.fetch(probe_request(descriptor.route_id, 1))
        self.assertGreater(descriptor.min_interval_ms, 0)
        self.assertEqual(
            governor.log[1].at_us - governor.log[0].at_us,
            descriptor.min_interval_ms * US_PER_MS,
        )

    def test_two_adapters_may_not_declare_one_route_two_different_budgets(self):
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
    def test_a_declared_burst_leaves_at_once_and_then_paces(self):
        clock = helpers.FakeClock()
        governor, opener = paced_governor(
            clock, {GITHUB_REST_ROUTE: OK_JSON}, latencies={GITHUB_REST_ROUTE: 0.0}
        )
        for index in range(GITHUB_REST_BUDGET.burst + 1):
            governor.fetch(probe_request(GITHUB_REST_ROUTE, index))
        assert_rate_budget_respected(self, governor, SEEDED_BUDGETS)
        arrivals = [read.at_us for read in governor.log]
        self.assertEqual(
            arrivals[: GITHUB_REST_BUDGET.burst], [0] * GITHUB_REST_BUDGET.burst
        )
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
        self.assertEqual(
            {request.route_id for request in opener.opened}, {REDDIT_FEED_ROUTE}
        )

    def test_a_rate_limited_response_is_typed_rather_than_substituted(self):
        later = load_module_beside_the_tree(LATER_ADAPTER)
        for module in SHIPPED_ADAPTERS + (later,):
            with self.subTest(adapter=module.DESCRIPTOR.adapter_id):
                page, opener = adapter_page(
                    module, helpers.FakeClock(), RATE_LIMITED_ANSWER
                )
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
        governor = runner.RateGovernor(
            carrier, clock=clock.monotonic, sleep=clock.sleep
        )
        artifact = runner.run_acquisition(
            schema.parse_manifest(DISCOVERY_MANIFEST), governor
        )
        self.assertEqual(artifact.steps[0].route_id, transport.DDG_HTML_ROUTE)
        self.assertEqual(artifact.steps[0].loss, (transport.RATE_LIMITED,))
        self.assertEqual(artifact.steps[0].outcome, "failed")
        self.assertEqual(artifact.loss, (transport.RATE_LIMITED,))
        self.assertEqual(artifact.records, ())
        self.assertEqual(
            {request.route_id for request in opener.opened}, {transport.DDG_HTML_ROUTE}
        )

    def test_the_page_s_own_account_of_the_read_reaches_the_artifact(self):
        clock = helpers.FakeClock()
        carrier, _ = helpers.offline_transport(
            clock, {transport.DDG_HTML_ROUTE: RATE_LIMITED_ANSWER}
        )
        governor = runner.RateGovernor(
            carrier, clock=clock.monotonic, sleep=clock.sleep
        )
        artifact = runner.run_acquisition(
            schema.parse_manifest(DISCOVERY_MANIFEST), governor
        )
        said = " ".join(artifact.steps[0].warnings)
        self.assertIn(transport.DDG_HTML_ROUTE, said)
        self.assertIn(str(transport.RATE_LIMITED_STATUS), said)

    def test_no_package_module_can_become_a_different_client(self):
        self.assertEqual(sources_naming(IDENTITY_ROTATION_NAMES, package_sources()), [])
        identities = {
            value
            for route_id in transport.ROUTE_CONSTANTS
            for name, value in transport.build_transport_request(
                route_id, helpers.probe_params(route_id)
            ).headers
            if name.lower() == "user-agent"
        }
        self.assertEqual(identities, {transport.USER_AGENT})


class OriginStatedCooldownTest(unittest.TestCase):
    def _held_after(
        self,
        headers,
        status=transport.RATE_LIMITED_STATUS,
        body="slow down",
        route_id=REDDIT_FEED_ROUTE,
    ):
        clock = helpers.FakeClock()
        governor, _ = paced_governor(
            clock,
            {route_id: [answer_stating(route_id, 0, status, body, headers), OK_JSON]},
            latencies={route_id: 0.0},
        )
        governor.fetch(probe_request(route_id, 0))
        governor.fetch(probe_request(route_id, 1))
        assert_rate_budget_respected(self, governor, SEEDED_BUDGETS)
        return cooldown_us(governor)

    def test_a_stated_retry_after_lengthens_the_wait_the_budget_alone_would_take(self):
        held_us = self._held_after(
            ((transport.RETRY_AFTER_HEADER, str(STATED_WAIT_SECONDS)),)
        )
        self.assertGreaterEqual(held_us, REDDIT_FEED_BUDGET.cooldown_ms * US_PER_MS)
        self.assertGreaterEqual(held_us, STATED_WAIT_SECONDS * US_PER_SECOND)

    def test_the_http_date_spelling_states_the_same_wait_as_the_seconds_one(self):
        held_us = self._held_after(
            ((transport.RETRY_AFTER_HEADER, http_date_after(STATED_WAIT_SECONDS)),)
        )
        self.assertGreaterEqual(held_us, REDDIT_FEED_BUDGET.cooldown_ms * US_PER_MS)
        self.assertGreaterEqual(held_us, STATED_WAIT_SECONDS * US_PER_SECOND)

    def test_a_stated_moment_already_past_leaves_the_local_budget_governing(self):
        held_us = self._held_after(
            ((transport.RETRY_AFTER_HEADER, http_date_after(-STATED_WAIT_SECONDS)),)
        )
        self.assertEqual(held_us, REDDIT_FEED_BUDGET.cooldown_ms * US_PER_MS)

    def test_a_stated_reset_window_is_read_under_the_same_floor_rule(self):
        held_us = self._held_after(
            ((transport.RATE_LIMIT_RESET_HEADER, epoch_after(STATED_WAIT_SECONDS)),)
        )
        self.assertGreaterEqual(held_us, REDDIT_FEED_BUDGET.cooldown_ms * US_PER_MS)
        self.assertGreaterEqual(held_us, STATED_WAIT_SECONDS * US_PER_SECOND)

    def test_a_reset_window_already_come_round_leaves_the_local_budget_governing(self):
        held_us = self._held_after(
            ((transport.RATE_LIMIT_RESET_HEADER, epoch_after(-STATED_WAIT_SECONDS)),)
        )
        self.assertEqual(held_us, REDDIT_FEED_BUDGET.cooldown_ms * US_PER_MS)

    def test_an_origin_that_states_two_intervals_is_obeyed_at_the_longer_one(self):
        held_us = self._held_after(
            (
                (transport.RETRY_AFTER_HEADER, "1"),
                (transport.RATE_LIMIT_RESET_HEADER, epoch_after(STATED_WAIT_SECONDS)),
            )
        )
        self.assertGreaterEqual(held_us, STATED_WAIT_SECONDS * US_PER_SECOND)

    def test_a_secondary_limit_403_opens_the_cooldown_the_status_alone_opened_none(self):
        held_us = self._held_after(
            (),
            status=transport.SECONDARY_RATE_LIMITED_STATUS,
            body=SECONDARY_LIMIT_BODY,
            route_id=GITHUB_REST_ROUTE,
        )
        self.assertGreaterEqual(held_us, GITHUB_REST_BUDGET.cooldown_ms * US_PER_MS)

    def test_a_403_about_who_is_asking_opens_no_cooldown_at_all(self):
        held_us = self._held_after(
            (),
            status=transport.SECONDARY_RATE_LIMITED_STATUS,
            body=FORBIDDEN_BODY,
            route_id=GITHUB_REST_ROUTE,
        )
        self.assertEqual(held_us, 0)

    def test_a_success_that_quotes_the_sentence_is_content_and_not_a_refusal(self):
        held_us = self._held_after(
            (), status=200, body=SECONDARY_LIMIT_BODY, route_id=GITHUB_REST_ROUTE
        )
        self.assertEqual(held_us, 0)

    def test_a_header_it_cannot_read_leaves_the_local_budget_governing(self):
        for stated in UNREADABLE_STATED_INTERVALS:
            for header in (
                transport.RETRY_AFTER_HEADER,
                transport.RATE_LIMIT_RESET_HEADER,
            ):
                with self.subTest(header=header, stated=stated):
                    held_us = self._held_after(((header, stated),))
                    self.assertEqual(
                        held_us, REDDIT_FEED_BUDGET.cooldown_ms * US_PER_MS
                    )

    def test_an_answer_that_states_nothing_is_paced_exactly_as_it_always_was(self):
        held_us = self._held_after(())
        self.assertEqual(held_us, REDDIT_FEED_BUDGET.cooldown_ms * US_PER_MS)


class VolatileIdentifierTest(unittest.TestCase):
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
        self.assertGreaterEqual(clock.seconds, 60.0)
        self.assertGreater(sum(read.waited_us for read in governor.log), 0)

    def test_neither_this_suite_nor_its_helpers_reach_a_wall_clock_wait(self):
        for path in (Path(__file__).resolve(), Path(helpers.__file__).resolve()):
            with self.subTest(module=path.name):
                self.assertNotIn("time.sleep", helpers.attribute_names(path))

    def test_the_governor_still_waits_for_real_when_nobody_injects_a_clock(self):
        waiting = sorted(
            path.name
            for path in PACKAGE_DIR.rglob("*.py")
            if "time.sleep" in helpers.attribute_names(path)
        )
        self.assertEqual(waiting, ["pacing.py"])
        self.assertIn(
            "time.monotonic", helpers.attribute_names(PACKAGE_DIR / "runner.py")
        )

    def test_the_whole_pipeline_runs_with_every_io_primitive_refused(self):
        governor, _, clock = tracer_governor()
        guarded_governor, _, guarded_clock = tracer_governor()
        expected = run_on(clock, governor, FUSED_MANIFEST)
        with helpers.forbid_io():
            guarded = run_on(guarded_clock, guarded_governor, FUSED_MANIFEST)
        self.assertTrue(expected.artifact.records)
        self.assertEqual(guarded.artifact, expected.artifact)
        self.assertEqual(guarded.ledger, expected.ledger)
