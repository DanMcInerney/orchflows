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
import dataclasses
import email
import importlib.util
import inspect
import io
import json
import os
import socket
import tokenize
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

from super_research import adapters, cache, pacing, runner, schema, transport
from super_research.adapters import fake, reddit_archive, web_search, x_guest
from tests import helpers


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "transport"
ITEM_DIR = Path(__file__).resolve().parent.parent
PACKAGE_DIR = ITEM_DIR / "scripts" / "super_research"
ADAPTER_DIR = PACKAGE_DIR / "adapters"
EVIDENCE_DOC = ITEM_DIR / "references" / "evidence.md"
FROZEN_OBSERVED_AT = "2026-08-10T09:00:00Z"

# Only the transport seam may reach the network.
NETWORK_MODULES = ("urllib.request", "http.client", "socket", "ssl")

# Which modules may spell a route's host, its endpoint, or a credential value.
# Declared, rather than matched by filename: the route table can be split across
# a second module without any scan having to learn its name, so admitting one is
# a one-line reviewable edit here and impossible anywhere else. One name, and
# `transport` is deliberately not it: the seam re-exports these constants and
# spells none of them, so it stays under the scan below. Admitting it would let
# a reachable host or a credential be defined at the seam with nothing to catch
# it, which is the whole of what the allowlist is for.
ROUTE_OWNING_MODULES = ("routes",)

# Which modules hold the outbound read on everybody's behalf. A second
# declaration and deliberately not the same list: owning a route's address is
# not permission to open a socket, so widening the set above must never widen
# what the network scan tolerates.
NETWORK_SEAM_MODULES = ("transport",)

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


def package_sources_but(declared):
    """Every package module a declaration does not name.

    The declaration names core modules by stem, so it excludes the one file the
    package root holds under that name and never an adapter that happens to
    share it.
    """

    excluded = {PACKAGE_DIR / (name + ".py") for name in declared}
    return sorted(path for path in PACKAGE_DIR.rglob("*.py") if path not in excluded)


def package_sources():
    """Every package module but the ones declared to own a route."""

    return package_sources_but(ROUTE_OWNING_MODULES)


def adapter_sources():
    """Every adapter module the package ships, the shared protocol excluded."""

    return sorted(path for path in ADAPTER_DIR.glob("*.py") if path.name != "__init__.py")


def owned_route_literals():
    """Every string only a declared route owner may name: a host, an endpoint, a credential."""

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


# The nouns that make a sentence a claim about route data, and how wide a
# claim reaches around the module it names.
ROUTE_DATA_NOUNS = ("route", "host", "endpoint", "credential", "address")
CLAIM_WINDOW = 80


def prose_blocks(path):
    """Everything one tracked file says in prose, each block flowed to one line.

    A markdown file is prose throughout. A python file is prose in its comment
    runs and its docstrings, and consecutive comment lines are one run: a claim
    wraps across lines, so a scan reading each line alone would miss every claim
    long enough to be worth making.
    """

    if path.suffix == ".md":
        return [" ".join(path.read_text(encoding="utf-8").split())]

    source = path.read_text(encoding="utf-8")
    blocks = []
    run = []
    previous = None
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type != tokenize.COMMENT:
            continue
        if previous is not None and token.start[0] != previous + 1:
            blocks.append(" ".join(run))
            run = []
        run.append(token.string.lstrip("#").strip())
        previous = token.start[0]
    if run:
        blocks.append(" ".join(run))

    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            text = ast.get_docstring(node)
            if text:
                blocks.append(" ".join(text.split()))
    return blocks


def module_spellings():
    """Every way this item's prose names one of the package's core modules.

    Core modules by stem, the same unit the declarations above are written in:
    the route table is a core module and a claim about where it lives names one.
    Adapters are out on purpose — an adapter's name is possessive all over the
    roster, and none of those sentences is about a route's address.
    """

    spellings = {}
    for path in sorted(PACKAGE_DIR.glob("*.py")):
        if path.stem == "__init__":
            continue
        for form in (
            "``super_research." + path.stem + "``",
            "`super_research." + path.stem + "`",
            "``" + path.stem + ".py``",
            "`" + path.stem + ".py`",
            ":mod:`." + path.stem + "`",
            "``" + path.stem + "``",
            "`" + path.stem + "`",
        ):
            spellings[form] = path.stem
    return spellings


def route_ownership_claims(paths):
    """Every (file, module) where prose gives route data to a named module.

    A claim is recognised by shape and never by a remembered sentence: the
    module's name carries a possessive, or is owning something, or is what
    something belongs to — with a route, a host, an endpoint, a credential or an
    address inside the same window. The alternative, a list of the exact
    sentences that were wrong once, would pass the next one written.
    """

    found = []
    spellings = module_spellings()
    for path in paths:
        for block in prose_blocks(path):
            for form, stem in spellings.items():
                start = block.find(form)
                while start != -1:
                    end = start + len(form)
                    before, after = block[:start], block[end:]
                    claiming = (
                        after.startswith("'s")
                        or after.lstrip().split(" ")[0].strip(".,;:") in ("owns", "own", "owned")
                        or "owner of" in after[:40]
                        or before.rstrip().endswith(("belongs to", "belong to"))
                    )
                    window = block[max(0, start - CLAIM_WINDOW): end + CLAIM_WINDOW]
                    if claiming and any(noun in window for noun in ROUTE_DATA_NOUNS):
                        found.append((path.name, stem))
                    start = block.find(form, end)
    return sorted(set(found))


def prose_bearing_files():
    """Every tracked file in this item that makes a claim in prose."""

    return (
        sorted(PACKAGE_DIR.rglob("*.py"))
        + sorted((ITEM_DIR / "references").glob("*.md"))
        + [ITEM_DIR / "SKILL.md"]
    )


