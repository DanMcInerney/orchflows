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
            self.assertEqual((core / "scripts/native_logs.py").read_bytes(), (ROOT / "scripts/native_logs.py").read_bytes())
            self.assertFalse((core / "example-workflows").exists())
            self.assertEqual(cli(python, script, "setup")["core"]["status"], "reused")

            native_log = outside / "claude/projects/demo/native-session.jsonl"
            native_log.parent.mkdir(parents=True)
            native_log.write_text(json.dumps({"type": "assistant", "cwd": str(project), "timestamp": "2026-09-11T12:00:00Z", "message": {"content": [
                {"type": "tool_use", "id": "call", "name": "Read", "input": {"file_path": "evidence-λ.txt"}}
            ]}}) + "\n", encoding="utf-8")
            inspected = cli(python, script, "history", "inspect", "claude", "native-session")
            self.assertEqual(inspected["agents"][0]["unmatched_count"], 1)
            found = cli(python, script, "history", "find", "claude", "--project", str(project), "--since", "2026-09-04")
            self.assertEqual(found["candidates"][0]["id"], "native-session")
            self.assertEqual(cli(python, script, "history", "read", "claude", "native-session", "--until", "2026-09-11")["events"], [])
            page = cli(python, script, "history", "read", "claude", "native-session", "--limit", "1")
            expanded = cli(python, script, "history", "read", "claude", "native-session", "--event", page["events"][0]["event_id"])
            self.assertEqual(json.loads(expanded["text"])["file_path"], "evidence-λ.txt")
            self.assertEqual({skill.name for skill in (core / "skills").iterdir()},
                             {"orch-work", "orch-review", "orch-dynamic-workflow", "orch-self-improve", "orch-build-workflow"})
            for removed in ("orch-parallel", "orch-compare", "orch-make-and-review", "orch-setup", "orch-record-run"):
                unavailable = cli(python, script, "resolve", "orchflows-light", "--skill", removed, expected=2)
                self.assertIn("error", unavailable)
            for skill in (ROOT / "skills").iterdir():
                resolved_core = cli(python, script, "resolve", "orchflows-light", "--skill", skill.name)
                self.assertEqual(Path(resolved_core["skill_path"]), core / "skills" / skill.name / "SKILL.md")

            def files(path):
                return {item.relative_to(path).as_posix(): hashlib.sha256(item.read_bytes()).hexdigest()
                        for item in path.rglob("*") if item.is_file()
                        and "__pycache__" not in item.parts and item.suffix not in {".pyc", ".pyo"}}

            self.assertEqual(files(ROOT / "example-workflows/social-search"), files(home / "libraries/social-search"))
            resolved = cli(python, script, "resolve", "social-search", "--skill", "social-search")
            self.assertEqual(resolved["runtime_python"], python)
            self.assertEqual(Path(resolved["skill_path"]), home / "libraries/social-search/skills/social-search/SKILL.md")

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
