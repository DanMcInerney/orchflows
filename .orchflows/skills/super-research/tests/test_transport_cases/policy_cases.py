"""Transport threat and policy cases."""

from .common import *
from .policy_support import *
from .request_cases import *
from .network_seam import adapter_page

class ThreatRemapTest(unittest.TestCase):
    """Criterion 11: the retained oracles, and which class each one is about."""

    def test_the_remap_names_every_retained_threat_exactly_once(self):
        self.assertEqual(
            sorted(THREAT_REMAP), ["T{0:02d}".format(number) for number in range(1, 17)]
        )

    def test_every_class_named_is_one_the_ladder_declares(self):
        for threat, (classes, form) in sorted(THREAT_REMAP.items()):
            with self.subTest(threat=threat):
                self.assertTrue(form)
                for access_class in classes:
                    self.assertIn(access_class, schema.ACCESS_CLASSES)

    def test_every_class_the_roster_answers_at_is_covered_by_the_remap(self):
        # A remap that quietly left a class out would be a threat model with a
        # hole in it, so the classes the routes actually use are read off the
        # route table and each has to appear.
        covered = {
            access_class for classes, _ in THREAT_REMAP.values() for access_class in classes
        }
        answered = {
            route.access_class
            for route in transport.ROUTE_CONSTANTS.values()
            if route.access_class != "offline"
        }

        self.assertTrue(answered)
        self.assertEqual(sorted(answered - covered), [])

    def test_the_three_threats_about_absent_machinery_are_declared_absent(self):
        # T05 and T06's argv half were about a CLI, T07 about an exported
        # browser session, T08 about a driver that clicks. The new ladder has
        # none of the three, and saying so is the remap rather than a gap in it.
        for threat in ("T05", "T07", "T08"):
            with self.subTest(threat=threat):
                self.assertEqual(THREAT_REMAP[threat][0], NO_CLASS)

    def test_no_first_release_route_answers_at_the_credentialed_class(self):
        self.assertEqual(routes_at((CREDENTIALED_CLASS,)), ())
        self.assertTrue(routes_at(("K1",)))