class RouteOwnershipScanTest(unittest.TestCase):
    """Criterion 3: one owner for the route table, booleans for the router.

    The scan covers the package's own modules. Tests are excluded on purpose:
    naming a route constant to assert it is exactly what a test is for.
    """

    def test_no_module_outside_the_declared_owners_names_a_route_host_or_a_credential(self):
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

    def test_no_credential_value_reaches_the_tracked_evidence_document(self):
        # `references/evidence.md` distils records of live reads, and a
        # transcript is exactly where a credential value would be copied from.
        # The scan above, the same literals, one surface that is prose.
        credentials = sorted(
            credential.value for credential in transport.PUBLIC_CLIENT_CREDENTIALS.values()
        )

        self.assertEqual(sources_naming(credentials, [EVIDENCE_DOC]), [])

    def test_no_module_outside_the_declared_seam_reaches_the_network(self):
        # Quantified over the seam declaration and not the route one, because
        # the two answer different questions: a module admitted to the route
        # table is admitted to spell an address, never to open a socket.
        for path in package_sources_but(NETWORK_SEAM_MODULES):
            with self.subTest(module=path.name):
                named = imported_names(path)

                for module in NETWORK_MODULES:
                    self.assertNotIn(module, named)

    def test_the_router_never_sees_a_module_that_holds_an_address(self):
        # `router.py`'s own docstring states the law: it never sees a host, a
        # path, or a credential. While one module held every address, naming
        # that module here was the whole law. Now that the addresses are
        # declared, this reads the declaration — because `from . import routes`
        # would hand the router every origin in the allowlist without spelling
        # one literal for the scan above to catch.
        holding = sorted(set(ROUTE_OWNING_MODULES) | set(NETWORK_SEAM_MODULES))
        named = imported_names(PACKAGE_DIR / "router.py")

        self.assertEqual(
            [name for name in sorted(named) if any(held in name for held in holding)], []
        )


class RouteOwnershipIsStatedTrulyTest(unittest.TestCase):
    """Criterion 12: what the item says about who owns route data is true.

    The scan above reads literals; this one reads sentences, and the two answer
    different questions. Splitting the table left `transport` the seam and made
    every comment calling it the owner of a host false — a source can pass every
    literal scan in this file while telling the next maintainer to put the next
    host in the wrong module. Quantified over the same declaration the literal
    scan uses, so moving the table again moves both. Tests are excluded for the
    reason they are above: describing a wrong arrangement is what one is for.
    """

    def test_no_prose_in_the_item_gives_route_data_to_a_module_that_does_not_declare_it(self):
        claims = route_ownership_claims(prose_bearing_files())

        # Non-empty first. A file set that went empty, or a reader that stopped
        # recognising a claim, is how this assertion would go on passing while
        # deciding nothing — and the item does say who owns the table.
        self.assertNotEqual(claims, [], "the scan found no ownership claim anywhere")
        self.assertEqual([claim for claim in claims if claim[1] not in ROUTE_OWNING_MODULES], [])

    def test_the_prose_scan_can_fail(self):
        # One source with the misattribution put back, written beside the tree
        # with a .txt suffix so it can never be imported, so the scan is shown
        # to discriminate rather than to match nothing at all.
        misattributing = FIXTURE_DIR / "misattributed_ownership_source.txt"

        self.assertEqual(
            route_ownership_claims([misattributing]),
            [(misattributing.name, "transport")],
        )


def sent_headers(content_type, headers=()):
    """What an origin sent back, in the ``email.message.Message`` urllib hands over.

    One builder for both stand-ins, the one that returns and the one that
    raises, so a header can never arrive on one path and be forgotten on the
    other — which is the whole failure `RaisingUrlopen` exists to catch.
    """

    return email.message_from_string(
        "".join(
            name + ": " + value + "\n"
            for name, value in (("Content-Type", content_type),) + tuple(headers)
        )
    )


class FakeHTTPResponse:
    """The little of an http response that ``urlopen_read`` reads.

    ``url`` is carried because urllib carries it: a real response states the
    address it was answered from, and that address is the one the request
    actually went out on — credential and all. A stand-in that omitted it made
    `final_url` fall back to the uncredentialed url a caller had built, which
    is the one shape in which the T02 leak below is invisible.

    ``headers`` is an ``email.message.Message`` because that is what urllib
    answers with: it keeps the origin's own casing rather than a tidier one a
    stand-in chose, and casing is exactly what the lookup under test must not
    depend on.
    """

    def __init__(self, status, body, content_type, url="", headers=()):
        self.status = status
        self.url = url
        self.headers = sent_headers(content_type, headers)
        self._body = body.encode("utf-8")

    def read(self, limit):
        return self._body[:limit]

    def __enter__(self):
        return self

    def __exit__(self, *exception):
        return False


class RecordingUrlopen:
    """Stand in for ``urllib.request.urlopen`` and keep what would go on the wire."""

    def __init__(self, status=200, body="{}", content_type="application/json", headers=()):
        self.status = status
        self.body = body
        self.content_type = content_type
        self.headers = tuple(headers)
        self.requests = []

    def __call__(self, outbound, timeout=None):
        self.requests.append(outbound)
        # Answered from the address it was asked at, which is what an origin
        # that did not redirect reports.
        return FakeHTTPResponse(
            self.status,
            self.body,
            self.content_type,
            url=outbound.full_url,
            headers=self.headers,
        )


def outbound_blob(outbound):
    """Everything a urllib request would put on the wire, as one string."""

    return " ".join(
        [outbound.full_url, repr(sorted(outbound.header_items())), repr(outbound.data)]
    )


