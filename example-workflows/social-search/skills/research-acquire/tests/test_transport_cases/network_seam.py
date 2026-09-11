"""Transport network-seam cases."""

from .common import *
from .route_ownership import adapter_sources, sources_naming

class ChannelVerdictTest(unittest.TestCase):
    """Completion criteria 1 and 2: the detector types both halves of the caveat."""

    def test_a_portal_marked_failure_is_a_network_interception(self):
        verdict = transport.channel_verdict(503, read_fixture("captive_portal.html"))

        self.assertEqual(verdict, transport.NETWORK_INTERCEPTED)

    def test_an_origin_503_without_the_marker_is_an_origin_failure(self):
        verdict = transport.channel_verdict(503, read_fixture("origin_service_unavailable.html"))

        self.assertEqual(verdict, transport.ORIGIN_FAILURE)

    def test_an_origin_authwall_stays_a_platform_failure(self):
        verdict = transport.channel_verdict(403, read_fixture("origin_authwall.html"))

        self.assertEqual(verdict, transport.ORIGIN_FAILURE)

    def test_genuine_origin_content_is_origin_content(self):
        verdict = transport.channel_verdict(200, read_fixture("origin_page.html"))

        self.assertEqual(verdict, transport.ORIGIN_CONTENT)

    def test_a_success_carrying_the_marker_is_still_origin_content(self):
        # An origin's own login page sets the same base href. Nothing measured
        # shows an interception answering 2xx, so claiming this one would be
        # over-claiming in the opposite direction.
        verdict = transport.channel_verdict(200, read_fixture("origin_login_page.html"))

        self.assertEqual(verdict, transport.ORIGIN_CONTENT)

    def test_the_marker_match_ignores_tag_case(self):
        verdict = transport.channel_verdict(503, read_fixture("captive_portal_uppercase_tag.html"))

        self.assertEqual(verdict, transport.NETWORK_INTERCEPTED)

    def test_every_measured_case_is_typed_as_its_evidence_says(self):
        assert_channel_verdicts(self, detected_verdicts())

    def test_the_detector_reads_no_file_and_opens_no_socket(self):
        body = read_fixture("captive_portal.html")

        with forbid_io():
            verdict = transport.channel_verdict(503, body)

        self.assertEqual(verdict, transport.NETWORK_INTERCEPTED)


class FetchedChannelVerdictTest(unittest.TestCase):
    """The verdict rides on the response, so no caller can fail to see it."""

    def _fetched(self, body_fixture, status):
        carrier, opener = offline_transport(
            {transport.DDG_HTML_ROUTE: (status, read_fixture(body_fixture), "text/html")}
        )
        response = carrier.fetch(
            transport.build_transport_request(transport.DDG_HTML_ROUTE, {"q": "probe"})
        )
        return response, opener

    def test_a_fetched_portal_503_is_typed_network_intercepted(self):
        response, opener = self._fetched("captive_portal.html", 503)

        self.assertEqual(response.channel_verdict, transport.NETWORK_INTERCEPTED)
        self.assertEqual(response.status, 503)
        self.assertEqual(len(opener.opened), 1)

    def test_a_fetched_origin_503_is_typed_origin_failure_and_never_intercepted(self):
        response, _ = self._fetched("origin_service_unavailable.html", 503)

        self.assertEqual(response.channel_verdict, transport.ORIGIN_FAILURE)
        self.assertNotEqual(response.channel_verdict, transport.NETWORK_INTERCEPTED)

    def test_a_fetched_success_is_typed_origin_content(self):
        response, _ = self._fetched("origin_page.html", 200)

        self.assertEqual(response.channel_verdict, transport.ORIGIN_CONTENT)

    def test_every_measured_case_survives_the_fetch_seam(self):
        assert_channel_verdicts(self, fetched_verdicts())

    def test_no_fetch_ever_produces_a_verdict_outside_the_closed_set(self):
        for name, verdict in sorted(fetched_verdicts().items()):
            with self.subTest(case=name):
                self.assertIn(verdict, transport.CHANNEL_VERDICTS)


def adapter_page(module, status, body, content_type="text/html"):
    """Run one adapter over one canned response; return its page and the opener."""

    carrier, opener = offline_transport(
        {module.DESCRIPTOR.route_id: (status, body, content_type)}
    )
    return module.fetch_native_page(carrier, PROBE_REQUEST), opener


def adapter_pages(module):
    """Type every measured case through one adapter's own ``fetch_native_page``."""

    return {
        row["case_name"]: adapter_page(module, row["status"], case_body(row))[0]
        for row in interception_cases()
    }


