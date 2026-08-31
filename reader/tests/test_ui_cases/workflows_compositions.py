"""Exact T3 composition topology derived without source repair.

No library entry is a composition any more -- every workflow is a skill
whose prose calls bricks -- so what is left here is the projection
machinery graded against trees built for it.
"""

from __future__ import annotations

import tempfile
import os
import unittest
from pathlib import Path

from reader.scripts import ui_workflows_compositions as compositions


class WorkflowCompositionTests(unittest.TestCase):
    def test_escaping_template_and_stub_symlinks_are_rejected(self):
        for link_kind in ("template", "stub"):
            with self.subTest(link_kind=link_kind), tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
                root = Path(directory)
                composition = root / "example-workflows" / "demo"
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

    def test_duplicate_dangling_and_unresolved_source_are_diagnosed_without_repair(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write(root / "example-workflows" / "demo" / "template.md", """---
name: demo
description: Demonstrate malformed topology.
entry: named
---
""")
            self._write(root / "example-workflows" / "demo" / "00-start.md", """---
id: 00-start
executor: orch-known
depends_on: []
bound: once
---
""")
            self._write(root / "example-workflows" / "demo" / "01-end.md", """---
id: 01-end
executor: orch-missing
depends_on: [00-start, 99-ghost]
bound: once
---
""")
            self._write(root / "example-workflows" / "demo" / "02-duplicate.md", """---
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