class GuestActivationRouteTest(unittest.TestCase):
    """The two non-read operations, and the gate that keeps them two.

    Minting an anonymous guest token needs a POST, and so does asking InnerTube
    a question it only takes in a JSON body. Neither creates anything at an
    origin: they are reads spelled in an awkward verb. What separates that from
    a write-capable channel is not the verb but the enumeration — each is named
    by route id in one of two closed sets, asserted below in both directions,
    and no route anywhere reaches PUT, PATCH or DELETE.
    """

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

    def test_the_routes_declaring_a_non_read_method_are_exactly_the_declared_exceptions(self):
        # Both directions. A route declaring a non-read method and named in
        # neither set fails here; a route named in a set while declaring a read
        # fails here too, because an exception nothing needs must not be held.
        declared = sorted(transport.TOKEN_ACTIVATION_ROUTES + transport.QUERY_BODY_ROUTES)
        non_read = sorted(
            route_id
            for route_id, route in transport.ROUTE_CONSTANTS.items()
            if route.method not in transport.READ_METHODS
        )

        self.assertEqual(non_read, declared)
        # Spelled as well as derived: an allowlist compared only against itself
        # would admit a third member silently.
        self.assertEqual(
            declared, [transport.X_GUEST_ACTIVATE_ROUTE, transport.YOUTUBE_INNERTUBE_ROUTE]
        )
        # Two exceptions, one verb between them, and no route in both.
        self.assertEqual(transport.TOKEN_ACTIVATION_METHODS, ("POST",))
        self.assertEqual(transport.QUERY_BODY_METHODS, ("POST",))
        self.assertEqual(
            sorted(set(transport.TOKEN_ACTIVATION_ROUTES) & set(transport.QUERY_BODY_ROUTES)),
            [],
        )

    def test_only_a_declared_exception_route_may_use_a_method_that_is_not_a_read(self):
        declared = transport.TOKEN_ACTIVATION_ROUTES + transport.QUERY_BODY_ROUTES

        for route_id in sorted(transport.ROUTE_CONSTANTS):
            with self.subTest(route=route_id):
                admitted = transport.admitted_methods(route_id)

                if route_id in declared:
                    self.assertEqual(admitted, transport.READ_METHODS + ("POST",))
                else:
                    self.assertEqual(admitted, transport.READ_METHODS)
                # Unconditional, and true of the exceptions too: the widening
                # is one more way to ask, never a way to change anything.
                for method in ("PUT", "PATCH", "DELETE"):
                    self.assertNotIn(method, admitted)


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

    def test_post_is_refused_on_every_route_but_the_two_declared_exceptions(self):
        declared = transport.TOKEN_ACTIVATION_ROUTES + transport.QUERY_BODY_ROUTES
        refused = []

        for route_id in sorted(transport.ROUTE_CONSTANTS):
            if route_id in declared:
                continue
            with self.subTest(route=route_id):
                self.assertIn(
                    "refusing a write-capable method", self._refusal_for(route_id, "POST")
                )
                refused.append(route_id)

        # The skip list is what a widening grows, so the loop states how much
        # it still covers: every route but the two, and never zero.
        self.assertEqual(len(refused), len(transport.ROUTE_CONSTANTS) - len(declared))
        self.assertGreater(len(refused), 0)

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


class RaisingUrlopen:
    """Stand in for ``urllib.request.urlopen`` the way it really answers a non-2xx.

    ``FakeHTTPResponse`` returns every status, which no real ``urlopen`` does:
    urllib raises :class:`urllib.error.HTTPError` for every response outside
    2xx, and the opener's own ``except`` is what turns that back into a status,
    a body, a content type, and an answering address. Nothing in the suite
    constructed one, so every failure path in this package — `stale_identifier`,
    `auth_required`, `rate_limited`, `network_intercepted` — reached production
    through a branch no test executed. ``HTTPError`` is also a response object
    in its own right, which is why the branch can read it at all.
    """

    def __init__(self, status, body, content_type, url="", headers=()):
        self.status = status
        self.body = body
        self.content_type = content_type
        self.url = url
        self.headers = tuple(headers)
        self.requests = []

    def __call__(self, outbound, timeout=None):
        self.requests.append(outbound)
        raise urllib.error.HTTPError(
            self.url or outbound.full_url,
            self.status,
            "an origin's own refusal",
            sent_headers(self.content_type, self.headers),
            io.BytesIO(self.body.encode("utf-8")),
        )


class TheOpenerReadsARealHTTPErrorTest(unittest.TestCase):
    """Fidelity: the branch every non-2xx in production goes through, executed.

    Nothing under test changes here. This exists because the stand-in that
    every other row uses is more forgiving than urllib is, and the last time an
    offline stand-in was gentler than the real thing it hid the `final_url`
    credential leak for ten tickets.
    """

    def _read(self, status, body, content_type="text/html", route=None, headers=()):
        recorder = RaisingUrlopen(status, body, content_type, headers=headers)
        request = transport.build_transport_request(
            transport.DDG_HTML_ROUTE if route is None else route, {"q": "local model"}
        )
        with mock.patch.object(urllib.request, "urlopen", recorder):
            return transport.urlopen_read(request), recorder.requests[0]

    def test_a_raised_status_comes_back_as_a_status_and_not_as_a_tool_failure(self):
        (status, body, content_type, final_url, _), outbound = self._read(
            404, "<html>not found</html>"
        )

        self.assertEqual(status, 404)
        self.assertIn("not found", body)
        self.assertEqual(content_type, "text/html")
        self.assertEqual(final_url, outbound.full_url)

    def test_the_channel_verdict_still_tells_this_network_from_the_origin(self):
        portal = read_fixture("captive_portal.html")
        blocked, _ = self._read(503, portal)
        refused, _ = self._read(503, "<html>Service Unavailable</html>")

        self.assertEqual(
            transport.channel_verdict(blocked[0], blocked[1]), transport.NETWORK_INTERCEPTED
        )
        self.assertEqual(
            transport.channel_verdict(refused[0], refused[1]), transport.ORIGIN_FAILURE
        )

    def test_a_credential_placed_in_the_query_does_not_ride_out_on_the_error(self):
        # T02, on the path that raises. `HTTPError.url` is the address the
        # request actually went out on — credential and all — so this is the
        # one branch where the answering address could carry one back out.
        route = transport.YOUTUBE_INNERTUBE_ROUTE
        (_, _, _, final_url, _), outbound = self._read(
            401, "{}", "application/json", route=route
        )

        for _, value in credential_strings():
            with self.subTest(secret=value):
                self.assertNotIn(value, final_url)
        self.assertTrue(outbound.full_url)

    def test_the_headers_arrive_on_the_branch_that_raises(self):
        # Where `Retry-After` actually lives. A 429 is a raise, so headers read
        # only off the returning branch would be headers the scheduler never
        # sees on the one status it exists to answer.
        answered, _ = self._read(
            transport.RATE_LIMITED_STATUS,
            "slow down",
            headers=((transport.RETRY_AFTER_HEADER, "120"),),
        )

        self.assertEqual(
            transport.header_value(answered[4], transport.RETRY_AFTER_HEADER), "120"
        )

    def test_an_oserror_is_still_a_tool_failure_and_never_a_status(self):
        # The other half of the same try: a refused connection has no status to
        # report, so it must stay a `TransportError` rather than becoming one.
        def refuse(outbound, timeout=None):
            raise OSError("connection refused")

        request = transport.build_transport_request(transport.DDG_HTML_ROUTE, {"q": "x"})
        with mock.patch.object(urllib.request, "urlopen", refuse):
            with self.assertRaises(transport.TransportError):
                transport.urlopen_read(request)


