"""Closed user-facing admission for the canonical browser-game composition."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from installer.packages import (
    discover_templates,
    split_frontmatter,
    template_adapter_body,
)
from scripts import tickets


ROOT = Path(__file__).resolve().parents[1]
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
    def _template(self):
        path = COMPOSITION / "template.md"
        text = path.read_text(encoding="utf-8")
        return path, text, tickets._parse_frontmatter(text)

    def test_named_invocation_closes_inputs_outputs_questions_and_dispositions(self):
        _, text, manifest = self._template()

        self.assertEqual("browser-game", manifest["name"])
        self.assertEqual("named", manifest["entry"])
        self.assertEqual(["brief", "workspace"], manifest["placeholders"])
        normalized = " ".join(text.split())
        for term in (
            "versioned program record",
            "evidence identities",
            "successor plan",
            "kind: user-only",
            "verbatim",
            "empirical",
        ):
            self.assertIn(term, normalized)
        for disposition in DISPOSITIONS:
            self.assertIn(f"`{disposition}`", text)

    def test_template_is_discoverable_instantiable_and_has_one_terminal(self):
        discovered = {
            path.name: (path, frontmatter, body)
            for path, frontmatter, body in discover_templates(ROOT)
        }
        self.assertIn("browser-game", discovered)

        stubs = {
            path.stem: tickets._parse_frontmatter(path.read_text(encoding="utf-8"))
            for path in sorted(COMPOSITION.glob("*.md"))
            if path.name != tickets.TEMPLATE_FILE
        }
        self.assertEqual(
            {
                "00-record": "orch-do",
                "01-evidence": "orch-do",
                "02-checkpoint": "orch-do",
            },
            {name: fields["executor"] for name, fields in stubs.items()},
        )
        depended_on = {
            dependency
            for fields in stubs.values()
            for dependency in fields.get("depends_on", [])
        }
        self.assertEqual({"02-checkpoint"}, set(stubs) - depended_on)

        previous = os.environ.get(tickets.state_root.ENV_VAR)
        with tempfile.TemporaryDirectory() as directory:
            os.environ[tickets.state_root.ENV_VAR] = directory
            try:
                result = tickets._cmd_instantiate(
                    [
                        str(COMPOSITION),
                        "--run",
                        "20260828T000000Z-browser-game-admission",
                        "--set",
                        "brief=an incomplete cooperative puzzle-game brief",
                        "--set",
                        "workspace=browser-game-product",
                    ]
                )
            finally:
                if previous is None:
                    os.environ.pop(tickets.state_root.ENV_VAR, None)
                else:
                    os.environ[tickets.state_root.ENV_VAR] = previous
        self.assertNotIn("error", result, result)
        self.assertIn("instantiate", result)

    def test_installer_adapter_exposes_exact_required_settings_without_legacy(self):
        path, text, _ = self._template()
        frontmatter, _ = split_frontmatter(text)
        adapter = template_adapter_body("browser-game", path.parent, frontmatter)

        self.assertIn("--set brief=<brief>", adapter)
        self.assertIn("--set workspace=<workspace>", adapter)
        self.assertEqual(2, adapter.count("--set "))
        admitted = "\n".join(
            file.read_text(encoding="utf-8") for file in sorted(COMPOSITION.rglob("*.md"))
        ) + "\n" + adapter
        for forbidden in LEGACY_INPUTS + OBSOLETE_EXECUTORS:
            self.assertNotIn(forbidden, admitted)

    def test_checkpoint_consumes_the_kind_separated_successor_plan_contract(self):
        checkpoint = (COMPOSITION / "02-checkpoint.md").read_text(encoding="utf-8")
        self.assertIn(
            "example-workflows/references/browser-game-program-record.schema.json"
            "#/$defs/successorPlanRevision",
            checkpoint,
        )
        for field in (
            "artifact identity",
            "artifact kind",
            "pack",
            "run/root identities",
            "dependencies",
            "status",
        ):
            self.assertIn(field, " ".join(checkpoint.split()))


if __name__ == "__main__":
    unittest.main()
