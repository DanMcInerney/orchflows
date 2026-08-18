"""Installer regression cases grouped by behavioral seam."""

from __future__ import annotations

from ..support import *  # noqa: F403


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

    def _role_agent_plan(self, project: Path, **kwargs) -> "install.Plan":
        defaults = dict(
            scope="project",
            project_root=project,
            lib_home=project / ".orchflows" / "lib",
            scope_home=project / ".orchflows",
            bin_dir=project / ".orch" / "bin",
            receipt_path=project / ".orchflows" / "receipt.json",
        )
        defaults.update(kwargs)
        return install.Plan(**defaults)

    def test_unowned_role_profile_is_kept_and_the_install_proceeds(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            source = project / "source.md"
            source.write_text("new library\n", encoding="utf-8")
            lib_dest = project / ".orchflows" / "lib" / "source.md"
            agent = project / ".codex" / "agents" / "orch-worker.toml"
            agent.parent.mkdir(parents=True)
            agent.write_text("personal = true\n", encoding="utf-8")
            plan = self._role_agent_plan(
                project,
                lib_copies=[(source, lib_dest)],
                codex_agents=[(agent, 'name = "orch-worker"\n')],
            )

            receipt = install.apply_plan(plan, keep_role_agents=True)

            self.assertEqual("personal = true\n", agent.read_text(encoding="utf-8"))
            # The rest of the install is no longer collateral of one
            # diverged agent: the library still lands.
            self.assertTrue(lib_dest.exists())
            # ...and the kept agent is left out of the receipt, so the next
            # install asks again instead of adopting its hash as its own.
            self.assertNotIn(
                str(agent), {entry["path"] for entry in receipt["files"]}
            )

    def test_modified_receipt_owned_role_profile_is_kept(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            agent = project / ".claude" / "agents" / "orch-planner.md"
            agent.parent.mkdir(parents=True)
            agent.write_text("modified\n", encoding="utf-8")
            receipt_path = project / ".orchflows" / "receipt.json"
            receipt_path.parent.mkdir(parents=True)
            receipt_path.write_text(
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
            plan = self._role_agent_plan(
                project, receipt_path=receipt_path, claude_agents=[(agent, "updated\n")]
            )

            install.apply_plan(plan, keep_role_agents=True)

            # A receipt-owned path dropped from the plan would be deleted as
            # stale; keeping it must not mean losing it.
            self.assertTrue(agent.is_file())
            self.assertEqual("modified\n", agent.read_text(encoding="utf-8"))

    def test_modified_role_profile_is_replaced_when_overwrite_is_chosen(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            agent = project / ".claude" / "agents" / "orch-planner.md"
            agent.parent.mkdir(parents=True)
            agent.write_text("modified\n", encoding="utf-8")
            plan = self._role_agent_plan(project, claude_agents=[(agent, "updated\n")])

            install.apply_plan(plan, keep_role_agents=False)

            self.assertEqual("updated\n", agent.read_text(encoding="utf-8"))

    def test_role_profile_that_is_not_a_regular_file_still_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            agent = project / ".claude" / "agents" / "orch-planner.md"
            agent.mkdir(parents=True)
            plan = self._role_agent_plan(project, claude_agents=[(agent, "updated\n")])

            with self.assertRaisesRegex(FileExistsError, "not a regular file"):
                install.apply_plan(plan, keep_role_agents=True)

    def test_legacy_header_role_profile_without_receipt_is_kept(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            agent = project / ".codex" / "agents" / "orch-worker.toml"
            agent.parent.mkdir(parents=True)
            legacy_header = (
                "# Managed by orchflows install.py.\n"
                "# This complete file is replaced on every orchflows install.\n"
            )
            agent.write_text(legacy_header + "old = true\n", encoding="utf-8")
            plan = self._role_agent_plan(
                project, codex_agents=[(agent, 'name = "orch-worker"\n')]
            )

            install.apply_plan(plan, keep_role_agents=True)

            self.assertEqual(legacy_header + "old = true\n", agent.read_text(encoding="utf-8"))

    def test_shipped_claude_bindings_are_the_documented_defaults(self):
        profiles = install.load_role_profiles()

        self.assertEqual(
            {"model": "claude-opus-5", "effort": "max"}, profiles["orch-planner"]["claude"]
        )
        self.assertEqual(
            {"model": "claude-opus-5", "effort": "high"}, profiles["orch-worker"]["claude"]
        )

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
