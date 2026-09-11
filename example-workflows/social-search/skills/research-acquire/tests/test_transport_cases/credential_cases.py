"""Transport credential cases."""

from .common import *
from .policy_support import *
from .request_cases import outbound_blob

class PublicClientCredentialTest(unittest.TestCase):
    """Completion criterion 3: the K1 credentials are route constants owned here."""

    def _credential(self, credential_id):
        return transport.PUBLIC_CLIENT_CREDENTIALS[credential_id]

    def test_the_three_k1_credentials_are_owned_by_this_module(self):
        self.assertEqual(
            sorted(transport.PUBLIC_CLIENT_CREDENTIALS),
            [
                transport.INSTAGRAM_WEB_APP_ID,
                transport.X_GUEST_PUBLIC_BEARER,
                transport.YOUTUBE_INNERTUBE_WEB_KEY,
            ],
        )

    def test_the_instagram_app_id_is_the_value_the_evidence_records(self):
        credential = self._credential(transport.INSTAGRAM_WEB_APP_ID)

        # The 2026-08-10 probes record this one in full.
        self.assertEqual(credential.name, "x-ig-app-id")
        self.assertEqual(credential.value, "936619743392459")
        self.assertEqual(credential.placement, "header")

    def test_the_innertube_web_key_matches_the_shape_the_evidence_records(self):
        credential = self._credential(transport.YOUTUBE_INNERTUBE_WEB_KEY)

        # The 2026-08-10 probes record this one elided, as `AIzaSy...11qcW8`. The
        # middle is not in the evidence, so this pins exactly what is.
        self.assertTrue(credential.value.startswith("AIzaSy"), credential.value)
        self.assertTrue(credential.value.endswith("11qcW8"), credential.value)
        self.assertEqual(credential.name, "key")
        self.assertEqual(credential.placement, "query")

    def test_the_x_guest_bearer_is_an_authorization_header(self):
        credential = self._credential(transport.X_GUEST_PUBLIC_BEARER)

        self.assertEqual(credential.name, "Authorization")
        self.assertEqual(credential.placement, "header")
        self.assertTrue(credential.value.startswith("Bearer AAAAAAAAAAAAAAAAAAAAA"), credential.value)

    def test_every_credential_declares_a_vendor_a_placement_and_a_value(self):
        for credential_id, credential in transport.PUBLIC_CLIENT_CREDENTIALS.items():
            with self.subTest(credential=credential_id):
                self.assertEqual(credential.credential_id, credential_id)
                self.assertIn(credential.placement, transport.CREDENTIAL_PLACEMENTS)
                self.assertTrue(credential.vendor)
                self.assertTrue(credential.name)
                self.assertTrue(credential.value)

    def test_every_route_that_names_a_credential_resolves_to_one(self):
        for route_id, route in transport.ROUTE_CONSTANTS.items():
            with self.subTest(route=route_id):
                if route.credential_id:
                    self.assertIs(
                        transport.route_credential(route_id),
                        transport.PUBLIC_CLIENT_CREDENTIALS[route.credential_id],
                    )
                else:
                    self.assertIsNone(transport.route_credential(route_id))

    def test_a_keyless_route_carries_no_credential(self):
        self.assertIsNone(transport.route_credential(transport.DDG_HTML_ROUTE))
        self.assertIsNone(transport.route_credential(transport.ARCTIC_SHIFT_POSTS_ROUTE))


