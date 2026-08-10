"""Transport suite: a local network block is never a platform response.

Every test here runs offline. The distinction this module defends is
findings.md §0's: this host sits behind an appliance that answers some
domains with a failure status and a captive-portal body, and a route blocked
that way is UNVERIFIED, never rejected. Confusing that with a platform
response would record a local block as a platform gap.

It is defended twice, because classifying correctly and recording correctly
are different claims: at the transport seam, where the channel verdict is
made, and at the adapter and artifact seams, where it is what a caller keeps.
"""

from __future__ import annotations

import ast
import builtins
import contextlib
import importlib.util
import io
import json
import os
import socket
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

from super_research import adapters, runner, schema, transport
from super_research.adapters import fake, reddit_archive, web_search


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "transport"
PACKAGE_DIR = Path(__file__).resolve().parent.parent / "scripts" / "super_research"
ADAPTER_DIR = PACKAGE_DIR / "adapters"
FROZEN_OBSERVED_AT = "2026-08-10T09:00:00Z"

# Only the transport seam may reach the network.
NETWORK_MODULES = ("urllib.request", "http.client", "socket", "ssl")

# Only the shared adapter protocol makes the call and reads the channel.
PROTOCOL_OWNED_NAMES = ("carrier.fetch", "channel_verdict", "NETWORK_INTERCEPTED")

# Every adapter the package ships today. One request serves all three: each
# reads only the fields its own route needs.
SHIPPED_ADAPTERS = (web_search, reddit_archive, fake)
PROBE_REQUEST = adapters.AdapterRequest(
    step_id="s1-probe", query="probe", target_ids=("1abc234",)
)


def read_fixture(name):
    """Read one offline fixture."""

    return FIXTURE_DIR.joinpath(name).read_text(encoding="utf-8")


def interception_cases():
    """The measured case table: a status, a body, and the verdict its evidence names."""

    return tuple(json.loads(read_fixture("interception_cases.json"))["cases"])


def case_body(row):
    return read_fixture(row["body_fixture"])


def wrong_channel_verdicts():
    """Verdict maps a broken detector would produce, written out beside the tree."""

    return json.loads(read_fixture("wrong_channel_verdicts.json"))["cases"]


class RecordingOpener:
    """Offline opener: one canned response per route, every call recorded.

    Standing in for the network is the whole point — nothing here can reach a
    socket, so a test that asks for an unseeded route fails loudly instead of
    egressing.
    """

    def __init__(self, responses):
        self.responses = dict(responses)
        self.opened = []

    def __call__(self, request):
        self.opened.append(request)
        if request.route_id not in self.responses:
            raise transport.TransportError("no offline response seeded for " + request.route_id)
        outcome = self.responses[request.route_id]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def offline_transport(responses):
    opener = RecordingOpener(responses)
    return transport.Transport(opener=opener, now=lambda: FROZEN_OBSERVED_AT), opener


class RefusingSocket(socket.socket):
    """A socket that cannot be opened.

    It stays a *subclass* on purpose: ``ssl`` does ``class SSLSocket(socket)``
    at import time, so a guard that swaps ``socket.socket`` for a plain
    function breaks any stdlib module that has not been imported yet.
    """

    def __init__(self, *args, **kwargs):
        raise AssertionError("a socket was opened inside a zero-I/O guard")


@contextlib.contextmanager
def forbid_io():
    """Make every filesystem and socket primitive raise for the guarded block."""

    def refuse(*args, **kwargs):
        raise AssertionError("I/O attempted inside a zero-I/O guard")

    with contextlib.ExitStack() as stack:
        stack.enter_context(mock.patch.object(builtins, "open", refuse))
        stack.enter_context(mock.patch.object(io, "open", refuse))
        stack.enter_context(mock.patch.object(os, "open", refuse))
        stack.enter_context(mock.patch.object(socket, "socket", RefusingSocket))
        stack.enter_context(mock.patch.object(socket, "create_connection", refuse))
        stack.enter_context(mock.patch.object(urllib.request, "urlopen", refuse))
        yield


