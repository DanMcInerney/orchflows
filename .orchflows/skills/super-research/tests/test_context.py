"""Tracer suite: the K4 hybrid path, linked and never merged.

Every test here runs offline. No test reaches the network, and importing
``super_research`` performs no I/O of any kind.
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

from super_research import adapters, normalize, project, router, runner, schema, transport
from super_research.adapters import fake, reddit_archive, web_search


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "tracer"
FROZEN_OBSERVED_AT = "2026-08-10T09:00:00Z"

REDDIT_THREAD_LOCATOR = (
    "https://www.reddit.com/r/LocalLLaMA/comments/1abc234/"
    "what_is_the_best_local_model_right_now/"
)
X_POST_LOCATOR = "https://x.com/simonw/status/1799990000000000001"

# Spelled here rather than imported, so the spelling is pinned from outside the
# module that owns it — the same way `test_router` holds `third_party_archive`.
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
    "schema_version": 2,
    "manifest_id": "tracer-k4-x",
    "mode": "staged",
    "as_of": "2026-08-10T00:00:00Z",
    "steps": [
        {
            "step_id": "s1-discover",
            "kind": "discovery",
            "adapter_id": "web_search",
            "query": "site:x.com local model benchmark",
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
        web_search,
        adapters.AdapterRequest(step_id="s1-discover", query="best local model"),
        "ddg_html_results.html",
        "text/html",
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
        "ddg_html": (200, read_fixture("ddg_html_results.html"), "text/html"),
        "arctic_shift_posts_ids": (
            200,
            read_fixture("arctic_shift_posts_ids.json"),
            "application/json",
        ),
        "fake_offline": (200, read_fixture("fake_x_native_page.json"), "application/json"),
    }


def run_tracer(payload):
    """Run one tracer manifest end to end over the offline fixtures."""

    carrier, opener = tracer_transport(tracer_responses())
    artifact = runner.run_acquisition(schema.parse_manifest(payload), carrier)
    return artifact, carrier, opener


def load_wrong_artifact(case_name):
    """Build one deliberately wrong artifact from the fixture beside the tree.

    Nothing in the package produces these. They exist so the K4 hybrid
    oracle can be shown to fail when the claim it stands for is false.
    """

    fixture = json.loads(read_fixture("wrong_merged_artifacts.json"))
    defaults = fixture["record_defaults"]
    case = fixture["cases"][case_name]
    records = []
    for row in case["records"]:
        fields = dict(defaults)
        fields.update(row)
        fields["engagement"] = tuple(
            schema.EngagementSnapshot(name, value, observed_at)
            for name, value, observed_at in fields["engagement"]
        )
        fields["loss"] = tuple(fields["loss"])
        records.append(schema.AcquisitionRecord(**fields))
    return schema.AcquisitionArtifact(
        artifact_id="artifact:wrong",
        manifest_id="wrong",
        mode="staged",
        as_of="2026-08-10T00:00:00Z",
        records=tuple(records),
        steps=(),
        edges=tuple(schema.ProvenanceEdge(**edge) for edge in case["edges"]),
        groups=tuple(
            schema.RecordGroup(
                key_kind=group["key_kind"],
                key=tuple(group["key"]),
                member_record_ids=tuple(group["member_record_ids"]),
            )
            for group in case["groups"]
        ),
    )


def sample_record(**overrides):
    """Build one record beside the tree, from the wrong-result fixture's defaults."""

    fields = dict(json.loads(read_fixture("wrong_merged_artifacts.json"))["record_defaults"])
    fields.update(overrides)
    fields["engagement"] = tuple(
        schema.EngagementSnapshot(name, value, observed_at)
        for name, value, observed_at in fields["engagement"]
    )
    fields["loss"] = tuple(fields["loss"])
    return schema.AcquisitionRecord(**fields)


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
    case.assertNotEqual(
        hit.access_class, target.access_class, "the pair collapsed onto one access class"
    )


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

    def test_an_as_of_the_ordering_cannot_parse_is_refused_at_the_manifest(self):
        # `schema.py` says validation is total, and `as_of` was checked only for
        # being a nonempty string. `ordering.instant_seconds` returns nothing
        # for any other spelling, so `2026-08-10T09:00:00+00:00` left the
        # horizon unset, made every snapshot eligible, and stopped the replay
        # being frozen without saying anything.
        for spelling in (
            "2026-08-10T09:00:00+00:00",
            "2026-08-10 09:00:00Z",
            "2026-08-10",
            "yesterday",
        ):
            with self.subTest(as_of=spelling):
                with self.assertRaises(schema.ManifestError) as caught:
                    schema.parse_manifest(dict(TRACER_MANIFEST, as_of=spelling))

                self.assertIn(spelling, str(caught.exception))

        parsed = schema.parse_manifest(TRACER_MANIFEST)
        self.assertIsNotNone(runner.instant_seconds(parsed.as_of))

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

    def test_non_success_status_is_typed_and_never_a_silent_empty(self):
        carrier, _ = tracer_transport({"ddg_html": (503, "<html>Service Unavailable</html>", "text/html")})

        page = web_search.fetch_native_page(carrier, self.request)

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.records, ())
        self.assertIn("http_status", page.loss)
        self.assertIn("503", " ".join(page.warnings))

    def test_two_nav_forms_leave_the_last_offset_and_nobody_spends_it(self):
        # A paginated page carries an `s` input in the "< Previous" form and
        # another in "Next", and this parser takes the last. Whether the last
        # is the forward one is not in the evidence — page one, which is what
        # The 2026-08-10 probes recorded, has only the forward form. Recorded here
        # rather than guarded, because nothing reads the value:
        # `runner.planned_calls` sets no cursor, which
        # `NothingOverlapsAndNothingPagesTest` pins.
        backwards = self.html.replace(
            '<div class="nav-link">',
            '<div class="nav-link"><form action="/html/" method="post">'
            '<input type="hidden" name="s" value="0" /></form></div>'
            '<div class="nav-link">',
            1,
        )
        carrier, _ = tracer_transport({"ddg_html": (200, backwards, "text/html")})

        page = web_search.fetch_native_page(carrier, self.request)

        self.assertEqual(page.cursor_out, "30")
        self.assertEqual(backwards.count('name="s"'), 2)

    def test_a_parsed_page_with_no_results_is_empty_not_failed(self):
        carrier, _ = tracer_transport(
            {"ddg_html": (200, "<html><body><div class='results'></div></body></html>", "text/html")}
        )

        page = web_search.fetch_native_page(carrier, self.request)

        self.assertEqual(page.outcome, "empty")
        self.assertEqual(page.records, ())
        self.assertNotIn("http_status", page.loss)


