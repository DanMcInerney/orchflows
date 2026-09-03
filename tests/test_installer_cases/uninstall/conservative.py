"""Installer regression cases grouped by behavioral seam."""

from __future__ import annotations

from ..support import *  # noqa: F403


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
        """``claude-config`` is the kind this line is for.

        Claude's is a JSON settings file the installer sets one env key
        inside, and nothing here can lift one key back out of JSON the way
        the two TOML blocks come out. So the removal stays the user's, and
        the manual line has to hand them the exact setting to undo.
        """

        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            config = project / ".claude" / "settings.json"
            config.parent.mkdir()
            config.write_text(
                '{"env": {"CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY": "20"}}\n', encoding="utf-8"
            )
            self._write_receipt(
                project,
                [
                    {
                        "path": str(config),
                        "kind": "claude-config",
                        "install_action": "created",
                        "sha256": digest(config),
                        "details": {"setting": "env.CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY"},
                    }
                ],
            )

            result = install.run_uninstall("project", project, dry_run=False)

            self.assertTrue(config.exists())
            self.assertIn(
                '"setting": "env.CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY"',
                result["manual_actions"][0]["action"],
            )

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
            stub = home / ".codex" / "skills" / "orch-outline" / "SKILL.md"
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

    # --- Grok ------------------------------------------------------------

    def test_uninstall_removes_the_installed_grok_surface_by_receipt(self):
        """A real install into an isolated Grok home, then its uninstall.

        The census is taken off the plan rather than spelled out, so a Grok
        artifact added later is graded by this case the day it is planned.
        Two things the receipt does not claim are seeded first: a hand-written
        skill, and a ``config.toml`` the user already had. The skill has to
        survive untouched and the config has to come back holding its own
        table -- the installer owns the marked block inside that file, not the
        file, and not everything that ends up inside the block either. Grok's
        own appended table is planted between the markers midway, so the
        reinstall and the uninstall are both graded on it.
        """

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            home.mkdir()
            with isolated_grok_home(root) as grok_home:
                config = grok_home / "config.toml"
                config.write_text('[permission]\nmode = "ask"\n', encoding="utf-8")
                mine = grok_home / "skills" / "handwritten" / "SKILL.md"
                mine.parent.mkdir(parents=True)
                mine.write_text("mine\n", encoding="utf-8")

                with patch.object(install.Path, "home", return_value=home), mock_host_clis(
                    "grok"
                ), patch.object(install, "private_runtime_action", return_value=None):
                    plan = install.build_plan()
                    install.apply_plan(plan, accepted_source=install.resolve_source_commit())
                    self.assertIn("max_concurrent", config.read_text(encoding="utf-8"))
                    # Grok appends its own table within 0.2s of any subcommand,
                    # and a TOML editor lands it ahead of a trailing END
                    # comment -- inside the markers. Planted rather than
                    # provoked: nothing here may execute ``grok.exe``.
                    config.write_text(
                        config.read_text(encoding="utf-8").replace(
                            install.GROK_LIMITS_END,
                            "[marketplace]\ndefault_skills_installs_purged = true\n"
                            + install.GROK_LIMITS_END,
                        ),
                        encoding="utf-8",
                    )
                    install.apply_plan(install.build_plan(), accepted_source=install.resolve_source_commit())
                    reinstalled = config.read_text(encoding="utf-8")
                    self.assertIn("default_skills_installs_purged = true", reinstalled)
                    self.assertIn("max_concurrent", reinstalled)
                    # The rewritten block sits above grok's table now, off the
                    # EOF that invited the append -- so the uninstall would
                    # never meet it. Grok runs again before the uninstall does,
                    # which puts a fresh table back inside the markers.
                    config.write_text(
                        reinstalled.replace(
                            install.GROK_LIMITS_END,
                            "[telemetry]\nenabled = false\n" + install.GROK_LIMITS_END,
                        ),
                        encoding="utf-8",
                    )
                    installed = [dest for dest, _ in plan.grok_skills + plan.grok_agents]
                    installed.append(plan.grok_rules.dest)
                    report = install.run_uninstall("user", None, dry_run=False)

                for path in installed:
                    self.assertFalse(path.exists(), path)
                removed = {entry["path"] for entry in report["skill_actions"]}
                self.assertTrue({str(path) for path in installed} <= removed)
                self.assertIn(str(config), removed)
                manual = {entry["path"] for entry in report["manual_actions"]}
                self.assertFalse({str(path) for path in installed + [config]} & manual)

                self.assertTrue(mine.is_file())
                self.assertEqual("mine\n", mine.read_text(encoding="utf-8"))
                remaining = config.read_text(encoding="utf-8")
                self.assertNotIn("# BEGIN ORCHFLOWS SUBAGENT LIMITS", remaining)
                self.assertNotIn("max_concurrent", remaining)
                self.assertIn('mode = "ask"', remaining)
                self.assertIn("default_skills_installs_purged = true", remaining)
                self.assertIn("enabled = false", remaining)

    def test_uninstall_drops_a_grok_config_the_installer_wrote_whole(self):
        """No user TOML, no file: the installer's own block was all of it.

        The companion to the case above. There the merge ran into a file the
        user already had, so the file stays; here the installer created it,
        so removing the block leaves nothing to keep. A hand-written file next
        to the managed rules file proves the removal reads the receipt and not
        the directory.
        """

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with isolated_grok_home(root) as grok_home:
                config = grok_home / "config.toml"
                config.write_text(
                    "# BEGIN ORCHFLOWS SUBAGENT LIMITS\n"
                    "subagents.max_concurrent = 20\n"
                    "# END ORCHFLOWS SUBAGENT LIMITS\n",
                    encoding="utf-8",
                )
                rules = grok_home / "rules" / "orchflows.md"
                mine = grok_home / "rules" / "mine.md"
                rules.parent.mkdir(parents=True)
                rules.write_text("managed\n", encoding="utf-8")
                mine.write_text("mine\n", encoding="utf-8")
                receipt_path = root / ".orchflows" / "receipt.json"
                receipt_path.parent.mkdir(parents=True)
                receipt_path.write_text(
                    json.dumps(
                        {
                            "files": [
                                {
                                    "path": str(rules),
                                    "kind": "grok-rules",
                                    "install_action": "created",
                                    "sha256": digest(rules),
                                },
                                {
                                    "path": str(config),
                                    "kind": "grok-config",
                                    "install_action": "created",
                                    "sha256": digest(config),
                                },
                            ]
                        }
                    ),
                    encoding="utf-8",
                )

                with patch.object(install.Path, "home", return_value=root):
                    report = install.run_uninstall("user", None, dry_run=True)
                    self.assertTrue(config.is_file())
                    self.assertTrue(rules.is_file())
                    report = install.run_uninstall("user", None, dry_run=False)

                self.assertFalse(config.exists())
                self.assertFalse(rules.exists())
                self.assertTrue(mine.is_file())
                self.assertEqual(2, len(report["skill_actions"]))

    def test_uninstall_keeps_a_table_grok_appended_inside_the_managed_block(self):
        """The removal is keyed on the installer's own lines, not on the span.

        Within 0.2s of any subcommand grok adds ``[marketplace]`` to its
        ``config.toml`` -- and a TOML editor appending a table at the end of
        the document body lands it *ahead of* the trailing END comment, which
        puts it inside the marked span. This plants exactly that file, since
        no test here may execute ``grok.exe``. The three installer keys go and
        grok's table stays, so the file stays too.
        """

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with isolated_grok_home(root) as grok_home:
                config = grok_home / "config.toml"
                config.write_text(
                    "# BEGIN ORCHFLOWS SUBAGENT LIMITS\n"
                    "subagents.max_concurrent = 20\n"
                    "subagents.max_depth = 4\n"
                    'subagents.limit_behavior = "queue"\n'
                    "[marketplace]\n"
                    "default_skills_installs_purged = true\n"
                    "# END ORCHFLOWS SUBAGENT LIMITS\n",
                    encoding="utf-8",
                )
                planted = config.read_text(encoding="utf-8")
                receipt_path = root / ".orchflows" / "receipt.json"
                receipt_path.parent.mkdir(parents=True)
                receipt_path.write_text(
                    json.dumps(
                        {
                            "files": [
                                {
                                    "path": str(config),
                                    "kind": "grok-config",
                                    "install_action": "created",
                                    "sha256": digest(config),
                                }
                            ]
                        }
                    ),
                    encoding="utf-8",
                )

                with patch.object(install.Path, "home", return_value=root):
                    dry = install.run_uninstall("user", None, dry_run=True)
                    self.assertEqual(planted, config.read_text(encoding="utf-8"))
                    report = install.run_uninstall("user", None, dry_run=False)

                for entry in dry["skill_actions"] + report["skill_actions"]:
                    self.assertIn("managed subagent limits block", entry["action"])
                # The receipt line is the only manual one left; the config is
                # not among them.
                self.assertEqual([str(receipt_path)], [e["path"] for e in report["manual_actions"]])

                self.assertTrue(config.is_file())
                remaining = config.read_text(encoding="utf-8")
                self.assertIn("[marketplace]", remaining)
                self.assertIn("default_skills_installs_purged = true", remaining)
                for gone in (
                    "# BEGIN ORCHFLOWS SUBAGENT LIMITS",
                    "# END ORCHFLOWS SUBAGENT LIMITS",
                    "max_concurrent",
                    "max_depth",
                    "limit_behavior",
                ):
                    self.assertNotIn(gone, remaining)
                if foundation.tomllib is not None:
                    parsed = foundation.tomllib.loads(remaining)
                    self.assertEqual(
                        {"default_skills_installs_purged": True}, parsed["marketplace"]
                    )
