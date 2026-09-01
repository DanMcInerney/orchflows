"""Closed public Workflows projections assembled from canonical owners."""

from __future__ import annotations

import unittest
import re
from pathlib import Path

from reader.scripts import ui_workflows_projection as workflows


ROOT = Path(__file__).resolve().parents[3]


class WorkflowProjectionTests(unittest.TestCase):
    def test_public_projection_defaults_bind_directly_to_library_root(self):
        self.assertNotIn("ROOT", vars(workflows))
        self.assertIs(workflows.LIBRARY_ROOT, workflows.project_workflow.__defaults__[0])
        self.assertIs(workflows.LIBRARY_ROOT, workflows.project_workflow_source.__defaults__[0])

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
        missing = ROOT / "reader" / "docs" / "missing-summary.json"
        with self.assertRaisesRegex(
            workflows.WorkflowProjectionError, re.escape(str(missing.resolve()))
        ):
            workflows.project_workflow_catalog(ROOT, missing)

    def test_evolve_source_contract_delivers_the_selected_canonical_text(self):
        detail = workflows.project_workflow(ROOT, "evolve")
        source_id = next(
            node["source_id"] for node in detail["nodes"]
            if node["id"] == "workflow:evolve"
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
        self.assertIn("Generations, until", source["text"])


if __name__ == "__main__":
    unittest.main()
