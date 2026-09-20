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
    def test_history_read_without_bytecode_flags_leaves_files_unchanged(self):
        with tempfile.TemporaryDirectory(prefix="orchflows-history-cli-") as temporary:
            outside = Path(temporary).resolve()
            scripts = outside / "scripts"
            scripts.mkdir()
            for source in (ROOT / "scripts").glob("*.py"):
                (scripts / source.name).write_bytes(source.read_bytes())
            project = outside / "unrelated-project"
            project.mkdir()
            environment = dict(os.environ, ORCHFLOWS_HOME=str(outside / "home"),
                               CODEX_HOME=str(outside / "codex"), CLAUDE_CONFIG_DIR=str(outside / "claude"),
                               HOME=str(outside / "userhome"), USERPROFILE=str(outside / "userhome"))
            environment.pop("PYTHONDONTWRITEBYTECODE", None)
            environment.pop("PYTHONPYCACHEPREFIX", None)
            native_log = outside / "claude/projects/demo/native-session.jsonl"
            native_log.parent.mkdir(parents=True)
            native_log.write_text(json.dumps({"type": "assistant", "cwd": str(project), "timestamp": "2026-09-11T12:00:00Z", "message": {"content": [
                {"type": "text", "text": "Read-only history λ"}
            ]}}) + "\n", encoding="utf-8")

            def files():
                return {item.relative_to(outside).as_posix(): hashlib.sha256(item.read_bytes()).hexdigest()
                        for item in outside.rglob("*") if item.is_file()}

            before = files()
            result = subprocess.run(
                [sys.executable, str(scripts / "orchflows.py"), "history", "read", "claude", "native-session"],
                cwd=project, env=environment, capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            page = json.loads(result.stdout)
            self.assertEqual(page["id"], "native-session")
            self.assertEqual([event["data"]["text"] for event in page["events"]], ["Read-only history λ"])
            self.assertEqual(files(), before)

    def test_real_core_resolves_logs_and_keeps_its_documentation_reachable(self):
        with tempfile.TemporaryDirectory(prefix="orchflows-installed-cli-") as temporary:
            outside = Path(temporary).resolve()
            home = outside / "home"
            project = outside / "unrelated-project"
            project.mkdir()
            environment = dict(os.environ, ORCHFLOWS_HOME=str(home), PYTHONDONTWRITEBYTECODE="1",
                               CODEX_HOME=str(outside / "codex"), CLAUDE_CONFIG_DIR=str(outside / "claude"),
                               HOME=str(outside / "userhome"), USERPROFILE=str(outside / "userhome"))

            def cli(python, script, *arguments, expected=0):
                if arguments[0] in {"setup", "doctor"}:
                    arguments = (*arguments, "--host", "none")
                result = subprocess.run(
                    [str(python), "-B", str(script), *map(str, arguments)],
                    cwd=project, env=environment, capture_output=True, text=True, timeout=60,
                )
                self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
                return json.loads(result.stdout or result.stderr)

            installed = cli(sys.executable, ROOT / "scripts/orchflows.py", "setup", "--example", "social-search")
            self.assertEqual(installed["host_config_status"], "skipped")
            self.assertEqual(installed["host_configs"], {})
            self.assertFalse((outside / "codex").exists())
            self.assertFalse((outside / "claude").exists())
            python = installed["runtime_python"]
            core = Path(installed["core"]["package_root"])
            script = core / "scripts/orchflows.py"
            self.assertEqual((core / "scripts/native_logs.py").read_bytes(), (ROOT / "scripts/native_logs.py").read_bytes())
            self.assertEqual((core / ".kimi-plugin/plugin.json").read_bytes(), (ROOT / ".kimi-plugin/plugin.json").read_bytes())
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
                             {"orch-work", "orch-review",
                              "orch-build-workflow", "orch-dynamic-workflow"})
            for removed in ("orch-parallel", "orch-compare", "orch-make-and-review", "orch-setup", "orch-record-run",
                            "orch-self-improve", "self-improve", "orch-review-revise-once", "review-revise-once"):
                unavailable = cli(python, script, "resolve", "orchflows", "--skill", removed, expected=2)
                self.assertIn("error", unavailable)
            for skill in (ROOT / "skills").iterdir():
                resolved_core = cli(python, script, "resolve", "orchflows", "--skill", skill.name)
                self.assertEqual(Path(resolved_core["skill_path"]), core / "skills" / skill.name / "SKILL.md")

            def files(path):
                return {item.relative_to(path).as_posix(): hashlib.sha256(item.read_bytes()).hexdigest()
                        for item in path.rglob("*") if item.is_file()
                        and "__pycache__" not in item.parts and item.suffix not in {".pyc", ".pyo"}}

            self.assertEqual(files(ROOT / "example-workflows/social-search"), files(home / "libraries/social-search"))
            catalog = json.loads((home / "marketplace.json").read_text(encoding="utf-8"))
            for entry in catalog["plugins"]:
                package = home / entry["source"]
                for host in (".claude-plugin", ".kimi-plugin"):
                    manifest = json.loads((package / host / "plugin.json").read_text(encoding="utf-8"))
                    self.assertEqual((manifest["name"], manifest["version"]), (entry["name"], entry["version"]))
                    self.assertTrue((package / manifest["skills"]).is_dir())
            resolved = cli(python, script, "resolve", "social-search", "--skill", "social-search")
            self.assertEqual(resolved["runtime_python"], python)
            self.assertEqual(Path(resolved["skill_path"]), home / "libraries/social-search/skills/social-search/SKILL.md")

            example_libraries = []
            for name, skill_names in (
                ("export-workflow", ("export-workflow",)),
                ("self-improve", ("self-improve",)),
                ("shared", ("compare-candidates", "review-revise-once")),
                ("design-loop", ("design-loop", "test-increment")),
                ("benchmaker", ("benchmaker",)),
            ):
                cli(python, script, "setup", "--source", ROOT, "--example", name)
                library = home / "libraries" / name
                example_libraries.append(library)
                self.assertEqual(files(ROOT / "example-workflows" / name), files(library))
                for skill_name in skill_names:
                    resolved_example = cli(python, script, "resolve", name, "--skill", skill_name)
                    self.assertEqual(Path(resolved_example["skill_path"]), library / "skills" / skill_name / "SKILL.md")
                self.assertFalse((core / "skills" / name).exists())
                self.assertFalse((core / "skills" / f"orch-{name}").exists())

            for package in (core, *example_libraries):
                for document in package.rglob("*.md"):
                    for target in re.findall(r'\]\(([^)\s]+)(?:\s+"[^"]*")?\)', document.read_text(encoding="utf-8")):
                        if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target):
                            continue
                        relative = unquote(target.partition("#")[0])
                        linked = (document.parent / relative).resolve() if relative else document
                        with self.subTest(package=package.name, document=document.relative_to(package), target=target):
                            self.assertTrue(linked.is_relative_to(package), "Link escapes the installed package")
                            self.assertTrue(linked.exists(), "Link target is absent from the installed package")


if __name__ == "__main__":
    unittest.main()
