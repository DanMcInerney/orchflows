"""Projection and oracle-discrimination cases."""

from .support import *  # noqa: F403

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

