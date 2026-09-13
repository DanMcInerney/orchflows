"""Breaking route removals and retained source facts stay observable to callers."""
import json
import unittest
from unittest import mock

from acquire_fixture import fixture_plan
from acquire_plan import PlanError, validate
from super_research import transport
from super_research.adapters import AdapterError, AdapterRequest, reddit_archive, scholarly
from tests.test_scholarly import AX_ONE_ENTRY


class RetainedRouteContractTests(unittest.TestCase):
    def test_removed_adapters_are_rejected_before_acquisition(self):
        for adapter in ("x_guest", "youtube_innertube", "tiktok_public", "oembed", "public_page", "web_search"):
            plan = fixture_plan()
            plan["allowed_adapters"].append(adapter)
            with self.subTest(adapter=adapter), self.assertRaises(PlanError):
                validate(plan)

    def test_scholarly_requires_an_explicit_supported_index(self):
        carrier = mock.Mock()
        for query in ("topic", "openalex:topic", "crossref:", "arxiv:"):
            with self.subTest(query=query), self.assertRaises(AdapterError):
                scholarly.fetch_native_page(carrier, AdapterRequest(step_id="source", query=query))
        carrier.fetch.assert_not_called()

    def test_archive_outbound_link_and_capture_time_survive_without_changing_publication(self):
        payload = {"data": [{"id": "abc", "permalink": "/r/research/comments/abc/paper/",
            "created_utc": 1788955200, "url": "https://arxiv.org/abs/2609.01334v1",
            "retrieved_on": 1789041600, "score": 7, "num_comments": 2}]}
        carrier = transport.Transport(opener=lambda request: (200, json.dumps(payload), "application/json", request.url, ()))
        page = reddit_archive.fetch_native_page(carrier, AdapterRequest(step_id="archive", target_ids=("abc",)))
        row = page.records[0]
        self.assertEqual(dict(row.attributes), {"url": payload["data"][0]["url"], "retrieved_on": "1789041600"})
        self.assertEqual(row.published_at, "2026-09-09T12:00:00Z")
        self.assertIn("third_party_archive", row.loss)

    def test_arxiv_revision_date_remains_separate_from_original_publication(self):
        carrier = transport.Transport(opener=lambda request: (200, AX_ONE_ENTRY, "application/atom+xml", request.url, ()))
        page = scholarly.fetch_native_page(carrier, AdapterRequest(step_id="paper", query="arxiv:things"))
        self.assertEqual(dict(page.records[0].attributes)["body_representation"], "abstract")
        self.assertTrue(dict(page.records[0].attributes)["modified_at"])