class TheAnswerCarriesWhatTheOriginSaidTest(unittest.TestCase):
    """Criterion 1: an origin's own headers reach a caller, or say it sent none.

    Until they did, the one thing an origin can say about how long it wants to
    be left alone died inside the opener, and every wait this package took was
    a constant it had guessed rather than an interval it had been told.
    """

    def _fetched(self, answer):
        carrier, _ = offline_transport({transport.DDG_HTML_ROUTE: answer})
        return carrier.fetch(
            transport.build_transport_request(transport.DDG_HTML_ROUTE, {"q": "local model"})
        )

    def test_the_headers_an_opener_reports_reach_the_response(self):
        response = self._fetched(
            (
                transport.RATE_LIMITED_STATUS,
                "slow down",
                "text/plain",
                "https://asked.invalid/html/",
                ((transport.RETRY_AFTER_HEADER, "120"),),
            )
        )

        self.assertEqual(response.headers, ((transport.RETRY_AFTER_HEADER, "120"),))

    def test_an_opener_that_reports_no_headers_says_the_origin_sent_none(self):
        # The four-value opener contract every stand-in in this suite was
        # written against, unchanged: it reports no headers and gets an empty
        # set rather than an error.
        response = self._fetched((200, "<html></html>", "text/html"))

        self.assertEqual(response.headers, ())

    def test_a_header_is_found_whatever_case_the_origin_spelled_it_in(self):
        for spelling in ("Retry-After", "retry-after", "RETRY-AFTER", "ReTrY-aFtEr"):
            with self.subTest(spelling=spelling):
                self.assertEqual(
                    transport.header_value(
                        ((spelling, "120"),), transport.RETRY_AFTER_HEADER
                    ),
                    "120",
                )

    def test_a_header_nobody_sent_reads_as_nothing_rather_than_raising(self):
        self.assertEqual(transport.header_value((), transport.RETRY_AFTER_HEADER), "")
        self.assertEqual(
            transport.header_value(
                (("Content-Type", "text/html"),), transport.RETRY_AFTER_HEADER
            ),
            "",
        )

    def test_the_real_opener_reports_what_the_origin_sent(self):
        recorder = RecordingUrlopen(
            200, "{}", "application/json", headers=(("x-ratelimit-remaining", "59"),)
        )
        request = transport.build_transport_request(
            transport.GITHUB_REST_ROUTE, {"owner": "o"}
        )

        with mock.patch.object(urllib.request, "urlopen", recorder):
            answered = transport.urlopen_read(request)

        self.assertEqual(
            transport.header_value(answered[4], "X-RateLimit-Remaining"), "59"
        )

    def test_the_three_value_view_is_still_three_values(self):
        recorder = RecordingUrlopen(200, "{}", "application/json")
        request = transport.build_transport_request(
            transport.GITHUB_REST_ROUTE, {"owner": "o"}
        )

        with mock.patch.object(urllib.request, "urlopen", recorder):
            self.assertEqual(len(transport.urlopen_response(request)), 3)


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


THREAT_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "threats"

# The ladder the retained threat oracles are remapped onto. `offline` is the
# fixture adapter's class and is not on it: nothing about `fake` is a claim
# about a route.
KEYLESS_CLASSES = ("K0", "K1", "K2", "K3", "K4")
CREDENTIALED_CLASS = "K5"
EVERY_CLASS = KEYLESS_CLASSES + (CREDENTIALED_CLASS,)
# The two classes where a credential exists at all. `K1`'s is vendor-published
# and names no user; `K5`'s is the user's own and no first-release capability
# may depend on it. Every credential-handling threat is quantified over both.
CREDENTIAL_CLASSES = ("K1", CREDENTIALED_CLASS)
NO_CLASS = ()

