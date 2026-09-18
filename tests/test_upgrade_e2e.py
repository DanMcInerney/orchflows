"""Real main installer -> current installer -> installed CLI, without mocks/network."""

import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
# The fetched main used in design/main-to-current.md; deliberately immutable.
MAIN = "16d2644ba25562d66af5648a7dfed8ebde1cfe90"


def snapshot(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()}


class MainUpgradeEndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("git"):
            raise unittest.SkipTest("Main-upgrade E2E needs git and the pinned main commit")
        archive = subprocess.run(["git", "archive", "--format=zip", MAIN], cwd=ROOT,
                                 capture_output=True, timeout=20)
        if archive.returncode:
            raise unittest.SkipTest(f"Pinned main {MAIN} is absent; fetch repository history to run this E2E")
        cls.archive = archive.stdout

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="orchflows-upgrade-e2e-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.main = self.root / "main"
        with zipfile.ZipFile(io.BytesIO(self.archive)) as archive:
            archive.extractall(self.main)
        self.project = self.root / "unrelated project"
        self.project.mkdir()
        self.home = self.root / "home"
        self.env = dict(os.environ, ORCHFLOWS_HOME=str(self.home), PYTHONDONTWRITEBYTECODE="1",
                        HOME=str(self.root / "user"), USERPROFILE=str(self.root / "user"),
                        CODEX_HOME=str(self.root / "codex"), CLAUDE_CONFIG_DIR=str(self.root / "claude"),
                        KIMI_CODE_HOME=str(self.root / "kimi"), GROK_HOME=str(self.root / "grok"))
        for directory, filename, contents in (
            ("codex", "config.toml", 'model = "user-chosen-model"\n'),
            ("claude", "settings.json", '{"env":{"USER_SENTINEL":"keep"}}\n'),
            ("kimi", "config.toml", '[background]\nmax_running_tasks = 7\n'),
        ):
            path = self.root / directory / filename
            path.parent.mkdir()
            path.write_text(contents, encoding="utf-8")
        self.host_before = {name: snapshot(self.root / name) for name in ("codex", "claude", "kimi")}
        installed = self.cli(self.main / "scripts/orchflows.py", "setup", "--example", "design-loop")
        self.assertEqual(installed["status"], "ready", installed)
        self.python = installed["runtime_python"]
        self.core = Path(installed["core"]["package_root"])
        self.script = self.core / "scripts/orchflows.py"
        self.assertEqual(installed["core"]["version"], "0.7.1")
        self.assertTrue(Path(self.cli(self.script, "resolve", "orchflows", "--skill",
                                      "orch-dynamic-workflow")["skill_path"]).is_file())
        personal = self.home / "libraries/personal"
        (personal / "skills/weekly-note").mkdir(parents=True)
        (personal / "plugin.json").write_text(json.dumps({"name": "personal", "version": "1.0.0"}), encoding="utf-8")
        (personal / "skills/weekly-note/SKILL.md").write_text("A user-owned weekly note.\n", encoding="utf-8")
        (self.home / "libraries/design-loop/guidance/design-iteration.md").write_text(
            "My modified design preferences. Preserve these.\n", encoding="utf-8")
        self.libraries_before = snapshot(self.home / "libraries")

    def cli(self, script, *arguments, expected=0):
        if arguments[0] in {"setup", "doctor"}:
            arguments = (*arguments, "--host", "none")
        completed = subprocess.run([getattr(self, "python", sys.executable), "-B", str(script), *arguments],
                                   cwd=self.project, env=self.env, capture_output=True, text=True, timeout=30)
        self.assertEqual(completed.returncode, expected, completed.stdout + completed.stderr)
        return json.loads(completed.stdout or completed.stderr)

    def test_upgrade_replaces_old_core_preserves_user_libraries_and_runs_without_source(self):
        # Upgrade through the actual OLD installed command, as an existing user can.
        upgraded = self.cli(self.script, "setup", "--source", str(ROOT), "--example", "design-loop")
        self.assertEqual(upgraded["status"], "ready", upgraded)
        self.assertEqual(upgraded["example"]["status"], "preserved")
        self.assertEqual(snapshot(self.home / "libraries"), self.libraries_before)
        expected_version = json.loads((ROOT / "plugin.json").read_text())["version"]
        self.assertEqual(upgraded["core"]["version"], expected_version)
        # Remove the old source, then use only the installed interpreter/command.
        self.assertTrue(self.main.resolve().is_relative_to(self.root))
        shutil.rmtree(self.main)
        for skill in ("orch-work", "orch-review", "orch-build-workflow", "orch-review-revise-once", "orch-dynamic-workflow"):
            resolved = Path(self.cli(self.script, "resolve", "orchflows", "--skill", skill)["skill_path"])
            self.assertTrue(resolved.is_relative_to(self.core))
            self.assertEqual(resolved.read_bytes(), (ROOT / "skills" / skill / "SKILL.md").read_bytes())
        for library, skill in (("orchflows", "orch-make-and-review"), ("shared", "review-revise-once")):
            if library == "shared":
                self.cli(self.script, "setup", "--source", str(ROOT), "--example", "shared")
            self.assertIn("not installed", self.cli(self.script, "resolve", library, "--skill", skill, expected=2)["error"])
        self.assertTrue(Path(self.cli(self.script, "resolve", "personal", "--skill", "weekly-note")["skill_path"]).is_file())
        self.assertEqual(self.cli(self.script, "doctor")["status"], "ready")
        before = snapshot(self.home)
        self.assertEqual(self.cli(self.script, "setup")["core"]["status"], "reused")
        self.assertEqual(snapshot(self.home), before, "Idempotent setup must not change installed bytes")
        self.assertEqual({name: snapshot(self.root / name) for name in self.host_before}, self.host_before)

    def test_rejected_upgrade_leaves_main_installation_usable_and_unchanged(self):
        invalid = self.root / "invalid-source"
        invalid.mkdir()
        (invalid / "plugin.json").write_text('{"name":"wrong-package","version":"1"}', encoding="utf-8")
        before = snapshot(self.home)
        failure = self.cli(ROOT / "scripts/orchflows.py", "setup", "--source", str(invalid), expected=2)
        self.assertIn("Core source must identify as orchflows", failure["error"])
        self.assertEqual(snapshot(self.home), before)
        resolved = self.cli(self.script, "resolve", "orchflows", "--skill", "orch-dynamic-workflow")
        self.assertEqual(resolved["version"], "0.7.1")
        self.assertTrue(Path(resolved["skill_path"]).is_file())
        self.assertEqual({name: snapshot(self.root / name) for name in self.host_before}, self.host_before)


if __name__ == "__main__":
    unittest.main()