class RedditArchiveHydrationTest(unittest.TestCase):
    """The K3 hydration adapter: the archive's own fields, labelled as the archive."""

    def setUp(self):
        self.payload = read_fixture("arctic_shift_posts_ids.json")
        self.request = adapters.AdapterRequest(step_id="s2-hydrate", target_ids=("1abc234",))

    def _page(self, response):
        carrier, opener = tracer_transport({"arctic_shift_posts_ids": response})
        return reddit_archive.fetch_native_page(carrier, self.request), carrier, opener

    def test_arctic_shift_post_yields_one_native_page_with_platform_engagement(self):
        page, carrier, opener = self._page((200, self.payload, "application/json"))

        self.assertEqual(page.adapter_id, "reddit_archive")
        self.assertEqual(page.representation_kind, "native")
        self.assertEqual(page.platform, "reddit")
        self.assertEqual(page.outcome, "ok")
        self.assertEqual(len(page.records), 1)
        self.assertEqual(len(opener.opened), 1)
        self.assertEqual([call.route_id for call in carrier.calls], ["arctic_shift_posts_ids"])

        post = page.records[0]
        self.assertEqual(post.canonical_content_kind, "post")
        self.assertEqual(post.canonical_locator, REDDIT_THREAD_LOCATOR)
        self.assertEqual(post.title, "What is the best local model right now?")
        self.assertIn("prompt-processing time", post.body)
        self.assertEqual(post.author, "vram_hoarder")
        self.assertEqual(post.community, "LocalLLaMA")
        self.assertEqual(post.published_at, "2026-08-09T13:20:00Z")
        self.assertEqual(dict(post.engagement), {"score": 120, "num_comments": 88})

    def test_reddit_native_identity_carries_the_fullname_prefix(self):
        page, _, _ = self._page((200, self.payload, "application/json"))

        self.assertEqual(page.records[0].native_item_id, "t3_1abc234")

    def test_third_party_archive_records_name_their_operator(self):
        page, _, _ = self._page((200, self.payload, "application/json"))

        self.assertEqual(page.operator_identity, "arctic-shift")
        self.assertEqual(page.access_class, "K3")
        self.assertIn("third_party_archive", page.records[0].loss)

    def test_malformed_json_is_typed_and_never_a_silent_empty(self):
        page, _, opener = self._page((200, "{not json", "application/json"))

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.records, ())
        self.assertIn("malformed_json", page.loss)
        self.assertEqual(len(opener.opened), 1)

    def test_non_success_status_is_typed_and_never_retried(self):
        page, _, opener = self._page((502, "bad gateway", "text/plain"))

        self.assertEqual(page.outcome, "failed")
        self.assertIn("http_status", page.loss)
        self.assertEqual(len(opener.opened), 1)

    def test_a_submission_the_archive_named_no_id_for_carries_no_identity(self):
        # wrong_merge_law rule 1: the prefix alone is not an identity. Two
        # submissions the archive answered without an `id` would otherwise both
        # be `t3_`, present one strong identity, and be folded into one group —
        # a merge of two distinct threads on a key neither of them has.
        payload = json.dumps(
            {
                "data": [
                    {"title": "first", "permalink": "/r/a/comments/x1/first/"},
                    {"title": "second", "permalink": "/r/a/comments/x2/second/"},
                ]
            }
        )
        page, _, _ = self._page((200, payload, "application/json"))

        self.assertEqual([record.native_item_id for record in page.records], ["", ""])
        for record in page.records:
            self.assertIn("field_omitted", record.loss)
            self.assertIn("third_party_archive", record.loss)

        step = schema.AcquisitionStep(
            step_id="s2-hydrate", kind="discovery", adapter_id="reddit_archive", max_items=8
        )
        records = normalize.normalize_page(page, step, "artifact:x", "x")
        for record in records:
            self.assertIsNone(normalize.strong_identity(record))
        self.assertEqual(len(normalize.group_records(records)), 2)


