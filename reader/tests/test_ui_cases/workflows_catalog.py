"""Canonical workflow catalog projection and summary joining."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from reader.scripts import ui_workflows_catalog as catalog


from reader.tests._repo_root import ROOT
SUMMARY = ROOT / "reader" / "docs" / "workflow-summary-manifest.json"


class WorkflowCatalogTests(unittest.TestCase):
    def test_escaping_file_and_directory_symlink_owners_are_rejected(self):
        for link_kind in ("file", "directory"):
            with self.subTest(link_kind=link_kind), tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
                root = Path(directory)
                external = Path(outside) / "demo"
                external.mkdir()
                external_template = external / "SKILL.md"
                external_template.write_text(
                    "---\nname: demo\ndescription: EXTERNAL_SECRET\n---\n",
                    encoding="utf-8",
                )
                composition = root / "example-workflows" / "demo"
                composition.parent.mkdir(parents=True)
                try:
                    if link_kind == "directory":
                        os.symlink(external, composition, target_is_directory=True)
                    else:
                        composition.mkdir()
                        os.symlink(external_template, composition / "SKILL.md")
                except OSError as error:
                    self.skipTest(f"symlink unavailable: {error}")
                summary_path = self._write_summary(root, {"demo": self._summary()})

                with self.assertRaises(catalog.WorkflowCatalogError):
                    catalog.project_catalog(root, summary_path)

    def test_repository_catalog_is_derived_from_both_canonical_homes(self):
        projected = catalog.project_catalog(ROOT, SUMMARY)

        self.assertEqual(
            [
                "benchmaker", "browser-game", "drift-canary", "evolve", "renovate",
                "self-improve", "skill-tournament", "super-research",
                "orch-do", "orch-judge",
            ],
            [workflow["id"] for workflow in projected],
        )
        self.assertTrue(all(
            set(workflow) == {"id", "type", "entry", "description", "summary"}
            for workflow in projected
        ))
        by_id = {workflow["id"]: workflow for workflow in projected}
        # Both homes carry the same kind now: a library workflow and a
        # callable are alike skills, differing only in what their prose calls.
        self.assertEqual("workflow-skill", by_id["browser-game"]["type"])
        self.assertEqual("callable", by_id["browser-game"]["entry"])
        self.assertEqual(
            "Turn an incomplete browser-game brief into evidence-bound checkpoints and pack-stamped successor delivery.",
            by_id["browser-game"]["description"],
        )
        self.assertEqual("workflow-skill", by_id["orch-do"]["type"])
        self.assertEqual("callable", by_id["orch-do"]["entry"])

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

    def test_duplicate_owner_identity_is_a_closed_error(self):
        """One name, two canonical homes: `example-workflows/demo/` and
        `skills/workflows/demo/` both claim `demo`, and the catalog refuses
        rather than picking one."""

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
    def _write_owner(root: Path, *, name: str) -> None:
        body = root / "example-workflows" / "demo" / "SKILL.md"
        body.parent.mkdir(parents=True)
        body.write_text(
            f"---\nname: {name}\ndescription: Demonstrate one flow.\n"
            "disable-model-invocation: true\n---\n",
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
    def _write(path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    @staticmethod
    def _summary() -> dict:
        return {
            "nodes": [{"id": "one", "label": "One"}, {"id": "two", "label": "Two"}],
            "edges": [{"source": "one", "target": "two", "kind": "sequence"}],
        }


if __name__ == "__main__":
    unittest.main()
