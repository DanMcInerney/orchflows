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