class AdapterCallBoundaryTest(unittest.TestCase):
    """Completion criterion 3, for every adapter the tracer crosses.

    One call, one page, one route: no pagination, no retry, no fallback, no
    cross-adapter call, no persistence.
    """

    def _seeded(self, module, fixture, content_type):
        return tracer_transport(
            {module.DESCRIPTOR.route_id: (200, read_fixture(fixture), content_type)}
        )

    def test_one_call_yields_one_page_over_the_adapters_own_route_only(self):
        for module, request, fixture, content_type in ADAPTER_CALLS:
            with self.subTest(adapter=module.DESCRIPTOR.adapter_id):
                carrier, opener = self._seeded(module, fixture, content_type)

                page = module.fetch_native_page(carrier, request)

                self.assertEqual(len(opener.opened), 1)
                self.assertEqual(
                    {call.route_id for call in carrier.calls}, {module.DESCRIPTOR.route_id}
                )
                self.assertEqual(page.route_id, module.DESCRIPTOR.route_id)
                self.assertTrue(page.records)

    def test_a_raising_transport_is_never_retried(self):
        for module, request, _, _ in ADAPTER_CALLS:
            with self.subTest(adapter=module.DESCRIPTOR.adapter_id):
                carrier, opener = tracer_transport(
                    {module.DESCRIPTOR.route_id: transport.TransportError("connection reset")}
                )

                with self.assertRaises(transport.TransportError):
                    module.fetch_native_page(carrier, request)

                self.assertEqual(len(opener.opened), 1)
                self.assertEqual(len(carrier.calls), 1)

    def test_no_adapter_touches_the_filesystem_or_a_socket(self):
        for module, request, fixture, content_type in ADAPTER_CALLS:
            with self.subTest(adapter=module.DESCRIPTOR.adapter_id):
                carrier, _ = self._seeded(module, fixture, content_type)

                with forbid_io():
                    page = module.fetch_native_page(carrier, request)

                self.assertTrue(page.records)


class FakeAdapterTest(unittest.TestCase):
    """The offline adapter stands in for a route that does not exist yet."""

    def test_fixture_page_declares_the_platform_it_stands_in_for(self):
        carrier, opener = tracer_transport(
            {"fake_offline": (200, read_fixture("fake_x_native_page.json"), "application/json")}
        )

        page = fake.fetch_native_page(
            carrier, adapters.AdapterRequest(step_id="s2-hydrate", target_ids=("x_native_page",))
        )

        self.assertEqual(page.adapter_id, "fake")
        self.assertEqual(page.platform, "x")
        self.assertEqual(page.native_identity_namespace, "x")
        self.assertEqual(page.representation_kind, "native")
        self.assertEqual(len(page.records), 2)
        self.assertEqual(len(opener.opened), 1)

        post, reply = page.records
        self.assertEqual(post.canonical_content_kind, "post")
        self.assertEqual(post.canonical_locator, X_POST_LOCATOR)
        self.assertEqual(dict(post.engagement)["favorite_count"], 412)
        self.assertEqual(reply.canonical_content_kind, "reply")
        self.assertEqual(reply.native_parent_id, post.native_item_id)


