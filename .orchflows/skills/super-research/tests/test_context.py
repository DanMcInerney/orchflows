"""Tracer suite: the K4 hybrid path, linked and never merged.

Every test here runs offline. No test reaches the network, and importing
``super_research`` performs no I/O of any kind.
"""

from __future__ import annotations

import unittest

from super_research import schema


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


if __name__ == "__main__":  # pragma: no cover - convenience runner
    unittest.main()
