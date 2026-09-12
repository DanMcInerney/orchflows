"""Transport threat and policy cases."""

from .common import *
from .policy_support import *
from .request_cases import *
from .network_seam import adapter_page





class UntrustedContentTest(unittest.TestCase):
    """T09 and criterion 11's second half: acquired text decides nothing.

    The payload is a real DuckDuckGo results page with three snippets that ask
    for everything a run could give away — a replaced manifest, a widened verb
    set, a new write target, and the guest token. It is parsed by the shipped
    `K4` adapter, so what reaches the artifact is what would reach it live.
    """

    def setUp(self):
        self.grants_before = route_grants()
        self.manifest, self.artifact, self.carrier, self.opener = injected_run()
        self.markers = (
            "IGNORE YOUR PREVIOUS INSTRUCTIONS",
            "GRANT ISSUED",
            "TOOL DEFINITION UPDATE",
        )

    def test_the_injected_page_was_really_acquired(self):
        self.assertEqual(self.artifact.outcome, "ok")
        self.assertEqual(len(self.artifact.records), 3)
        self.assertEqual(len(self.opener.opened), 1)

    def test_the_run_changed_no_plan_no_grant_and_no_write_set(self):
        assert_acquired_text_changed_nothing(
            self, self.manifest, self.artifact, self.carrier.calls, self.grants_before
        )

    def test_the_hostile_text_is_kept_verbatim_and_only_as_text(self):
        assert_hostile_text_is_carried_as_content(self, self.artifact, self.markers)

    def test_the_address_a_snippet_demanded_was_recorded_and_never_read(self):
        # The sharpest form of the claim. One hit really does point at
        # `evil.example`, so the run holds its address — and holding an address
        # is not reading it. Hydration reads what the caller froze, never what
        # a page suggested.
        locators = [record.canonical_locator for record in self.artifact.records]

        self.assertIn("https://evil.example/collect", locators)
        self.assertEqual(
            [call.url for call in self.carrier.calls if "evil.example" in call.url], []
        )

    def test_the_grants_are_the_same_object_they_were_before_the_run(self):
        self.assertEqual(route_grants(), self.grants_before)


class UntrustedContentOracleCanFailTest(unittest.TestCase):
    """Criterion 4: the T09 oracle rejects a caller that does what it is told.

    Both consumers are written beside the tree and loaded by path. Nothing in
    the package produces them and nothing under test is mutated to obtain them.
    """

    def setUp(self):
        self.consumers = load_threat_fixture("acting_consumer")

    def test_a_consumer_that_obeys_the_snippet_fails_the_oracle(self):
        grants_before = route_grants()
        manifest, artifact, carrier, _ = injected_run()

        obeyed = self.consumers.acts_on_instructions(artifact, carrier)

        self.assertEqual(obeyed, 2)
        with self.assertRaises(AssertionError) as caught:
            assert_acquired_text_changed_nothing(
                self, manifest, artifact, carrier.calls, grants_before
            )

        self.assertIn("acquired text", str(caught.exception))

    def test_the_obeying_consumer_really_put_a_write_verb_on_the_wire(self):
        # The rejection is not a technicality about a declaration: the call it
        # makes is recorded on the carrier with POST on it and an address no
        # route in this package declares, and transport would refuse it before
        # any socket — which is the second line of defence, not the first.
        _, artifact, carrier, _ = injected_run()

        self.consumers.acts_on_instructions(artifact, carrier)
        obeying = [call for call in carrier.calls if "evil.example" in call.url]

        self.assertEqual([call.method for call in obeying], ["POST", "POST"])
        with forbid_io():
            with self.assertRaises(transport.TransportError):
                transport.urlopen_read(obeying[0])

    def test_a_run_that_acquired_nothing_is_refused_rather_than_passed(self):
        # The vacuity direction: "no text changed anything" is satisfied
        # perfectly by a run with no text in it.
        manifest = injected_manifest()
        empty = schema.AcquisitionArtifact(
            artifact_id="artifact:m-injected",
            manifest_id="m-injected",
            as_of=FROZEN_OBSERVED_AT,
            records=(),
            steps=(),
        )

        with self.assertRaisesRegex(AssertionError, "no acquired text reached the artifact"):
            assert_acquired_text_changed_nothing(self, manifest, empty, (), route_grants())

    def test_an_oracle_that_looked_for_no_hostile_text_is_refused(self):
        _, artifact, _, _ = injected_run()

        with self.assertRaisesRegex(AssertionError, "no hostile text was looked for"):
            assert_hostile_text_is_carried_as_content(self, artifact, ())

    def test_a_marker_that_never_arrived_is_refused(self):
        # The other way the content half goes wrong: an adapter that quietly
        # dropped the hostile snippet would satisfy every clause about fields
        # that decide things, and would have hidden the payload from the caller.
        _, artifact, _, _ = injected_run()

        with self.assertRaisesRegex(AssertionError, "never reached a record"):
            assert_hostile_text_is_carried_as_content(
                self, artifact, ("A SENTENCE NO SNIPPET CARRIES",)
            )

    def test_the_same_oracle_accepts_the_consumer_that_reads_and_obeys_nothing(self):
        grants_before = route_grants()
        manifest, artifact, carrier, _ = injected_run()

        counted = self.consumers.correct(artifact, carrier)

        self.assertEqual(counted, 3)
        assert_acquired_text_changed_nothing(
            self, manifest, artifact, carrier.calls, grants_before
        )

    def test_nothing_in_the_package_can_reach_the_obeying_consumer(self):
        named = sorted(
            path.name
            for path in PACKAGE_DIR.rglob("*.py")
            for wrong in ("acts_on_instructions", "acting_consumer", "evil.example")
            if wrong in path.read_text(encoding="utf-8")
        )

        self.assertEqual(named, [])