class AdapterDeclarationTest(unittest.TestCase):
    """A live adapter's page always agrees with the descriptor it ships."""

    def test_live_pages_agree_with_their_static_descriptor(self):
        carrier, _ = tracer_transport(
            {
                "ddg_html": (200, read_fixture("ddg_html_results.html"), "text/html"),
                "arctic_shift_posts_ids": (
                    200,
                    read_fixture("arctic_shift_posts_ids.json"),
                    "application/json",
                ),
            }
        )
        pages = (
            web_search.fetch_native_page(
                carrier, adapters.AdapterRequest(step_id="s1-discover", query="q")
            ),
            reddit_archive.fetch_native_page(
                carrier, adapters.AdapterRequest(step_id="s2-hydrate", target_ids=("1abc234",))
            ),
        )
        descriptors = (web_search.DESCRIPTOR, reddit_archive.DESCRIPTOR)

        for page, descriptor in zip(pages, descriptors):
            self.assertEqual(page.adapter_id, descriptor.adapter_id)
            self.assertEqual(page.route_id, descriptor.route_id)
            self.assertEqual(page.access_class, descriptor.access_class)
            self.assertEqual(page.platform, descriptor.platform)
            self.assertEqual(page.representation_kind, descriptor.representation_kind)
            self.assertEqual(
                page.native_identity_namespace, descriptor.native_identity_namespace
            )

    def test_discovery_and_hydration_declare_different_representations(self):
        self.assertEqual(web_search.DESCRIPTOR.representation_kind, "index")
        self.assertEqual(reddit_archive.DESCRIPTOR.representation_kind, "native")


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


class RouterTest(unittest.TestCase):
    """The router decides from per-route booleans and nothing else."""

    def setUp(self):
        self.step = schema.parse_manifest(TRACER_MANIFEST).steps[0]

    def test_an_admitted_route_is_selected(self):
        decision = router.select_route(self.step, web_search.DESCRIPTOR, {"ddg_html": True})

        self.assertTrue(decision.admitted)
        self.assertEqual(decision.route_id, "ddg_html")
        self.assertEqual(decision.access_class, "K4")
        self.assertEqual(decision.refusal_reason, "")

    def test_the_same_route_turned_off_is_refused_as_auth_required(self):
        decision = router.select_route(self.step, web_search.DESCRIPTOR, {"ddg_html": False})

        self.assertFalse(decision.admitted)
        self.assertEqual(decision.refusal_reason, "auth_required")

    def test_a_route_absent_from_the_admissions_map_is_refused_as_no_route(self):
        decision = router.select_route(self.step, web_search.DESCRIPTOR, {})

        self.assertFalse(decision.admitted)
        self.assertEqual(decision.refusal_reason, "no_route")

    def test_a_descriptor_for_another_adapter_is_refused_as_no_route(self):
        decision = router.select_route(
            self.step, reddit_archive.DESCRIPTOR, {"arctic_shift_posts_ids": True}
        )

        self.assertFalse(decision.admitted)
        self.assertEqual(decision.refusal_reason, "no_route")


class OutcomeReductionTest(unittest.TestCase):
    """Batch reduction is exact; a usable record never hides a failure."""

    def test_every_reduction_branch(self):
        self.assertEqual(schema.reduce_outcomes(("empty", "empty")), "empty")
        self.assertEqual(schema.reduce_outcomes(("ok", "empty")), "ok")
        self.assertEqual(schema.reduce_outcomes(("ok", "partial")), "partial")
        self.assertEqual(schema.reduce_outcomes(("ok", "failed")), "partial")
        self.assertEqual(schema.reduce_outcomes(("failed", "refused")), "failed")
        self.assertEqual(schema.reduce_outcomes(("refused", "refused")), "refused")
        self.assertEqual(schema.reduce_outcomes(()), "empty")


class NormalizeTest(unittest.TestCase):
    """Normalization derives artifact fields without inventing any."""

    def test_engagement_refuses_a_boolean_value(self):
        with self.assertRaises(normalize.NormalizeError):
            normalize.engagement_snapshots((("score", True),), FROZEN_OBSERVED_AT)

    def test_engagement_refuses_a_negative_value(self):
        with self.assertRaises(normalize.NormalizeError):
            normalize.engagement_snapshots((("score", -1),), FROZEN_OBSERVED_AT)

    def test_locator_normalization_is_stable_across_case_and_trailing_slash(self):
        self.assertEqual(
            normalize.normalized_locator("HTTPS://Www.Reddit.com/r/LocalLLaMA/comments/1abc234/"),
            normalize.normalized_locator("https://www.reddit.com/r/LocalLLaMA/comments/1abc234"),
        )

    def test_content_hash_is_empty_when_there_is_no_content(self):
        self.assertEqual(normalize.content_hash(""), "")
        self.assertNotEqual(normalize.content_hash("a snippet"), "")


