"""Shipped authoring entry point and its concrete external output seam."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import install
from scripts import standards
from tests._repo_root import ROOT


BUILDER = "orch-build-workflow"
QUALITY = "orch-workflow-authoring"
PACKAGE = ROOT / "example-workflows" / BUILDER


class BuildWorkflowTests(unittest.TestCase):
    def test_default_distribution_has_one_manual_roleless_builder(self):
        workflows = install.discover_workflow_skills()
        self.assertEqual(1, sum(path.name == BUILDER for path, _, _ in workflows))
        with tempfile.TemporaryDirectory() as raw:
            with patch.object(install.Path, "home", return_value=Path(raw)), \
                    patch("installer.planning.detect_hosts", return_value=(True, True, True)):
                plan = install.build_plan()
        for surfaces in (plan.claude_adapters, plan.codex_skills, plan.grok_skills):
            matches = [body for path, body in surfaces if path.parent.name == BUILDER]
            self.assertEqual(1, len(matches))
            frontmatter, _ = install.split_frontmatter(matches[0])
            if surfaces is not plan.grok_skills:
                self.assertEqual("true", install.frontmatter_field(
                    frontmatter, "disable-model-invocation"))
            for field in ("role", "agent", "context"):
                self.assertIsNone(install.frontmatter_field(frontmatter, field))
            self.assertFalse(any(path.parent.name == QUALITY for path, _ in surfaces))
        self.assertEqual(1, sum(path.parent.name == QUALITY for path, _ in plan.by_name))
        self.assertIn(PACKAGE / "references" / "dogfood.md",
                      [source for source, _ in plan.lib_copies])

    def test_authoring_narrowing_expands_in_public_callee_scope(self):
        # No caller-private scope: the callee resolves from the ordinary library.
        chain = standards.resolve_chain([QUALITY], lib_dir=ROOT / "standards")
        self.assertEqual(["orch-code", QUALITY], [item["name"] for item in chain])
        repeated = standards.resolve_chain(
            ["orch-code", QUALITY], lib_dir=ROOT / "standards")
        self.assertEqual(chain, repeated)

    def test_receipt_probe_rejects_missing_and_corrupt_output(self):
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            fixture = (PACKAGE / "references" / "dogfood.md").read_text(encoding="utf-8")
            probe = fixture.split("```python\n", 1)[1].split("```", 1)[0]
            command = [sys.executable, "-c", probe, raw]
            for payload, expected in ((None, 1), (b"wrong\n", 1),
                                      (b"layered workflow admitted\n", 0)):
                with self.subTest(payload=payload):
                    if payload is not None:
                        (workspace / "receipt.txt").write_bytes(payload)
                    result = subprocess.run(command, capture_output=True, text=True,
                                            timeout=30, check=False)
                    self.assertEqual(expected, result.returncode, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
