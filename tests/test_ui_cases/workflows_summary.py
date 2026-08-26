"""Compact semantic summaries for the canonical Workflows catalog."""

from __future__ import annotations

import copy
import unittest
from pathlib import Path

from scripts import ui_workflows_summary as summaries


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs" / "ui" / "workflow-summary-manifest.json"

EXPECTED_WORKFLOWS = {
    "benchmaker",
    "drift-canary",
    "errand",
    "evolve",
    "fix",
    "orch-build",
    "orch-eval-design",
    "orch-fixture",
    "orch-repair",
    "orch-self-improve",
    "orch-spec",
    "orch-triage",
    "renovate",
    "self-improve",
    "skill-tournament",
}


class WorkflowSummaryManifestTests(unittest.TestCase):
    def test_checked_in_manifest_is_closed_and_covers_the_canonical_catalog(self):
        manifest = summaries.load_manifest(MANIFEST)

        self.assertEqual("orchflows.workflow-summary.v1", manifest["schema"])
        self.assertEqual(EXPECTED_WORKFLOWS, set(manifest["workflows"]))
        self.assertEqual({"schema", "workflows"}, set(manifest))
        for workflow_id, summary in manifest["workflows"].items():
            with self.subTest(workflow=workflow_id):
                self.assertEqual({"nodes", "edges"}, set(summary))
                if workflow_id == "errand":
                    self.assertEqual(1, len(summary["nodes"]))
                    self.assertFalse(summary["edges"])
                else:
                    self.assertGreaterEqual(len(summary["nodes"]), 2)
                    self.assertTrue(summary["edges"])
                for node in summary["nodes"]:
                    self.assertEqual({"id", "label"}, set(node))
                for edge in summary["edges"]:
                    self.assertEqual({"source", "target", "kind"}, set(edge))

    def test_manifest_and_members_are_closed(self):
        manifest = self._synthetic_manifest()
        additions = (
            (manifest, "extra"),
            (manifest["workflows"]["demo"], "extra"),
            (manifest["workflows"]["demo"]["nodes"][0], "extra"),
            (manifest["workflows"]["demo"]["edges"][0], "extra"),
        )

        for target, field in additions:
            candidate = copy.deepcopy(manifest)
            path = self._same_path(candidate, manifest, target)
            path[field] = True
            with self.subTest(target=set(target)):
                with self.assertRaises(summaries.SummaryManifestError):
                    summaries.validate_manifest(candidate, {"demo"})

    def test_catalog_coverage_is_exact(self):
        manifest = self._synthetic_manifest()
        for keys in (set(), {"demo", "invented"}):
            with self.subTest(keys=keys):
                with self.assertRaises(summaries.SummaryManifestError):
                    summaries.validate_manifest(manifest, keys)

    def test_node_ids_are_unique_and_well_formed(self):
        invalid_ids = ("", " two", "two words", "Two", "two_underscores")
        for node_id in invalid_ids:
            manifest = self._synthetic_manifest()
            manifest["workflows"]["demo"]["nodes"][1]["id"] = node_id
            with self.subTest(node_id=node_id):
                with self.assertRaises(summaries.SummaryManifestError):
                    summaries.validate_manifest(manifest, {"demo"})

        manifest = self._synthetic_manifest()
        manifest["workflows"]["demo"]["nodes"][1]["id"] = "one"
        with self.assertRaises(summaries.SummaryManifestError):
            summaries.validate_manifest(manifest, {"demo"})

    def test_labels_are_trimmed_single_line_and_bounded(self):
        invalid_labels = ("", " padded", "padded ", "two\nlines", "x" * 41)
        for label in invalid_labels:
            manifest = self._synthetic_manifest()
            manifest["workflows"]["demo"]["nodes"][0]["label"] = label
            with self.subTest(label=repr(label)):
                with self.assertRaises(summaries.SummaryManifestError):
                    summaries.validate_manifest(manifest, {"demo"})

    def test_edges_have_known_endpoints_kinds_and_unique_tuples(self):
        for field, value in (
            ("source", "missing"),
            ("target", "missing"),
            ("kind", "conditional"),
        ):
            manifest = self._synthetic_manifest()
            manifest["workflows"]["demo"]["edges"][0][field] = value
            with self.subTest(field=field):
                with self.assertRaises(summaries.SummaryManifestError):
                    summaries.validate_manifest(manifest, {"demo"})

        manifest = self._synthetic_manifest()
        manifest["workflows"]["demo"]["edges"].append(
            copy.deepcopy(manifest["workflows"]["demo"]["edges"][0])
        )
        with self.assertRaises(summaries.SummaryManifestError):
            summaries.validate_manifest(manifest, {"demo"})

    def test_every_directed_cycle_contains_a_loop_edge(self):
        manifest = self._synthetic_manifest()
        manifest["workflows"]["demo"]["edges"].append(
            {"source": "two", "target": "one", "kind": "branch"}
        )

        with self.assertRaises(summaries.SummaryManifestError):
            summaries.validate_manifest(manifest, {"demo"})

    def test_every_loop_edge_is_part_of_a_directed_cycle(self):
        manifest = self._synthetic_manifest()
        manifest["workflows"]["demo"]["edges"][0]["kind"] = "loop"

        with self.assertRaises(summaries.SummaryManifestError):
            summaries.validate_manifest(manifest, {"demo"})

    def test_loop_edges_can_close_multi_node_cycles_or_self_cycles(self):
        multi_node = self._synthetic_manifest()
        multi_node["workflows"]["demo"]["edges"].append(
            {"source": "two", "target": "one", "kind": "loop"}
        )
        self_cycle = self._synthetic_manifest()
        self_cycle["workflows"]["demo"]["edges"].append(
            {"source": "two", "target": "two", "kind": "loop"}
        )

        self.assertIs(multi_node, summaries.validate_manifest(multi_node, {"demo"}))
        self.assertIs(self_cycle, summaries.validate_manifest(self_cycle, {"demo"}))

    def test_malformed_member_types_fail_as_manifest_errors(self):
        candidates = []
        for section, field, value in (
            ("node", "id", 1),
            ("node", "label", ["First"]),
            ("edge", "source", ["one"]),
            ("edge", "target", {"two": True}),
            ("edge", "kind", ["sequence"]),
        ):
            manifest = self._synthetic_manifest()
            member = manifest["workflows"]["demo"][section + "s"][0]
            member[field] = value
            candidates.append((f"{section}.{field}", manifest))

        for subject, manifest in candidates:
            with self.subTest(subject=subject):
                with self.assertRaises(summaries.SummaryManifestError):
                    summaries.validate_manifest(manifest, {"demo"})

    @staticmethod
    def _synthetic_manifest():
        return {
            "schema": "orchflows.workflow-summary.v1",
            "workflows": {
                "demo": {
                    "nodes": [
                        {"id": "one", "label": "First"},
                        {"id": "two", "label": "Second"},
                    ],
                    "edges": [
                        {"source": "one", "target": "two", "kind": "sequence"}
                    ],
                }
            },
        }

    @staticmethod
    def _same_path(candidate, original, target):
        if target is original:
            return candidate
        workflow = original["workflows"]["demo"]
        if target is workflow:
            return candidate["workflows"]["demo"]
        if target is workflow["nodes"][0]:
            return candidate["workflows"]["demo"]["nodes"][0]
        return candidate["workflows"]["demo"]["edges"][0]


if __name__ == "__main__":
    unittest.main()
