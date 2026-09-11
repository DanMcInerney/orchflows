"""The actual shipped core must work after setup from an unrelated project."""

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]


class InstalledCliTests(unittest.TestCase):
    def test_real_core_resolves_logs_and_keeps_its_documentation_reachable(self):
        with tempfile.TemporaryDirectory(prefix="orchflows-installed-cli-") as temporary:
            outside = Path(temporary).resolve()
            home = outside / "home"
            project = outside / "unrelated-project"
            project.mkdir()
            environment = dict(os.environ, ORCHFLOWS_HOME=str(home), PYTHONDONTWRITEBYTECODE="1",
                               CODEX_HOME=str(outside / "codex"), CLAUDE_CONFIG_DIR=str(outside / "claude"))

            def cli(python, script, *arguments, expected=0):
                result = subprocess.run(
                    [str(python), "-B", str(script), *map(str, arguments)],
                    cwd=project, env=environment, capture_output=True, text=True, timeout=60,
                )
                self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
                return json.loads(result.stdout or result.stderr)

            installed = cli(sys.executable, ROOT / "scripts/orchflows.py", "setup", "--example", "social-search")
            self.assertEqual(installed["host_config_status"], "configured")
            self.assertEqual(installed["host_configs"]["codex"]["value"], 15)
            self.assertEqual(installed["host_configs"]["claude"]["value"], 15)
            python = installed["runtime_python"]
            core = Path(installed["core"]["package_root"])
            script = core / "scripts/orchflows.py"
            self.assertFalse((core / "example-workflows").exists())
            self.assertEqual(cli(python, script, "setup")["core"]["status"], "reused")

            def files(path):
                return {item.relative_to(path).as_posix(): hashlib.sha256(item.read_bytes()).hexdigest()
                        for item in path.rglob("*") if item.is_file()
                        and "__pycache__" not in item.parts and item.suffix not in {".pyc", ".pyo"}}

            self.assertEqual(files(ROOT / "example-workflows/social-search"), files(home / "libraries/social-search"))
            resolved = cli(python, script, "resolve", "social-search", "--skill", "social-search")
            self.assertEqual(resolved["runtime_python"], python)
            self.assertEqual(Path(resolved["skill_path"]), home / "libraries/social-search/skills/social-search/SKILL.md")

            started = cli(python, script, "run", "start", "--workflow", "social-search:social-search")
            run = Path(started["run_dir"])
            summary = project / "summary.md"
            summary.write_text("Installed CLI integration check completed.\n", encoding="utf-8")
            finished = cli(python, script, "run", "finish", run, "--status", "complete", "--summary", summary)
            self.assertEqual(Path(finished["summary_file"]).read_bytes(), summary.read_bytes())
            self.assertEqual(finished["provenance"]["core"]["version"], installed["core"]["version"])
            self.assertEqual(finished["provenance"]["workflow"]["version"], resolved["version"])
            self.assertEqual(cli(python, script, "run", "finish", run, "--status", "complete", "--summary", summary), finished)
            summary.write_text("A conflicting outcome.\n", encoding="utf-8")
            rejected = cli(python, script, "run", "finish", run, "--status", "complete", "--summary", summary, expected=2)
            self.assertIn("already finalized", rejected["error"])

            for document in core.rglob("*.md"):
                for target in re.findall(r'\]\(([^)\s]+)(?:\s+"[^"]*")?\)', document.read_text(encoding="utf-8")):
                    if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target):
                        continue
                    relative = unquote(target.partition("#")[0])
                    linked = (document.parent / relative).resolve() if relative else document
                    with self.subTest(document=document.relative_to(core), target=target):
                        self.assertTrue(linked.is_relative_to(core), "Link escapes the installed package")
                        self.assertTrue(linked.exists(), "Link target is absent from the installed package")


if __name__ == "__main__":
    unittest.main()
