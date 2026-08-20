"""Compact semantic summaries for the canonical Workflows catalog."""

from __future__ import annotations

import unittest
from pathlib import Path

from scripts import ui_workflows_summary as summaries


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs" / "ui" / "workflow-summary-manifest.json"

EXPECTED_WORKFLOWS = {
    "benchmaker",
    "drift-canary",
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
                self.assertGreaterEqual(len(summary["nodes"]), 2)
                self.assertTrue(summary["edges"])
                for node in summary["nodes"]:
                    self.assertEqual({"id", "label"}, set(node))
                for edge in summary["edges"]:
                    self.assertEqual({"source", "target", "kind"}, set(edge))


if __name__ == "__main__":
    unittest.main()