def load_adapter_fixture(name):
    """Load one adapter written beside the tree, by path.

    These are not package modules: nothing in the package imports them and no
    discovery pattern matches them. They exist so the protocol can be shown to
    carry — or, for a wrong one, to fail to carry — the channel verdict on an
    adapter's behalf, without mutating the tree under test.
    """

    spec = importlib.util.spec_from_file_location(
        "adapter_fixture_" + name, FIXTURE_DIR / (name + ".py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def assert_interception_reaches_the_page(case, adapter_id, pages):
    """The page oracle: the record an adapter emits names the party that answered.

    ``pages`` maps a measured case name to the ``NativePage`` some adapter
    produced for it. A local block must arrive as `network_intercepted` and
    never as an http status — the captive-portal caveat's rule is about what gets
    recorded, not only about what transport can tell — and an origin's own
    response must never be blamed on the network. Each assertion names the
    confusion it caught.
    """

    for row in interception_cases():
        name = row["case_name"]
        case.assertIn(name, pages, "{0} produced no page for case {1}".format(adapter_id, name))
        loss = tuple(pages[name].loss)
        detail = " {0} typed case {1} as loss {2}".format(adapter_id, name, loss)
        if row["expected_verdict"] == transport.NETWORK_INTERCEPTED:
            if transport.NETWORK_INTERCEPTED not in loss:
                case.fail("a local network block reached the page as a platform gap:" + detail)
            if "http_status" in loss:
                case.fail("a local network block was recorded as an http status:" + detail)
        elif transport.NETWORK_INTERCEPTED in loss:
            case.fail("an origin response was recorded as a network interception:" + detail)


class InterceptionReachesThePageTest(unittest.TestCase):
    """Completion criteria 1 and 2: the verdict reaches the page, from one place.

    The distinction `transport.py` draws is worth nothing until it is what an
    adapter records, so every case here reads a ``NativePage``'s loss, not a
    response's verdict.
    """

    def test_every_shipped_adapter_records_a_local_block_as_a_local_one(self):
        for module in SHIPPED_ADAPTERS:
            with self.subTest(adapter=module.DESCRIPTOR.adapter_id):
                assert_interception_reaches_the_page(
                    self, module.DESCRIPTOR.adapter_id, adapter_pages(module)
                )

    def test_an_intercepted_call_yields_one_typed_page_and_no_second_call(self):
        for module in SHIPPED_ADAPTERS:
            with self.subTest(adapter=module.DESCRIPTOR.adapter_id):
                page, opener = adapter_page(module, 503, read_fixture("captive_portal.html"))

                self.assertEqual(page.loss, (transport.NETWORK_INTERCEPTED,))
                self.assertEqual(page.outcome, "failed")
                self.assertEqual(page.records, ())
                self.assertEqual(page.route_id, module.DESCRIPTOR.route_id)
                self.assertEqual(len(opener.opened), 1)

    def test_an_adapter_that_writes_no_interception_branch_still_types_the_block(self):
        minimal = load_adapter_fixture("minimal_adapter")

        assert_interception_reaches_the_page(self, "minimal_adapter", adapter_pages(minimal))

        page, opener = adapter_page(minimal, 503, read_fixture("captive_portal.html"))
        self.assertEqual(page.loss, (transport.NETWORK_INTERCEPTED,))
        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.records, ())
        self.assertEqual(len(opener.opened), 1)

    def test_the_minimal_adapter_names_nothing_the_protocol_owns(self):
        # Which is what makes the case above worth anything: the inheritance
        # is free, not a branch the fixture quietly wrote for itself.
        self.assertEqual(
            sources_naming(PROTOCOL_OWNED_NAMES, [FIXTURE_DIR / "minimal_adapter.py"]), []
        )

    def test_no_shipped_adapter_reads_the_channel_or_calls_the_carrier_itself(self):
        # Criterion 2 as a structure, not only as a behavior: the branch lives
        # in the protocol, so an adapter added later inherits it by writing
        # nothing. Naming any of these is how the distinction would get lost
        # again, one adapter at a time.
        self.assertEqual(sources_naming(PROTOCOL_OWNED_NAMES, adapter_sources()), [])


class OriginBehaviorSurvivesTest(unittest.TestCase):
    """The origin's own responses, pinned before the interception branch existed.

    These say what each shipped adapter does with a response the origin itself
    sent. They are the counterweight to the interception path: a branch that
    widened to swallow ordinary failures, or that read the portal marker
    without the failure status, is caught here.
    """

    def test_a_marker_less_503_stays_the_origins_own_http_failure(self):
        for module in (web_search, reddit_archive):
            with self.subTest(adapter=module.DESCRIPTOR.adapter_id):
                page, opener = adapter_page(
                    module, 503, read_fixture("origin_service_unavailable.html")
                )

                self.assertEqual(page.outcome, "failed")
                self.assertEqual(page.loss, ("http_status",))
                self.assertEqual(page.records, ())
                self.assertIn("503", " ".join(page.warnings))
                self.assertEqual(len(opener.opened), 1)

    def test_a_403_authwall_stays_the_platforms_own_refusal(self):
        for module in (web_search, reddit_archive):
            with self.subTest(adapter=module.DESCRIPTOR.adapter_id):
                page, _ = adapter_page(module, 403, read_fixture("origin_authwall.html"))

                self.assertEqual(page.outcome, "failed")
                self.assertEqual(page.loss, ("http_status",))
                self.assertIn("403", " ".join(page.warnings))

    def test_the_offline_adapter_keeps_its_own_typed_failure(self):
        # `fake` never had a status branch: a body it cannot parse is
        # `malformed_json`, whatever status carried it.
        page, _ = adapter_page(fake, 503, read_fixture("origin_service_unavailable.html"))

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.loss, ("malformed_json",))

    def test_a_success_carrying_the_portal_marker_still_parses_into_records(self):
        page, _ = adapter_page(
            web_search, 200, read_fixture("origin_results_with_portal_marker.html")
        )

        self.assertEqual(page.outcome, "ok")
        self.assertEqual(page.loss, ())
        self.assertEqual(
            [record.canonical_locator for record in page.records],
            ["https://example.org/notes/local-models", "https://example.net/kv-cache"],
        )

    def test_a_record_whose_body_quotes_the_marker_is_still_content(self):
        page, _ = adapter_page(
            reddit_archive,
            200,
            read_fixture("origin_archive_with_portal_marker.json"),
            "application/json",
        )

        self.assertEqual(page.outcome, "ok")
        self.assertEqual(page.loss, ())
        self.assertIn('<base href="/login/">', page.records[0].body)