class StagedRunTest(unittest.TestCase):
    """The core owns the run: route selection, caps, page count, and stop."""

    def test_staged_run_produces_discovery_and_hydration_records(self):
        artifact, carrier, _ = run_tracer(TRACER_MANIFEST)

        self.assertEqual(artifact.manifest_id, "tracer-k4-reddit")
        self.assertEqual(artifact.mode, "staged")
        self.assertEqual(artifact.outcome, "ok")
        self.assertEqual([step.step_id for step in artifact.steps], ["s1-discover", "s2-hydrate"])
        self.assertEqual([step.outcome for step in artifact.steps], ["ok", "ok"])
        self.assertEqual([step.pages for step in artifact.steps], [1, 1])
        self.assertEqual(len(carrier.calls), 2)

        discovered = [record for record in artifact.records if record.step_id == "s1-discover"]
        hydrated = [record for record in artifact.records if record.step_id == "s2-hydrate"]
        self.assertEqual(len(discovered), 6)
        self.assertEqual(len(hydrated), 1)

        self.assertEqual(discovered[0].representation_kind, "index")
        self.assertEqual(discovered[0].time_confidence, "unknown")
        self.assertEqual(discovered[0].usable_basis_time, "")
        self.assertEqual(discovered[0].group_scope, "duckduckgo")
        self.assertEqual(discovered[0].observed_at, FROZEN_OBSERVED_AT)
        self.assertEqual(discovered[0].record_id, "s1-discover#0.0")
        self.assertEqual(discovered[0].adapter_version, "1")

        self.assertEqual(hydrated[0].representation_kind, "native")
        self.assertEqual(hydrated[0].native_item_id, "t3_1abc234")
        self.assertEqual(hydrated[0].time_confidence, "reported")
        self.assertEqual(hydrated[0].usable_basis_time, "2026-08-09T13:20:00Z")
        self.assertEqual(hydrated[0].group_scope, "reddit")
        self.assertEqual(hydrated[0].operator_identity, "arctic-shift")
        self.assertEqual(
            [(snapshot.metric_name, snapshot.value) for snapshot in hydrated[0].engagement],
            [("score", 120), ("num_comments", 88)],
        )
        self.assertEqual(
            hydrated[0].discovery_locator, normalize.normalized_locator(REDDIT_THREAD_LOCATOR)
        )

    def test_a_step_cap_truncates_and_emits_recall_window_partial(self):
        steps = [dict(TRACER_MANIFEST["steps"][0], max_items=2), TRACER_MANIFEST["steps"][1]]
        artifact, _, _ = run_tracer(dict(TRACER_MANIFEST, steps=steps))

        discovery = artifact.steps[0]
        self.assertEqual(discovery.records_received, 6)
        self.assertEqual(discovery.records_kept, 2)
        self.assertEqual(discovery.outcome, "partial")
        self.assertIn("recall_window_partial", discovery.loss)
        self.assertEqual(artifact.outcome, "partial")
        self.assertEqual(
            len([record for record in artifact.records if record.step_id == "s1-discover"]), 2
        )

    def test_an_unimplemented_adapter_is_refused_before_any_transport_call(self):
        steps = [dict(TRACER_MANIFEST["steps"][0], adapter_id="reddit_oauth")]
        artifact, carrier, _ = run_tracer(dict(TRACER_MANIFEST, steps=steps))

        self.assertEqual(artifact.steps[0].outcome, "refused")
        self.assertIn("no_route", artifact.steps[0].loss)
        self.assertEqual(artifact.records, ())
        self.assertEqual(carrier.calls, [])
        self.assertEqual(artifact.outcome, "refused")

    def test_the_x_shaped_manifest_runs_through_the_offline_adapter(self):
        artifact, carrier, _ = run_tracer(TRACER_X_MANIFEST)

        hydrated = [record for record in artifact.records if record.step_id == "s2-hydrate-x"]
        self.assertEqual(len(hydrated), 2)
        self.assertEqual(hydrated[0].platform, "x")
        self.assertEqual(hydrated[0].representation_kind, "native")
        self.assertEqual(hydrated[0].time_confidence, "authoritative")
        self.assertEqual(hydrated[1].canonical_content_kind, "reply")
        self.assertEqual(hydrated[1].native_parent_id, "1799990000000000001")
        self.assertEqual(len(carrier.calls), 2)


