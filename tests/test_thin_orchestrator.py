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


from tests._repo_root import ROOT
PROFILE_OWNER_LINK = "[role profiles](../hosts/profiles.md)"


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


def _skill_path(name: str) -> str:
    return f"skills/kernel/{name}/SKILL.md"


class ThinOrchestratorContractTests(unittest.TestCase):
    WORKFLOW_ROLES = {
        "orch-judge": "planner",
        "orch-do": "worker",
    }

    def test_canonical_role_map_and_glue_only_contract(self):
        for name, role in self.WORKFLOW_ROLES.items():
            with self.subTest(skill=name):
                self.assertEqual(
                    role,
                    _frontmatter(_skill_path(name))["role"],
                )

        # No skill is glue any more: the driver and the join are commands,
        # so every callable declares planner or worker. The kernel tier is
        # where the callables are; `skills/workflows/` is the library's
        # other skills tier, and a body there is prose a driver reads by
        # name rather than a callable anything dispatches -- so it answers
        # to the same no-glue reading and to no entry in this map. That the
        # tier actually carries one is
        # tests/test_catalog_completeness.py's population check.
        self.assertEqual(
            set(self.WORKFLOW_ROLES),
            {path.parent.name for path in (ROOT / "skills" / "kernel").rglob("SKILL.md")},
        )
        for path in sorted((ROOT / "skills" / "workflows").rglob("SKILL.md")):
            with self.subTest(workflow=path.parent.name):
                self.assertNotIn(
                    "role",
                    _frontmatter(path.relative_to(ROOT).as_posix()),
                    "a workflow declares no role: its prose runs in the "
                    "orchestrator's own context, so there is no role for a "
                    "host surface to bind (validate_role refuses one here)",
                )

        delegation = (ROOT / "rules/delegation.md").read_text(encoding="utf-8")
        roles = (ROOT / "rules/roles.md").read_text(encoding="utf-8")
        profiles = (ROOT / "hosts/profiles.md").read_text(encoding="utf-8")
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
            "**direct**",
            "**worker**",
            "**team**",
            "**plan**",
            "`launch`",
            "`tickets.py do <run>",
            "`tickets.py land`",
            # The UX contract's write-the-shape sentence, which replaced the
            # say-the-lane one; a seam-judge blocker (F1, run
            # 20260901T021739Z) found that one cut for budget with no anchor
            # here to catch it.
            "write the run's shape line before the first dispatch",
        ):
            self.assertIn(anchor, collapsed_host)
        authoring_pointer = "{{ORCH_LIB}}/docs/custom-workflow-authoring.md"
        self.assertEqual(1, host.count(authoring_pointer))
        self.assertRegex(
            collapsed_host,
            re.compile(r"Skill/workflow/pack/contract/router work carries .*custom-workflow-authoring\.md` in Context"),
        )
        self.assertNotIn("**errand**", collapsed_host)
        self.assertNotIn("sequence: [orch-outline, orch-slice]", host)
        self.assertLessEqual(validate.body_words(host), 400)

    def test_team_lane_emits_the_wave_lifecycle(self):
        """The team lane is the whole wave: open the frame, re-read its
        journal, run children at scoped checks, and close. Each anchor is a
        step a driver cannot supply from its own reading, and the journal
        re-read is the one that survives a compaction nothing else notices.
        The per-child invocation itself is the worker command's own text, so the
        team lane does not re-teach it -- see
        test_host_and_frontier_establish_the_workspace_before_dispatch."""
        host = re.sub(
            r"\s+",
            " ",
            (ROOT / "templates/host-block.md").read_text(encoding="utf-8"),
        )
        team = host.partition("**team**")[2].partition("**plan**")[0]

        for anchor in (
            "tickets.py frame-open <run>",
            "each wave re-read its `## Report`",
            "`artifact:` and `findings:` lines verbatim",
            "`frame-close`",
            "`unjudged: <reason>`",
            "`orchflows resume`",
        ):
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, team)
        # The facade owns each of these; the route may not re-teach a manual
        # spelling of a step a worker command or `land` already performs.
        for absent in (
            "tickets.py claim",
            "tickets.py packet",
            "tickets.py dispatch-open",
            "tickets.py dispatch-packet",
            "tickets.py dispatch-join",
            "tickets.py dispatch-receive",
            "workspace.py establish",
        ):
            with self.subTest(absent=absent):
                self.assertNotIn(absent, team)

    def test_host_and_frontier_establish_the_workspace_before_dispatch(self):
        host = re.sub(
            r"\s+",
            " ",
            (ROOT / "templates/host-block.md").read_text(encoding="utf-8"),
        )
        worker = host.partition("**worker**")[2].partition("**team**")[0]

        self.assertIn("tickets.py do", worker)
        self.assertLess(
            worker.index("tickets.py do"), worker.index("tickets.py land")
        )
        # Establishment is inside the dispatch transaction, so the contract
        # that owns the transaction states it and the route does not repeat
        # it as a step of its own.
        dispatch_contract = (ROOT / "contracts/dispatch.md").read_text(encoding="utf-8")
        self.assertIn("the established workspace", dispatch_contract)
        self.assertNotIn("workspace.py establish", worker)

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
            "launch-stated ordered sequence",
            "never hand your ticket or role to another agent",
        ):
            self.assertIn(anchor, role_agent)

    def test_plan_route_consumes_the_root_shape_it_sealed(self):
        host = re.sub(
            r"\s+",
            " ",
            (ROOT / "templates/host-block.md").read_text(encoding="utf-8"),
        )
        spec_route = host.split("**plan**", 1)[1].split("`install.py doctor`", 1)[0]

        for anchor in (
            "an unresolved goal",
            "one planning `orch-do`",
            "the planner never drives",
            # The two named tripwires a seam-judge blocker (F1, run
            # 20260901T021739Z) found cut for budget with no anchor here to
            # catch it; the third (unknown cause) was already pinned via
            # "cause investigates before any edit" below.
            "a second concern mid-direct enters worker",
            "splitting scope enters team",
            "an unknown cause investigates before any edit",
        ):
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, spec_route)

        self.assertRegex(spec_route, r"unresolved goal.*one planning `orch-do`")
        self.assertIn("planner never drives", spec_route)

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
                    "emitted launch prompt",
                    "matching role",
                    "directly",
                    "refuse",
                ):
                    self.assertIn(anchor, prompt)
                self.assertNotIn("automatic binding", prompt)
                self.assertNotIn("root guard", prompt)
                self.assertNotIn("hook", prompt.lower())

        for name in {"orch-judge", "orch-do"}:
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
            "launch-stated ordered sequence",
            "never hand your ticket or role to another agent",
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