# T01-T16, retained by reference from the superseded spec and remapped from
# `A0`-`A5` to `K0`-`K5`. The remap is of *applicability* — which classes a
# threat is about — and the rule is the one the old mapping used: a threat
# applies to a class when that class has the machinery the threat is about.
#
# Three threats apply to no class, and that is the finding rather than a gap.
# `A2` was a CLI with an ambient identity and `A3` was an exported browser
# session; the new ladder has neither, so T05, T06's argv half, T07 and T08
# are about machinery this package does not contain. They are answered by its
# absence, which `test_dependency_boundary` proves and which the row below
# restates at this seam.
#
# One clause is dropped on purpose. The superseded T09 also demanded a
# `hostile_instruction_present` code. The frozen spec's criterion 11 states
# the remapped T09 without it — "acquired text is `untrusted_content` and
# cannot alter plan, grants, or write set" — and the criterion is the runnable
# authority here. Emitting a code would mean this package judging which text
# is hostile, which is the calling lane's job and is the one thing an
# acquisition core must not start doing.
THREAT_REMAP = {
    "T01": (CREDENTIAL_CLASSES, "no credential id or value reaches a request, a response, a call log, or an artifact"),
    "T02": (CREDENTIAL_CLASSES, "an echoed credential — the address a query-placed key was appended to — comes back stripped"),
    "T03": (CREDENTIAL_CLASSES, "a credential is attached at send time from the route's own constant, so it reaches that origin and no other"),
    "T04": (EVERY_CLASS, "no route admits a state-changing verb: PUT, PATCH and DELETE nowhere, POST only for two named reads"),
    "T05": (NO_CLASS, "no process is launched, because none can be: nothing here imports one or spells a command"),
    "T06": (EVERY_CLASS, "a caller cannot escape a route's admitted method set, and a body is the route's shape with the caller's values"),
    "T07": (NO_CLASS, "there is no session state to export: the one token a run mints lives in memory and nowhere else"),
    "T08": (NO_CLASS, "nothing navigates, clicks or submits: the only outbound operation is one bounded read"),
    "T09": (EVERY_CLASS, "acquired text is untrusted_content: it changes no plan, no grant, and no write set"),
    "T10": (CREDENTIAL_CLASSES, "a K1 credential names no user, so there is no principal to mismatch; the operator that answered is declared"),
    "T11": (EVERY_CLASS, "a refusal is typed rate_limited on one call, and no identity changes because of it"),
    "T12": (EVERY_CLASS, "a route the run cannot reach is refused with a typed reason and never probed"),
    "T13": (("K4",), "an index surface declares itself an index, and it is the only surface in the roster that does"),
    "T14": (EVERY_CLASS, "the package has no delete primitive: its only stores are in memory and clearing one is all there is"),
    "T15": (EVERY_CLASS, "a refusal costs the origin nothing: it is decided before any call is made"),
    "T16": (EVERY_CLASS, "no fallback: a failed read is a typed failure, never a second read somewhere else"),
}