def detected_verdicts():
    """Type every measured case with the detector itself."""

    return {
        row["case_name"]: transport.channel_verdict(row["status"], case_body(row))
        for row in interception_cases()
    }


def fetched_verdicts():
    """Type every measured case through the fetch seam a caller actually uses."""

    verdicts = {}
    for row in interception_cases():
        carrier, _ = offline_transport(
            {transport.DDG_HTML_ROUTE: (row["status"], case_body(row), "text/html")}
        )
        response = carrier.fetch(
            transport.build_transport_request(transport.DDG_HTML_ROUTE, {"q": "probe"})
        )
        verdicts[row["case_name"]] = response.channel_verdict
    return verdicts


def assert_channel_verdicts(case, verdicts):
    """The interception oracle: every measured case typed as its evidence says.

    ``verdicts`` maps a case name to the verdict some classifier produced.
    Each assertion names the confusion it caught, so a failure says which half
    of findings.md §0 was broken.
    """

    for row in interception_cases():
        name = row["case_name"]
        expected = row["expected_verdict"]
        case.assertIn(name, verdicts, "case {0} was never classified".format(name))
        produced = verdicts[name]
        if expected == transport.NETWORK_INTERCEPTED and produced != expected:
            case.fail("a captive-portal response was recorded as a platform response: " + name)
        if expected != transport.NETWORK_INTERCEPTED and produced == transport.NETWORK_INTERCEPTED:
            case.fail("an origin response was recorded as a network interception: " + name)
        case.assertEqual(
            produced,
            expected,
            "case {0} was typed {1}, its evidence says {2}".format(name, produced, expected),
        )


class ChannelVerdictTest(unittest.TestCase):
    """Completion criteria 1 and 2: the detector types both halves of §0."""

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
    never as an http status — findings.md §0's rule is about what gets
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
    """The origin's own responses, pinned before the interception branch exists.

    These say what each shipped adapter already does with a response the
    origin itself sent. They are the counterweight to the interception path:
    a branch that widened to swallow ordinary failures, or that read the
    portal marker without the failure status, is caught here.
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

        # findings.md §1 records this one in full.
        self.assertEqual(credential.name, "x-ig-app-id")
        self.assertEqual(credential.value, "936619743392459")
        self.assertEqual(credential.placement, "header")

    def test_the_innertube_web_key_matches_the_shape_the_evidence_records(self):
        credential = self._credential(transport.YOUTUBE_INNERTUBE_WEB_KEY)

        # findings.md §1 records this one elided, as `AIzaSy...11qcW8`. The
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
                request = transport.build_transport_request(route_id, {"q": "probe"})

                for value in self._credential_values():
                    self.assertNotIn(value, repr(request))

    def test_no_fetched_response_or_call_log_carries_a_credential_value(self):
        for route_id in sorted(transport.ROUTE_CONSTANTS):
            with self.subTest(route=route_id):
                carrier, _ = offline_transport({route_id: (200, read_fixture("origin_page.html"), "text/html")})

                response = carrier.fetch(transport.build_transport_request(route_id))

                for value in self._credential_values():
                    self.assertNotIn(value, repr(response))
                    self.assertNotIn(value, repr(carrier.calls))


def package_sources():
    """Every package module except the transport seam itself."""

    return sorted(path for path in PACKAGE_DIR.rglob("*.py") if path.name != "transport.py")


def adapter_sources():
    """Every adapter module the package ships, the shared protocol excluded."""

    return sorted(path for path in ADAPTER_DIR.glob("*.py") if path.name != "__init__.py")


def owned_route_literals():
    """Every string only ``transport.py`` may name: a route's host, its endpoint, a credential."""

    literals = set()
    for route in transport.ROUTE_CONSTANTS.values():
        literals.add(route.origin)
        literals.add(route.origin + route.path)
    for credential in transport.PUBLIC_CLIENT_CREDENTIALS.values():
        literals.add(credential.value)
    return sorted(literals)