class CredentialApplicationTest(unittest.TestCase):
    """A credential is attached at send time, to the url or to the headers."""

    def setUp(self):
        self.query_credential = transport.PUBLIC_CLIENT_CREDENTIALS[
            transport.YOUTUBE_INNERTUBE_WEB_KEY
        ]
        self.header_credential = transport.PUBLIC_CLIENT_CREDENTIALS[
            transport.INSTAGRAM_WEB_APP_ID
        ]

    def test_a_query_placed_credential_is_appended_to_a_bare_url(self):
        url = transport.credentialed_url("https://example.test/v1/search", self.query_credential)

        self.assertEqual(
            url, "https://example.test/v1/search?key=" + self.query_credential.value
        )

    def test_a_query_placed_credential_joins_an_existing_query_string(self):
        url = transport.credentialed_url("https://example.test/v1?q=a", self.query_credential)

        self.assertEqual(url, "https://example.test/v1?q=a&key=" + self.query_credential.value)

    def test_a_header_placed_credential_never_touches_the_url(self):
        url = transport.credentialed_url("https://example.test/v1", self.header_credential)

        self.assertEqual(url, "https://example.test/v1")

    def test_a_header_placed_credential_is_appended_to_the_headers(self):
        headers = transport.credentialed_headers(
            (("Accept", "application/json"),), self.header_credential
        )

        self.assertEqual(
            headers,
            (("Accept", "application/json"), ("x-ig-app-id", self.header_credential.value)),
        )

    def test_a_query_placed_credential_never_touches_the_headers(self):
        headers = transport.credentialed_headers(
            (("Accept", "application/json"),), self.query_credential
        )

        self.assertEqual(headers, (("Accept", "application/json"),))

    def test_a_route_without_a_credential_changes_neither(self):
        self.assertEqual(transport.credentialed_url("https://example.test/v1", None), "https://example.test/v1")
        self.assertEqual(transport.credentialed_headers((("Accept", "text/html"),), None), (("Accept", "text/html"),))

    def test_applying_a_credential_opens_no_socket_and_reads_no_file(self):
        with forbid_io():
            url = transport.credentialed_url("https://example.test/v1", self.query_credential)
            headers = transport.credentialed_headers((), self.header_credential)

        self.assertIn(self.query_credential.value, url)
        self.assertEqual(headers[0][1], self.header_credential.value)


class CredentialStaysInsideTransportTest(unittest.TestCase):
    """Criterion 3, leak half: no K1 credential rides on a value the package keeps.

    Everything downstream of this module sees only ``TransportRequest`` and
    ``TransportResponse`` — the request log, the adapters, and therefore every
    record and artifact derive from those two. A credential absent from both
    cannot reach a manifest or an artifact.
    """

    def _credential_values(self):
        return [
            credential.value
            for credential in transport.PUBLIC_CLIENT_CREDENTIALS.values()
        ]

    def test_no_built_request_carries_a_credential_value(self):
        for route_id in sorted(transport.ROUTE_CONSTANTS):
            with self.subTest(route=route_id):
                request = transport.build_transport_request(route_id, helpers.probe_params(route_id))

                for value in self._credential_values():
                    self.assertNotIn(value, repr(request))

    def test_no_fetched_response_or_call_log_carries_a_credential_value(self):
        for route_id in sorted(transport.ROUTE_CONSTANTS):
            with self.subTest(route=route_id):
                carrier, _ = offline_transport({route_id: (200, read_fixture("origin_page.html"), "text/html")})

                response = carrier.fetch(transport.build_transport_request(route_id, helpers.probe_params(route_id)))

                for value in self._credential_values():
                    self.assertNotIn(value, repr(response))
                    self.assertNotIn(value, repr(carrier.calls))

