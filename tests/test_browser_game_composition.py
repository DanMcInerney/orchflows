"""Closed user-facing admission for the canonical browser-game workflow."""

from __future__ import annotations

import unittest

from installer.packages import (
    MANUAL_ONLY,
    discover_workflow_skills,
    manual_only_frontmatter,
    split_frontmatter,
    workflow_adapter_body,
)
from scripts import tickets


from tests._repo_root import ROOT
COMPOSITION = ROOT / "example-workflows" / "browser-game"
LEGACY_INPUTS = (
    "29DF4D680E47A8162AE94BBD7C9BCD1FA9A2DFC3E7EE4D26025933B2C5D79653",
    "3C5EB92FB148C4177FA8CE4CE88B4EE9576D457F6C47F1B9762407843ACC8F48",
)
OBSOLETE_EXECUTORS = ("orch-build", "orch-compose", "carry-packets")
DISPOSITIONS = (
    "advance",
    "revise",
    "experiment",
    "user-decision-required",
    "stop",
)


class BrowserGameCompositionTests(unittest.TestCase):
    def _workflow(self):
        path = COMPOSITION / "SKILL.md"
        text = path.read_text(encoding="utf-8")
        return path, text, tickets._parse_frontmatter(text)

    def test_named_invocation_closes_inputs_outputs_questions_and_dispositions(self):
        _, text, frontmatter = self._workflow()

        self.assertEqual("browser-game", frontmatter["name"])
        self.assertEqual("true", frontmatter["disable-model-invocation"])
        normalized = " ".join(text.split())
        for term in (
            "`brief`",
            "`workspace`",
            "versioned program record",
            "evidence",
            "successor plan",
            "kind: user-only",
            "verbatim",
            "empirical",
        ):
            self.assertIn(term, normalized)
        for disposition in DISPOSITIONS:
            self.assertIn(f"`{disposition}`", text)

    def test_the_workflow_is_discoverable_and_calls_a_frame_and_callables(self):
        discovered = {
            path.name: (path, frontmatter, body)
            for path, frontmatter, body in discover_workflow_skills(ROOT)
        }
        self.assertIn("browser-game", discovered)

        _, text, _ = self._workflow()
        for call in (
            "tickets.py frame-open",
            "do --standard orch-content",
            "do --standard orch-research",
            "judge --standard orch-content",
            "tickets.py frame-close",
        ):
            self.assertIn(call, text)
        # The template era is gone: no stub files, no instantiation route.
        self.assertEqual(
            ["SKILL.md"], sorted(path.name for path in COMPOSITION.glob("*.md"))
        )
        self.assertNotIn("instantiate", text)

    def test_installer_adapter_points_at_the_body_and_forces_manual_only(self):
        path, text, _ = self._workflow()
        frontmatter, _ = split_frontmatter(text)
        adapter = workflow_adapter_body("browser-game", path.parent, frontmatter)
        rendered = manual_only_frontmatter(frontmatter) + adapter

        self.assertIn(str(path.parent / "SKILL.md"), adapter)
        self.assertNotIn("--set ", adapter)
        self.assertNotIn("instantiate", adapter)
        self.assertEqual(1, rendered.count(MANUAL_ONLY))
        admitted = "\n".join(
            file.read_text(encoding="utf-8") for file in sorted(COMPOSITION.rglob("*.md"))
        ) + "\n" + adapter
        for forbidden in LEGACY_INPUTS + OBSOLETE_EXECUTORS:
            self.assertNotIn(forbidden, admitted)

    def test_checkpoint_consumes_the_kind_separated_successor_plan_contract(self):
        _, checkpoint, _ = self._workflow()
        self.assertIn(
            "../references/browser-game-program-record.schema.json"
            "#/$defs/successorPlanRevision",
            checkpoint,
        )
        for field in (
            "artifact identity",
            "artifact kind",
            "standard",
            "run/root identities",
            "dependencies",
            "status",
        ):
            self.assertIn(field, " ".join(checkpoint.split()))