def sources_naming(literals, paths):
    """Every (file name, literal) pair where a source names something it must not."""

    found = []
    for path in paths:
        source = path.read_text(encoding="utf-8")
        for literal in literals:
            if literal in source:
                found.append((path.name, literal))
    return sorted(found)


def imported_names(path):
    """Every module and imported symbol path one source file names in an import."""

    names = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module:
                names.add(module)
            for alias in node.names:
                names.add(module + "." + alias.name if module else alias.name)
    return names


class RouteOwnershipScanTest(unittest.TestCase):
    """Criterion 3: one owner for the route table, booleans for the router.

    The scan covers the package's own modules. Tests are excluded on purpose:
    naming a route constant to assert it is exactly what a test is for.
    """

    def test_no_package_module_but_transport_names_a_route_host_or_a_credential(self):
        self.assertEqual(sources_naming(owned_route_literals(), package_sources()), [])

    def test_the_ownership_scan_can_fail(self):
        # A module that names a route origin and a credential, written beside
        # the tree so the scan is shown to discriminate rather than to match
        # nothing at all.
        rogue = FIXTURE_DIR / "rogue_module_source.txt"

        found = sources_naming(owned_route_literals(), [rogue])

        self.assertEqual(
            [literal for _, literal in found],
            [
                transport.PUBLIC_CLIENT_CREDENTIALS[transport.INSTAGRAM_WEB_APP_ID].value,
                transport.ROUTE_CONSTANTS[transport.DDG_HTML_ROUTE].origin,
                transport.ROUTE_CONSTANTS[transport.DDG_HTML_ROUTE].origin
                + transport.ROUTE_CONSTANTS[transport.DDG_HTML_ROUTE].path,
            ],
        )

    def test_no_package_module_but_transport_reaches_the_network(self):
        for path in package_sources():
            with self.subTest(module=path.name):
                named = imported_names(path)

                for module in NETWORK_MODULES:
                    self.assertNotIn(module, named)

    def test_the_router_never_sees_the_transport_module(self):
        named = imported_names(PACKAGE_DIR / "router.py")

        self.assertEqual([name for name in sorted(named) if "transport" in name], [])


class FakeHTTPResponse:
    """The little of an http response that ``urlopen_response`` reads."""

    def __init__(self, status, body, content_type):
        self.status = status
        self.headers = {"Content-Type": content_type}
        self._body = body.encode("utf-8")

    def read(self, limit):
        return self._body[:limit]

    def __enter__(self):
        return self

    def __exit__(self, *exception):
        return False


class RecordingUrlopen:
    """Stand in for ``urllib.request.urlopen`` and keep what would go on the wire."""

    def __init__(self, status=200, body="{}", content_type="application/json"):
        self.status = status
        self.body = body
        self.content_type = content_type
        self.requests = []

    def __call__(self, outbound, timeout=None):
        self.requests.append(outbound)
        return FakeHTTPResponse(self.status, self.body, self.content_type)


def outbound_blob(outbound):
    """Everything a urllib request would put on the wire, as one string."""

    return " ".join(
        [outbound.full_url, repr(sorted(outbound.header_items())), repr(outbound.data)]
    )


class GuestActivationRouteTest(unittest.TestCase):
    """The one non-read operation: minting an anonymous guest token."""

    def test_the_activation_route_carries_the_shape_the_evidence_measured(self):
        route = transport.route_constant(transport.X_GUEST_ACTIVATE_ROUTE)

        # findings.md §1 (X): POST api.twitter.com/1.1/guest/activate.json
        # returned 200 with a guest token, keylessly.
        self.assertEqual(route.access_class, "K1")
        self.assertEqual(route.method, "POST")
        self.assertEqual(route.origin, "https://api.twitter.com")
        self.assertEqual(route.path, "/1.1/guest/activate.json")
        self.assertEqual(route.credential_id, transport.X_GUEST_PUBLIC_BEARER)

    def test_the_activation_route_needs_no_user_credential(self):
        self.assertTrue(transport.route_admissions()[transport.X_GUEST_ACTIVATE_ROUTE])

    def test_it_is_the_only_route_declaring_a_method_that_is_not_a_read(self):
        non_read = sorted(
            route_id
            for route_id, route in transport.ROUTE_CONSTANTS.items()
            if route.method not in transport.READ_METHODS
        )

        self.assertEqual(non_read, [transport.X_GUEST_ACTIVATE_ROUTE])

    def test_only_the_activation_route_may_use_a_method_that_is_not_a_read(self):
        for route_id in sorted(transport.ROUTE_CONSTANTS):
            with self.subTest(route=route_id):
                admitted = transport.admitted_methods(route_id)

                if route_id == transport.X_GUEST_ACTIVATE_ROUTE:
                    self.assertEqual(admitted, transport.READ_METHODS + ("POST",))
                else:
                    self.assertEqual(admitted, transport.READ_METHODS)


