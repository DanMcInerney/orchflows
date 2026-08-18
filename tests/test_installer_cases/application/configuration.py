"""Installer regression cases grouped by behavioral seam."""

from __future__ import annotations

from ..support import *  # noqa: F403


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

    def test_no_warning_when_hooks_file_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual([], install._codex_hooks_warnings(Path(tmp)))

    def test_an_unreadable_hooks_file_says_it_was_not_checked(self):
        # "No dangling paths" and "I could not look" are different answers;
        # returning [] for both let a broken hooks.json read as a clean
        # preflight (F F9).
        with tempfile.TemporaryDirectory() as tmp:
            codex_home = Path(tmp)
            (codex_home / "hooks.json").write_text("not json", encoding="utf-8")

            warnings = install._codex_hooks_warnings(codex_home)

            self.assertEqual(1, len(warnings))
            self.assertIn(str(codex_home / "hooks.json"), warnings[0])
            self.assertIn("not checked", warnings[0])

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

            with patch.object(install.Path, "home", return_value=home), mock_host_clis("codex"):
                plan = install.build_plan("user", None)

            dangling = dangling_path_warnings(plan)
            self.assertEqual(1, len(dangling), plan.warnings)
            self.assertIn("orch-missing", dangling[0])

    def test_user_plan_says_when_the_codex_config_could_not_be_toml_checked(self):
        # Below 3.11 there is no tomllib, so the merged config.toml is written
        # unparsed. Silently is how a malformed merge reaches a user's Codex.
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".codex").mkdir(parents=True)

            with patch.object(install.Path, "home", return_value=home), mock_host_clis(
                "codex"
            ), patch.object(install, "tomllib", None):
                plan = install.build_plan("user", None)

            self.assertTrue(
                any("tomllib" in warning for warning in plan.warnings),
                plan.warnings,
            )

    @requires_tomllib
    def test_no_toml_check_warning_when_this_interpreter_has_tomllib(self):
        # The other half of the pin above, and the coverage the hooks tests
        # gave up when they stopped counting every warning: where tomllib
        # exists the merge is parse-checked, so the warning must not fire --
        # and a clean codex user plan then has no true warning left, so the
        # whole list is asserted empty, which is what catches any spurious
        # warning on this path. Nothing to assert below 3.11, where the
        # TOML-merge warning is the truth.
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".codex").mkdir(parents=True)

            with patch.object(install.Path, "home", return_value=home), mock_host_clis("codex"):
                plan = install.build_plan("user", None)

            self.assertEqual([], plan.warnings)
class TestClaudeConfigDir(unittest.TestCase):
    """``CLAUDE_CONFIG_DIR`` relocates Claude Code's user config directory, so
    every user-scope Claude surface follows it instead of ``~/.claude`` — the
    same override Claude Code itself reads."""

    def test_user_plan_writes_every_claude_surface_under_claude_config_dir(self):
        plan, home, config_dir, _codex_dir = relocated_user_install()
        self.assertTrue(plan.claude_adapters)
        for dest, _ in plan.claude_adapters:
            self.assertEqual(config_dir / "skills", dest.parent.parent)
        self.assertTrue(plan.claude_agents)
        for dest, _ in plan.claude_agents:
            self.assertEqual(config_dir / "agents", dest.parent)
        self.assertTrue((config_dir / "settings.json").is_file())
        self.assertTrue((config_dir / "CLAUDE.md").is_file())
        self.assertFalse((home / ".claude").exists())

    def test_uninstall_removes_adapter_installed_under_claude_config_dir(self):
        plan, report, config_dir, _codex_dir = relocated_user_uninstall()
        adapters = {str(dest) for dest, _ in plan.claude_adapters}
        self.assertTrue(adapters)
        self.assertTrue(adapters <= removed_unchanged(report))
        for path in adapters:
            self.assertEqual(config_dir / "skills", Path(path).parent.parent)
        self.assertFalse((config_dir / "skills").exists())

    def test_blank_claude_config_dir_falls_back_to_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".claude").mkdir(parents=True)
            with patch.object(install.Path, "home", return_value=home), patch.dict(
                os.environ, {"CLAUDE_CONFIG_DIR": "  "}
            ), mock_host_clis("claude"):
                plan = install.build_plan("user", None)

            for dest, _ in plan.claude_adapters:
                self.assertEqual(home / ".claude" / "skills", dest.parent.parent)
class TestCodexHome(unittest.TestCase):
    """``CODEX_HOME`` relocates the Codex CLI's config directory the same way
    ``CLAUDE_CONFIG_DIR`` relocates Claude Code's."""

    def test_user_plan_writes_every_codex_surface_under_codex_home(self):
        plan, home, _claude_dir, codex_home = relocated_user_install()
        self.assertTrue(plan.codex_prompts)
        for dest, _ in plan.codex_prompts:
            self.assertEqual(codex_home / "prompts", dest.parent)
        self.assertTrue(plan.codex_skills)
        for dest, _ in plan.codex_skills:
            self.assertEqual(codex_home / "skills", dest.parent.parent)
        self.assertTrue(plan.codex_agents)
        for dest, _ in plan.codex_agents:
            self.assertEqual(codex_home / "agents", dest.parent)
        self.assertTrue((codex_home / "config.toml").is_file())
        self.assertTrue((codex_home / "AGENTS.md").is_file())
        self.assertFalse((home / ".codex").exists())

    def test_uninstall_removes_codex_skills_installed_under_codex_home(self):
        plan, report, _claude_dir, codex_home = relocated_user_uninstall()
        installed = {str(dest) for dest, _ in plan.codex_prompts + plan.codex_skills}
        self.assertTrue(installed)
        self.assertTrue(installed <= removed_unchanged(report))
        for path in installed:
            self.assertIn(codex_home, Path(path).parents)
        self.assertFalse((codex_home / "skills").exists())
        self.assertFalse((codex_home / "prompts").exists())

    def test_hooks_warning_reads_relocated_codex_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()
            codex_home = Path(tmp) / "elsewhere" / "codex"
            codex_home.mkdir(parents=True)
            (codex_home / "hooks.json").write_text(
                json.dumps({"command": [str(codex_home / "orch-missing" / "x.py")]}),
                encoding="utf-8",
            )

            with patch.object(install.Path, "home", return_value=home), patch.dict(
                os.environ, {"CODEX_HOME": str(codex_home)}
            ), mock_host_clis("codex"):
                plan = install.build_plan("user", None)

            dangling = dangling_path_warnings(plan)
            self.assertEqual(1, len(dangling), plan.warnings)
            self.assertIn(str(codex_home / "hooks.json"), dangling[0])
            self.assertIn("orch-missing", dangling[0])

    def test_blank_codex_home_falls_back_to_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".codex").mkdir(parents=True)
            with patch.object(install.Path, "home", return_value=home), patch.dict(
                os.environ, {"CODEX_HOME": "  "}
            ), mock_host_clis("codex"):
                plan = install.build_plan("user", None)

            for dest, _ in plan.codex_skills:
                self.assertEqual(home / ".codex" / "skills", dest.parent.parent)
