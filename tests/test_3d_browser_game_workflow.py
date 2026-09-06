"""Admission seams for the private package composition."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from scripts import rings
from tools.validate_support import structure, workflows


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "example-workflows" / "3d-browser-game"
PUBLIC = "3d-browser-game"
PRIVATE_WORKFLOWS = (
    "discovery",
    "playable-increment",
    "gameplay-gate",
    "blender-asset",
    "final-acceptance",
)
PRIVATE_STANDARDS = (
    "browser-game-3d-asset",
    "blender-game-asset",
    "threejs-browser-game",
    "browser-game-interface",
    "browser-game-playtest",
)


def resolve(kind: str, name: str, *, owner: str | None = None):
    """Resolve against this checkout so tests exercise package scope."""

    return rings.resolve(
        kind,
        name,
        owner=owner,
        project=ROOT,
        home=ROOT / ".test-home-that-does-not-exist",
        lib=ROOT,
        trust=False,
    )


class WorkflowPackageTests(unittest.TestCase):
    def test_public_entry_and_private_members_have_expected_paths(self):
        public = PACKAGE / "SKILL.md"
        self.assertTrue(public.is_file())
        for name in PRIVATE_WORKFLOWS:
            record = resolve("workflow", name, owner=PUBLIC)
            path = Path(record["path"]).resolve()
            self.assertTrue(path.is_relative_to(PACKAGE.resolve()))
            self.assertEqual(f"workflows/{name}/SKILL.md", path.relative_to(PACKAGE).as_posix())
        for name in PRIVATE_STANDARDS:
            record = resolve("standard", name, owner=PUBLIC)
            path = Path(record["path"]).resolve()
            self.assertTrue(path.is_relative_to(PACKAGE.resolve()))
            self.assertEqual(f"standards/{name}/STANDARD.md", path.relative_to(PACKAGE).as_posix())

    def test_private_workflows_are_not_global_names(self):
        for name in PRIVATE_WORKFLOWS:
            with self.subTest(name=name), self.assertRaises(rings.RingError):
                resolve("workflow", name)

    def test_literal_workflow_commands_preserve_stage_order(self):
        text = (PACKAGE / "SKILL.md").read_text(encoding="utf-8")
        commands = list(workflows._commands(text))
        names = [match.group(1) for command in commands for match in [re.search(r"--workflow\s+([^\s]+)", command)] if match]
        self.assertEqual([PUBLIC, *PRIVATE_WORKFLOWS], names)

    def test_private_bodies_have_no_workflow_edges_or_cycles(self):
        bodies = [PACKAGE / "SKILL.md"] + [PACKAGE / "workflows" / name / "SKILL.md" for name in PRIVATE_WORKFLOWS]
        graph = {PUBLIC: set(), **{path.parent.name: set() for path in bodies[1:]}}
        for command in workflows._commands(bodies[0].read_text(encoding="utf-8")):
            match = re.search(r"--workflow\s+([^\s]+)", command)
            if match and "--parent" in command:
                graph[PUBLIC].add(match.group(1))
        for path in bodies[1:]:
            for command in workflows._commands(path.read_text(encoding="utf-8")):
                self.assertNotRegex(command, r"--workflow\s+(?:" + "|".join(PRIVATE_WORKFLOWS) + r")\b")
        self.assertIsNone(structure.find_cycle(graph))

    def test_literal_standard_names_resolve_inside_public_package(self):
        text = "\n".join(
            (PACKAGE / "workflows" / name / "SKILL.md").read_text(encoding="utf-8")
            for name in PRIVATE_WORKFLOWS
        )
        names = sorted(set(match.group(1) for match in re.finditer(r"--standard\s+([^\s]+)", text)))
        for name in names:
            with self.subTest(name=name):
                self.assertIsNotNone(resolve("standard", name, owner=PUBLIC))

    def test_gate_judging_criteria_are_reference_contracts(self):
        core = (PACKAGE / "references" / "core-rubric.md").read_text(encoding="utf-8")
        final = (PACKAGE / "references" / "final-rubric.md").read_text(encoding="utf-8")
        self.assertIn("| Loop and fun |", core)
        self.assertIn("| Presentation |", final)
        gameplay = (PACKAGE / "workflows" / "gameplay-gate" / "SKILL.md").read_text(encoding="utf-8")
        acceptance = (PACKAGE / "workflows" / "final-acceptance" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("../../references/core-rubric.md", gameplay)
        self.assertIn("../../references/final-rubric.md", acceptance)


if __name__ == "__main__":
    unittest.main()
