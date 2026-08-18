"""Transport suite: a local network block is never a platform response.

Every test here runs offline. The distinction this module defends is
the captive-portal caveat's: this host sits behind an appliance that answers some
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


TEST_DIR = Path(__file__).resolve().parent.parent
FIXTURE_DIR = TEST_DIR / "fixtures" / "transport"
ITEM_DIR = TEST_DIR.parent
PACKAGE_DIR = ITEM_DIR / "scripts" / "super_research"
ADAPTER_DIR = PACKAGE_DIR / "adapters"
EVIDENCE_DOC = ITEM_DIR / "references" / "evidence.md"
FROZEN_OBSERVED_AT = "2026-08-10T09:00:00Z"

# Only the transport seam may reach the network.
NETWORK_MODULES = ("urllib.request", "http.client", "socket", "ssl")

# The logical route table spans its facade and the two access-class catalogs.
# `transport` deliberately is not an owner: it re-exports and reaches the
# routes, but may not define an address or credential itself.
ROUTE_OWNING_MODULES = (
    "routes",
    "_support/route_contracts",
    "_support/route_catalog_k0",
    "_support/route_catalog_k1_k4",
)

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
    of the captive-portal caveat was broken.
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


def credential_strings():
    """Every string that would identify this package's client to a vendor."""

    secrets = []
    for credential in transport.PUBLIC_CLIENT_CREDENTIALS.values():
        secrets.append((credential.credential_id + " value", credential.value))
        secrets.append((credential.credential_id + " id", credential.credential_id))
    return tuple(secrets)
