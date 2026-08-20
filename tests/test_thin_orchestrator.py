"""Focused acceptance oracle for the thin-orchestrator contract."""

from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import install
from tools import validate


ROOT = Path(__file__).resolve().parents[1]


def _frontmatter(path: str) -> dict[str, str]:
    text = (ROOT / path).read_text(encoding="utf-8")
    frontmatter = text.split("---", 2)[1]
    return {
        key.strip(): value.strip()
        for line in frontmatter.splitlines()
        if (key := line.partition(":")[0]) and (value := line.partition(":")[2])
    }


class ThinOrchestratorContractTests(unittest.TestCase):
    WORKFLOW_ROLES = {
        "orch-spec": "planner",
        "orch-eval-design": "planner",
        "orch-self-improve": "planner",
        "orch-triage": "planner",
        "orch-build": "worker",
        "orch-fixture": "worker",
        "orch-repair": "worker",
    }

    def test_canonical_role_map_and_glue_only_contract(self):
        for name, role in self.WORKFLOW_ROLES.items():
            with self.subTest(skill=name):
                self.assertEqual(
                    role,
                    _frontmatter(f"skills/workflows/{name}/SKILL.md")["role"],
                )

        glue = {
            "skills/engines/orch-frontier/SKILL.md",
            "skills/engines/orch-loop/SKILL.md",
            "skills/kernel/orch-integrate/SKILL.md",
            "skills/utilities/orch-off/SKILL.md",
        }
        for path in glue:
            with self.subTest(glue=path):
                self.assertEqual("none", _frontmatter(path)["role"])

        delegation = (ROOT / "rules/delegation.md").read_text(encoding="utf-8")
        roles = (ROOT / "rules/roles.md").read_text(encoding="utf-8")
        profiles = (
            ROOT / "skills/engines/orch-frontier/references/profiles.md"
        ).read_text(encoding="utf-8")
        host = (ROOT / "templates/host-block.md").read_text(encoding="utf-8")
        combined = "\n".join((delegation, roles, profiles, host))

        for anchor in (
            "glue-only",
            "role-bearing",
            "exact named skill",
            "matching role",
            "user-only",
            "verbatim",
        ):
            self.assertIn(anchor, combined)
        self.assertNotIn("ad-hoc ticket", delegation)
        self.assertNotRegex(delegation, re.compile(r"inline fallback", re.I))
        self.assertLessEqual(validate.body_words(host), 400)

    def test_claude_role_skills_use_native_fork_and_matching_agent(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".claude").mkdir()
            with patch.object(install.Path, "home", return_value=home), patch.object(
                install.shutil, "which", return_value="claude"
            ):
                plan = install.build_plan("user", None)

        adapters = {dest.parent.name: content for dest, content in plan.claude_adapters}
        for skill_md in install.discover_packages():
            frontmatter, _body = install.split_frontmatter(
                skill_md.read_text(encoding="utf-8")
            )
            name = install.frontmatter_field(frontmatter, "name")
            role = install.frontmatter_field(frontmatter, "role")
            if role not in {"planner", "worker"}:
                continue
            with self.subTest(skill=name):
                adapter_frontmatter, _ = install.split_frontmatter(adapters[name])
                self.assertEqual(
                    "fork", install.frontmatter_field(adapter_frontmatter, "context")
                )
                self.assertEqual(
                    f"orch-{role}",
                    install.frontmatter_field(adapter_frontmatter, "agent"),
                )
                self.assertIsNone(
                    install.frontmatter_field(adapter_frontmatter, "role")
                )

        role_agent = install.render_claude_agent(
            "orch-worker", install.load_role_profiles()["orch-worker"]
        )
        for anchor in ("exact named skill", "directly", "never redispatch"):
            self.assertIn(anchor, role_agent)


if __name__ == "__main__":
    unittest.main()