class K4HybridNeverMergesTest(unittest.TestCase):
    """Completion criterion 1: the pair stays two linked records, in both shapes."""

    def test_reddit_pair_is_linked_and_never_merged(self):
        artifact, _, _ = run_tracer(TRACER_MANIFEST)

        assert_linked_never_merged(self, artifact, REDDIT_THREAD_LOCATOR, "reddit")

    def test_x_pair_is_linked_and_never_merged(self):
        artifact, _, _ = run_tracer(TRACER_X_MANIFEST)

        assert_linked_never_merged(self, artifact, X_POST_LOCATOR, "x")

    def test_a_root_relative_redirect_wrapper_still_yields_the_target_locator(self):
        # The wrapper arrives in three shapes and `unwrap_result_url` unwrapped
        # only the two that name a host, so `/l/?uddg=` was published unchanged
        # as the canonical locator. `normalized_locator` keeps a host-less
        # string host-less, `link_discovery_hydration` matches exactly, and the
        # edge this criterion is about silently never forms — as an absence, so
        # no merge test would have caught it, on the one route it protects.
        rewritten = read_fixture("ddg_html_results.html").replace(
            'href="//duckduckgo.com/l/?uddg=', 'href="/l/?uddg='
        )
        self.assertIn('href="/l/?uddg=', rewritten)
        responses = dict(tracer_responses(), ddg_html=(200, rewritten, "text/html"))
        carrier, _ = tracer_transport(responses)

        artifact = runner.run_acquisition(schema.parse_manifest(TRACER_MANIFEST), carrier)

        assert_linked_never_merged(self, artifact, REDDIT_THREAD_LOCATOR, "reddit")

    def test_hydration_happens_even_though_a_hit_already_names_that_locator(self):
        artifact, carrier, _ = run_tracer(TRACER_MANIFEST)

        # wrong_merge_law rule 2: locator equality never authorizes reuse in
        # place of hydration, and the discovery edge is still emitted.
        self.assertEqual(
            [call.route_id for call in carrier.calls], ["ddg_html", "arctic_shift_posts_ids"]
        )
        self.assertEqual(len(artifact.edges), 1)

    def test_a_selection_that_matches_no_hit_produces_no_invented_edge(self):
        hit = {"discovery_locator": "https://www.reddit.com/r/other/comments/zzz/", "target_id": "zzz"}
        steps = [
            TRACER_MANIFEST["steps"][0],
            dict(TRACER_MANIFEST["steps"][1], selected_hits=[hit]),
        ]
        artifact, _, _ = run_tracer(dict(TRACER_MANIFEST, steps=steps))

        self.assertTrue(
            [record for record in artifact.records if record.step_id == "s2-hydrate"]
        )
        self.assertEqual(artifact.edges, ())


def gap_carriers(artifact):
    """Every record in one artifact that says its discovery went unrecorded."""

    return [
        record.record_id
        for record in artifact.records
        if DISCOVERY_NOT_RECORDED in record.loss
    ]


class LineageGapIsTypedTest(unittest.TestCase):
    """The absence beside `test_a_selection_that_matches_no_hit_produces_no_invented_edge`.

    That test pins the right half of the call: an unmatched selection invents no
    edge. This class pins the other half — the gap is *said*, because a caller
    learns of it by counting edges otherwise, and a caller that does not count
    never learns of it at all.

    The rule has a second clause, and the last two tests here are what make it
    more than a preference. Only a run that itself discovered may report a
    hydration unaccounted for. The same hydration step, against the same frozen
    locator, carries the code when this run's discovery did not produce the hit
    and stays silent when this run performed no discovery at all — because a
    `staged` hydration dispatch missed nothing: its discovery is in the artifact
    the caller froze the selection from. Stamping it there would be a false
    claim on the ordinary staged path, which is the whole reason this rule is
    written the way it is.
    """

    def test_a_selection_that_matches_no_hit_says_so_by_type(self):
        hit = {
            "discovery_locator": "https://www.reddit.com/r/other/comments/zzz/",
            "target_id": "zzz",
        }
        steps = [
            TRACER_MANIFEST["steps"][0],
            dict(TRACER_MANIFEST["steps"][1], selected_hits=[hit]),
        ]
        artifact, _, _ = run_tracer(dict(TRACER_MANIFEST, steps=steps))

        hydrated = [r for r in artifact.records if r.step_id == "s2-hydrate"]
        self.assertTrue(hydrated)
        self.assertEqual(artifact.edges, ())
        # On the record that has the gap, and on no other: the discovery hits
        # are what the hydration failed to match, not things that failed.
        self.assertEqual(gap_carriers(artifact), [r.record_id for r in hydrated])
        for record in hydrated:
            self.assertEqual(record.loss[-1], DISCOVERY_NOT_RECORDED)

    def test_a_hydration_that_matches_its_hit_says_nothing(self):
        # The type says something, so it has to be absent when that thing is
        # false. This is the same manifest as the linked-pair tests above, whose
        # one edge is exactly what makes the silence meaningful.
        artifact, _, _ = run_tracer(TRACER_MANIFEST)

        self.assertEqual(len(artifact.edges), 1)
        self.assertEqual(gap_carriers(artifact), [])

    def test_a_run_that_hydrates_nothing_says_nothing(self):
        artifact, _, _ = run_tracer(dict(TRACER_MANIFEST, steps=[TRACER_MANIFEST["steps"][0]]))

        self.assertTrue(artifact.records)
        self.assertEqual(gap_carriers(artifact), [])

    def test_a_staged_hydration_dispatch_reports_no_gap_it_could_not_have_closed(self):
        # The staged pair: discovery is one dispatch, hydration is another, and
        # the caller carries the selection between them. The second artifact
        # holds a hydration and no discovery, so it links nothing — and that is
        # `staged` working, not a gap. Compare with the first test in this
        # class: same step, same frozen locator, opposite verdict, and the only
        # difference is whether this run discovered.
        discovery = dict(TRACER_MANIFEST, steps=[TRACER_MANIFEST["steps"][0]])
        hydration = dict(
            TRACER_MANIFEST,
            manifest_id="tracer-k4-reddit-hydrate",
            steps=[dict(TRACER_MANIFEST["steps"][1], prior_step_id="")],
        )
        first, _, _ = run_tracer(discovery)
        second, _, _ = run_tracer(hydration)

        # The caller could not have frozen a selection it never discovered.
        self.assertIn(
            normalize.normalized_locator(REDDIT_THREAD_LOCATOR),
            [record.normalized_locator for record in first.records],
        )
        self.assertTrue([r for r in second.records if r.discovery_locator])
        self.assertEqual(second.edges, ())
        self.assertEqual(gap_carriers(second), [])
        self.assertEqual(gap_carriers(first), [])