class NoWriteIsReachableTest(unittest.TestCase):
    """T04 and T06, and the four conditions the T07 widening was granted under.

    The gate admitted a second non-read route because InnerTube publishes no
    GET form. What keeps that a read is not the verb but the enumeration, and
    each condition is re-proved here at the assembled revision rather than
    taken from the ticket that asked for it.
    """

    def test_condition_a_each_non_read_set_is_exactly_what_it_declares(self):
        # Each set on its own, not only their union: a union assertion is
        # satisfied by the two routes swapping sets, and the sets do not mean
        # the same thing — one mints a token, the other asks a question.
        self.assertEqual(
            transport.TOKEN_ACTIVATION_ROUTES, (transport.X_GUEST_ACTIVATE_ROUTE,)
        )
        self.assertEqual(transport.QUERY_BODY_ROUTES, (transport.YOUTUBE_INNERTUBE_ROUTE,))
        self.assertEqual(transport.TOKEN_ACTIVATION_METHODS, ("POST",))
        self.assertEqual(transport.QUERY_BODY_METHODS, ("POST",))

    def test_condition_b_post_is_reachable_for_those_two_routes_and_no_other(self):
        reached = sorted(
            route_id
            for route_id in transport.ROUTE_CONSTANTS
            if "POST" in transport.admitted_methods(route_id)
        )

        self.assertEqual(
            reached,
            sorted((transport.X_GUEST_ACTIVATE_ROUTE, transport.YOUTUBE_INNERTUBE_ROUTE)),
        )

    def test_condition_c_a_body_is_the_routes_shape_and_the_callers_values(self):
        # The point a query-body route would become the generic HTTP primitive
        # the non-goals forbid: a caller that can choose the body's shape can
        # send anything. It can choose values into a shape this module owns and
        # nothing else — a name the route never declared stays a query
        # parameter, in the open, on a url the run records.
        route = transport.route_constant(transport.YOUTUBE_INNERTUBE_ROUTE)
        declared = {name for name, _ in route.body_params}
        request = transport.build_transport_request(
            transport.YOUTUBE_INNERTUBE_ROUTE,
            {
                "endpoint": "search",
                "query": "probe",
                "client_name": "WEB",
                "smuggled": '{"mutate": true}',
            },
        )

        self.assertNotIn("smuggled", request.body)
        self.assertNotIn("mutate", request.body)
        self.assertIn("smuggled", request.url)
        self.assertEqual(json.loads(request.body), {
            "context": {"client": {"clientName": "WEB"}},
            "query": "probe",
        })
        self.assertTrue(declared)

    def test_condition_c_a_route_declaring_no_body_params_never_carries_one(self):
        for route_id in sorted(transport.ROUTE_CONSTANTS):
            if transport.route_constant(route_id).body_params:
                continue
            with self.subTest(route=route_id):
                request = transport.build_transport_request(
                    route_id,
                    dict(
                        helpers.probe_params(route_id),
                        **{"body": "anything", "data": "anything"}
                    ),
                )

                self.assertEqual(request.body, "")

    def test_condition_d_put_patch_and_delete_are_admitted_by_no_route(self):
        for route_id in sorted(transport.ROUTE_CONSTANTS):
            admitted = transport.admitted_methods(route_id)
            for method in ("PUT", "PATCH", "DELETE"):
                with self.subTest(route=route_id, method=method):
                    self.assertNotIn(method, admitted)

    def test_t04_zero_writes_are_reachable_from_any_class_on_the_ladder(self):
        # Criterion 11's headline, quantified over the ladder rather than over
        # the route table, so a class with no route today still states the law
        # it would answer under.
        for access_class in EVERY_CLASS:
            for route_id in routes_at((access_class,)):
                with self.subTest(access_class=access_class, route=route_id):
                    admitted = transport.admitted_methods(route_id)

                    self.assertEqual(
                        [method for method in admitted if method not in transport.READ_METHODS],
                        ["POST"] if route_id in (
                            transport.TOKEN_ACTIVATION_ROUTES + transport.QUERY_BODY_ROUTES
                        ) else [],
                    )

    def test_t06_a_caller_cannot_escape_a_routes_admitted_method_set(self):
        for route_id in sorted(transport.ROUTE_CONSTANTS):
            for method in ("PUT", "PATCH", "DELETE", "CONNECT", "TRACE"):
                with self.subTest(route=route_id, method=method):
                    request = transport.TransportRequest(
                        route_id=route_id, method=method, url="https://example.test/probe"
                    )

                    with forbid_io():
                        with self.assertRaises(transport.TransportError):
                            transport.urlopen_response(request)


