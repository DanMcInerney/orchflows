"""Tracer suite: the K4 hybrid path, linked and never merged.

Every test here runs offline. No test reaches the network, and importing
``super_research`` performs no I/O of any kind.
"""

from __future__ import annotations

import builtins
import contextlib
import io
import os
import socket
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

from super_research import adapters, schema, transport
from super_research.adapters import web_search


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "tracer"
FROZEN_OBSERVED_AT = "2026-08-10T09:00:00Z"

REDDIT_THREAD_LOCATOR = (
    "https://www.reddit.com/r/LocalLLaMA/comments/1abc234/"
    "what_is_the_best_local_model_right_now/"
)
X_POST_LOCATOR = "https://x.com/simonw/status/1799990000000000001"


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


def tracer_transport(responses):
    opener = RecordingOpener(responses)
    return transport.Transport(opener=opener, now=lambda: FROZEN_OBSERVED_AT), opener


@contextlib.contextmanager
def forbid_io():
    """Make every filesystem and socket primitive raise for the guarded block."""

    def refuse(*args, **kwargs):
        raise AssertionError("I/O attempted inside a zero-I/O guard")

    with contextlib.ExitStack() as stack:
        stack.enter_context(mock.patch.object(builtins, "open", refuse))
        stack.enter_context(mock.patch.object(io, "open", refuse))
        stack.enter_context(mock.patch.object(os, "open", refuse))
        stack.enter_context(mock.patch.object(socket, "socket", refuse))
        stack.enter_context(mock.patch.object(urllib.request, "urlopen", refuse))
        yield


TRACER_MANIFEST = {
    "schema_version": 2,
    "manifest_id": "tracer-k4-reddit",
    "mode": "staged",
    "as_of": "2026-08-10T00:00:00Z",
    "steps": [
        {
            "step_id": "s1-discover",
            "kind": "discovery",
            "adapter_id": "web_search",
            "query": "site:reddit.com best local model",
            "max_items": 4,
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
            "max_items": 4,
        },
    ],
}


class ManifestSchemaTest(unittest.TestCase):
    """The schema seam: a manifest is validated before anything is fetched."""

    def test_staged_manifest_parses_into_ordered_discovery_and_hydration_steps(self):
        manifest = schema.parse_manifest(TRACER_MANIFEST)

        self.assertEqual(manifest.manifest_id, "tracer-k4-reddit")
        self.assertEqual(manifest.mode, "staged")
        self.assertEqual(manifest.as_of, "2026-08-10T00:00:00Z")
        self.assertEqual([step.step_id for step in manifest.steps], ["s1-discover", "s2-hydrate"])

        discovery, hydration = manifest.steps
        self.assertEqual(discovery.kind, "discovery")
        self.assertEqual(discovery.adapter_id, "web_search")
        self.assertEqual(discovery.query, "site:reddit.com best local model")
        self.assertEqual(discovery.selected_hits, ())

        self.assertEqual(hydration.kind, "hydration")
        self.assertEqual(hydration.adapter_id, "reddit_archive")
        self.assertEqual(hydration.prior_step_id, "s1-discover")
        self.assertEqual(len(hydration.selected_hits), 1)
        self.assertEqual(hydration.selected_hits[0].target_id, "1abc234")
        self.assertTrue(
            hydration.selected_hits[0].discovery_locator.startswith(
                "https://www.reddit.com/r/LocalLLaMA/comments/1abc234/"
            )
        )

    def test_unknown_mode_is_refused(self):
        payload = dict(TRACER_MANIFEST, mode="turbo")

        with self.assertRaises(schema.ManifestError) as caught:
            schema.parse_manifest(payload)

        self.assertIn("turbo", str(caught.exception))

    def test_unknown_step_field_is_refused(self):
        steps = [dict(TRACER_MANIFEST["steps"][0], follow_pagination=True)]
        payload = dict(TRACER_MANIFEST, steps=steps)

        with self.assertRaises(schema.ManifestError) as caught:
            schema.parse_manifest(payload)

        self.assertIn("follow_pagination", str(caught.exception))

    def test_hydration_step_without_selected_hits_is_refused(self):
        steps = [TRACER_MANIFEST["steps"][0], dict(TRACER_MANIFEST["steps"][1], selected_hits=[])]
        payload = dict(TRACER_MANIFEST, steps=steps)

        with self.assertRaises(schema.ManifestError) as caught:
            schema.parse_manifest(payload)

        self.assertIn("s2-hydrate", str(caught.exception))

    def test_discovery_step_carrying_selected_hits_is_refused(self):
        first = dict(
            TRACER_MANIFEST["steps"][0],
            selected_hits=[{"discovery_locator": "https://example.com/", "target_id": "x"}],
        )
        payload = dict(TRACER_MANIFEST, steps=[first, TRACER_MANIFEST["steps"][1]])

        with self.assertRaises(schema.ManifestError) as caught:
            schema.parse_manifest(payload)

        self.assertIn("s1-discover", str(caught.exception))


