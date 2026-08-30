"""Sequence admission for skill and pack-stage chains."""

from pathlib import Path
import unittest
from unittest.mock import patch

from scripts.tickets_lint import lint_findings
from scripts.tickets_sequence import (
    sequence_block, sequence_defects, sequence_role_findings,
)


ROOT = Path(__file__).resolve().parents[1]


class SequenceAdmissionTests(unittest.TestCase):
    def test_declared_pack_stages_are_accepted(self):
        self.assertEqual(
            [],
            sequence_defects(
                ["draft", "edit"], "orch-execute", "orch-content-pack",
            ),
        )

    def test_undeclared_pack_stage_is_refused(self):
        defects = sequence_defects(
            ["draft", "publish"], "orch-execute", "orch-content-pack",
        )
        self.assertTrue(any("publish" in defect for defect in defects), defects)
        self.assertTrue(any("declared" in defect for defect in defects), defects)

    def test_skill_and_cell_forms_cannot_be_mixed(self):
        defects = sequence_defects(
            ["draft", "orch-check"], "orch-execute", "orch-content-pack",
        )
        self.assertTrue(any("mix" in defect.lower() for defect in defects), defects)

    def test_later_skill_role_does_not_change_the_head_binding(self):
        self.assertEqual([], sequence_defects(["orch-execute", "orch-check"], "orch-execute"))
        prompt = "\n".join(
            sequence_block({"sequence": ["orch-execute", "orch-check"]})
        )
        self.assertIn("head's binding", prompt)

    def test_a_disagreeing_continuation_role_is_graded_but_never_refused(self):
        """rules/roles.md 4 makes the continuation's own `role:` inert, so
        the chain stays lawful; the caller is told what that costs."""

        chain = ["orch-execute", "orch-check"]
        self.assertEqual([], sequence_defects(chain, "orch-execute"))

        findings = sequence_role_findings(chain, "orch-execute")

        self.assertEqual(1, len(findings), findings)
        self.assertEqual(
            {
                "code": "sequence-role-mismatch",
                "severity": "warning",
                "entry": "orch-check",
                "declared_role": "planner",
                "head_role": "worker",
            },
            {key: value for key, value in findings[0].items() if key != "message"},
        )

    def test_an_agreeing_or_roleless_continuation_is_graded_clean(self):
        for chain, executor in (
            (["orch-check", "orch-decompose"], "orch-check"),
            (["orch-execute", "orch-integrate"], "orch-execute"),
            (["draft", "edit"], "orch-execute"),
        ):
            with self.subTest(chain=chain):
                self.assertEqual([], sequence_role_findings(chain, executor))

    def test_the_packet_prompt_names_the_disagreeing_continuation(self):
        prompt = "\n".join(sequence_block({
            "sequence": ["orch-execute", "orch-check"],
            "executor": "orch-execute",
        }))

        self.assertIn("'orch-check' declares role 'planner'", prompt)
        self.assertIn("no fresh independent verdict", prompt)

    def test_skill_sequence_requires_resolvable_names(self):
        defects = sequence_defects(
            ["orch-execute", "orch-does-not-exist"], "orch-execute",
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


class SequenceRoleReachesTheLintTests(unittest.TestCase):
    """The grade has a caller. A finding produced by a function nothing
    calls is a finding nobody sees, which is what `sequence_role_findings`
    was until the lint carried it."""

    TICKET = """---
id: T1
run: testrun
status: pending
executor: orch-execute
sequence: [orch-execute, orch-check]
pack: orch-code-pack
depends_on: []
isolation: required
bound: 30m
---

## Goal

Deliver the behavior.

## Context

[]

## Result

## Verification

## Feedback

[]

## Risks

[]
"""

    def test_the_lint_carries_the_mismatch_as_a_warning(self):
        findings = lint_findings(self.TICKET, ticket_id="T1")
        mismatch = [
            item for item in findings if item["code"] == "sequence-role-mismatch"
        ]
        self.assertEqual(1, len(mismatch), findings)
        self.assertEqual("warning", mismatch[0]["severity"])
        self.assertIn("orch-check", mismatch[0]["message"])
        # A warning is not a refusal: `_cmd_lint` exits 1 only on an error.
        self.assertFalse(
            any(item["severity"] == "error" for item in findings), findings
        )

    def test_an_agreeing_chain_leaves_the_lint_silent(self):
        agreeing = self.TICKET.replace(
            "sequence: [orch-execute, orch-check]",
            "sequence: [orch-execute, orch-integrate]",
        )
        self.assertEqual(
            [],
            [
                item for item in lint_findings(agreeing, ticket_id="T1")
                if item["code"] == "sequence-role-mismatch"
            ],
        )


if __name__ == "__main__":
    unittest.main()
