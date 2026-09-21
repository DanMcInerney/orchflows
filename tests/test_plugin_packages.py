"""Native plugin entrypoints must describe the same complete package."""

import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


SHIPPED = [ROOT, *sorted(path for path in (ROOT / "example-workflows").iterdir() if (path / "plugin.json").is_file())]
FIXTURES = sorted({path.parent for pattern in ("tests/e2e/cases/**/packages/*/plugin.json", "example-workflows/*/trials/**/plugin.json")
                   for path in ROOT.glob(pattern) if not path.parent.name.startswith(".")})
QUALIFIED = re.compile(r"(?<![\w/.:-])([a-z0-9][a-z0-9-]*):([a-z0-9][a-z0-9-]*)(?![\w-])")
BARE_CORE = re.compile(r"(?<![\w/.:-])(orch-[a-z-]+)(?![\w-])")


def package_skills(package: Path) -> dict[str, Path]:
    name = json.loads((package / "plugin.json").read_text(encoding="utf-8"))["name"]
    return {f"{name}:{skill.parent.name}": skill.parent for skill in (package / "skills").glob("*/SKILL.md")}


def named_dependencies(skills: dict[str, Path]) -> set[str]:
    """Skills that another skill, reference, doc or guidance file loads by name."""
    named = set()
    for package in SHIPPED + FIXTURES:
        for folder in ("skills", "references", "guidance", "docs"):
            for path in (package / folder).rglob("*.md"):
                text = path.read_text(encoding="utf-8")
                names = {":".join(match) for match in QUALIFIED.findall(text)}
                if package != ROOT:
                    names |= {f"orchflows:{match}" for match in BARE_CORE.findall(text)}
                named |= {name for name in names if name in skills and not path.is_relative_to(skills[name])}
    return named


class PluginPackageTests(unittest.TestCase):
    def test_named_dependencies_allow_model_invocation_and_entrypoints_stay_manual(self):
        # Hosts cannot load manual-only skills by name, even for a workflow.
        skills = {key: path for package in SHIPPED for key, path in package_skills(package).items()}
        named = named_dependencies({**skills, **{k: v for p in FIXTURES for k, v in package_skills(p).items()}})
        self.assertLessEqual({"orchflows:orch-work", "orchflows:orch-review", "shared:review-revise-once"}, named)
        for key, skill in sorted(skills.items()):
            with self.subTest(skill=key):
                frontmatter = (skill / "SKILL.md").read_text(encoding="utf-8").split("---", 2)[1]
                claude = [line.split(":", 1)[1].strip() for line in frontmatter.splitlines()
                          if line.startswith("disable-model-invocation:")]
                metadata = (skill / "agents/openai.yaml").read_text(encoding="utf-8")
                codex = [line.split(":", 1)[1].strip() for line in metadata.splitlines()
                         if line.strip().startswith("allow_implicit_invocation:")]
                invocable = key == "orchflows:orch-dynamic-workflow" or key in named
                self.assertEqual(claude, ["false" if invocable else "true"])
                self.assertEqual(codex, ["true" if invocable else "false"])

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
