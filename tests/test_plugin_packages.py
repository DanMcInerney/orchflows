"""Native plugin entrypoints must describe the same complete package."""

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PluginPackageTests(unittest.TestCase):
    def test_only_dynamic_workflow_allows_automatic_selection(self):
        packages = [ROOT, *sorted((ROOT / "example-workflows").iterdir())]
        automatic = []
        for package in packages:
            for skill in sorted((package / "skills").glob("*/SKILL.md")):
                with self.subTest(skill=str(skill.relative_to(ROOT))):
                    frontmatter = skill.read_text(encoding="utf-8").split("---", 2)[1]
                    claude = [line.split(":", 1)[1].strip() for line in frontmatter.splitlines()
                              if line.startswith("disable-model-invocation:")]
                    metadata = (skill.parent / "agents/openai.yaml").read_text(encoding="utf-8")
                    codex = [line.split(":", 1)[1].strip() for line in metadata.splitlines()
                             if line.strip().startswith("allow_implicit_invocation:")]
                    is_dynamic = skill == ROOT / "skills/orch-dynamic-workflow/SKILL.md"
                    self.assertEqual(claude, ["false" if is_dynamic else "true"])
                    self.assertEqual(codex, ["true" if is_dynamic else "false"])
                    if is_dynamic:
                        automatic.append(skill)
        self.assertEqual(len(automatic), 1)

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
