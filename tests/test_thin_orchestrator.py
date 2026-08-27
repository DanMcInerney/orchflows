"""Focused acceptance oracle for the thin-orchestrator contract."""

from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import install
from installer.packages import codex_role_adapter_body
from tools import validate


ROOT = Path(__file__).resolve().parents[1]
PROFILE_OWNER_LINK = (
    "[role profiles](../skills/engines/orch-frontier/references/profiles.md)"
)


def _custom_routing_uses_profile_owner(text: str) -> bool:
    return (
        PROFILE_OWNER_LINK in text
        and "resolve the declared role" in text
        and "use the native binding that owner returns" in text
        and not re.search(r"\b(?:derive|reconstruct|synthesize)\b", text)
    )


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
        collapsed_host = re.sub(r"\s+", " ", host)
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
        for anchor in (
            "**answer**",
            "**single**",
            "**graph**",
            "**spec**",
            "one same planner child",
            "`ready` → `claim` → `packet`",
            "outer coordinator",
        ):
            self.assertIn(anchor, collapsed_host)
        authoring_pointer = "{{ORCH_LIB}}/docs/custom-workflow-authoring.md"
        self.assertEqual(1, host.count(authoring_pointer))
        self.assertRegex(
            collapsed_host,
            re.compile(r"Skill/composition/pack/contract/router work uses those routes; seal .*custom-workflow-authoring\.md` in Context"),
        )
        decompose = (ROOT / "skills/kernel/orch-decompose/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("relevant Context", decompose)
        self.assertNotIn("**errand**", collapsed_host)
        self.assertNotIn("sequence: [orch-spec, orch-decompose]", host)
        self.assertLessEqual(validate.body_words(host), 400)

    def test_graph_lane_emits_the_complete_decompose_packet(self):
        host = re.sub(
            r"\s+",
            " ",
            (ROOT / "templates/host-block.md").read_text(encoding="utf-8"),
        )
        graph = host.partition("**graph**")[2].partition("**spec**")[0]

        for anchor in (
            "stamped root",
            "tickets.py ready --run <run>",
            "tickets.py claim <run> <root> --by <assigned-name>",
            "tickets.py packet <run> <root> --reply-to <parent-name> "
            "--by <assigned-name> --workspace <tree>",
            "exact `orch-decompose`",
            "matching `orch-planner` child",
            "complete emitted packet",
            "ticket path is not a packet",
            "outer coordinator integrates",
            "starts `orch-frontier`",
        ):
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, graph)

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
        for anchor in (
            "exact primary skill",
            "each exact member",
            "packet-stated ordered sequence",
            "directly",
            "never redispatch",
        ):
            self.assertIn(anchor, role_agent)

    def test_spec_route_consumes_the_root_shape_it_sealed(self):
        host = re.sub(
            r"\s+",
            " ",
            (ROOT / "templates/host-block.md").read_text(encoding="utf-8"),
        )
        spec_route = host.split("**spec**", 1)[1].split("**fix**", 1)[0]

        for anchor in (
            "direct root",
            "one lawful executor",
            "`orch-decompose` root",
            "distinct outcomes or dependencies",
            "same planner",
            "`ready` → `claim` → `packet`",
            "outer coordinator",
            "`orch-frontier`",
        ):
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, spec_route)

        self.assertRegex(spec_route, r"same planner.*`orch-decompose` root")
        self.assertRegex(spec_route, r"outer coordinator.*`orch-frontier`")

    def test_codex_named_surfaces_dispatch_or_refuse_and_child_runs_directly(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".codex").mkdir()
            with patch.object(install.Path, "home", return_value=home), patch.object(
                install.shutil, "which", return_value="codex"
            ):
                plan = install.build_plan("user", None)

        prompts = {dest.stem: content for dest, content in plan.codex_prompts}
        redirects = {dest.parent.name: content for dest, content in plan.codex_skills}
        for name, role in self.WORKFLOW_ROLES.items():
            with self.subTest(prompt=name):
                prompt = prompts[name]
                for anchor in (
                    f"agent_type `orch_{role}`",
                    "fork_turns `none`",
                    f"`{name}`",
                    "complete packet",
                    "matching role",
                    "directly",
                    "refuse",
                ):
                    self.assertIn(anchor, prompt)
                self.assertNotIn("automatic binding", prompt)
                self.assertNotIn("root guard", prompt)
                self.assertNotIn("hook", prompt.lower())

        for name in {"orch-spec", "orch-repair"}:
            with self.subTest(redirect=name):
                content = redirects[name]
                role = self.WORKFLOW_ROLES[name]
                self.assertIn(f"agent_type `orch_{role}`", content)
                self.assertIn("fork_turns `none`", content)
                self.assertIn("matching role", content)
                self.assertIn("refuse", content)

        role_agent = install.render_codex_agent(
            "orch-planner", install.load_role_profiles()["orch-planner"]
        )
        for anchor in (
            "exact primary skill",
            "each exact member",
            "packet-stated ordered sequence",
            "directly",
            "never redispatch",
            "mismatched",
        ):
            self.assertIn(anchor, role_agent)

    def test_custom_codex_routing_uses_the_resolved_native_binding(self):
        rendered = codex_role_adapter_body(
            "custom-worker",
            "worker",
            {
                "role": "worker",
                "codex": {"agent_type": "resolved_worker", "fork_turns": "3"},
            },
            Path("X"),
        )
        self.assertIn("agent_type `resolved_worker`", rendered)
        self.assertIn("fork_turns `3`", rendered)
        with self.assertRaisesRegex(ValueError, "declared role planner.*profile role worker"):
            codex_role_adapter_body(
                "custom-planner",
                "planner",
                {
                    "role": "worker",
                    "codex": {"agent_type": "resolved_worker", "fork_turns": "3"},
                },
                Path("X"),
            )

        scopes = (ROOT / "docs/custom-workflow-authoring.md").read_text(encoding="utf-8")
        self.assertTrue(_custom_routing_uses_profile_owner(scopes))
        reconstructed = scopes.replace(
            "use the native binding that owner returns",
            "reconstruct agent_type and fork_turns from the role name",
        )
        self.assertFalse(_custom_routing_uses_profile_owner(reconstructed))


if __name__ == "__main__":
    unittest.main()