class AbsentMachineryTest(unittest.TestCase):
    """T07 at this seam: the only state a run holds is a token in memory."""

    def test_t07_a_minted_token_lives_in_the_store_and_nowhere_else(self):
        store = transport.GuestTokenStore()
        self.assertEqual(store._tokens, {})

        store._tokens["probe_route"] = "a-token-this-run-minted"
        self.assertEqual(store.token_for("probe_route"), "a-token-this-run-minted")
        store.clear()

        self.assertEqual(store._tokens, {})
        self.assertEqual(
            transport.tokened_headers((("Accept", "text/html"),), ""),
            (("Accept", "text/html"),),
        )

    def test_t07_no_route_constant_or_response_field_can_hold_a_session(self):
        # There is no cookie, no netrc, no profile and no export: the only
        # field that could carry one is a header this module attaches at send
        # time, and a caller's request has never had it.
        request = transport.build_transport_request(transport.X_GUEST_GRAPHQL_ROUTE, {
            "query_id": "abc", "operation_name": "TweetResultByRestId"
        })

        self.assertNotIn(transport.GUEST_TOKEN_HEADER, dict(request.headers))

    def test_t14_the_only_store_there_is_clears_and_nothing_persists(self):
        # "The package has no delete primitive" — there is nothing to delete,
        # because the one thing it holds is a dict that goes away with the
        # process. Physical deletion stays the caller's run store's.
        self.assertIsInstance(transport.GUEST_TOKENS, transport.GuestTokenStore)
        transport.GUEST_TOKENS.clear()

        self.assertEqual(transport.GUEST_TOKENS._tokens, {})

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
                transport.urlopen_response(obeying[0])

    def test_a_run_that_acquired_nothing_is_refused_rather_than_passed(self):
        # The vacuity direction: "no text changed anything" is satisfied
        # perfectly by a run with no text in it.
        manifest = injected_manifest()
        empty = schema.AcquisitionArtifact(
            artifact_id="artifact:m-injected",
            manifest_id="m-injected",
            mode="staged",
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
        page, opener = adapter_page(web_search, 429, read_fixture("origin_page.html"))

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
            mode="staged",
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

    def test_t13_the_index_surface_declares_itself_and_is_the_only_one(self):
        indexes = sorted(
            surface.adapter_id
            for adapter_id in runner.ADAPTER_IDS
            for surface in runner.surface_descriptors(adapter_id)
            if surface.representation_kind == "index"
        )

        # One adapter, four index surfaces since 2026-08-17: DuckDuckGo answers
        # 202 to every identity, so Bing's two RSS forms and Google News's join
        # it as parallel planned routes rather than as fallbacks. They are one
        # adapter because an index hit is one kind of record whoever indexed it.
        self.assertEqual(sorted(set(indexes)), ["web_search"])
        self.assertEqual(len(indexes), 4)
        for surface in runner.surface_descriptors("web_search"):
            with self.subTest(route=surface.route_id):
                self.assertEqual(surface.access_class, "K4")

    def test_t13_every_row_a_k4_read_produces_is_marked_an_index(self):
        _, artifact, _, _ = injected_run()

        self.assertEqual(
            sorted({record.representation_kind for record in artifact.records}), ["index"]
        )

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
        self.assertEqual([call.route_id for call in carrier.calls], [transport.DDG_HTML_ROUTE])
        self.assertEqual(len(opener.opened), 1)

class ThreatTableIsReadOffTheDocumentTest(unittest.TestCase):
    """`internals.md`'s sixteen threat rows, checked against `THREAT_REMAP`.

    `THREAT_REMAP` is guarded three ways above. The copy of it a reader
    actually meets was guarded not at all, and it restates **two** hand-kept
    judgments per row: the classes a threat applies to, and the form it takes
    here. `protocol.md` tells that reader this table gets the treatment the
    loss tables get, so it gets it — both columns of all sixteen rows are
    parsed out of the document and compared, and neither side can be corrected
    while the other is left.
    """

    def setUp(self):
        self.rows = threat_table_rows()

    def test_the_table_was_found_and_every_row_is_three_cells(self):
        # A parse that silently found nothing passes every assertion below
        # while checking no table at all.
        self.assertEqual(len(self.rows), 16)
        self.assertEqual(len(self.rows), len(THREAT_REMAP))
        for row in self.rows:
            self.assertEqual(len(row), 3, "a threat row is {0} cells".format(len(row)))

    def test_the_table_names_every_remapped_threat_exactly_once(self):
        self.assertEqual([row[0] for row in self.rows], sorted(THREAT_REMAP))

    def test_each_row_applies_to_exactly_the_classes_the_remap_gives_it(self):
        for threat, applies, _ in self.rows:
            with self.subTest(threat=threat):
                self.assertEqual(
                    documented_classes(applies),
                    THREAT_REMAP[threat][0],
                    "internals.md says {0} applies to {1}; THREAT_REMAP says {2}".format(
                        threat, applies, THREAT_REMAP[threat][0]
                    ),
                )

    def test_each_row_states_exactly_the_form_the_remap_gives_it(self):
        for threat, _, form in self.rows:
            with self.subTest(threat=threat):
                self.assertEqual(
                    comparable(form),
                    comparable(THREAT_REMAP[threat][1]),
                    "internals.md states {0} as {1!r}; THREAT_REMAP states it as {2!r}".format(
                        threat, comparable(form), comparable(THREAT_REMAP[threat][1])
                    ),
                )

    def test_the_parse_can_tell_two_cells_apart(self):
        # The oracle can fail. A class reader that collapsed the range, or a
        # form comparison that normalized the words away, would pass over any
        # table at all — so both are shown distinguishing, on hand-built cells.
        self.assertEqual(documented_classes("`K0`–`K5`"), EVERY_CLASS)
        self.assertEqual(documented_classes("`K1`, `K5`"), CREDENTIAL_CLASSES)
        self.assertEqual(documented_classes("`K4`"), ("K4",))
        self.assertEqual(documented_classes("no class"), NO_CLASS)
        self.assertNotEqual(documented_classes("`K1`, `K5`"), EVERY_CLASS)
        self.assertEqual(comparable("a `K1`\n  credential"), "a K1 credential")
        self.assertNotEqual(comparable("no fallback"), comparable("no fallbacks"))


if __name__ == "__main__":  # pragma: no cover - convenience runner
    unittest.main()
