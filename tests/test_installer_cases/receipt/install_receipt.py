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
                scope="user",
                project_root=None,
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
            scope="user",
            project_root=None,
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
            {"model": "claude-sonnet-5", "effort": "xhigh"}, profiles["orch-worker"]["claude"]
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
                scope="user",
                project_root=None,
                lib_home=project / ".orchflows" / "lib",
                scope_home=project / ".orchflows",
                bin_dir=project / ".orch" / "bin",
                receipt_path=receipt,
                codex_agents=[(new_agent, 'name = "orch_worker"\n')],
            )

            install.apply_plan(plan)

            self.assertFalse(old_agent.exists())
            self.assertEqual('name = "orch_worker"\n', new_agent.read_text(encoding="utf-8"))

    # --- Grok ------------------------------------------------------------
    #
    # On this class rather than a Grok class of its own. Nothing under
    # ``tests/test_installer_cases/`` is discovered: a class reaches the
    # suite only by explicit class-name import in a shard module, and
    # ``tests.test_run_tests`` holds every declared class name against the
    # loaded one, so a new class here would be declared and never loaded.

    @staticmethod
    def _no_runtime_build():
        """Plan the install with ``runtime_action`` ``None``.

        The private runtime is an ``ensurepip`` plus a hash-locked dependency
        install, and it lands under ``~/.orchflows``, which is not what any
        case below reads. The runtime's own lifecycle is graded by the cases
        that build one for real.
        """

        return patch.object(install, "private_runtime_action", return_value=None)

    def test_a_grok_install_writes_the_planned_surface_and_records_its_kind(self):
        """Every planned Grok artifact lands under ``GROK_HOME``, nothing else
        does, and each is recorded under a kind of Grok's own.

        The kinds cannot be the Claude and Codex ones they resemble:
        ``_remove_stale`` sweeps by kind against the plan's wanted paths, so a
        Grok skill filed as an ``adapter`` would be deleted by the very next
        install as a stale Claude adapter.
        """

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            home.mkdir()
            with isolated_grok_home(root) as grok_home, patch.object(
                install.Path, "home", return_value=home
            ), mock_host_clis("grok"), self._no_runtime_build():
                plan = install.build_plan("user", None)
                receipt = install.apply_plan(plan)

            configs = [entry for entry in plan.configs if entry.kind == "grok-config"]
            self.assertEqual(1, len(configs))
            self.assertIsNotNone(plan.grok_rules)
            planned = dict(plan.grok_skills + plan.grok_agents)
            planned[plan.grok_rules.dest] = plan.grok_rules.content
            planned[configs[0].dest] = configs[0].content

            self.assertEqual(
                set(planned), {path for path in grok_home.rglob("*") if path.is_file()}
            )
            for dest, content in planned.items():
                self.assertEqual(content, dest.read_text(encoding="utf-8"))

            expected = {str(dest): "grok-skill" for dest, _ in plan.grok_skills}
            expected.update({str(dest): "grok-agent" for dest, _ in plan.grok_agents})
            expected[str(plan.grok_rules.dest)] = "grok-rules"
            expected[str(configs[0].dest)] = "grok-config"
            recorded = {entry["path"]: entry["kind"] for entry in receipt["files"]}
            self.assertEqual(
                expected,
                {path: kind for path, kind in recorded.items() if path in expected},
            )
            for entry in receipt["files"]:
                self.assertEqual(digest(Path(entry["path"])), entry["sha256"])

    def test_reinstall_removes_a_receipt_owned_grok_artifact_the_plan_dropped(self):
        """A canonical name that goes away leaves no Grok file behind, and a
        file the receipt never claimed stays exactly where the user put it."""

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with isolated_grok_home(root) as grok_home:
                stale_skill = grok_home / "skills" / "orch-gone" / "SKILL.md"
                stale_agent = grok_home / "agents" / "orch-gone.md"
                mine = grok_home / "skills" / "handwritten" / "SKILL.md"
                for path in (stale_skill, stale_agent, mine):
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text("before\n", encoding="utf-8")
                receipt_path = root / ".orchflows" / "receipt.json"
                receipt_path.parent.mkdir(parents=True)
                receipt_path.write_text(
                    json.dumps(
                        {
                            "files": [
                                {
                                    "path": str(stale_skill),
                                    "kind": "grok-skill",
                                    "sha256": digest(stale_skill),
                                },
                                {
                                    "path": str(stale_agent),
                                    "kind": "grok-agent",
                                    "sha256": digest(stale_agent),
                                },
                            ]
                        }
                    ),
                    encoding="utf-8",
                )
                kept_skill = grok_home / "skills" / "orch-here" / "SKILL.md"
                kept_agent = grok_home / "agents" / "orch-worker.md"
                plan = self._role_agent_plan(
                    root,
                    receipt_path=receipt_path,
                    grok_skills=[(kept_skill, "here\n")],
                    grok_agents=[(kept_agent, "worker\n")],
                )

                install.apply_plan(plan)

                self.assertFalse(stale_skill.exists())
                self.assertFalse(stale_skill.parent.exists())
                self.assertFalse(stale_agent.exists())
                self.assertEqual("here\n", kept_skill.read_text(encoding="utf-8"))
                self.assertEqual("worker\n", kept_agent.read_text(encoding="utf-8"))
                self.assertEqual("before\n", mine.read_text(encoding="utf-8"))

    def test_enabling_grok_leaves_every_claude_and_codex_write_byte_identical(self):
        """The third host adds files; it moves and rewrites none.

        Both halves install into the same absolute home, the first one
        removed before the second runs, so the comparison is of bytes rather
        than of bytes modulo a root path -- two fake homes at different paths
        could not be compared at all, since an adapter body names its own
        library home.
        """

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            censuses = []
            for hosts in (("claude", "codex"), ("claude", "codex", "grok")):
                if home.exists():
                    shutil.rmtree(home)
                home.mkdir()
                with isolated_grok_home(root) as grok_home, patch.object(
                    install.Path, "home", return_value=home
                ), mock_host_clis(*hosts), self._no_runtime_build():
                    plan = install.build_plan("user", None)
                    install.apply_plan(plan)
                censuses.append(
                    {
                        str(path.relative_to(home)): digest(path)
                        for directory in (home / ".claude", home / ".codex")
                        for path in sorted(directory.rglob("*"))
                        if path.is_file()
                    }
                )
                self.assertEqual(
                    "grok" in hosts,
                    any(path.is_file() for path in grok_home.rglob("*")),
                )
            without, with_grok = censuses
            self.assertTrue(without)
            self.assertEqual(without, with_grok)

    def test_the_printed_plan_and_summary_report_the_grok_surface(self):
        """``--dry-run`` and the install summary say what lands on Grok.

        A host whose surface is planned and applied but never named reads, to
        the one person who has to check it, exactly like a host that was
        never installed.
        """

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            home.mkdir()
            with isolated_grok_home(root) as grok_home, patch.object(
                install.Path, "home", return_value=home
            ), mock_host_clis("grok"), self._no_runtime_build():
                plan = install.build_plan("user", None)
                printed = io.StringIO()
                with redirect_stdout(printed):
                    install.print_plan(plan)
                    install.print_summary(plan)

            text = printed.getvalue()
            self.assertIn("detected grok CLI: yes", text)
            self.assertIn(str(plan.grok_rules.dest), text)
            self.assertIn(str(plan.grok_agents[0][0]), text)
            self.assertIn(f"Grok skills ({len(plan.grok_skills)})", text)
            self.assertIn(str(grok_home / "skills"), text)

        with tempfile.TemporaryDirectory() as other:
            second = Path(other) / "home"
            second.mkdir()
            with isolated_grok_home(Path(other)), patch.object(
                install.Path, "home", return_value=second
            ), mock_host_clis("claude"), self._no_runtime_build():
                quiet = io.StringIO()
                with redirect_stdout(quiet):
                    install.print_plan(install.build_plan("user", None))
        self.assertIn("detected grok CLI: no", quiet.getvalue())
        self.assertIn("Grok skills (0)", quiet.getvalue())