class WebSearchDiscoveryTest(unittest.TestCase):
    """The K4 discovery adapter: one page in, one NativePage out, nothing else."""

    def setUp(self):
        self.html = read_fixture("ddg_html_results.html")
        self.request = adapters.AdapterRequest(
            step_id="s1-discover", query="site:reddit.com best local model"
        )

    def test_ddg_html_yields_one_native_page_of_index_hits(self):
        carrier, opener = tracer_transport({"ddg_html": (200, self.html, "text/html")})

        page = web_search.fetch_native_page(carrier, self.request)

        self.assertEqual(page.adapter_id, "web_search")
        self.assertEqual(page.route_id, "ddg_html")
        self.assertEqual(page.outcome, "ok")
        self.assertEqual(len(page.records), 6)
        self.assertEqual(len(opener.opened), 1)
        self.assertEqual([call.route_id for call in carrier.calls], ["ddg_html"])

        first = page.records[0]
        self.assertEqual(first.canonical_content_kind, "web_hit")
        self.assertEqual(first.canonical_locator, REDDIT_THREAD_LOCATOR)
        self.assertEqual(first.title, "What is the best local model right now? : r/LocalLLaMA")
        self.assertIn("24GB of VRAM", first.body)
        self.assertEqual(first.native_position, 0)
        self.assertEqual(first.engagement, ())

        self.assertEqual(page.records[1].canonical_locator, X_POST_LOCATOR)

        snippetless = page.records[5]
        self.assertEqual(snippetless.canonical_locator, "https://example.net/empty")
        self.assertEqual(snippetless.body, "")
        self.assertIn("field_omitted", snippetless.loss)

    def test_index_hit_snippet_never_becomes_native_engagement(self):
        carrier, _ = tracer_transport({"ddg_html": (200, self.html, "text/html")})

        page = web_search.fetch_native_page(carrier, self.request)

        # The first snippet literally reads "120 votes, 88 comments"; a K4 index
        # hit reports it as prose and claims no native metric from it.
        self.assertEqual(page.records[0].engagement, ())
        self.assertIn("engagement_unavailable", page.records[0].loss)
        self.assertIn("target_not_hydrated", page.records[0].loss)

    def test_next_page_cursor_is_surfaced_but_never_followed(self):
        carrier, opener = tracer_transport({"ddg_html": (200, self.html, "text/html")})

        page = web_search.fetch_native_page(carrier, self.request)

        self.assertEqual(page.cursor_out, "30")
        self.assertEqual(len(opener.opened), 1)

    def test_transport_failure_is_not_retried(self):
        failure = transport.TransportError("connection reset")
        carrier, opener = tracer_transport({"ddg_html": failure})

        with self.assertRaises(transport.TransportError):
            web_search.fetch_native_page(carrier, self.request)

        self.assertEqual(len(opener.opened), 1)
        self.assertEqual(len(carrier.calls), 1)

    def test_discovery_performs_no_filesystem_or_socket_io(self):
        carrier, _ = tracer_transport({"ddg_html": (200, self.html, "text/html")})

        with forbid_io():
            page = web_search.fetch_native_page(carrier, self.request)

        self.assertEqual(len(page.records), 6)

    def test_non_success_status_is_typed_and_never_a_silent_empty(self):
        carrier, _ = tracer_transport({"ddg_html": (503, "<html>Service Unavailable</html>", "text/html")})

        page = web_search.fetch_native_page(carrier, self.request)

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.records, ())
        self.assertIn("http_status", page.loss)
        self.assertIn("503", " ".join(page.warnings))

    def test_a_parsed_page_with_no_results_is_empty_not_failed(self):
        carrier, _ = tracer_transport(
            {"ddg_html": (200, "<html><body><div class='results'></div></body></html>", "text/html")}
        )

        page = web_search.fetch_native_page(carrier, self.request)

        self.assertEqual(page.outcome, "empty")
        self.assertEqual(page.records, ())
        self.assertNotIn("http_status", page.loss)


class RouteConstantOwnershipTest(unittest.TestCase):
    """Route constants live in transport.py; callers see booleans, not hosts."""

    def test_every_declared_route_carries_its_origin_and_access_class(self):
        route = transport.ROUTE_CONSTANTS["ddg_html"]

        self.assertEqual(route.access_class, "K4")
        self.assertEqual(route.origin, "https://html.duckduckgo.com")

        built = transport.build_transport_request("ddg_html", {"q": "best local model"})
        self.assertTrue(built.url.startswith("https://html.duckduckgo.com/html/?"))
        self.assertIn("q=best+local+model", built.url)

    def test_route_admissions_are_booleans_only(self):
        admissions = transport.route_admissions()

        self.assertIn("ddg_html", admissions)
        self.assertTrue(all(value is True or value is False for value in admissions.values()))
        self.assertTrue(admissions["ddg_html"])

    def test_default_opener_refuses_a_non_https_url_without_touching_a_socket(self):
        offline = transport.TransportRequest(
            route_id="ddg_html", method="GET", url="http://html.duckduckgo.com/html/"
        )

        with forbid_io():
            with self.assertRaises(transport.TransportError):
                transport.urlopen_response(offline)


if __name__ == "__main__":  # pragma: no cover - convenience runner
    unittest.main()