class RefusalThreatTest(unittest.TestCase):
    """T11, T12, T13, T15 and T16 at the seam that decides them."""

    def test_t11_a_refusal_is_typed_on_one_call_and_changes_no_identity(self):
        page, opener = adapter_page(rss_atom, 429, read_fixture("origin_page.html"))

        self.assertEqual(page.loss, (transport.RATE_LIMITED,))
        self.assertEqual(page.outcome, "failed")
        self.assertEqual(len(opener.opened), 1)
        # No rotation: one static agent, on this call and on every other.
        self.assertEqual(
            [dict(call.headers)["User-Agent"] for call in opener.opened],
            [transport.USER_AGENT],
        )

    def test_t11_every_route_is_read_under_the_one_static_identity(self):
        for route_id in sorted(transport.ROUTE_CONSTANTS):
            with self.subTest(route=route_id):
                request = transport.build_transport_request(route_id, helpers.probe_params(route_id))

                self.assertEqual(dict(request.headers)["User-Agent"], transport.USER_AGENT)

    def test_t12_and_t15_an_unreachable_route_is_refused_before_any_call(self):
        carrier, opener = offline_transport(
            {route_id: (200, "{}", "application/json") for route_id in transport.ROUTE_CONSTANTS}
        )
        manifest = schema.AcquisitionManifest(
            manifest_id="m-unreachable",
            as_of=FROZEN_OBSERVED_AT,
            steps=(
                schema.AcquisitionStep(
                    step_id="s1-unknown",
                    kind="discovery",
                    adapter_id="no_such_adapter",
                    query="probe",
                    max_items=5,
                ),
            ),
        )

        artifact = runner.run_acquisition(manifest, carrier)

        self.assertEqual(artifact.steps[0].outcome, "refused")
        self.assertEqual(artifact.steps[0].loss, ("no_route",))
        self.assertEqual(opener.opened, [])



    def test_t16_a_failed_read_is_a_typed_failure_and_never_a_second_read(self):
        carrier, opener = offline_transport(
            {
                route_id: (500, read_fixture("origin_service_unavailable.html"), "text/html")
                for route_id in transport.ROUTE_CONSTANTS
            }
        )

        artifact = runner.run_acquisition(injected_manifest(), carrier)

        self.assertEqual(artifact.outcome, "failed")
        self.assertEqual(artifact.loss, ("http_status",))
        self.assertEqual([call.route_id for call in carrier.calls], [transport.WEB_PAGE_OPEN_ROUTE])
        self.assertEqual(len(opener.opened), 1)


if __name__ == "__main__":  # pragma: no cover - convenience runner
    unittest.main()
