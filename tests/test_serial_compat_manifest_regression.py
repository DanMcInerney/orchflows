"""Regression pin for installer test identities in the serial manifest."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "tests" / "serial_compat_manifest.json"


class TestCodexRedirectManifestRegression(unittest.TestCase):
    def test_the_codex_redirect_test_identities_stay_serial_compatible(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        identities = set(manifest["discovery"]["identities"])

        self.assertIn(
            "test_installer.TestClaudeAdapterSet."
            "test_installer_description_says_codex_redirects_every_canonical_name",
            identities,
        )
        self.assertIn(
            "test_installer.TestScopedHostConfiguration."
            "test_user_plan_writes_claude_adapters_and_codex_skill_stubs",
            identities,
        )

        scoped_host_owners = [
            owner
            for owner in manifest["mutation_owners"]
            if owner["module"] == "tests.test_installer_cases.planning.scoped_hosts"
            and owner["owner"].startswith(
                "TestScopedHostConfiguration.test_user_plan_writes_claude_adapters"
            )
        ]
        self.assertEqual(
            [
                {
                    "module": "tests.test_installer_cases.planning.scoped_hosts",
                    "owner": (
                        "TestScopedHostConfiguration."
                        "test_user_plan_writes_claude_adapters_and_codex_skill_stubs"
                    ),
                    "restoration": "sharded-module-guard",
                    "seams": ["monkeypatch"],
                }
            ],
            scoped_host_owners,
        )


if __name__ == "__main__":
    unittest.main()