class WrongMergeLawTest(unittest.TestCase):
    """Completion criterion 2: rules 1-8 over the tracer's own records."""

    def setUp(self):
        self.artifact, _, _ = run_tracer(TRACER_MANIFEST)
        self.x_artifact, _, _ = run_tracer(TRACER_X_MANIFEST)
        self.by_id = {record.record_id: record for record in self.artifact.records}

    def _group_of(self, artifact, record_id):
        for group in artifact.groups:
            if record_id in group.member_record_ids:
                return group
        raise AssertionError("record {0} belongs to no group".format(record_id))

    def test_rule_1_strong_identity_is_the_retained_triple(self):
        target = [r for r in self.artifact.records if r.representation_kind == "native"][0]

        self.assertEqual(
            normalize.strong_identity(target), ("reddit", "t3_1abc234", "post")
        )
        self.assertIsNone(normalize.strong_identity(self.by_id["s1-discover#0.0"]))

    def test_rule_1_grouping_holds_duplicates_side_by_side_without_overwriting(self):
        group = self._group_of(self.artifact, "s1-discover#0.2")

        self.assertEqual(group.member_record_ids, ("s1-discover#0.2", "s1-discover#0.3"))
        first = self.by_id["s1-discover#0.2"]
        second = self.by_id["s1-discover#0.3"]
        self.assertEqual(first.exact_content_hash, second.exact_content_hash)
        self.assertNotEqual(first.record_id, second.record_id)
        self.assertNotEqual(first.list_index, second.list_index)

    def test_rule_3_weak_key_needs_every_component(self):
        grouped = self.by_id["s1-discover#0.2"]
        snippetless = self.by_id["s1-discover#0.5"]

        self.assertEqual(len(normalize.weak_group_key(grouped)), 5)
        self.assertEqual(
            normalize.weak_group_key(grouped),
            (
                "duckduckgo",
                "index",
                grouped.normalized_locator,
                "web_hit",
                grouped.exact_content_hash,
            ),
        )
        self.assertEqual(snippetless.exact_content_hash, "")
        self.assertIsNone(normalize.weak_group_key(snippetless))
        self.assertEqual(
            self._group_of(self.artifact, snippetless.record_id).key_kind, "ungrouped"
        )

    def test_rule_4_a_reply_never_joins_its_parent_post(self):
        post = self.x_artifact.records[-2]
        reply = self.x_artifact.records[-1]

        self.assertEqual(reply.native_parent_id, post.native_item_id)
        self.assertNotIn(
            reply.record_id, self._group_of(self.x_artifact, post.record_id).member_record_ids
        )

    def test_rule_5_changed_content_at_one_locator_is_a_distinct_observation(self):
        duplicate = self.by_id["s1-discover#0.3"]
        rewritten = self.by_id["s1-discover#0.4"]

        self.assertEqual(duplicate.normalized_locator, rewritten.normalized_locator)
        self.assertNotEqual(duplicate.exact_content_hash, rewritten.exact_content_hash)
        self.assertNotIn(
            rewritten.record_id,
            self._group_of(self.artifact, duplicate.record_id).member_record_ids,
        )

    def test_rule_6_reddit_platform_identity_includes_the_fullname_prefix(self):
        target = [r for r in self.artifact.records if r.representation_kind == "native"][0]

        self.assertEqual(target.native_item_id, "t3_1abc234")
        self.assertEqual(target.native_identity_namespace, "reddit")

    def test_rule_7_no_group_spans_two_representation_kinds(self):
        for artifact in (self.artifact, self.x_artifact):
            by_id = {record.record_id: record for record in artifact.records}
            for group in artifact.groups:
                kinds = {by_id[member].representation_kind for member in group.member_record_ids}
                self.assertEqual(len(kinds), 1, "group {0} spans {1}".format(group.key, kinds))

    def test_rule_7_partitions_grouping_even_under_one_shared_strong_identity(self):
        # Built beside the tree: an index hit that wrongly claims the target's
        # own native identity. Rule 7 must still keep the two apart.
        hit = sample_record(
            record_id="hand#0.0",
            representation_kind="index",
            native_identity_namespace="reddit",
            native_item_id="t3_1abc234",
            canonical_content_kind="post",
        )
        target = sample_record(
            record_id="hand#1.0",
            representation_kind="native",
            native_identity_namespace="reddit",
            native_item_id="t3_1abc234",
            canonical_content_kind="post",
        )

        self.assertEqual(normalize.strong_identity(hit), normalize.strong_identity(target))
        groups = normalize.group_records((hit, target))
        self.assertEqual(len(groups), 2)
        for group in groups:
            self.assertEqual(len(group.member_record_ids), 1)

    def test_rule_8_a_raw_cap_counts_every_received_record(self):
        steps = [dict(TRACER_MANIFEST["steps"][0], max_items=2), TRACER_MANIFEST["steps"][1]]
        capped, _, _ = run_tracer(dict(TRACER_MANIFEST, steps=steps))

        self.assertEqual(capped.steps[0].records_received, 6)
        self.assertEqual(capped.steps[0].records_kept, 2)
        self.assertIn("recall_window_partial", capped.loss)


