"""Manifest parsing and validation cases."""

from .support import *  # noqa: F403

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
