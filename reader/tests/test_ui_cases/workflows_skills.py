"""Exact T1 workflow-skill call topology from canonical skill bodies."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from reader.scripts import ui_workflows_identity as identity
from reader.scripts import ui_workflows_skills as skills


ROOT = Path(__file__).resolve().parents[3]


class WorkflowSkillTests(unittest.TestCase):
    def test_installed_layout_resolves_sibling_bin_script(self):
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory)
            root = package / "lib"
            self._skill(
                root,
                "workflows",
                "demo",
                "Require: input.\n\nRun `runner.py execute`.\n\nReturn: output.\n",
            )
            script = package / "bin" / "runner.py"
            script.parent.mkdir(parents=True)
            script.write_text("print('installed')\n", encoding="utf-8")

            detail = skills.project_workflow_skill(root, "demo")

        node = next(item for item in detail["nodes"] if item["id"] == "script:bin/runner.py")
        self.assertEqual(identity.source_id("bin/runner.py"), node["source_id"])
        self.assertEqual([], detail["diagnostics"])

    def test_repository_skill_derives_only_backticked_calls_and_invoked_scripts(self):
        detail = skills.project_workflow_skill(ROOT, "orch-spec")

        self.assertEqual(
            {"schema", "id", "type", "nodes", "edges", "relations", "diagnostics"},
            set(detail),
        )
        self.assertEqual("orchflows.workflow-detail.v1", detail["schema"])
        self.assertEqual("orch-spec", detail["id"])
        self.assertEqual("workflow-skill", detail["type"])

        edge_tuples = {
            (edge["kind"], edge["from"], edge["to"])
            for edge in detail["edges"]
        }
        self.assertIn(
            ("skill-call", "workflow:orch-spec", "skill:orch-integrate"),
            edge_tuples,
        )
        self.assertIn(
            ("skill-call", "workflow:orch-spec", "skill:orch-frontier"),
            edge_tuples,
        )
        self.assertIn(
            ("skill-call", "workflow:orch-spec", "skill:orch-decompose"),
            edge_tuples,
        )
        self.assertIn(
            ("script-call", "workflow:orch-spec", "script:bin/tickets.py"),
            edge_tuples,
        )
        self.assertNotIn("skill:objective", {node["id"] for node in detail["nodes"]})
        self.assertNotIn("skill:inputs", {node["id"] for node in detail["nodes"]})
        self.assertEqual(len(detail["edges"]), len({edge["id"] for edge in detail["edges"]}))
        self.assertEqual(
            sorted(
                detail["edges"],
                key=lambda edge: (edge["from"], edge["kind"], edge["to"], edge["id"]),
            ),
            detail["relations"],
        )

    def test_repeated_calls_coalesce_while_prose_links_and_carriage_create_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._skill(
                root,
                "workflows",
                "demo",
                """Require: the packet's `objective` and plain orch-target prose.

Call `orch-target`, then repeat `orch-target`. A [skill](orch-target) link is
only a file dependency. Run `runner.py execute`, then `runner.py verify`.
The uninstalled command `tools/validate.py` remains visible as unresolved.

Never: read a path from the request.

Return: the result.
""",
            )
            self._skill(root, "kernel", "orch-target", "Require: input.\n\nReturn: output.\n")
            self._script(root, "runner.py", "print('ok')\n")

            detail = skills.project_workflow_skill(root, "demo")

        edge_tuples = [
            (edge["kind"], edge["from"], edge["to"])
            for edge in detail["edges"]
        ]
        self.assertEqual(
            [
                ("script-call", "workflow:demo", "script:bin/runner.py"),
                ("script-call", "workflow:demo", "script:tools/validate.py"),
                ("skill-call", "workflow:demo", "skill:orch-target"),
            ],
            edge_tuples,
        )
        self.assertEqual(
            [{
                "code": "unresolved-reference",
                "subject_id": "script:tools/validate.py",
                "message": "The canonical call does not resolve to an installed source.",
            }],
            detail["diagnostics"],
        )
        by_id = {node["id"]: node for node in detail["nodes"]}
        self.assertEqual(
            identity.source_id("lib/skills/workflows/demo/SKILL.md"),
            by_id["workflow:demo"]["source_id"],
        )
        self.assertEqual(
            identity.source_id("lib/skills/kernel/orch-target/SKILL.md"),
            by_id["skill:orch-target"]["source_id"],
        )
        self.assertEqual(
            identity.source_id("bin/runner.py"),
            by_id["script:bin/runner.py"]["source_id"],
        )
        self.assertNotIn("source_id", by_id["script:tools/validate.py"])

    def test_unresolved_skill_is_diagnosed_without_promoting_plain_prose(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._skill(
                root,
                "workflows",
                "demo",
                """Require: an input.

Use `orch-missing`; plain orch-also-missing is explanatory prose.

Return: the result.
""",
            )

            detail = skills.project_workflow_skill(root, "demo")

        self.assertEqual(
            [("skill-call", "workflow:demo", "skill:orch-missing")],
            [(edge["kind"], edge["from"], edge["to"]) for edge in detail["edges"]],
        )
        self.assertEqual(
            [("unresolved-reference", "skill:orch-missing")],
            [(item["code"], item["subject_id"]) for item in detail["diagnostics"]],
        )
        self.assertNotIn("skill:orch-also-missing", {node["id"] for node in detail["nodes"]})

    @staticmethod
    def _skill(root: Path, tier: str, name: str, body: str) -> None:
        path = root / "skills" / tier / name / "SKILL.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"---\nname: {name}\ndescription: Test {name}.\nrole: none\n---\n\n{body}",
            encoding="utf-8",
        )

    @staticmethod
    def _script(root: Path, name: str, text: str) -> None:
        path = root / "scripts" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
