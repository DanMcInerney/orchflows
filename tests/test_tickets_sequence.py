"""Sequence admission for skill and pack-stage chains."""

from pathlib import Path
import unittest
from unittest.mock import patch

from scripts.tickets_sequence import sequence_block, sequence_defects


ROOT = Path(__file__).resolve().parents[1]


class SequenceAdmissionTests(unittest.TestCase):
    def test_declared_pack_stages_are_accepted(self):
        self.assertEqual(
            [],
            sequence_defects(
                ["draft", "edit"], "orch-draft", "orch-content-pack",
            ),
        )

    def test_undeclared_pack_stage_is_refused(self):
        defects = sequence_defects(
            ["draft", "publish"], "orch-draft", "orch-content-pack",
        )
        self.assertTrue(any("publish" in defect for defect in defects), defects)
        self.assertTrue(any("declared" in defect for defect in defects), defects)

    def test_skill_and_cell_forms_cannot_be_mixed(self):
        defects = sequence_defects(
            ["draft", "orch-edit"], "orch-draft", "orch-content-pack",
        )
        self.assertTrue(any("mix" in defect.lower() for defect in defects), defects)

    def test_later_skill_role_does_not_change_the_head_binding(self):
        self.assertEqual([], sequence_defects(["orch-draft", "orch-synthesize"], "orch-draft"))
        prompt = "\n".join(
            sequence_block({"sequence": ["orch-draft", "orch-synthesize"]})
        )
        self.assertIn("head's binding", prompt)

    def test_skill_sequence_requires_resolvable_names(self):
        defects = sequence_defects(
            ["orch-draft", "orch-does-not-exist"], "orch-draft",
        )
        self.assertTrue(any("resolve" in defect for defect in defects), defects)

    def test_project_skill_sequence_resolves_from_project_scope(self):
        with self.subTest("project scope"):
            project = ROOT / ".sequence-test-project"
            skill = project / ".orchflows" / "skills" / "cleanup" / "SKILL.md"
            second = project / ".orchflows" / "skills" / "publish" / "SKILL.md"
            skill.parent.mkdir(parents=True, exist_ok=True)
            second.parent.mkdir(parents=True, exist_ok=True)
            skill.write_text("---\nname: cleanup\n---\n", encoding="utf-8")
            second.write_text("---\nname: publish\n---\n", encoding="utf-8")
            try:
                with patch("scripts.tickets_sequence.Path.cwd", return_value=project):
                    self.assertEqual(
                        [],
                        sequence_defects(
                            ["project:cleanup", "project:publish"],
                            "project:cleanup",
                        ),
                    )
            finally:
                second.unlink(missing_ok=True)
                skill.unlink(missing_ok=True)
                second.parent.rmdir()
                skill.parent.rmdir()
                (project / ".orchflows" / "skills").rmdir()
                (project / ".orchflows").rmdir()
                project.rmdir()


if __name__ == "__main__":
    unittest.main()
