"""Canonical workflow catalog projection and summary joining."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from scripts import ui_workflows_catalog as catalog


ROOT = Path(__file__).resolve().parents[2]
SUMMARY = ROOT / "docs" / "ui" / "workflow-summary-manifest.json"


class WorkflowCatalogTests(unittest.TestCase):
    def test_escaping_file_and_directory_symlink_owners_are_rejected(self):
        for link_kind in ("file", "directory"):
            with self.subTest(link_kind=link_kind), tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
                root = Path(directory)
                external = Path(outside) / "demo"
                external.mkdir()
                external_template = external / "template.md"
                external_template.write_text(
                    "---\nname: demo\ndescription: EXTERNAL_SECRET\nentry: named\n---\n",
                    encoding="utf-8",
                )
                composition = root / "compositions" / "demo"
                composition.parent.mkdir(parents=True)
                try:
                    if link_kind == "directory":
                        os.symlink(external, composition, target_is_directory=True)
                    else:
                        composition.mkdir()
                        os.symlink(external_template, composition / "template.md")
                except OSError as error:
                    self.skipTest(f"symlink unavailable: {error}")
                summary_path = self._write_summary(root, {"demo": self._summary()})

                with self.assertRaises(catalog.WorkflowCatalogError):
                    catalog.project_catalog(root, summary_path)

    def test_repository_catalog_is_derived_from_compositions_and_workflow_skills(self):
        projected = catalog.project_catalog(ROOT, SUMMARY)

        self.assertEqual(
            [
                "benchmaker", "drift-canary", "errand", "evolve", "fix", "renovate",
                "self-improve", "skill-tournament", "orch-build",
                "orch-eval-design", "orch-fixture", "orch-repair",
                "orch-self-improve", "orch-spec", "orch-triage",
            ],
            [workflow["id"] for workflow in projected],
        )
        self.assertTrue(all(
            set(workflow) == {"id", "type", "entry", "description", "summary"}
            for workflow in projected
        ))
        by_id = {workflow["id"]: workflow for workflow in projected}
        self.assertEqual("composition", by_id["fix"]["type"])
        self.assertEqual("routed", by_id["fix"]["entry"])
        self.assertEqual("composition", by_id["errand"]["type"])
        self.assertEqual("named", by_id["errand"]["entry"])
        self.assertEqual(
            "Take a failure to a proven, regression-guarded repair. Use for any bug or defect with an unknown or unverified cause.",
            by_id["fix"]["description"],
        )
        self.assertEqual("workflow-skill", by_id["orch-spec"]["type"])
        self.assertEqual("callable", by_id["orch-spec"]["entry"])

    def test_validated_summary_is_joined_by_canonical_id(self):
        projected = catalog.project_catalog(ROOT, SUMMARY)
        manifest = json.loads(SUMMARY.read_text(encoding="utf-8"))

        for workflow in projected:
            self.assertEqual(
                manifest["workflows"][workflow["id"]], workflow["summary"]
            )

    def test_owner_name_must_match_its_canonical_package(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_owner(root, name="other")
            summary_path = self._write_summary(root, {"other": self._summary()})

            with self.assertRaises(catalog.WorkflowCatalogError):
                catalog.project_catalog(root, summary_path)

    def test_duplicate_owner_identity_and_unknown_entry_are_closed_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_owner(root, name="demo", entry="automatic")
            summary_path = self._write_summary(root, {"demo": self._summary()})
            with self.assertRaises(catalog.WorkflowCatalogError):
                catalog.project_catalog(root, summary_path)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_owner(root, name="demo")
            skill = root / "skills" / "workflows" / "demo" / "SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text(
                "---\nname: demo\ndescription: Same owner twice.\nrole: none\n---\n",
                encoding="utf-8",
            )
            summary_path = self._write_summary(root, {"demo": self._summary()})
            with self.assertRaises(catalog.WorkflowCatalogError):
                catalog.project_catalog(root, summary_path)

    @staticmethod
    def _write_owner(root: Path, *, name: str, entry: str = "named") -> None:
        template = root / "compositions" / "demo" / "template.md"
        template.parent.mkdir(parents=True)
        template.write_text(
            f"---\nname: {name}\ndescription: Demonstrate one flow.\nentry: {entry}\n---\n",
            encoding="utf-8",
        )

    @staticmethod
    def _write_summary(root: Path, workflows: dict) -> Path:
        path = root / "summary.json"
        path.write_text(
            json.dumps({"schema": "orchflows.workflow-summary.v1", "workflows": workflows}),
            encoding="utf-8",
        )
        return path

    @staticmethod
    def _summary() -> dict:
        return {
            "nodes": [{"id": "one", "label": "One"}, {"id": "two", "label": "Two"}],
            "edges": [{"source": "one", "target": "two", "kind": "sequence"}],
        }


if __name__ == "__main__":
    unittest.main()
