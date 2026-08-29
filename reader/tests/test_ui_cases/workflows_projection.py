"""Closed public Workflows projections assembled from canonical owners."""

from __future__ import annotations

import unittest
from pathlib import Path

from reader.scripts import ui_workflows_projection as workflows


ROOT = Path(__file__).resolve().parents[3]


class WorkflowProjectionTests(unittest.TestCase):
    def test_catalog_detail_and_source_are_closed_and_inventory_exact(self):
        catalog = workflows.project_workflow_catalog(ROOT)

        self.assertEqual(
            {"schema", "workflows"}, set(catalog)
        )
        self.assertEqual("orchflows.workflow-catalog.v1", catalog["schema"])
        self.assertTrue(catalog["workflows"])
        self.assertTrue(all(
            set(item) == {"id", "type", "entry", "description", "summary"}
            for item in catalog["workflows"]
        ))

        for item in catalog["workflows"]:
            with self.subTest(workflow=item["id"]):
                detail = workflows.project_workflow(ROOT, item["id"])
                self.assertEqual(
                    {"schema", "id", "type", "nodes", "edges", "relations", "diagnostics"},
                    set(detail),
                )
                self.assertEqual("orchflows.workflow-detail.v1", detail["schema"])
                self.assertEqual(item["id"], detail["id"])
                self.assertEqual(item["type"], detail["type"])
                self.assertEqual(
                    sorted(
                        detail["edges"],
                        key=lambda edge: (edge["from"], edge["kind"], edge["to"], edge["id"]),
                    ),
                    detail["relations"],
                )
                self.assertEqual(
                    sorted(
                        detail["diagnostics"],
                        key=lambda item: (item["code"], item["subject_id"]),
                    ),
                    detail["diagnostics"],
                )
                expected = {node["source_id"] for node in detail["nodes"] if "source_id" in node}
                self.assertEqual(expected, set(workflows.source_inventory(ROOT, item["id"])))

    def test_unknown_workflow_and_source_are_generic_not_found(self):
        self.assertIsNone(workflows.project_workflow(ROOT, "no-such-workflow"))
        self.assertEqual(
            (404, {"error": {"code": "not_found", "message": "resource not found"}}),
            workflows.project_workflow_source(ROOT, "no-such-workflow", "src_bad"),
        )

    def test_evolve_source_contract_delivers_the_selected_canonical_text(self):
        detail = workflows.project_workflow(ROOT, "evolve")
        source_id = next(
            node["source_id"] for node in detail["nodes"]
            if node["id"] == "work:evolve/02-campaign"
        )

        status, source = workflows.project_workflow_source(ROOT, "evolve", source_id)

        self.assertEqual(200, status)
        self.assertEqual(
            {"schema", "id", "text", "sha256", "language", "redacted"},
            set(source),
        )
        self.assertEqual("orchflows.workflow-source.v1", source["schema"])
        self.assertEqual(source_id, source["id"])
        self.assertEqual("markdown", source["language"])
        self.assertIn("02-campaign", source["text"])


if __name__ == "__main__":
    unittest.main()