def intercepted_step_manifest():
    """One discovery step, one call, over whichever adapter ``runner`` resolves."""

    return schema.AcquisitionManifest(
        manifest_id="m-intercepted",
        mode="staged",
        as_of=FROZEN_OBSERVED_AT,
        steps=(
            schema.AcquisitionStep(
                step_id="s1-discover",
                kind="discovery",
                adapter_id="web_search",
                query="probe",
                max_items=10,
            ),
        ),
    )


def assert_artifact_never_blames_the_platform(case, artifact):
    """The objective at its widest seam: what a caller keeps names who blocked it."""

    if transport.NETWORK_INTERCEPTED not in artifact.loss:
        case.fail(
            "a local network block reached the artifact as loss {0}".format(artifact.loss)
        )
    if "http_status" in artifact.loss:
        case.fail(
            "a local network block was recorded as an http status: {0}".format(artifact.loss)
        )


class InterceptionReachesTheArtifactTest(unittest.TestCase):
    """Criterion 1, at the seam the objective names: the artifact a caller keeps.

    A page is an intermediate value. ``runner`` folds page loss into the step
    result and the step results into the artifact, so this is where "never
    recorded as a platform gap" is finally either true or false.
    """

    def test_a_blocked_run_is_recorded_as_a_local_block_end_to_end(self):
        carrier, _ = offline_transport(
            {transport.DDG_HTML_ROUTE: (503, read_fixture("captive_portal.html"), "text/html")}
        )

        artifact = runner.run_acquisition(intercepted_step_manifest(), carrier)

        assert_artifact_never_blames_the_platform(self, artifact)
        self.assertEqual(artifact.loss, (transport.NETWORK_INTERCEPTED,))
        self.assertEqual(artifact.outcome, "failed")
        self.assertEqual(artifact.records, ())
        self.assertEqual(
            [step.loss for step in artifact.steps], [(transport.NETWORK_INTERCEPTED,)]
        )

