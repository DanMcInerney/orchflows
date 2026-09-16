"""Native plugin entrypoints must describe the same complete package."""

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PluginPackageTests(unittest.TestCase):
    def test_host_manifests_match_package_identity_and_reachable_skills(self):
        packages = [ROOT, *sorted((ROOT / "example-workflows").iterdir())]
        for package in packages:
            if not (package / "plugin.json").is_file():
                continue
            identity = json.loads((package / "plugin.json").read_text(encoding="utf-8"))
            for host in (".claude-plugin", ".codex-plugin", ".kimi-plugin"):
                with self.subTest(package=package.name, host=host):
                    manifest = json.loads((package / host / "plugin.json").read_text(encoding="utf-8"))
                    self.assertEqual(manifest["name"], identity["name"])
                    self.assertEqual(manifest["version"], identity["version"])
                    skills = (package / manifest["skills"]).resolve()
                    self.assertTrue(skills.is_relative_to(package))
                    self.assertTrue(list(skills.glob("*/SKILL.md")))

    def test_zcode_checkout_catalog_loads_core_at_its_current_version(self):
        catalog = json.loads((ROOT / "marketplace.json").read_text(encoding="utf-8"))
        self.assertEqual(catalog["name"], "orchflows-local")
        self.assertEqual(len(catalog["plugins"]), 1)
        entry = catalog["plugins"][0]
        package = (ROOT / entry["source"]).resolve()
        self.assertEqual(package, ROOT)
        native = json.loads((package / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
        self.assertEqual((entry["name"], entry["version"]), (native["name"], native["version"]))


if __name__ == "__main__":
    unittest.main()
