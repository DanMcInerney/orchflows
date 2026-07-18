"""Installer receipts and conservative uninstall behavior."""

import hashlib
import io
import json
import re
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path, PurePosixPath
from unittest.mock import patch

import install


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TestScriptNames(unittest.TestCase):
    """Behavioral replacement: SCRIPT_NAMES only matters if every named
    script actually reaches the installed bin dir with matching content --
    checking membership in the tuple two lines from its own declaration
    proved nothing about install.py's behavior."""

    def test_build_plan_installs_every_managed_script_with_matching_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".claude").mkdir(parents=True)
            with patch.object(install.Path, "home", return_value=home):
                plan = install.build_plan("user", None)
                install.apply_plan(plan)

            self.assertEqual(set(install.SCRIPT_NAMES), {path.name for _, path in plan.scripts})
            for name in install.SCRIPT_NAMES:
                installed = plan.bin_dir / name
                self.assertTrue(installed.is_file(), f"{name} was not installed to {plan.bin_dir}")
                source = install.REPO_ROOT / "scripts" / name
                self.assertEqual(source.read_bytes(), installed.read_bytes())


class TestInstallReceipt(unittest.TestCase):
    def test_receipt_records_actions_and_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project"
            project.mkdir()
            source = root / "source.md"
            source.write_text("new library\n", encoding="utf-8")
            script_source = root / "tool.py"
            script_source.write_text("print('new')\n", encoding="utf-8")

            lib_dest = project / ".orchflows" / "lib" / "source.md"
            lib_dest.parent.mkdir(parents=True)
            lib_dest.write_text("old library\n", encoding="utf-8")
            script_dest = project / ".orch" / "bin" / "tool.py"
            script_dest.parent.mkdir(parents=True)
            script_dest.write_text("print('old')\n", encoding="utf-8")
            adapter_dest = project / ".claude" / "skills" / "orch-test" / "SKILL.md"
            agents = project / "AGENTS.md"
            agents.write_text("user instructions\n", encoding="utf-8")

            plan = install.Plan(
                scope="project",
                project_root=project,
                lib_home=project / ".orchflows" / "lib",
                scope_home=project / ".orchflows",
                bin_dir=project / ".orch" / "bin",
                receipt_path=project / ".orchflows" / "receipt.json",
                lib_copies=[(source, lib_dest)],
                scripts=[(script_source, script_dest)],
                claude_adapters=[(adapter_dest, "---\nname: orch-test\n---\n@library\n")],
                blocks=[
                    install.BlockPlan(
                        agents,
                        "# BEGIN TEST\nmanaged\n# END TEST\n",
                        "# BEGIN TEST",
                        "# END TEST",
                        "test block",
                    )
                ],
            )

            receipt = install.apply_plan(plan)

            self.assertEqual(4, receipt["version"])
            self.assertIn("source_commit", receipt)
            files = {entry["kind"]: entry for entry in receipt["files"]}
            self.assertEqual("replaced", files["lib"]["install_action"])
            self.assertEqual("replaced", files["script"]["install_action"])
            self.assertEqual("created", files["adapter"]["install_action"])
            for entry in receipt["files"]:
                self.assertEqual(digest(Path(entry["path"])), entry["sha256"])
            self.assertEqual("added-block", receipt["blocks"][0]["install_action"])

    def test_unowned_role_profile_blocks_install_before_any_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            source = project / "source.md"
            source.write_text("new library\n", encoding="utf-8")
            lib_dest = project / ".orchflows" / "lib" / "source.md"
            agent = project / ".codex" / "agents" / "orch-worker.toml"
            agent.parent.mkdir(parents=True)
            agent.write_text("personal = true\n", encoding="utf-8")
            plan = install.Plan(
                scope="project",
                project_root=project,
                lib_home=project / ".orchflows" / "lib",
                scope_home=project / ".orchflows",
                bin_dir=project / ".orch" / "bin",
                receipt_path=project / ".orchflows" / "receipt.json",
                lib_copies=[(source, lib_dest)],
                codex_agents=[(agent, 'name = "orch-worker"\n')],
            )

            with self.assertRaisesRegex(FileExistsError, "not owned"):
                install.apply_plan(plan)

            self.assertEqual("personal = true\n", agent.read_text(encoding="utf-8"))
            self.assertFalse(lib_dest.exists())

    def test_modified_receipt_owned_role_profile_blocks_reinstall(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            agent = project / ".claude" / "agents" / "orch-planner.md"
            agent.parent.mkdir(parents=True)
            agent.write_text("modified\n", encoding="utf-8")
            receipt = project / ".orchflows" / "receipt.json"
            receipt.parent.mkdir(parents=True)
            receipt.write_text(
                json.dumps(
                    {
                        "files": [
                            {
                                "path": str(agent),
                                "kind": "claude-agent",
                                "sha256": hashlib.sha256(b"installed\n").hexdigest(),
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            plan = install.Plan(
                scope="project",
                project_root=project,
                lib_home=project / ".orchflows" / "lib",
                scope_home=project / ".orchflows",
                bin_dir=project / ".orch" / "bin",
                receipt_path=receipt,
                claude_agents=[(agent, "updated\n")],
            )

            with self.assertRaisesRegex(FileExistsError, "changed since"):
                install.apply_plan(plan)

    def test_legacy_header_role_profile_without_receipt_blocks_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            agent = project / ".codex" / "agents" / "orch-worker.toml"
            agent.parent.mkdir(parents=True)
            legacy_header = (
                "# Managed by orchflows install.py.\n"
                "# This complete file is replaced on every orchflows install.\n"
            )
            agent.write_text(legacy_header + "old = true\n", encoding="utf-8")
            plan = install.Plan(
                scope="project",
                project_root=project,
                lib_home=project / ".orchflows" / "lib",
                scope_home=project / ".orchflows",
                bin_dir=project / ".orch" / "bin",
                receipt_path=project / ".orchflows" / "receipt.json",
                codex_agents=[(agent, 'name = "orch-worker"\n')],
            )

            with self.assertRaisesRegex(FileExistsError, "not owned"):
                install.apply_plan(plan)

            self.assertEqual(legacy_header + "old = true\n", agent.read_text(encoding="utf-8"))

    def test_reinstall_removes_receipt_owned_hyphenated_codex_agent(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            old_agent = project / ".codex" / "agents" / "orch-worker.toml"
            old_agent.parent.mkdir(parents=True)
            old_agent.write_text('name = "orch-worker"\n', encoding="utf-8")
            receipt = project / ".orchflows" / "receipt.json"
            receipt.parent.mkdir(parents=True)
            receipt.write_text(
                json.dumps(
                    {
                        "files": [
                            {
                                "path": str(old_agent),
                                "kind": "codex-agent",
                                "sha256": digest(old_agent),
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            new_agent = project / ".codex" / "agents" / "orch_worker.toml"
            plan = install.Plan(
                scope="project",
                project_root=project,
                lib_home=project / ".orchflows" / "lib",
                scope_home=project / ".orchflows",
                bin_dir=project / ".orch" / "bin",
                receipt_path=receipt,
                codex_agents=[(new_agent, 'name = "orch_worker"\n')],
            )

            install.apply_plan(plan)

            self.assertFalse(old_agent.exists())
            self.assertEqual('name = "orch_worker"\n', new_agent.read_text(encoding="utf-8"))


class TestScopedHostConfiguration(unittest.TestCase):
    def test_invalid_codex_agent_type_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            profiles = Path(tmp) / "profiles.md"
            content = install.PROFILES_MD.read_text(encoding="utf-8").replace(
                "agent_type `orch_planner`", "agent_type `orch-planner`", 1
            )
            profiles.write_text(content, encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "invalid Codex agent_type"):
                install.load_role_profiles(profiles)

    def test_codex_role_agent_names_follow_spawn_identifier_grammar(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".codex").mkdir(parents=True)
            with patch.object(install.Path, "home", return_value=home):
                plan = install.build_plan("user", None)

            parsed_agents = [
                (dest, install.tomllib.loads(content)) for dest, content in plan.codex_agents
            ]
            self.assertEqual(
                {"orch_planner", "orch_worker"},
                {parsed["name"] for _, parsed in parsed_agents},
            )
            for dest, parsed in parsed_agents:
                self.assertEqual(dest.stem, parsed["name"])
                self.assertIsNotNone(re.fullmatch(r"[a-z0-9_]+", parsed["name"]))

    def test_user_plan_merges_limits_and_writes_native_role_agents(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            claude_settings = home / ".claude" / "settings.json"
            claude_settings.parent.mkdir(parents=True)
            claude_settings.write_text(
                json.dumps({"theme": "dark", "env": {"EXISTING": "1"}}), encoding="utf-8"
            )
            codex_config = home / ".codex" / "config.toml"
            codex_config.parent.mkdir(parents=True)
            codex_config.write_text(
                "[agents]\nmax_threads = 2\ncustom = true\n\n[other]\nvalue = 1\n",
                encoding="utf-8",
            )

            with patch.object(install.Path, "home", return_value=home):
                plan = install.build_plan("user", None)

            configs = {config.kind: config for config in plan.configs}
            claude = json.loads(configs["claude-config"].content)
            self.assertEqual("dark", claude["theme"])
            self.assertEqual("1", claude["env"]["EXISTING"])
            self.assertEqual("20", claude["env"]["CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY"])
            codex = install.tomllib.loads(configs["codex-config"].content)
            self.assertEqual(20, codex["agents"]["max_threads"])
            self.assertEqual(1, codex["agents"]["max_depth"])
            self.assertTrue(codex["agents"]["custom"])
            self.assertEqual(1, codex["other"]["value"])

            self.assertEqual(2, len(plan.claude_agents))
            self.assertEqual(2, len(plan.codex_agents))
            for dest, content in plan.claude_agents:
                self.assertEqual(home / ".claude" / "agents", dest.parent)
                self.assertIn("name: orch-", content)
            for dest, content in plan.codex_agents:
                self.assertEqual(home / ".codex" / "agents", dest.parent)
                parsed = install.tomllib.loads(content)
                self.assertIn(parsed["name"], {"orch_planner", "orch_worker"})
                self.assertIn("developer_instructions", parsed)

    def test_user_plan_writes_claude_adapters_and_four_codex_skill_stubs(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".claude").mkdir(parents=True)
            (home / ".codex").mkdir(parents=True)
            with patch.object(install.Path, "home", return_value=home):
                plan = install.build_plan("user", None)

            self.assertEqual(len(install.discover_packages()), len(plan.claude_adapters))
            expected_lib_path = (home / ".orchflows" / "lib").resolve()
            for dest, content in plan.claude_adapters:
                self.assertEqual(home / ".claude" / "skills", dest.parent.parent)
                self.assertEqual("SKILL.md", dest.name)
                frontmatter, body = install.split_frontmatter(content)
                self.assertIn("name:", frontmatter)
                self.assertIn("description:", frontmatter)
                self.assertNotIn("role:", frontmatter)
                self.assertTrue(body.strip().startswith("@"))
                self.assertIn(str(expected_lib_path), body)

            self.assertEqual(
                {"orch-spec", "orch-task", "orch-fix", "orch-build"},
                {dest.parent.name for dest, _ in plan.codex_skills},
            )
            for dest, content in plan.codex_skills:
                self.assertEqual(home / ".codex" / "skills", dest.parent.parent)
                self.assertEqual("SKILL.md", dest.name)
                frontmatter, body = install.split_frontmatter(content)
                self.assertIn(f"name: {dest.parent.name}", frontmatter)
                self.assertIn("description:", frontmatter)
                self.assertIn(str(expected_lib_path), body)
                self.assertIn("follow it exactly.", body)

    def test_user_plan_writes_flat_by_name_index_for_every_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".claude").mkdir(parents=True)
            (home / ".codex").mkdir(parents=True)
            with patch.object(install.Path, "home", return_value=home):
                plan = install.build_plan("user", None)

            by_name_root = (home / ".orchflows" / "lib" / "by-name").resolve()
            expected_lib_path = (home / ".orchflows" / "lib").resolve()
            packages = install.discover_packages()
            # One flat entry per canonical package — skills across every tier and
            # packs alike — keyed by the bare orch-name, no tier in the path.
            self.assertEqual(len(packages), len(plan.by_name))
            self.assertEqual(
                {p.parent.name for p in packages},
                {dest.parent.name for dest, _ in plan.by_name},
            )
            for dest, content in plan.by_name:
                self.assertEqual(by_name_root, dest.parent.parent.resolve())
                self.assertEqual("SKILL.md", dest.name)
                frontmatter, body = install.split_frontmatter(content)
                self.assertIn(f"name: {dest.parent.name}", frontmatter)
                # Pointer only — names the canonical source, never duplicates it.
                self.assertIn(str(expected_lib_path), body)
                self.assertIn("follow it exactly.", body)

    def test_by_name_index_is_host_agnostic(self):
        # The flat index lives in the shared library, so it is built whether or
        # not either host surface is present — a Codex-only install still gets it.
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".codex").mkdir(parents=True)
            with patch.object(install.Path, "home", return_value=home):
                plan = install.build_plan("user", None)
            self.assertEqual([], plan.claude_adapters)
            self.assertEqual(len(install.discover_packages()), len(plan.by_name))

    def test_project_plan_writes_only_instruction_blocks_and_minimal_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            project = Path(tmp) / "project"
            project.mkdir()
            with patch.object(install.Path, "home", return_value=home):
                plan = install.build_plan("project", project)

            self.assertFalse(plan.manage_host_surfaces)
            self.assertEqual([], plan.lib_copies)
            self.assertEqual([], plan.scripts)
            self.assertEqual([], plan.claude_adapters)
            self.assertEqual([], plan.codex_prompts)
            self.assertEqual([], plan.codex_skills)
            self.assertEqual([], plan.by_name)
            self.assertEqual([], plan.claude_agents)
            self.assertEqual([], plan.codex_agents)
            self.assertEqual([], plan.configs)
            self.assertEqual([], plan.runtime_dirs)
            self.assertEqual(project / ".orchflows" / "receipt.json", plan.receipt_path)

            self.assertEqual(2, len(plan.blocks))
            dests = {block.dest for block in plan.blocks}
            self.assertEqual({project / "CLAUDE.md", project / "AGENTS.md"}, dests)
            user_lib = str((home / ".orchflows" / "lib").resolve())
            for block in plan.blocks:
                self.assertIn(user_lib, block.content)
                self.assertNotIn(str(project), block.content)

    def test_project_apply_writes_only_blocks_and_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            project = Path(tmp) / "project"
            project.mkdir()
            with patch.object(install.Path, "home", return_value=home):
                plan = install.build_plan("project", project)
                install.apply_plan(plan)

            self.assertTrue((project / "CLAUDE.md").is_file())
            self.assertTrue((project / "AGENTS.md").is_file())
            self.assertTrue((project / ".orchflows" / "receipt.json").is_file())
            self.assertFalse((project / ".claude").exists())
            self.assertFalse((project / ".codex").exists())
            self.assertFalse((project / ".orch").exists())
            self.assertFalse((project / ".orchflows" / "lib").exists())

    def test_project_apply_never_touches_legacy_fat_install_claude_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            project = Path(tmp) / "project"
            legacy_adapter = project / ".claude" / "skills" / "orch-test" / "SKILL.md"
            legacy_adapter.parent.mkdir(parents=True)
            legacy_adapter.write_text("legacy adapter\n", encoding="utf-8")
            receipt_path = project / ".orchflows" / "receipt.json"
            receipt_path.parent.mkdir(parents=True)
            receipt_path.write_text(
                json.dumps(
                    {
                        "files": [
                            {
                                "path": str(legacy_adapter),
                                "kind": "adapter",
                                "install_action": "created",
                                "sha256": digest(legacy_adapter),
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with patch.object(install.Path, "home", return_value=home):
                plan = install.build_plan("project", project)
                install.apply_plan(plan)

            self.assertTrue(legacy_adapter.exists())
            self.assertEqual("legacy adapter\n", legacy_adapter.read_text(encoding="utf-8"))

    def test_user_plan_targets_user_config_and_agent_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".claude").mkdir(parents=True)
            (home / ".codex").mkdir(parents=True)
            with patch.object(install.Path, "home", return_value=home):
                plan = install.build_plan("user", None)

            self.assertEqual(
                {home / ".claude" / "settings.json", home / ".codex" / "config.toml"},
                {config.dest for config in plan.configs},
            )
            self.assertEqual({home / ".claude" / "agents"}, {dest.parent for dest, _ in plan.claude_agents})
            self.assertEqual({home / ".codex" / "agents"}, {dest.parent for dest, _ in plan.codex_agents})

    def test_codex_limit_merge_handles_dotted_agent_keys(self):
        rendered, details = install.render_codex_agent_limits(
            "agents.max_threads = 3\nagents.max_depth = 2\n\n[other]\nvalue = true\n"
        )
        parsed = install.tomllib.loads(rendered)

        self.assertEqual(20, parsed["agents"]["max_threads"])
        self.assertEqual(1, parsed["agents"]["max_depth"])
        self.assertEqual(3, details["previous"]["agents.max_threads"])
        self.assertEqual(2, details["previous"]["agents.max_depth"])


class TestHostAutoDetection(unittest.TestCase):
    """Criterion 2: configure the Claude half only when ``~/.claude`` exists,
    the Codex half only when ``~/.codex`` exists; error with guidance when
    neither does."""

    def test_detect_hosts_reads_presence_of_each_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            self.assertEqual((False, False), install.detect_hosts(home))
            (home / ".claude").mkdir()
            self.assertEqual((True, False), install.detect_hosts(home))
            (home / ".codex").mkdir()
            self.assertEqual((True, True), install.detect_hosts(home))

    def test_neither_host_present_raises_with_guidance(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            with patch.object(install.Path, "home", return_value=home):
                with self.assertRaisesRegex(ValueError, "neither ~/.claude nor ~/.codex"):
                    install.build_plan("user", None)

    def test_only_claude_present_builds_claude_half_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".claude").mkdir(parents=True)
            with patch.object(install.Path, "home", return_value=home):
                plan = install.build_plan("user", None)

            self.assertTrue(plan.claude_enabled)
            self.assertFalse(plan.codex_enabled)
            self.assertTrue(plan.claude_adapters)
            self.assertTrue(plan.claude_agents)
            self.assertIsNotNone(plan.host_block)
            self.assertIsNotNone(plan.claude_import)
            self.assertEqual([], plan.codex_prompts)
            self.assertEqual([], plan.codex_skills)
            self.assertEqual([], plan.codex_agents)
            self.assertEqual([], plan.blocks)
            self.assertEqual([], plan.warnings)
            self.assertEqual({"claude-config"}, {config.kind for config in plan.configs})

    def test_only_codex_present_builds_codex_half_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".codex").mkdir(parents=True)
            with patch.object(install.Path, "home", return_value=home):
                plan = install.build_plan("user", None)

            self.assertFalse(plan.claude_enabled)
            self.assertTrue(plan.codex_enabled)
            self.assertEqual([], plan.claude_adapters)
            self.assertEqual([], plan.claude_agents)
            self.assertIsNone(plan.host_block)
            self.assertIsNone(plan.claude_import)
            self.assertTrue(plan.codex_prompts)
            self.assertTrue(plan.codex_agents)
            self.assertEqual(1, len(plan.blocks))
            self.assertEqual({"codex-config"}, {config.kind for config in plan.configs})

    def test_dry_run_prints_what_it_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".claude").mkdir(parents=True)
            with patch.object(install.Path, "home", return_value=home):
                plan = install.build_plan("user", None)
                buffer = io.StringIO()
                with redirect_stdout(buffer):
                    install.print_plan(plan)

            output = buffer.getvalue()
            self.assertIn("detected Claude Code (~/.claude): yes", output)
            self.assertIn("detected Codex (~/.codex): no", output)


class TestClaudeAlwaysOnImport(unittest.TestCase):
    """Criteria 3-4: the always-on layer is one appended import line in
    CLAUDE.md pointing at an installer-owned ``~/.orchflows/host-block.md``;
    Codex keeps the proven inline marker block (import expansion was probed
    against the installed CLI and does not resolve in AGENTS.md)."""

    def test_upsert_import_line_is_idempotent(self):
        updated, action = install.upsert_import_line("", "@/x/host-block.md", "<!-- BEGIN -->", "<!-- END -->")
        self.assertEqual("@/x/host-block.md\n", updated)
        self.assertEqual("created-file", action)

        updated2, action2 = install.upsert_import_line(
            updated, "@/x/host-block.md", "<!-- BEGIN -->", "<!-- END -->"
        )
        self.assertEqual(updated, updated2)
        self.assertEqual("already-present", action2)

    def test_upsert_import_line_migrates_legacy_inline_block(self):
        legacy = "before\n<!-- BEGIN -->\nold managed content\n<!-- END -->\nafter\n"

        updated, action = install.upsert_import_line(legacy, "@/x/host-block.md", "<!-- BEGIN -->", "<!-- END -->")

        self.assertEqual("migrated-from-block", action)
        self.assertNotIn("<!-- BEGIN -->", updated)
        self.assertNotIn("old managed content", updated)
        self.assertIn("before\n", updated)
        self.assertIn("after\n", updated)
        self.assertIn("@/x/host-block.md\n", updated)

    def test_upsert_import_line_appends_to_existing_file_without_block(self):
        updated, action = install.upsert_import_line(
            "# My CLAUDE.md\nsome instructions\n", "@/x/host-block.md", "<!-- BEGIN -->", "<!-- END -->"
        )

        self.assertEqual("added-import", action)
        self.assertTrue(updated.startswith("# My CLAUDE.md\nsome instructions\n"))
        self.assertTrue(updated.rstrip("\n").endswith("@/x/host-block.md"))

    def test_user_plan_renders_host_block_file_and_claude_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".claude").mkdir(parents=True)
            (home / ".codex").mkdir(parents=True)
            with patch.object(install.Path, "home", return_value=home):
                plan = install.build_plan("user", None)

            self.assertEqual(home / ".orchflows" / "host-block.md", plan.host_block.dest)
            self.assertEqual("host-block", plan.host_block.kind)
            self.assertNotIn("{{ORCH_LIB}}", plan.host_block.content)
            self.assertIn("Friction law", plan.host_block.content)

            self.assertEqual(home / ".claude" / "CLAUDE.md", plan.claude_import.dest)
            self.assertEqual(plan.host_block.dest.resolve(), plan.claude_import.import_target)

            # Codex keeps the full inline block, never an import.
            self.assertEqual(1, len(plan.blocks))
            self.assertEqual(home / ".codex" / "AGENTS.md", plan.blocks[0].dest)
            self.assertIn("Friction law", plan.blocks[0].content)

    def test_apply_writes_host_block_file_and_appends_import_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".claude").mkdir(parents=True)
            (home / ".codex").mkdir(parents=True)
            with patch.object(install.Path, "home", return_value=home):
                plan = install.build_plan("user", None)
                install.apply_plan(plan)

            host_block_path = home / ".orchflows" / "host-block.md"
            claude_md = home / ".claude" / "CLAUDE.md"
            self.assertTrue(host_block_path.is_file())
            self.assertIn("Friction law", host_block_path.read_text(encoding="utf-8"))

            claude_text = claude_md.read_text(encoding="utf-8")
            import_line = f"@{host_block_path.resolve()}"
            self.assertEqual(1, claude_text.count(import_line))

            # Codex AGENTS.md still carries the full inline block.
            agents_text = (home / ".codex" / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("Friction law", agents_text)
            self.assertNotIn(f"@{host_block_path.resolve()}", agents_text)

    def test_reapply_does_not_duplicate_import_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".claude").mkdir(parents=True)
            with patch.object(install.Path, "home", return_value=home):
                plan = install.build_plan("user", None)
                install.apply_plan(plan)
                plan2 = install.build_plan("user", None)
                install.apply_plan(plan2)

            claude_text = (home / ".claude" / "CLAUDE.md").read_text(encoding="utf-8")
            host_block_path = home / ".orchflows" / "host-block.md"
            import_line = f"@{host_block_path.resolve()}"
            self.assertEqual(1, claude_text.count(import_line))

    def test_apply_migrates_legacy_inline_block_in_claude_md(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".claude").mkdir(parents=True)
            claude_md = home / ".claude" / "CLAUDE.md"
            template_text = install.HOST_BLOCK_TEMPLATE.read_text(encoding="utf-8")
            start_marker, end_marker = install.template_markers(template_text)
            claude_md.write_text(
                f"# personal notes\n{start_marker}\nold rendered block\n{end_marker}\n", encoding="utf-8"
            )

            with patch.object(install.Path, "home", return_value=home):
                plan = install.build_plan("user", None)
                install.apply_plan(plan)

            claude_text = claude_md.read_text(encoding="utf-8")
            self.assertIn("# personal notes", claude_text)
            self.assertNotIn(start_marker, claude_text)
            self.assertNotIn("old rendered block", claude_text)
            self.assertIn(f"@{(home / '.orchflows' / 'host-block.md').resolve()}", claude_text)

    def test_uninstall_reports_manual_cleanup_for_import_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            claude_md = project / "CLAUDE.md"
            claude_md.write_text("notes\n@/x/host-block.md\n", encoding="utf-8")
            receipt_path = project / ".orchflows" / "receipt.json"
            receipt_path.parent.mkdir(parents=True)
            receipt_path.write_text(
                json.dumps(
                    {
                        "files": [],
                        "blocks": [],
                        "imports": [
                            {
                                "path": str(claude_md),
                                "import_line": "@/x/host-block.md",
                                "install_action": "created-file",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = install.run_uninstall("project", project, dry_run=False)

            self.assertTrue(claude_md.exists())
            actions = "\n".join(entry["action"] for entry in result["manual_actions"])
            self.assertIn("@/x/host-block.md", actions)


class TestMarkerEngineMisuse(unittest.TestCase):
    """Marker matching is line equality on ``rstrip("\\r\\n")``. Duplicate,
    unbalanced, and out-of-order markers must raise ``ValueError`` naming the
    offending marker, for ``upsert_marked_block``, ``without_marked_block``,
    and ``upsert_import_line`` (which delegates legacy-marker stripping to
    ``without_marked_block``) alike, and for CRLF line endings too."""

    # -- upsert_marked_block -------------------------------------------

    def test_upsert_marked_block_duplicate_begin_raises(self):
        text = "# BEGIN\nold\n# BEGIN\nold2\n# END\n"
        with self.assertRaisesRegex(ValueError, "duplicate"):
            install.upsert_marked_block(text, "new\n", "# BEGIN", "# END")

    def test_upsert_marked_block_duplicate_end_raises(self):
        text = "# BEGIN\nold\n# END\nold2\n# END\n"
        with self.assertRaisesRegex(ValueError, "duplicate"):
            install.upsert_marked_block(text, "new\n", "# BEGIN", "# END")

    def test_upsert_marked_block_begin_without_end_raises(self):
        text = "# BEGIN\nold\n"
        with self.assertRaisesRegex(ValueError, "unbalanced"):
            install.upsert_marked_block(text, "new\n", "# BEGIN", "# END")

    def test_upsert_marked_block_end_without_begin_raises(self):
        text = "old\n# END\n"
        with self.assertRaisesRegex(ValueError, "unbalanced"):
            install.upsert_marked_block(text, "new\n", "# BEGIN", "# END")

    def test_upsert_marked_block_out_of_order_raises(self):
        text = "# END\nold\n# BEGIN\n"
        with self.assertRaisesRegex(ValueError, "out of order"):
            install.upsert_marked_block(text, "new\n", "# BEGIN", "# END")

    def test_upsert_marked_block_duplicate_begin_raises_with_crlf(self):
        text = "# BEGIN\r\nold\r\n# BEGIN\r\nold2\r\n# END\r\n"
        with self.assertRaisesRegex(ValueError, "duplicate"):
            install.upsert_marked_block(text, "new\n", "# BEGIN", "# END")

    def test_upsert_marked_block_unbalanced_raises_with_crlf(self):
        text = "# BEGIN\r\nold\r\n"
        with self.assertRaisesRegex(ValueError, "unbalanced"):
            install.upsert_marked_block(text, "new\n", "# BEGIN", "# END")

    def test_upsert_marked_block_out_of_order_raises_with_crlf(self):
        text = "# END\r\nold\r\n# BEGIN\r\n"
        with self.assertRaisesRegex(ValueError, "out of order"):
            install.upsert_marked_block(text, "new\n", "# BEGIN", "# END")

    # -- without_marked_block -------------------------------------------

    def test_without_marked_block_duplicate_begin_raises(self):
        text = "# BEGIN\nold\n# BEGIN\nold2\n# END\n"
        with self.assertRaisesRegex(ValueError, "invalid"):
            install.without_marked_block(text, "# BEGIN", "# END")

    def test_without_marked_block_duplicate_end_raises(self):
        text = "# BEGIN\nold\n# END\nold2\n# END\n"
        with self.assertRaisesRegex(ValueError, "invalid"):
            install.without_marked_block(text, "# BEGIN", "# END")

    def test_without_marked_block_begin_without_end_raises(self):
        text = "# BEGIN\nold\n"
        with self.assertRaisesRegex(ValueError, "invalid"):
            install.without_marked_block(text, "# BEGIN", "# END")

    def test_without_marked_block_end_without_begin_raises(self):
        text = "old\n# END\n"
        with self.assertRaisesRegex(ValueError, "invalid"):
            install.without_marked_block(text, "# BEGIN", "# END")

    def test_without_marked_block_out_of_order_raises(self):
        text = "# END\nold\n# BEGIN\n"
        with self.assertRaisesRegex(ValueError, "invalid"):
            install.without_marked_block(text, "# BEGIN", "# END")

    def test_without_marked_block_out_of_order_raises_with_crlf(self):
        text = "# END\r\nold\r\n# BEGIN\r\n"
        with self.assertRaisesRegex(ValueError, "invalid"):
            install.without_marked_block(text, "# BEGIN", "# END")

    def test_without_marked_block_absent_markers_is_a_no_op(self):
        # Contrast case: no markers at all is not misuse -- text passes through.
        text = "plain content\n"
        self.assertEqual(text, install.without_marked_block(text, "# BEGIN", "# END"))

    # -- upsert_import_line (delegates legacy-marker stripping) ---------

    def test_upsert_import_line_duplicate_legacy_begin_raises(self):
        text = "<!-- BEGIN -->\nold\n<!-- BEGIN -->\nold2\n<!-- END -->\n"
        with self.assertRaisesRegex(ValueError, "invalid"):
            install.upsert_import_line(text, "@x", "<!-- BEGIN -->", "<!-- END -->")

    def test_upsert_import_line_legacy_begin_without_end_raises(self):
        text = "<!-- BEGIN -->\nold\n"
        with self.assertRaisesRegex(ValueError, "invalid"):
            install.upsert_import_line(text, "@x", "<!-- BEGIN -->", "<!-- END -->")

    def test_upsert_import_line_legacy_end_without_begin_raises(self):
        text = "old\n<!-- END -->\n"
        with self.assertRaisesRegex(ValueError, "invalid"):
            install.upsert_import_line(text, "@x", "<!-- BEGIN -->", "<!-- END -->")

    def test_upsert_import_line_legacy_out_of_order_raises(self):
        text = "<!-- END -->\nold\n<!-- BEGIN -->\n"
        with self.assertRaisesRegex(ValueError, "invalid"):
            install.upsert_import_line(text, "@x", "<!-- BEGIN -->", "<!-- END -->")

    def test_upsert_import_line_legacy_out_of_order_raises_with_crlf(self):
        text = "<!-- END -->\r\nold\r\n<!-- BEGIN -->\r\n"
        with self.assertRaisesRegex(ValueError, "invalid"):
            install.upsert_import_line(text, "@x", "<!-- BEGIN -->", "<!-- END -->")


class TestPartialApplyAfterRmtree(unittest.TestCase):
    """Characterization test: ``apply_plan`` is not transactional around its
    library install. It removes ``lib_home`` wholesale, then re-copies each
    ``lib_copies`` entry in a plain loop with no rollback. This pins the
    *observed* behavior of a crash injected mid-copy -- it does not assert
    this is the ideal design, only what a caller must expect today."""

    def test_crash_mid_copy_leaves_lib_home_partially_repopulated_and_no_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project"
            project.mkdir()

            src_a = root / "a.md"
            src_b = root / "b.md"
            src_c = root / "c.md"
            src_a.write_text("new a\n", encoding="utf-8")
            src_b.write_text("new b\n", encoding="utf-8")
            src_c.write_text("new c\n", encoding="utf-8")

            lib_home = project / ".orchflows" / "lib"
            lib_home.mkdir(parents=True)
            (lib_home / "old.md").write_text("stale\n", encoding="utf-8")

            receipt_path = project / ".orchflows" / "receipt.json"
            receipt_path.write_text('{"pre-existing": true}\n', encoding="utf-8")
            receipt_before = receipt_path.read_bytes()

            dest_a = lib_home / "a.md"
            dest_b = lib_home / "b.md"
            dest_c = lib_home / "c.md"

            plan = install.Plan(
                scope="project",
                project_root=project,
                lib_home=lib_home,
                scope_home=project / ".orchflows",
                bin_dir=project / ".orch" / "bin",
                receipt_path=receipt_path,
                lib_copies=[(src_a, dest_a), (src_b, dest_b), (src_c, dest_c)],
            )

            real_copy2 = shutil.copy2

            def flaky_copy2(src, dest, *args, **kwargs):
                if Path(dest) == dest_b:
                    raise RuntimeError("simulated crash during copy")
                return real_copy2(src, dest, *args, **kwargs)

            with patch.object(install.shutil, "copy2", side_effect=flaky_copy2):
                with self.assertRaisesRegex(RuntimeError, "simulated crash"):
                    install.apply_plan(plan)

            # rmtree already ran: the pre-existing stale file is gone.
            self.assertFalse((lib_home / "old.md").exists())
            # The copy before the failing one landed...
            self.assertTrue(dest_a.exists())
            self.assertEqual("new a\n", dest_a.read_text(encoding="utf-8"))
            # ...the failing copy and everything queued after it never did.
            self.assertFalse(dest_b.exists())
            self.assertFalse(dest_c.exists())
            # apply_plan aborted before reaching the receipt write.
            self.assertEqual(receipt_before, receipt_path.read_bytes())


class TestSourceCommit(unittest.TestCase):
    """Criterion 6: the receipt gains ``source_commit`` (git HEAD of the
    installed-from repo, null when unavailable); a rerun whose HEAD moved
    prints the drift."""

    def test_resolve_source_commit_follows_a_branch_ref(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / ".git" / "refs" / "heads").mkdir(parents=True)
            (repo / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
            (repo / ".git" / "refs" / "heads" / "main").write_text("abc123\n", encoding="utf-8")

            self.assertEqual("abc123", install.resolve_source_commit(repo))

    def test_resolve_source_commit_reads_detached_head(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / ".git").mkdir(parents=True)
            (repo / ".git" / "HEAD").write_text("deadbeef\n", encoding="utf-8")

            self.assertEqual("deadbeef", install.resolve_source_commit(repo))

    def test_resolve_source_commit_falls_back_to_packed_refs(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / ".git").mkdir(parents=True)
            (repo / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
            (repo / ".git" / "packed-refs").write_text(
                "# pack-refs with: peeled fully-peeled sorted\nfeedface refs/heads/main\n",
                encoding="utf-8",
            )

            self.assertEqual("feedface", install.resolve_source_commit(repo))

    def test_resolve_source_commit_is_none_without_git(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(install.resolve_source_commit(Path(tmp)))

    def test_source_commit_drift_message_only_on_actual_change(self):
        self.assertIsNone(install.source_commit_drift_message(None, "abc"))
        self.assertIsNone(install.source_commit_drift_message({"source_commit": None}, "abc"))
        self.assertIsNone(install.source_commit_drift_message({"source_commit": "abc"}, "abc"))
        self.assertIsNone(install.source_commit_drift_message({"source_commit": "abc"}, None))
        self.assertEqual(
            "source commit drift: abc -> def",
            install.source_commit_drift_message({"source_commit": "abc"}, "def"),
        )

    def test_receipt_carries_resolved_source_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            plan = install.Plan(
                scope="project",
                project_root=project,
                lib_home=project / ".orchflows" / "lib",
                scope_home=project / ".orchflows",
                bin_dir=project / ".orch" / "bin",
                receipt_path=project / ".orchflows" / "receipt.json",
            )

            with patch.object(install, "resolve_source_commit", return_value="cafe"):
                receipt = install.apply_plan(plan)

            self.assertEqual("cafe", receipt["source_commit"])

    def test_main_prints_drift_on_second_install_with_moved_head(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".claude").mkdir(parents=True)

            with patch.object(install.Path, "home", return_value=home), patch.object(
                install, "resolve_source_commit", side_effect=["sha1", "sha2"]
            ):
                first = io.StringIO()
                with redirect_stdout(first):
                    code1 = install.main(["--user", "--yes"])
                second = io.StringIO()
                with redirect_stdout(second):
                    code2 = install.main(["--user", "--yes"])

            self.assertEqual(0, code1)
            self.assertEqual(0, code2)
            self.assertNotIn("source commit drift", first.getvalue())
            self.assertIn("source commit drift: sha1 -> sha2", second.getvalue())


class TestBootstrapWrappers(unittest.TestCase):
    """Criterion 7: install.sh / install.cmd resolve uv -> python3 -> python
    and forward every argument to install.py; never a bare hardcoded
    interpreter. Strengthened over a plain "does this substring appear
    anywhere in the file" check: each resolution branch is asserted to pair
    its own interpreter invocation with the target script and full argument
    forwarding, on the same branch -- a branch that resolved an interpreter
    but forgot to forward arguments would pass the old check and fail this
    one."""

    def test_install_sh_is_posix_wrapper_resolving_interpreters(self):
        path = install.REPO_ROOT / "install.sh"
        self.assertTrue(path.is_file())
        text = path.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("#!/bin/sh"))
        self.assertRegex(
            text,
            r'command -v uv[^\n]*\n(?:.*\n)*?\s*exec uv run --no-project python "\$target" "\$@"',
        )
        self.assertRegex(
            text,
            r'command -v python3[^\n]*\n(?:.*\n)*?\s*exec python3 "\$target" "\$@"',
        )
        self.assertRegex(
            text,
            r'command -v python[^\n]*\n(?:.*\n)*?\s*exec python "\$target" "\$@"',
        )

    def test_install_cmd_is_windows_wrapper_resolving_interpreters(self):
        path = install.REPO_ROOT / "install.cmd"
        self.assertTrue(path.is_file())
        text = path.read_text(encoding="utf-8")
        self.assertRegex(
            text,
            r'where uv[^\n]*\n(?:.*\n)*?\s*uv run --no-project python "%target%" %\*',
        )
        self.assertRegex(
            text,
            r'where python3[^\n]*\n(?:.*\n)*?\s*python3 "%target%" %\*',
        )
        self.assertRegex(
            text,
            r'where python[^\n]*\n(?:.*\n)*?\s*python "%target%" %\*',
        )


class TestPluginSubsystemRemoved(unittest.TestCase):
    """Criterion 1: the Claude plugin distribution is dropped from the tree
    (preserved in git history). Kept as a structure guard (binding
    constraints keep structure guards; this asserts real repo/file state,
    not a module constant against itself) and strengthened to also check
    install.py's own source carries no reference back to the removed
    subsystem."""

    def test_plugin_subsystem_paths_are_absent(self):
        self.assertFalse((install.REPO_ROOT / "tools" / "build_plugin.py").exists())
        self.assertFalse((install.REPO_ROOT / "plugin").exists())
        self.assertFalse((install.REPO_ROOT / ".claude-plugin").exists())
        self.assertFalse((install.REPO_ROOT / "tests" / "test_plugin_build.py").exists())

    def test_install_py_source_has_no_plugin_subsystem_reference(self):
        source = (install.REPO_ROOT / "install.py").read_text(encoding="utf-8")
        self.assertNotIn("build_plugin", source)
        self.assertNotIn(".claude-plugin", source)


class TestHostBlockRendering(unittest.TestCase):
    def _rendered(self, python_interpreter: str = "/usr/bin/python3") -> str:
        # PurePosixPath (not Path) keeps the "/" separators literal for
        # assertions below regardless of host platform.
        template_text = install.HOST_BLOCK_TEMPLATE.read_text(encoding="utf-8")
        return install.render_host_block(
            template_text,
            PurePosixPath("/bin"),
            PurePosixPath("/lib/docs"),
            PurePosixPath("/lib/skills"),
            PurePosixPath("/lib"),
            python_interpreter,
        )

    def test_render_host_block_substitutes_resolved_interpreter(self):
        rendered = self._rendered("/usr/bin/python3")

        self.assertIn("/usr/bin/python3 /bin/friction.py", rendered)
        self.assertNotIn("{{PYTHON}}", rendered)
        self.assertNotIn("{{ORCH_LIB}}", rendered)

    def test_resolved_python_interpreter_falls_back_when_unset(self):
        with patch.object(install.sys, "executable", ""):
            self.assertEqual("python", install.resolved_python_interpreter())
        with patch.object(install.sys, "executable", "/usr/bin/python3"):
            self.assertEqual("/usr/bin/python3", install.resolved_python_interpreter())

    def test_rendered_block_contains_name_to_path_map(self):
        # Only phrases that depend on a substituted placeholder belong here;
        # static template prose (e.g. "tier is not inferable from the name")
        # mirrors templates/host-block.md verbatim and asserts nothing about
        # render_host_block's substitution logic, so it is not checked here.
        rendered = self._rendered()

        self.assertIn(
            "/lib/by-name/<orch-name>/SKILL.md",
            rendered,
        )
        for sibling in ("packs/<orch-name>/SKILL.md", "contracts/", "rules/", "compositions/"):
            self.assertIn(f"/lib/{sibling}", rendered)
        self.assertIn("/lib/docs/", rendered)

    def test_build_plan_host_block_uses_running_interpreter(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)

            plan = install.build_plan("project", project)

            block = plan.blocks[0].content
            self.assertIn(f"{install.resolved_python_interpreter()} ", block)
            self.assertNotIn("{{PYTHON}}", block)


class TestConservativeUninstall(unittest.TestCase):
    def _write_receipt(self, project: Path, files: list[dict], blocks=None, dirs=None) -> Path:
        receipt_path = project / ".orchflows" / "receipt.json"
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(
            json.dumps(
                {
                    "version": 2,
                    "scope": "project",
                    "files": files,
                    "blocks": blocks or [],
                    "dirs": dirs or [],
                }
            ),
            encoding="utf-8",
        )
        return receipt_path

    def test_uninstall_removes_only_unchanged_skill_entrypoints(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            home = project / "home"
            adapter = project / ".claude" / "skills" / "orch-test" / "SKILL.md"
            prompt = home / ".codex" / "prompts" / "orch-test.md"
            script = project / ".orch" / "bin" / "friction.py"
            library = project / ".orchflows" / "lib" / "contracts" / "spec.md"
            host = project / "AGENTS.md"
            for path, content in (
                (adapter, "adapter\n"),
                (prompt, "prompt\n"),
                (script, "script\n"),
                (library, "contract\n"),
                (host, "before\n# BEGIN TEST\nmanaged\n# END TEST\nafter\n"),
            ):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")

            receipt_path = self._write_receipt(
                project,
                [
                    {"path": str(adapter), "kind": "adapter", "install_action": "created", "sha256": digest(adapter)},
                    {"path": str(prompt), "kind": "prompt", "install_action": "created", "sha256": digest(prompt)},
                    {"path": str(script), "kind": "script", "install_action": "created", "sha256": digest(script)},
                    {"path": str(library), "kind": "lib", "install_action": "created", "sha256": digest(library)},
                ],
                blocks=[
                    {
                        "path": str(host),
                        "start_marker": "# BEGIN TEST",
                        "end_marker": "# END TEST",
                        "install_action": "added-block",
                    }
                ],
                dirs=[str(project / ".orch" / "bin")],
            )

            with patch.object(install.Path, "home", return_value=home):
                result = install.run_uninstall("project", project, dry_run=False)

            self.assertFalse(adapter.exists())
            self.assertFalse(prompt.exists())
            self.assertTrue(script.exists())
            self.assertTrue(library.exists())
            self.assertIn("# BEGIN TEST", host.read_text(encoding="utf-8"))
            self.assertTrue(receipt_path.exists())
            self.assertEqual(2, len(result["skill_actions"]))
            manual_paths = {entry["path"] for entry in result["manual_actions"]}
            self.assertTrue({str(script), str(library), str(host), str(receipt_path)} <= manual_paths)

    def test_receipt_cannot_remove_skill_outside_verified_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            project.mkdir()
            outside = project.parent / "outside-skill.md"
            outside.write_text("matching\n", encoding="utf-8")
            self._write_receipt(
                project,
                [
                    {
                        "path": str(outside),
                        "kind": "adapter",
                        "install_action": "created",
                        "sha256": digest(outside),
                    }
                ],
            )

            result = install.run_uninstall("project", project, dry_run=False)

            self.assertTrue(outside.exists())
            self.assertIn("outside its verified install boundary", result["manual_actions"][0]["action"])

    def test_modified_and_unverified_skills_require_manual_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            home = project / "home"
            modified = project / ".claude" / "skills" / "modified" / "SKILL.md"
            legacy = home / ".codex" / "prompts" / "legacy.md"
            modified.parent.mkdir(parents=True)
            legacy.parent.mkdir(parents=True)
            modified.write_text("installed\n", encoding="utf-8")
            installed_hash = digest(modified)
            modified.write_text("user edit\n", encoding="utf-8")
            legacy.write_text("legacy\n", encoding="utf-8")
            self._write_receipt(
                project,
                [
                    {"path": str(modified), "kind": "adapter", "install_action": "created", "sha256": installed_hash},
                    {"path": str(legacy), "kind": "prompt", "install_action": "created"},
                ],
            )

            with patch.object(install.Path, "home", return_value=home):
                result = install.run_uninstall("project", project, dry_run=False)

            self.assertTrue(modified.exists())
            self.assertTrue(legacy.exists())
            actions = "\n".join(entry["action"] for entry in result["manual_actions"])
            self.assertIn("modified since install", actions)
            self.assertIn("no install hash", actions)

    def test_replaced_skill_requires_manual_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            skill = project / ".claude" / "skills" / "personal" / "SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text("installer content\n", encoding="utf-8")
            self._write_receipt(
                project,
                [
                    {
                        "path": str(skill),
                        "kind": "adapter",
                        "install_action": "replaced",
                        "sha256": digest(skill),
                    }
                ],
            )

            result = install.run_uninstall("project", project, dry_run=False)

            self.assertTrue(skill.exists())
            self.assertIn("no original backup", result["manual_actions"][0]["action"])

    def test_manual_config_action_reports_installed_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            config = project / ".codex" / "config.toml"
            config.parent.mkdir()
            config.write_text("agents.max_threads = 6\n", encoding="utf-8")
            self._write_receipt(
                project,
                [
                    {
                        "path": str(config),
                        "kind": "codex-config",
                        "install_action": "created",
                        "sha256": digest(config),
                        "details": {"settings": {"agents.max_threads": 6}},
                    }
                ],
            )

            result = install.run_uninstall("project", project, dry_run=False)

            self.assertTrue(config.exists())
            self.assertIn('"agents.max_threads": 6', result["manual_actions"][0]["action"])

    def test_dry_run_changes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            adapter = project / ".claude" / "skills" / "orch-test" / "SKILL.md"
            adapter.parent.mkdir(parents=True)
            adapter.write_text("adapter\n", encoding="utf-8")
            receipt_path = self._write_receipt(
                project,
                [
                    {
                        "path": str(adapter),
                        "kind": "adapter",
                        "install_action": "created",
                        "sha256": digest(adapter),
                    }
                ],
            )

            result = install.run_uninstall("project", project, dry_run=True)

            self.assertTrue(adapter.exists())
            self.assertTrue(receipt_path.exists())
            self.assertEqual("would remove unchanged skill", result["skill_actions"][0]["action"])

    def test_uninstall_auto_removes_unchanged_codex_skill_stub(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            home = project / "home"
            stub = home / ".codex" / "skills" / "orch-spec" / "SKILL.md"
            stub.parent.mkdir(parents=True)
            stub.write_text("stub\n", encoding="utf-8")
            self._write_receipt(
                project,
                [
                    {
                        "path": str(stub),
                        "kind": "codex-skill",
                        "install_action": "created",
                        "sha256": digest(stub),
                    }
                ],
            )

            with patch.object(install.Path, "home", return_value=home):
                result = install.run_uninstall("project", project, dry_run=False)

            self.assertFalse(stub.exists())
            self.assertEqual(1, len(result["skill_actions"]))


class TestCodexHooksPreflight(unittest.TestCase):
    def test_warns_on_dangling_orchflows_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            codex_home = Path(tmp)
            hooks = codex_home / "hooks.json"
            hooks.write_text(
                json.dumps(
                    {
                        "hooks": [
                            {
                                "command": [
                                    "python3",
                                    str(codex_home / "skills" / "orch-self-improve" / "scripts" / "ledger.py"),
                                ]
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            warnings = install._codex_hooks_warnings(codex_home)

            self.assertEqual(1, len(warnings))
            self.assertIn(str(hooks), warnings[0])
            self.assertIn("orch-self-improve", warnings[0])

    def test_no_warning_when_referenced_path_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            codex_home = Path(tmp)
            target = codex_home / "skills" / "orch-spec" / "SKILL.md"
            target.parent.mkdir(parents=True)
            target.write_text("present\n", encoding="utf-8")
            hooks = codex_home / "hooks.json"
            hooks.write_text(json.dumps({"command": [str(target)]}), encoding="utf-8")

            self.assertEqual([], install._codex_hooks_warnings(codex_home))

    def test_no_warning_when_hooks_file_absent_or_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            codex_home = Path(tmp)

            self.assertEqual([], install._codex_hooks_warnings(codex_home))

            (codex_home / "hooks.json").write_text("not json", encoding="utf-8")
            self.assertEqual([], install._codex_hooks_warnings(codex_home))

    def test_never_deletes_or_edits_hooks_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            codex_home = Path(tmp)
            hooks = codex_home / "hooks.json"
            original = json.dumps({"command": [str(codex_home / "orch-missing" / "x.py")]})
            hooks.write_text(original, encoding="utf-8")

            install._codex_hooks_warnings(codex_home)

            self.assertEqual(original, hooks.read_text(encoding="utf-8"))

    def test_user_plan_surfaces_hooks_warnings(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            hooks = home / ".codex" / "hooks.json"
            hooks.parent.mkdir(parents=True)
            hooks.write_text(
                json.dumps({"command": [str(home / ".codex" / "orch-missing" / "x.py")]}),
                encoding="utf-8",
            )

            with patch.object(install.Path, "home", return_value=home):
                plan = install.build_plan("user", None)

            self.assertEqual(1, len(plan.warnings))
            self.assertIn("orch-missing", plan.warnings[0])


if __name__ == "__main__":
    unittest.main()