class CredentialThreatTest(unittest.TestCase):
    """T01, T02, T03, T10 over `K1` and `K5`: the credential stays inside."""

    def test_t01_no_credentialed_route_puts_its_secret_in_anything_kept(self):
        for route_id in routes_at(CREDENTIAL_CLASSES):
            with self.subTest(route=route_id):
                carrier, _ = offline_transport(
                    {route_id: (200, read_fixture("origin_page.html"), "text/html")}
                )
                request = transport.build_transport_request(route_id, {"q": "probe"})
                response = carrier.fetch(request)

                for name, secret in credential_strings():
                    self.assertNotIn(secret, repr(request), name)
                    self.assertNotIn(secret, repr(response), name)
                    self.assertNotIn(secret, repr(carrier.calls), name)

    def test_t02_a_query_placed_key_goes_out_on_the_wire(self):
        # Which is what makes the next test mean anything: the credential is
        # really sent, and really appended to the address that is asked for.
        credential = transport.PUBLIC_CLIENT_CREDENTIALS[transport.YOUTUBE_INNERTUBE_WEB_KEY]
        _, outbound = sent_and_answered(
            transport.YOUTUBE_INNERTUBE_ROUTE, {"endpoint": "search", "query": "probe"}
        )

        self.assertIn(credential.value, outbound.full_url)

    def test_t02_the_address_the_origin_answered_from_comes_back_stripped(self):
        credential = transport.PUBLIC_CLIENT_CREDENTIALS[transport.YOUTUBE_INNERTUBE_WEB_KEY]
        # `prettyPrint` is an ordinary query parameter — the route declares it
        # neither as a path segment nor in `body_params` — so it is on the
        # address beside the key and has to still be there afterwards.
        answered, _ = sent_and_answered(
            transport.YOUTUBE_INNERTUBE_ROUTE,
            {"endpoint": "search", "query": "probe", "prettyPrint": "false"},
        )
        final_url = answered[3]

        # The one string in this package that can carry a query-placed key past
        # the transport seam: the origin answers from the address the key was
        # appended to, and `final_url` is a caller-visible field one adapter
        # publishes onto a record.
        self.assertNotIn(credential.value, final_url)
        self.assertNotIn(credential.name + "=", final_url)
        # Stripped, not blanked: the path, the endpoint segment and every other
        # parameter say exactly what they said on the way out.
        self.assertTrue(
            final_url.startswith(
                transport.route_constant(transport.YOUTUBE_INNERTUBE_ROUTE).origin
            )
        )
        self.assertIn("/youtubei/v1/search", final_url)
        self.assertIn("prettyPrint=false", final_url)

    def test_t02_no_routes_answering_address_carries_any_credential(self):
        # Every route on the ladder. The offline fixture route is left out
        # because it has no address to answer from: it never leaves the
        # process, which is why its class is `offline` and not one of these.
        for route_id in routes_at(EVERY_CLASS):
            with self.subTest(route=route_id):
                answered, _ = sent_and_answered(route_id, helpers.probe_params(route_id))
                response = transport.Transport(
                    opener=lambda request, held=answered: held, now=lambda: FROZEN_OBSERVED_AT
                ).fetch(transport.build_transport_request(route_id, helpers.probe_params(route_id)))

                for name, secret in credential_strings():
                    self.assertNotIn(secret, answered[3], name)
                    self.assertNotIn(secret, response.final_url, name)

    def test_t03_a_credential_reaches_its_own_routes_origin_and_no_other(self):
        for route_id in routes_at(CREDENTIAL_CLASSES):
            with self.subTest(route=route_id):
                route = transport.route_constant(route_id)
                _, outbound = sent_and_answered(route_id)

                self.assertTrue(outbound.full_url.startswith(route.origin))

    def test_t03_a_keyless_route_never_receives_another_routes_credential(self):
        keyless = sorted(set(routes_at(EVERY_CLASS)) - set(routes_at(CREDENTIAL_CLASSES)))
        for route_id in keyless:
            with self.subTest(route=route_id):
                _, outbound = sent_and_answered(route_id, {"q": "probe"})
                blob = outbound_blob(outbound)

                for name, secret in credential_strings():
                    self.assertNotIn(secret, blob, name)

    def test_t10_a_public_client_credential_names_a_vendor_and_no_user(self):
        # The remapped principal check. `A1`'s was about an account a wrong
        # credential could belong to; a `K1` credential is one the vendor ships
        # in its own web client, so what has to be declared is which vendor,
        # and which operator answered.
        for route_id in routes_at(("K1",)):
            with self.subTest(route=route_id):
                route = transport.route_constant(route_id)
                credential = transport.route_credential(route_id)

                self.assertTrue(route.operator_identity)
                if credential is not None:
                    self.assertTrue(credential.vendor)
                    self.assertIn(credential.placement, transport.CREDENTIAL_PLACEMENTS)