class WriteVerbRefusalTest(unittest.TestCase):
    """Read-only bar: no code path here can mutate a remote resource."""

    def _refusal_for(self, route_id, method):
        request = transport.TransportRequest(
            route_id=route_id, method=method, url="https://example.test/probe"
        )

        with forbid_io():
            with self.assertRaises(transport.TransportError) as caught:
                transport.urlopen_response(request)

        return str(caught.exception)

    def test_every_write_verb_is_refused_on_every_route(self):
        for method in ("PUT", "DELETE", "PATCH", "OPTIONS"):
            for route_id in sorted(transport.ROUTE_CONSTANTS):
                with self.subTest(method=method, route=route_id):
                    self.assertIn(
                        "refusing a write-capable method", self._refusal_for(route_id, method)
                    )

    def test_post_is_refused_on_every_route_but_the_activation_route(self):
        for route_id in sorted(transport.ROUTE_CONSTANTS):
            if route_id == transport.X_GUEST_ACTIVATE_ROUTE:
                continue
            with self.subTest(route=route_id):
                self.assertIn(
                    "refusing a write-capable method", self._refusal_for(route_id, "POST")
                )

    def test_a_non_https_url_is_still_refused_before_any_socket(self):
        request = transport.TransportRequest(
            route_id=transport.X_GUEST_ACTIVATE_ROUTE,
            method="POST",
            url="http://api.twitter.com/1.1/guest/activate.json",
        )

        with forbid_io():
            with self.assertRaises(transport.TransportError) as caught:
                transport.urlopen_response(request)

        self.assertIn("non-https", str(caught.exception))


class OutboundRequestTest(unittest.TestCase):
    """What the default opener would put on the wire, captured without a socket."""

    def _sent(self, request, recorder):
        with mock.patch.object(urllib.request, "urlopen", recorder):
            result = transport.urlopen_response(request)
        return result, recorder.requests[0]

    def test_the_activation_post_carries_the_public_bearer_and_no_body(self):
        recorder = RecordingUrlopen(200, '{"guest_token": "1234567890"}', "application/json")
        request = transport.build_transport_request(transport.X_GUEST_ACTIVATE_ROUTE)

        (status, body, content_type), outbound = self._sent(request, recorder)

        bearer = transport.PUBLIC_CLIENT_CREDENTIALS[transport.X_GUEST_PUBLIC_BEARER].value
        self.assertEqual(outbound.get_method(), "POST")
        self.assertIsNone(outbound.data)
        self.assertIn(bearer, outbound_blob(outbound))
        self.assertEqual(status, 200)
        self.assertIn("guest_token", body)
        self.assertEqual(content_type, "application/json")

    def test_a_keyless_route_sends_no_credential_at_all(self):
        recorder = RecordingUrlopen(200, "<html></html>", "text/html")
        request = transport.build_transport_request(transport.DDG_HTML_ROUTE, {"q": "probe"})

        _, outbound = self._sent(request, recorder)

        blob = outbound_blob(outbound)
        for credential in transport.PUBLIC_CLIENT_CREDENTIALS.values():
            self.assertNotIn(credential.value, blob)
        self.assertEqual(outbound.get_method(), "GET")
        self.assertIn(transport.USER_AGENT, blob)


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


if __name__ == "__main__":  # pragma: no cover - convenience runner
    unittest.main()