class OracleCanFailTest(unittest.TestCase):
    """Completion criterion 4: the interception oracle fails on a wrong result.

    Every verdict map here is built beside the tree from
    ``fixtures/transport/wrong_channel_verdicts.json``. Nothing in the package
    produces them, and nothing under test is mutated to obtain them.
    """

    def _assert_oracle_rejects(self, case_name):
        wrong = wrong_channel_verdicts()[case_name]

        with self.assertRaises(AssertionError) as caught:
            assert_channel_verdicts(self, wrong["verdicts"])

        self.assertIn(wrong["expected_oracle_reason"], str(caught.exception))

    def test_a_portal_marked_503_read_as_a_platform_gap_fails_the_oracle(self):
        self._assert_oracle_rejects("portal_read_as_platform_gap")

    def test_a_detector_with_no_portal_branch_at_all_fails_the_oracle(self):
        # The whole output of a status-only detector — one that types every
        # failure as the origin's. The oracle discriminates on the mechanism,
        # not only on a single doctored cell.
        self._assert_oracle_rejects("portal_blind_detector")

    def test_a_case_sensitive_detector_that_misses_the_marker_fails_the_oracle(self):
        self._assert_oracle_rejects("uppercase_marker_missed")

    def test_an_origin_503_read_as_an_interception_fails_the_oracle(self):
        self._assert_oracle_rejects("origin_failure_read_as_interception")

    def test_a_login_page_read_as_an_interception_fails_the_oracle(self):
        self._assert_oracle_rejects("login_page_read_as_interception")

    def test_origin_content_read_as_a_failure_fails_the_oracle(self):
        self._assert_oracle_rejects("success_read_as_failure")

    def test_a_case_left_unclassified_fails_the_oracle(self):
        self._assert_oracle_rejects("portal_case_never_classified")

    def test_the_same_oracle_passes_on_the_real_detector(self):
        assert_channel_verdicts(self, detected_verdicts())
        assert_channel_verdicts(self, fetched_verdicts())


class InterceptionOracleCanFailTest(unittest.TestCase):
    """Completion criterion 4: every oracle this ticket adds fails on a wrong result.

    Both adapters below are written beside the tree and loaded by path: they
    are the two ways this claim can be false, one in each direction. Nothing
    in the package produces them and nothing under test is mutated to obtain
    them.
    """

    def _assert_oracle_rejects(self, name, reason):
        wrong = load_adapter_fixture(name)

        with self.assertRaises(AssertionError) as caught:
            assert_interception_reaches_the_page(self, name, adapter_pages(wrong))

        self.assertIn(reason, str(caught.exception))

    def test_an_adapter_that_tests_status_before_the_verdict_fails_the_oracle(self):
        # Row 4's named case, and the shape every adapter had before this
        # change: the local block arrives as the platform's own http failure.
        self._assert_oracle_rejects(
            "status_first_adapter",
            "a local network block reached the page as a platform gap",
        )

    def test_an_adapter_that_blames_the_network_for_every_failure_fails_the_oracle(self):
        # The opposite error. Without this side the oracle could be satisfied
        # by typing everything as a local block, which erases every platform
        # gap the run exists to record.
        self._assert_oracle_rejects(
            "intercept_every_failure_adapter",
            "an origin response was recorded as a network interception",
        )

    def test_the_protocol_scan_can_fail(self):
        found = sources_naming(
            PROTOCOL_OWNED_NAMES,
            [
                FIXTURE_DIR / "intercept_every_failure_adapter.py",
                FIXTURE_DIR / "status_first_adapter.py",
            ],
        )

        self.assertEqual(
            found,
            [
                ("intercept_every_failure_adapter.py", "NETWORK_INTERCEPTED"),
                ("intercept_every_failure_adapter.py", "carrier.fetch"),
                ("status_first_adapter.py", "carrier.fetch"),
            ],
        )

    def test_a_status_first_adapter_fails_the_artifact_oracle_too(self):
        # The same wrong adapter, stood in for `web_search` at the runner's
        # own branch: the run completes and its artifact blames DuckDuckGo for
        # a page this network never let out. Restored on exit — the tree on
        # disk is never the thing mutated.
        wrong = load_adapter_fixture("status_first_adapter")
        carrier, _ = offline_transport(
            {transport.DDG_HTML_ROUTE: (503, read_fixture("captive_portal.html"), "text/html")}
        )

        with mock.patch.object(runner, "web_search", wrong):
            artifact = runner.run_acquisition(intercepted_step_manifest(), carrier)

        self.assertEqual(artifact.loss, ("http_status",))
        with self.assertRaises(AssertionError) as caught:
            assert_artifact_never_blames_the_platform(self, artifact)

        self.assertIn("reached the artifact as loss", str(caught.exception))

    def test_the_same_oracle_passes_on_every_shipped_adapter(self):
        for module in SHIPPED_ADAPTERS:
            with self.subTest(adapter=module.DESCRIPTOR.adapter_id):
                assert_interception_reaches_the_page(
                    self, module.DESCRIPTOR.adapter_id, adapter_pages(module)
                )
