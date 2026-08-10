"""Transport suite: a local network block is never a platform response.

Every test here runs offline. The distinction this module defends is
findings.md §0's: this host sits behind an appliance that answers some
domains with a failure status and a captive-portal body, and a route blocked
that way is UNVERIFIED, never rejected. Confusing that with a platform
response would record a local block as a platform gap.
"""

from __future__ import annotations

import builtins
import contextlib
import io
import json
import os
import socket
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

from super_research import transport


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "transport"
FROZEN_OBSERVED_AT = "2026-08-10T09:00:00Z"


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

    def test_the_verdict_is_one_of_the_closed_set(self):
        for row in interception_cases():
            with self.subTest(case=row["case_name"]):
                self.assertIn(row["expected_verdict"], transport.CHANNEL_VERDICTS)


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


if __name__ == "__main__":  # pragma: no cover - convenience runner
    unittest.main()