def load_threat_fixture(name):
    """Load one module written beside the tree, by path."""

    spec = importlib.util.spec_from_file_location(
        "threat_fixture_" + name, THREAT_FIXTURE_DIR / (name + ".py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_threat_fixture(name):
    return THREAT_FIXTURE_DIR.joinpath(name).read_text(encoding="utf-8")


def routes_at(classes):
    """Every declared route answering at one of these access classes."""

    return tuple(
        route_id
        for route_id, route in sorted(transport.ROUTE_CONSTANTS.items())
        if route.access_class in classes
    )


def credential_strings():
    """Every string that would identify this package's client to a vendor."""

    secrets = []
    for credential in transport.PUBLIC_CLIENT_CREDENTIALS.values():
        secrets.append((credential.credential_id + " value", credential.value))
        secrets.append((credential.credential_id + " id", credential.credential_id))
    return tuple(secrets)


def sent_and_answered(route_id, params=None):
    """One read through the real opener, with the wire captured and no socket.

    The recorder answers from the address it was asked at, which is what
    urllib reports for a read nobody redirected. That makes the outbound blob
    and the returned address two different things: the credential belongs in
    the first and must not survive into the second.
    """

    recorder = RecordingUrlopen(200, "{}", "application/json")
    request = transport.build_transport_request(route_id, params or {})
    with mock.patch.object(urllib.request, "urlopen", recorder):
        answered = transport.urlopen_read(request)
    return answered, recorder.requests[0]


def route_grants():
    """Every grant this package holds, as one comparable value.

    Two halves, because a widening could arrive as either: which routes are
    reachable at all, and what each one is allowed to do.
    """

    return (
        tuple(sorted(transport.route_admissions().items())),
        tuple(
            (route_id, transport.admitted_methods(route_id))
            for route_id in sorted(transport.ROUTE_CONSTANTS)
        ),
    )


def authorized_routes(manifest):
    """Every route the steps of one manifest authorize a read on."""

    return {
        surface.route_id
        for step in manifest.steps
        for surface in runner.surface_descriptors(step.adapter_id)
    }


def assert_acquired_text_changed_nothing(case, manifest, artifact, calls, grants_before):
    """The T09 oracle: what was read cannot decide what happens next.

    Four clauses, and they are four separate ways for the claim to be false: a
    read that left for a route the plan never authorized, a read that left for
    an address its own route does not own, a verb on the wire the route does
    not admit, and a grant that is not the grant the run started with. The
    fifth is vacuity — an artifact holding nothing proves nothing about what
    text can do, and fails here rather than passing.
    """

    if not artifact.records:
        case.fail("no acquired text reached the artifact, so nothing about it was proven")
    if not calls:
        case.fail("no read was made, so nothing about what a read can be aimed at was proven")

    authorized = authorized_routes(manifest)
    for call in calls:
        if call.route_id not in authorized:
            case.fail(
                "acquired text reached a route the plan never authorized: " + call.route_id
            )
        if call.method not in transport.admitted_methods(call.route_id):
            case.fail(
                "acquired text put {0} on the wire, which route {1} does not admit".format(
                    call.method, call.route_id
                )
            )
        origin = transport.route_constant(call.route_id).origin
        if not call.url.startswith(origin):
            case.fail("acquired text chose the address a read went to: " + call.url)

    if route_grants() != grants_before:
        case.fail("acquired text changed the grants this package holds")
    if tuple(step.adapter_id for step in artifact.steps) != tuple(
        step.adapter_id for step in manifest.steps
    ):
        case.fail("acquired text changed the plan the caller wrote")


def assert_hostile_text_is_carried_as_content(case, artifact, markers):
    """The other half: the text is kept verbatim, and it is kept only as text.

    Refusing to record a hostile sentence would be the same mistake in the
    other direction — a caller cannot judge a source it is not shown. So each
    marker has to be somewhere in the acquired rows, and nowhere in the fields
    that decide anything.
    """

    if not markers:
        case.fail("no hostile text was looked for, so nothing about it was checked")
    for marker in markers:
        carried = [
            record
            for record in artifact.records
            if marker in record.title or marker in record.body
        ]
        if not carried:
            case.fail("marker {0!r} never reached a record: nothing hostile was carried".format(marker))
    for record in artifact.records:
        deciding = (
            record.adapter_id,
            record.route_id,
            record.access_class,
            record.representation_kind,
            record.operator_identity,
        ) + tuple(record.loss)
        for marker in markers:
            for field in deciding:
                if marker in field:
                    case.fail(
                        "hostile text reached a field that decides something: {0!r} in {1!r}".format(
                            marker, field
                        )
                    )


def injected_manifest():
    """One discovery step over the K4 surface, answered with an injected page."""

    return schema.AcquisitionManifest(
        manifest_id="m-injected",
        mode="staged",
        as_of=FROZEN_OBSERVED_AT,
        steps=(
            schema.AcquisitionStep(
                step_id="s1-discover",
                kind="discovery",
                adapter_id="web_search",
                query="local model benchmarks",
                max_items=10,
            ),
        ),
    )


def injected_run():
    """Acquire the injected page, and hand back everything a caller would hold."""

    carrier, opener = offline_transport(
        {
            route_id: (200, read_threat_fixture("injected_search_results.html"), "text/html")
            for route_id in transport.ROUTE_CONSTANTS
        }
    )
    manifest = injected_manifest()
    artifact = runner.run_acquisition(manifest, carrier)
    return manifest, artifact, carrier, opener


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
                answered, _ = sent_and_answered(route_id, {"q": "probe"})
                response = transport.Transport(
                    opener=lambda request, held=answered: held, now=lambda: FROZEN_OBSERVED_AT
                ).fetch(transport.build_transport_request(route_id, {"q": "probe"}))

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
                    route_id, {"q": "probe", "body": "anything", "data": "anything"}
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


MINTED_GUEST_TOKEN = "a-token-this-run-minted"
ACTIVATION_ANSWER = (
    200,
    json.dumps({transport.GUEST_TOKEN_FIELD: MINTED_GUEST_TOKEN}),
    "application/json",
)
GUEST_READ_ANSWER = (200, "{}", "application/json")

# The one function that turns an activation into a token. A place that calls it
# is a place that mints, which is what the site scan below counts.
MINTER = "mint_guest_token"


def guest_read_request():
    """One read on the route that declares an activation route of its own."""

    return transport.build_transport_request(
        transport.X_GUEST_GRAPHQL_ROUTE,
        {"query_id": "abc123", "operation_name": "UserByScreenName"},
    )


def called_name(func):
    """The bare name a call node spells, whether it was reached plainly or dotted."""

    if isinstance(func, ast.Name):
        return func.id
    return func.attr if isinstance(func, ast.Attribute) else ""


def sites_calling(node, owners, module_name, found):
    """Collect every enclosing function in one tree that calls the minter."""

    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            sites_calling(child, owners + (child.name,), module_name, found)
            continue
        if isinstance(child, ast.Call) and called_name(child.func) == MINTER:
            found.add(module_name + ":" + ".".join(owners))
        sites_calling(child, owners, module_name, found)


def minting_sites():
    """Every place in the package that mints, as ``module:qualified name``.

    Stated as the set of sites for the reason `test_pipeline` states the set of
    modules that build a carrier as a set: naming one site would not notice a
    second one appearing beside it, and a count would not say which.
    """

    found = set()
    for path in sorted(PACKAGE_DIR.rglob("*.py")):
        sites_calling(ast.parse(path.read_text(encoding="utf-8")), (), path.name, found)
    return sorted(found)


class GuestMintIsOnePacedRecordedCallTest(unittest.TestCase):
    """The mint is one recorded, paced call on whatever opener was injected.

    It used to run inside ``urlopen_read``, below every seam: invisible to the
    call log, unreachable by an injected opener, and outside every budget. It
    now runs at the governor, which is the only place all three are true at
    once — a carrier cannot put a request inside a budget, because the carrier
    is what the governor paces.

    The store is module-level, so every test here clears it: ordering would
    otherwise decide which of them minted.
    """

    def setUp(self):
        transport.GUEST_TOKENS.clear()
        self.addCleanup(transport.GUEST_TOKENS.clear)

    def guest_carrier(self, activation=ACTIVATION_ANSWER, read=GUEST_READ_ANSWER):
        """The carrier a run actually gets: the governor over a recording transport."""

        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(clock, {
            transport.X_GUEST_ACTIVATE_ROUTE: activation,
            transport.X_GUEST_GRAPHQL_ROUTE: read,
        })
        governor = runner.RateGovernor(carrier, clock=clock.monotonic, sleep=clock.sleep)
        return governor, carrier, opener

    def test_the_activation_is_in_the_call_log_ahead_of_the_read_it_authorizes(self):
        governor, carrier, _ = self.guest_carrier()

        governor.fetch(guest_read_request())

        self.assertEqual(
            [call.route_id for call in carrier.calls],
            [transport.X_GUEST_ACTIVATE_ROUTE, transport.X_GUEST_GRAPHQL_ROUTE],
        )

    def test_the_injected_opener_answers_the_activation_and_urllib_never_does(self):
        governor, _, opener = self.guest_carrier()

        # Bypassing the injected opener means reaching urllib, which this guard
        # turns into an assertion failure rather than an egress.
        with forbid_io():
            governor.fetch(guest_read_request())

        self.assertEqual(
            [request.route_id for request in opener.opened],
            [transport.X_GUEST_ACTIVATE_ROUTE, transport.X_GUEST_GRAPHQL_ROUTE],
        )
        self.assertEqual(
            transport.GUEST_TOKENS._tokens,
            {transport.X_GUEST_ACTIVATE_ROUTE: MINTED_GUEST_TOKEN},
        )

    def test_the_activation_is_charged_against_its_own_routes_budget(self):
        # The governor's log is what it charged, and it is a different list
        # from the carrier's: a request in `calls` but not in `log` is one the
        # scheduler never saw and no budget ever covered.
        governor, _, _ = self.guest_carrier()

        governor.fetch(guest_read_request())

        self.assertEqual(
            [read.route_id for read in governor.log],
            [transport.X_GUEST_ACTIVATE_ROUTE, transport.X_GUEST_GRAPHQL_ROUTE],
        )
        self.assertEqual(
            runner.route_budgets()[transport.X_GUEST_ACTIVATE_ROUTE],
            runner.budget_of(x_guest.ACTIVATION_DESCRIPTOR),
        )

    def test_a_second_activation_would_wait_out_the_interval_its_route_declares(self):
        # The point of a budget is the wait it can impose. One mint per process
        # means the second activation never happens on its own, so the ceiling
        # is proven by asking the governor to spend the route twice.
        governor, _, _ = self.guest_carrier()
        interval_us = (
            runner.route_budgets()[transport.X_GUEST_ACTIVATE_ROUTE].min_interval_ms
            * runner.US_PER_MS
        )

        with helpers.forbid_sleep():
            governor.fetch(guest_read_request())
            governor.fetch(
                transport.build_transport_request(transport.X_GUEST_ACTIVATE_ROUTE)
            )

        activations = [
            read for read in governor.log
            if read.route_id == transport.X_GUEST_ACTIVATE_ROUTE
        ]
        self.assertEqual(len(activations), 2)
        self.assertGreater(interval_us, 0)
        self.assertEqual(activations[1].at_us - activations[0].at_us, interval_us)

    def test_a_bare_transport_mints_nothing_and_the_read_goes_out_unauthorized(self):
        # 4b. A caller reaches an unpaced origin only by building a carrier and
        # handing it in, which `run_scheduled` already calls an act rather than
        # a default. The mint is now inside that same choice: no governor, no
        # activation — and the read that needed one goes out without it, so the
        # origin's own refusal is what the run records.
        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(clock, {
            transport.X_GUEST_ACTIVATE_ROUTE: ACTIVATION_ANSWER,
            transport.X_GUEST_GRAPHQL_ROUTE: (401, "unauthorized", "application/json"),
        })

        response = carrier.fetch(guest_read_request())

        self.assertEqual([call.route_id for call in carrier.calls], [transport.X_GUEST_GRAPHQL_ROUTE])
        self.assertEqual(
            [request.route_id for request in opener.opened], [transport.X_GUEST_GRAPHQL_ROUTE]
        )
        # No invented token, and the refusal is the origin's own — not a local
        # error and not a retry.
        self.assertEqual(transport.GUEST_TOKENS._tokens, {})
        self.assertEqual(response.status, 401)
        self.assertEqual(response.channel_verdict, transport.ORIGIN_FAILURE)

    def test_the_bare_carrier_consequence_is_stated_where_the_mint_is_documented(self):
        # 4b's second half. The behaviour is proven above; this is the claim
        # that a reader meets it without running the suite. Both places that
        # document the mint must name the un-minted outcome, so deleting it
        # from either one fails here rather than quietly leaving a reader to
        # assume every carrier mints.
        for owner in (pacing.RateGovernor._mint_for, transport.mint_guest_token):
            with self.subTest(documented=owner.__qualname__):
                stated = inspect.getdoc(owner)

                self.assertIn("unauthorized", stated)

    def test_the_token_is_minted_once_and_the_store_answers_every_later_read(self):
        governor, carrier, _ = self.guest_carrier()

        governor.fetch(guest_read_request())
        governor.fetch(guest_read_request())

        self.assertEqual(
            [call.route_id for call in carrier.calls],
            [
                transport.X_GUEST_ACTIVATE_ROUTE,
                transport.X_GUEST_GRAPHQL_ROUTE,
                transport.X_GUEST_GRAPHQL_ROUTE,
            ],
        )

    def test_a_route_declaring_no_activation_route_mints_nothing(self):
        clock = helpers.FakeClock()
        carrier, _ = helpers.offline_transport(
            clock, {transport.DDG_HTML_ROUTE: GUEST_READ_ANSWER}
        )
        governor = runner.RateGovernor(carrier, clock=clock.monotonic, sleep=clock.sleep)

        governor.fetch(
            transport.build_transport_request(transport.DDG_HTML_ROUTE, {"q": "probe"})
        )

        self.assertEqual([call.route_id for call in carrier.calls], [transport.DDG_HTML_ROUTE])
        self.assertEqual(transport.GUEST_TOKENS._tokens, {})

    def test_an_activation_the_opener_refuses_outright_yields_no_token(self):
        # The opener raises rather than answering, so the read that needed a
        # token goes out without one and the origin's own 401 is what the run
        # records — never an invented token.
        clock = helpers.FakeClock()
        carrier, _ = helpers.offline_transport(
            clock,
            {transport.X_GUEST_GRAPHQL_ROUTE: (401, "unauthorized", "application/json")},
        )
        governor = runner.RateGovernor(carrier, clock=clock.monotonic, sleep=clock.sleep)

        response = governor.fetch(guest_read_request())

        self.assertEqual(
            transport.GUEST_TOKENS._tokens, {transport.X_GUEST_ACTIVATE_ROUTE: ""}
        )
        self.assertEqual(response.status, 401)

    def test_a_refused_mint_sends_the_read_unauthorized_and_is_never_retried(self):
        # The rule :func:`mint_guest_token` states, now under test: a mint that
        # produced nothing is not turned into a second activation, and the
        # origin's own 401 is what the run records. A refusal re-attempted per
        # read would spend two requests on every one the origin already refused.
        governor, carrier, _ = self.guest_carrier(
            activation=(403, "forbidden", "text/plain"),
            read=(401, "unauthorized", "application/json"),
        )

        first = governor.fetch(guest_read_request())
        second = governor.fetch(guest_read_request())

        self.assertEqual(
            transport.GUEST_TOKENS._tokens, {transport.X_GUEST_ACTIVATE_ROUTE: ""}
        )
        self.assertEqual(
            [call.route_id for call in carrier.calls],
            [
                transport.X_GUEST_ACTIVATE_ROUTE,
                transport.X_GUEST_GRAPHQL_ROUTE,
                transport.X_GUEST_GRAPHQL_ROUTE,
            ],
        )
        self.assertEqual((first.status, second.status), (401, 401))

    def test_an_activation_route_that_named_a_token_route_cannot_recurse(self):
        # Minting at the governor is re-entrant: the activation is itself a
        # paced fetch. Nothing in the table declares this today, so the guard is
        # proven against a table that does.
        looping = dict(transport.ROUTE_CONSTANTS)
        looping[transport.X_GUEST_ACTIVATE_ROUTE] = dataclasses.replace(
            looping[transport.X_GUEST_ACTIVATE_ROUTE],
            token_route_id=transport.X_GUEST_ACTIVATE_ROUTE,
        )
        governor, carrier, _ = self.guest_carrier()

        with mock.patch.object(transport, "ROUTE_CONSTANTS", looping):
            governor.fetch(guest_read_request())

        self.assertEqual(
            [call.route_id for call in carrier.calls],
            [transport.X_GUEST_ACTIVATE_ROUTE, transport.X_GUEST_GRAPHQL_ROUTE],
        )

    def test_a_read_a_run_already_remembers_costs_no_activation(self):
        # The mint is on the miss path, where pacing lives: a token buys an
        # origin read, and a cache hit reaches no origin. Minting for one would
        # spend a request the run had already decided not to make.
        clock = helpers.FakeClock()
        carrier, _ = helpers.offline_transport(clock, {
            transport.X_GUEST_ACTIVATE_ROUTE: ACTIVATION_ANSWER,
            transport.X_GUEST_GRAPHQL_ROUTE: GUEST_READ_ANSWER,
        })
        governor = runner.RateGovernor(
            carrier,
            run_cache=cache.RunCache(clock=clock.monotonic),
            clock=clock.monotonic,
            sleep=clock.sleep,
        )

        governor.fetch(guest_read_request())
        transport.GUEST_TOKENS.clear()
        governor.fetch(guest_read_request())

        self.assertEqual([serve.cache_hit for serve in governor.serves], [False, True])
        self.assertEqual(transport.GUEST_TOKENS._tokens, {})

    def test_the_opener_attaches_what_the_governor_minted_and_mints_nothing_itself(self):
        governor, _, _ = self.guest_carrier()
        governor.fetch(guest_read_request())

        # Under the guard on purpose: a lookup that still minted would reach
        # urllib here, and a store the governor filled needs no network.
        with forbid_io():
            held = transport.tokened_headers((), transport.X_GUEST_ACTIVATE_ROUTE)
            transport.GUEST_TOKENS.clear()
            empty = transport.tokened_headers((), transport.X_GUEST_ACTIVATE_ROUTE)

        self.assertEqual(held, ((transport.GUEST_TOKEN_HEADER, MINTED_GUEST_TOKEN),))
        self.assertEqual(empty, ())

    def test_the_minted_token_reaches_no_call_no_response_and_no_environment(self):
        governor, carrier, opener = self.guest_carrier()

        # The guard is half the claim: no file was written because none could be.
        with forbid_io():
            response = governor.fetch(guest_read_request())

        # A token really was minted, so the four claims below are about
        # something rather than about nothing.
        self.assertEqual(
            transport.GUEST_TOKENS._tokens,
            {transport.X_GUEST_ACTIVATE_ROUTE: MINTED_GUEST_TOKEN},
        )
        self.assertNotIn(MINTED_GUEST_TOKEN, repr(carrier.calls))
        self.assertNotIn(MINTED_GUEST_TOKEN, repr(opener.opened))
        self.assertNotIn(MINTED_GUEST_TOKEN, repr(response))
        self.assertEqual(
            [name for name, value in os.environ.items() if MINTED_GUEST_TOKEN in value], []
        )

    def test_exactly_one_site_in_the_package_mints(self):
        self.assertEqual(minting_sites(), ["pacing.py:RateGovernor._mint_for"])

    def test_the_minting_site_scan_notices_a_site_it_was_not_told_about(self):
        # The scan is shown to discriminate rather than to match nothing at all.
        found = set()

        sites_calling(
            ast.parse(
                "class Rogue:\n"
                "    def read(self):\n"
                "        return mint_guest_token(self.fetch, 'r')\n"
            ),
            (),
            "rogue.py",
            found,
        )

        self.assertEqual(sorted(found), ["rogue.py:Rogue.read"])


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
                request = transport.build_transport_request(route_id, {"q": "probe"})

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

        self.assertEqual(indexes, ["web_search"])
        self.assertEqual(runner.descriptor_for("web_search").access_class, "K4")

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


INTERNALS_PATH = Path(__file__).resolve().parent.parent / "references" / "internals.md"

# The one table in `internals.md` that restates `THREAT_REMAP`, named by its
# header row. Only this table is read; every other table in that file belongs
# to someone else.
THREAT_TABLE_HEADER = "| threat | applies to | form here |"


def threat_table_rows():
    """`internals.md`'s threat table, as `(threat, applies, form)` cells in document order.

    Parsed rather than transcribed: the table a reader meets is the one the
    assertions run against, so a row corrected in the document and left in
    `THREAT_REMAP` — or the reverse — is a red test rather than two statements
    nobody compared.
    """

    rows = []
    inside = False
    for line in INTERNALS_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped == THREAT_TABLE_HEADER:
            inside = True
            continue
        if not inside:
            continue
        if not stripped.startswith("|"):
            break
        cells = tuple(cell.strip() for cell in stripped.strip("|").split("|"))
        if set(cells[0]) <= set("- "):
            continue
        rows.append(cells)
    return tuple(rows)


def documented_classes(cell):
    """The access classes one `applies to` cell names, `K0`–`K5` read as a range.

    The ladder the range is expanded over is `schema.ACCESS_CLASSES`, so the
    shorthand means whatever the package says it means and not a second list.
    """

    named = tuple(piece for index, piece in enumerate(cell.split("`")) if index % 2 and piece)
    if not named or "–" not in cell:
        return named
    ladder = list(schema.ACCESS_CLASSES)
    return tuple(ladder[ladder.index(named[0]) : ladder.index(named[-1]) + 1])


def comparable(prose):
    """One form statement with the document's typography taken off, and nothing else.

    Backticks and line breaks are how a cell is written, not what it claims.
    Every word survives, so a clause dropped on either side stays a difference.
    """

    return " ".join(prose.replace("`", "").split())


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