class ProjectionTest(unittest.TestCase):
    """Completion criterion 2, projection half: pure, bounded, zero I/O."""

    def setUp(self):
        self.artifact, _, _ = run_tracer(TRACER_MANIFEST)
        self.pair = (
            [r for r in self.artifact.records if r.representation_kind == "index"][0].record_id,
            [r for r in self.artifact.records if r.representation_kind == "native"][0].record_id,
        )

    def _manifest(self, record_ids, max_records=8, artifact_id=None):
        return project.ProjectionManifest(
            projection_id="proj-1",
            source_artifact_id=(
                self.artifact.artifact_id if artifact_id is None else artifact_id
            ),
            record_ids=tuple(record_ids),
            max_records=max_records,
        )

    def test_projection_keeps_both_records_and_their_edge(self):
        projected = project.project_context(self._manifest(self.pair), self.artifact)

        self.assertEqual(
            [record.record_id for record in projected.records], list(self.pair)
        )
        self.assertEqual(len(projected.edges), 1)
        self.assertEqual(projected.source_artifact_id, self.artifact.artifact_id)

    def test_projecting_only_the_hydrated_record_keeps_its_lineage(self):
        projected = project.project_context(self._manifest(self.pair[1:]), self.artifact)

        self.assertEqual([record.record_id for record in projected.records], [self.pair[1]])
        self.assertEqual(projected.edges[0].from_record_id, self.pair[0])

    def test_a_foreign_source_artifact_is_refused(self):
        with self.assertRaises(project.ProjectionError):
            project.project_context(
                self._manifest(self.pair, artifact_id="artifact:somewhere-else"), self.artifact
            )

    def test_an_unknown_record_id_is_refused_rather_than_dropped(self):
        with self.assertRaises(project.ProjectionError):
            project.project_context(self._manifest(("s9-nope#0.0",)), self.artifact)

    def test_a_selection_larger_than_the_cap_is_refused(self):
        with self.assertRaises(project.ProjectionError):
            project.project_context(self._manifest(self.pair, max_records=1), self.artifact)

    def test_projection_performs_no_io_at_all(self):
        manifest = self._manifest(self.pair)

        with forbid_io():
            projected = project.project_context(manifest, self.artifact)

        self.assertEqual(len(projected.records), 2)


class OracleCanFailTest(unittest.TestCase):
    """Completion criterion 4: the K4 hybrid oracle fails on a wrong result.

    Each artifact here is built beside the tree from
    ``fixtures/tracer/wrong_merged_artifacts.json``. Nothing under test is
    mutated to produce them.
    """

    def _assert_oracle_rejects(self, case_name, expected_reason):
        wrong = load_wrong_artifact(case_name)

        with self.assertRaises(AssertionError) as caught:
            assert_linked_never_merged(self, wrong, REDDIT_THREAD_LOCATOR, "reddit")

        self.assertIn(expected_reason, str(caught.exception))

    def test_a_merged_single_record_fails_the_oracle(self):
        self._assert_oracle_rejects(
            "merged_into_one_record", "expected exactly one index record for the pair"
        )

    def test_a_grouped_pair_fails_the_oracle(self):
        self._assert_oracle_rejects(
            "grouped_pair", "a group merged the index hit with its hydrated target"
        )

    def test_folded_engagement_fails_the_oracle(self):
        self._assert_oracle_rejects(
            "folded_engagement", "the index hit was given native engagement"
        )

    def test_a_pair_with_no_provenance_edge_fails_the_oracle(self):
        self._assert_oracle_rejects(
            "unlinked_pair", "expected exactly one discovery_hydration edge"
        )

    def test_the_same_oracle_passes_on_the_real_tracer_result(self):
        artifact, _, _ = run_tracer(TRACER_MANIFEST)

        assert_linked_never_merged(self, artifact, REDDIT_THREAD_LOCATOR, "reddit")


if __name__ == "__main__":  # pragma: no cover - convenience runner
    unittest.main()
