"""Exact T3 composition topology derived without source repair."""

from __future__ import annotations

import tempfile
import os
import unittest
from pathlib import Path

from reader.scripts import ui_workflows_compositions as compositions
from reader.scripts import ui_workflows_identity as identity


ROOT = Path(__file__).resolve().parents[3]


class WorkflowCompositionTests(unittest.TestCase):
    def test_escaping_template_and_stub_symlinks_are_rejected(self):
        for link_kind in ("template", "stub"):
            with self.subTest(link_kind=link_kind), tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
                root = Path(directory)
                composition = root / "compositions" / "demo"
                composition.mkdir(parents=True)
                external = Path(outside) / f"{link_kind}.md"
                if link_kind == "template":
                    external.write_text(
                        "---\nname: demo\ndescription: EXTERNAL_SECRET\nentry: named\n---\n",
                        encoding="utf-8",
                    )
                    link = composition / "template.md"
                    self._write(
                        composition / "00-start.md",
                        "---\nid: 00-start\nexecutor: orch-missing\ndepends_on: []\nbound: once\n---\n",
                    )
                else:
                    self._write(
                        composition / "template.md",
                        "---\nname: demo\ndescription: Safe owner.\nentry: named\n---\n",
                    )
                    external.write_text(
                        "---\nid: 00-secret\nexecutor: orch-missing\ndepends_on: []\nbound: once\n---\n",
                        encoding="utf-8",
                    )
                    link = composition / "00-secret.md"
                try:
                    os.symlink(external, link)
                except OSError as error:
                    self.skipTest(f"symlink unavailable: {error}")

                with self.assertRaises(compositions.WorkflowCompositionError):
                    compositions.project_composition(root, "demo")

    def test_evolve_has_exact_dependency_executor_and_deliberate_loop_topology(self):
        detail = compositions.project_composition(ROOT, "evolve")

        self.assertEqual(
            {"schema", "id", "type", "nodes", "edges", "relations", "diagnostics"},
            set(detail),
        )
        self.assertEqual("orchflows.workflow-detail.v1", detail["schema"])
        self.assertEqual("evolve", detail["id"])
        self.assertEqual("composition", detail["type"])
        self.assertEqual(
            {
                ("unresolved-reference", "skill:orch-eval-design"),
                ("unresolved-reference", "skill:orch-verify"),
            },
            {(item["code"], item["subject_id"]) for item in detail["diagnostics"]},
        )

        node_ids = {node["id"] for node in detail["nodes"]}
        self.assertEqual(
            {
                "workflow:evolve",
                "work:evolve/00-eval",
                "work:evolve/01-eligibility",
                "work:evolve/02-campaign",
                "work:evolve/03-result",
                "skill:orch-eval-design",
                "skill:orch-loop",
                "skill:orch-verify",
            },
            node_ids,
        )
        edge_tuples = {
            (edge["kind"], edge["from"], edge["to"])
            for edge in detail["edges"]
        }
        self.assertEqual(
            {
                ("dependency", "work:evolve/00-eval", "work:evolve/01-eligibility"),
                ("dependency", "work:evolve/01-eligibility", "work:evolve/02-campaign"),
                ("dependency", "work:evolve/02-campaign", "work:evolve/03-result"),
                ("executor", "work:evolve/00-eval", "skill:orch-eval-design"),
                ("executor", "work:evolve/01-eligibility", "skill:orch-verify"),
                ("executor", "work:evolve/02-campaign", "skill:orch-loop"),
                ("executor", "work:evolve/03-result", "skill:orch-verify"),
                ("loop", "work:evolve/02-campaign", "work:evolve/02-campaign"),
            },
            edge_tuples,
        )
        loop = next(edge for edge in detail["edges"] if edge["kind"] == "loop")
        for phrase in ("Write candidates", "eligibility", "score blind", "frozen rule", "{{bound}}"):
            self.assertIn(phrase, loop["label"])

    def test_nodes_carry_exact_opaque_sources_and_relations_are_sorted_edge_copies(self):
        detail = compositions.project_composition(ROOT, "evolve")
        by_id = {node["id"]: node for node in detail["nodes"]}

        self.assertEqual(
            identity.source_id("lib/compositions/evolve/template.md"),
            by_id["workflow:evolve"]["source_id"],
        )
        self.assertEqual(
            identity.source_id("lib/compositions/evolve/02-campaign.md"),
            by_id["work:evolve/02-campaign"]["source_id"],
        )
        self.assertEqual(
            identity.source_id("lib/skills/engines/orch-loop/SKILL.md"),
            by_id["skill:orch-loop"]["source_id"],
        )
        self.assertEqual(
            sorted(detail["edges"], key=lambda edge: (
                edge["from"], edge["kind"], edge["to"], edge["id"]
            )),
            detail["relations"],
        )
        self.assertEqual(len(detail["edges"]), len({edge["id"] for edge in detail["edges"]}))

    def test_duplicate_dangling_and_unresolved_source_are_diagnosed_without_repair(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write(root / "compositions" / "demo" / "template.md", """---
name: demo
description: Demonstrate malformed topology.
entry: named
---
""")
            self._write(root / "compositions" / "demo" / "00-start.md", """---
id: 00-start
executor: orch-known
depends_on: []
bound: once
---
""")
            self._write(root / "compositions" / "demo" / "01-end.md", """---
id: 01-end
executor: orch-missing
depends_on: [00-start, 99-ghost]
bound: once
---
""")
            self._write(root / "compositions" / "demo" / "02-duplicate.md", """---
id: 01-end
executor: orch-missing
depends_on: [00-start]
bound: once
---
""")
            self._write(root / "skills" / "kernel" / "orch-known" / "SKILL.md", """---
name: orch-known
description: Known executor.
role: none
---
""")

            detail = compositions.project_composition(root, "demo")

        self.assertNotIn("work:demo/99-ghost", {node["id"] for node in detail["nodes"]})
        self.assertEqual(
            ["dangling-edge", "duplicate-node", "unresolved-reference"],
            [diagnostic["code"] for diagnostic in detail["diagnostics"]],
        )
        self.assertEqual(
            [
                ("dependency", "work:demo/00-start", "work:demo/01-end"),
                ("dependency", "work:demo/99-ghost", "work:demo/01-end"),
                ("executor", "work:demo/00-start", "skill:orch-known"),
                ("executor", "work:demo/01-end", "skill:orch-missing"),
            ],
            sorted({(edge["kind"], edge["from"], edge["to"]) for edge in detail["edges"]}),
        )

    @staticmethod
    def _write(path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
