"""Shared offline fixtures and harnesses for context seam cases."""

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

from tests import helpers
from super_research import adapters, normalize, runner, schema, transport
from super_research.adapters import fake, reddit_archive


FIXTURE_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "tracer"
FROZEN_OBSERVED_AT = "2026-08-10T09:00:00Z"

REDDIT_THREAD_LOCATOR = (
    "https://www.reddit.com/r/LocalLLaMA/comments/1abc234/"
    "what_is_the_best_local_model_right_now/"
)
X_POST_LOCATOR = "https://x.com/simonw/status/1799990000000000001"

# Spelled here rather than imported, so the spelling is pinned from outside the
# module that owns it.
DISCOVERY_NOT_RECORDED = "discovery_not_recorded"


def read_fixture(name):
    """Read one offline fixture; the only filesystem read the suite performs."""

    return FIXTURE_DIR.joinpath(name).read_text(encoding="utf-8")


class RecordingOpener:
    """Offline opener: one canned response per route, every call recorded.

    Standing in for the network is the whole point — nothing here can reach
    a socket, so a test that accidentally asks for an unseeded route fails
    loudly instead of egressing.
    """

    def __init__(self, responses):
        self.responses = {route: list(answers) if isinstance(answers, list) else [answers]
                          for route, answers in responses.items()}
        self.opened = []

    def __call__(self, request):
        self.opened.append(request)
        if request.route_id not in self.responses:
            raise transport.TransportError("no offline response seeded for " + request.route_id)
        answers = self.responses[request.route_id]
        outcome = answers.pop(0) if len(answers) > 1 else answers[0]
        if isinstance(outcome, Exception):
            raise outcome
        return helpers.answered(request, outcome)


def tracer_transport(responses):
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


TRACER_MANIFEST = {
    "manifest_id": "tracer-k4-reddit",
    "as_of": "2026-08-10T00:00:00Z",
    "steps": [
        {
            "step_id": "s1-discover",
            "kind": "discovery",
            "adapter_id": "fake",
            "query": "fixture:local-model-index",
            "max_items": 6,
        },
        {
            "step_id": "s2-hydrate",
            "kind": "hydration",
            "adapter_id": "reddit_archive",
            "prior_step_id": "s1-discover",
            "selected_hits": [
                {
                    "discovery_locator": (
                        "https://www.reddit.com/r/LocalLLaMA/comments/1abc234/"
                        "what_is_the_best_local_model_right_now/"
                    ),
                    "target_id": "1abc234",
                }
            ],
            "max_items": 6,
        },
    ],
}


TRACER_X_MANIFEST = {
    "manifest_id": "tracer-k4-x",
    "as_of": "2026-08-10T00:00:00Z",
    "steps": [
        {
            "step_id": "s1-discover",
            "kind": "discovery",
            "adapter_id": "fake",
            "query": "fixture:local-model-index",
            "max_items": 6,
        },
        {
            "step_id": "s2-hydrate-x",
            "kind": "hydration",
            "adapter_id": "fake",
            "prior_step_id": "s1-discover",
            "selected_hits": [
                {"discovery_locator": X_POST_LOCATOR, "target_id": "1799990000000000001"}
            ],
            "max_items": 6,
        },
    ],
}


ADAPTER_CALLS = (
    (
        fake,
        adapters.AdapterRequest(step_id="s1-discover", query="fixture:local-model-index"),
        "index_results.json",
        "application/json",
    ),
    (
        reddit_archive,
        adapters.AdapterRequest(step_id="s2-hydrate", target_ids=("1abc234",)),
        "arctic_shift_posts_ids.json",
        "application/json",
    ),
    (
        fake,
        adapters.AdapterRequest(step_id="s2-hydrate-x", target_ids=("1799990000000000001",)),
        "fake_x_native_page.json",
        "application/json",
    ),
)


def tracer_responses():
    return {
        "fake_offline": (200, read_fixture("index_results.json"), "application/json"),
        "arctic_shift_posts_ids": (
            200,
            read_fixture("arctic_shift_posts_ids.json"),
            "application/json",
        ),
    }


def run_tracer(payload):
    """Run one tracer manifest end to end over the offline fixtures."""

    responses = tracer_responses()
    if any(step["kind"] == "hydration" and step["adapter_id"] == "fake"
           for step in payload["steps"]):
        responses["fake_offline"] = [
            responses["fake_offline"],
            (200, read_fixture("fake_x_native_page.json"), "application/json"),
        ]
    carrier, opener = tracer_transport(responses)
    artifact = runner.run_acquisition(schema.parse_manifest(payload), carrier)
    return artifact, carrier, opener


def assert_linked_never_merged(case, artifact, discovery_locator, native_platform):
    """The K4 hybrid oracle: one index hit, its native target, linked, unmerged.

    Every assertion carries its own message so a failure names which part of
    ``wrong_merge_law`` the artifact broke.
    """

    locator = normalize.normalized_locator(discovery_locator)
    hits = [
        record
        for record in artifact.records
        if record.representation_kind == "index" and record.normalized_locator == locator
    ]
    targets = [
        record
        for record in artifact.records
        if record.representation_kind == "native" and record.platform == native_platform
    ]
    case.assertEqual(len(hits), 1, "expected exactly one index record for the pair")
    case.assertTrue(targets, "expected at least one native record for the pair")
    hit = hits[0]
    target = targets[0]

    case.assertNotEqual(
        hit.record_id, target.record_id, "the pair collapsed into a single record"
    )
    case.assertEqual(hit.representation_kind, "index")
    case.assertEqual(target.representation_kind, "native")

    edges = [
        edge
        for edge in artifact.edges
        if edge.edge_kind == "discovery_hydration"
        and edge.from_record_id == hit.record_id
        and edge.to_record_id == target.record_id
    ]
    case.assertEqual(len(edges), 1, "expected exactly one discovery_hydration edge")

    for group in artifact.groups:
        case.assertFalse(
            hit.record_id in group.member_record_ids
            and target.record_id in group.member_record_ids,
            "a group merged the index hit with its hydrated target",
        )

    case.assertEqual(hit.engagement, (), "the index hit was given native engagement")
    case.assertTrue(target.engagement, "the native record lost its engagement")
    case.assertEqual(hit.native_item_id, "", "the index hit was given a native identity")
    case.assertTrue(target.native_item_id, "the native record lost its identity")
    case.assertNotEqual(hit.body, target.body, "one record's body was folded into the other")
    case.assertNotEqual(
        hit.exact_content_hash,
        target.exact_content_hash,
        "one record's content hash was folded into the other",
    )
    case.assertEqual(hit.time_confidence, "unknown", "the index hit was given a target time")
    case.assertTrue(target.usable_basis_time, "the native record lost its usable basis time")
    case.assertEqual(hit.access_class, "offline", "fixture discovery claims live provenance")
    case.assertEqual(target.access_class, "K3" if native_platform == "reddit" else "offline")
