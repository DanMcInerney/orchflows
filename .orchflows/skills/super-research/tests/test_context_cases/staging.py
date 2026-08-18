"""Staged acquisition orchestration cases."""

from .support import *  # noqa: F403

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
