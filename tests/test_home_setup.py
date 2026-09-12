"""Observable setup/resolve behavior, always using disposable homes."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/orchflows.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("orchflows", SCRIPT)
orchflows = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(orchflows)


def write(path: Path, contents: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents, encoding="utf-8")


def package(root: Path, name: str, version: str = "0.1.0") -> None:
    write(root / "plugin.json", json.dumps({"name": name, "version": version}))
    write(root / "skills/sample/SKILL.md", "---\nname: sample\ndescription: Test fixture.\n---\nRun the fixture.\n")


def snapshot(root: Path) -> dict[str, bytes]:
    return {str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()}


class HomeSetupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="orchflows-home-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.environment_patch = patch.dict(os.environ, {"CODEX_HOME": str(self.root / "codex"),
                                                         "CLAUDE_CONFIG_DIR": str(self.root / "claude")})
        self.environment_patch.start()
        self.addCleanup(self.environment_patch.stop)
        self.home = self.root / "home"
        self.source = self.root / "source"
        package(self.source, "orchflows-light", "7.8.9")
        write(self.source / ".codex-plugin/plugin.json", json.dumps({"name": "orchflows-light", "version": "7.8.9+cache"}))
        write(self.source / ".claude-plugin/plugin.json", json.dumps({"name": "orchflows-light", "version": "7.8.9"}))
        write(self.source / "guidance/code.md", "Local coding guidance.\n")
        write(self.source / "docs/hosts.md", "Fixture host docs.\n")
        write(self.source / "README.md", "Fixture core.\n")
        (self.source / "scripts").mkdir()
        for name in ("orchflows.py", "host_config.py", "native_logs.py"):
            shutil.copy2(SCRIPT.with_name(name), self.source / "scripts" / name)
        self.example = self.source / "example-workflows/social-search"
        package(self.example, "social-search")
        write(self.example / "README.md", "Example library.\n")
        write(self.example / "skills/sample/tests/test_fixture.py", "# Retained source test.\n")

    def install(self, *, example: bool = False) -> dict:
        result = orchflows.setup(self.home, self.source, "social-search" if example else None)
        self.assertEqual(result["status"], "ready", result)
        return result

    def cli(self, script: Path, *arguments: str, python: str | None = None, env: dict | None = None) -> subprocess.CompletedProcess:
        unrelated = self.root / "unrelated-project"
        unrelated.mkdir(exist_ok=True)
        return subprocess.run([python or sys.executable, "-B", str(script), *arguments], cwd=unrelated,
                              env=env, text=True, capture_output=True, timeout=45, check=False)

    def test_first_setup_installs_complete_core_runtime_and_example(self) -> None:
        write(self.source / ".git/config", "never copy source git")
        write(self.source / "tests/large-output.json", "never copy root tests")
        write(self.source / "scripts/__pycache__/discard.pyc", "never copy cache")
        result = self.install(example=True)
        core = Path(result["core"]["package_root"])
        self.assertEqual(result["core"]["status"], "installed")
        self.assertTrue((core / ".codex-plugin/plugin.json").is_file())
        self.assertTrue((core / ".claude-plugin/plugin.json").is_file())
        for relative in (".git", "tests", "example-workflows", "scripts/__pycache__"):
            self.assertFalse((core / relative).exists(), relative)
        self.assertEqual(snapshot(self.example), snapshot(self.home / "libraries/social-search"))
        config_text = (self.home / "config.toml").read_text(encoding="utf-8")
        self.assertEqual(tomllib.loads(config_text)["core"], {"name": "orchflows-light", "version": "7.8.9"})
        self.assertNotIn(str(self.source), config_text)
        self.assertEqual(orchflows.doctor(self.home)["status"], "ready")
        probe = subprocess.run([result["runtime_python"], "-I", "-c", "import importlib.util; print(importlib.util.find_spec('pip'))"], text=True, capture_output=True, check=True)
        self.assertEqual(probe.stdout.strip(), "None")

    def test_setup_cli_concurrency_override_and_opt_out(self) -> None:
        write(self.root / "codex/config.toml", "malformed = [\n")
        result = self.cli(SCRIPT, "setup", "--home", str(self.home), "--source", str(self.source), "--skip-host-config")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["host_config_status"], "skipped")
        self.assertEqual((self.root / "codex/config.toml").read_text(), "malformed = [\n")
        self.assertFalse((self.root / "claude").exists())
        write(self.root / "codex/config.toml", 'model = "personal"\n')
        result = self.cli(SCRIPT, "setup", "--home", str(self.home), "--source", str(self.source), "--concurrency", "22")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["host_configs"]["codex"]["value"], 22)
        self.assertEqual(tomllib.loads((self.root / "codex/config.toml").read_text())["agents"]["max_threads"], 22)
        self.assertEqual(json.loads((self.root / "claude/settings.json").read_text())["env"]["CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY"], "22")

    def test_host_preflight_and_invalid_concurrency_do_not_create_home(self) -> None:
        write(self.root / "claude/settings.json", '{"env":null}')
        with self.assertRaisesRegex(ValueError, "Host configuration preserved"):
            orchflows.setup(self.home, self.source)
        self.assertFalse(self.home.exists())
        self.assertFalse((self.root / "codex").exists())
        for arguments in (("--concurrency", "0"), ("--concurrency", "-1"), ("--concurrency", "many"),
                          ("--concurrency", "5", "--skip-host-config")):
            result = self.cli(SCRIPT, "setup", "--home", str(self.home), "--source", str(self.source), *arguments)
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertFalse(self.home.exists())

    def test_repeat_preserves_user_files_and_runtime_and_regenerates_owned_files(self) -> None:
        first = self.install(example=True)
        custom = self.home / "libraries/social-search/README.md"
        write(custom, "User's altered example.\n")
        write(self.home / "README.md", "My user-owned README.\n")
        write(self.home / ".gitignore", "my-user-pattern\n")
        runtime = self.home / ".local/runtime"
        marker = runtime / "user-marker.txt"
        write(marker, "Keep installed environment content.\n")
        write(self.home / "config.toml", "# hand edit\n[core]\nname = \"orchflows-light\"\nversion = \"0.0.0\"\n")
        catalog = self.home / ".claude-plugin/marketplace.json"
        write(catalog, '{"name":"my-own-catalog","plugins":[]}\n')
        write(Path(first["core"]["package_root"]) / "guidance/code.md", "Local edit inside the managed core.\n")
        before = {path: path.read_bytes() for path in (custom, self.home / "README.md", self.home / ".gitignore", marker, runtime / "pyvenv.cfg")}
        interpreter_mtime = Path(first["runtime_python"]).stat().st_mtime_ns
        second = self.install(example=True)
        self.assertEqual(second["core"]["status"], "updated")
        self.assertEqual(second["runtime"], "preserved")
        self.assertEqual(second["example"]["status"], "preserved")
        self.assertEqual({path: path.read_bytes() for path in before}, before)
        self.assertEqual(Path(first["runtime_python"]).stat().st_mtime_ns, interpreter_mtime)
        self.assertEqual(tomllib.loads((self.home / "config.toml").read_text())["core"]["version"], "7.8.9")
        self.assertEqual(json.loads(catalog.read_text())["name"], "orchflows-home")
        self.assertEqual((Path(first["core"]["package_root"]) / "guidance/code.md").read_text(), "Local coding guidance.\n")
        self.assertEqual(list((self.home / ".local/packages").iterdir()), [Path(first["core"]["package_root"])])

    def test_incomplete_existing_runtime_is_not_repaired(self) -> None:
        marker = self.home / ".local/runtime/my-environment.txt"
        write(marker, "not a venv; leave this directory alone\n")
        before = snapshot(marker.parent)
        result = orchflows.setup(self.home, self.source)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["runtime"], "unavailable")
        self.assertEqual(snapshot(marker.parent), before)
        self.assertIn("existing contents preserved", " ".join(result["issues"]))

    def test_changed_source_updates_core_and_preserves_user_content(self) -> None:
        write(self.source / "guidance/obsolete.md", "Old guidance.\n")
        first = self.install(example=True)
        core = Path(first["core"]["package_root"])
        write(self.home / "libraries/social-search/README.md", "My authored library.\n")
        write(self.home / "logs/saved.md", "My existing report.\n")
        retained = [self.home / "libraries/social-search/README.md", self.home / "logs/saved.md",
                    self.home / ".local/runtime/pyvenv.cfg", Path(first["runtime_python"])]
        retained_bytes = {path: path.read_bytes() for path in retained}
        (self.source / "guidance/obsolete.md").unlink()
        write(self.source / "guidance/code.md", "A changed guidance.\n")
        write(self.source / "plugin.json", json.dumps({"name": "orchflows-light", "version": "8.0.0"}))
        result = orchflows.setup(self.home, self.source)
        self.assertEqual(result["status"], "ready", result)
        self.assertEqual(result["core"]["status"], "updated")
        self.assertEqual((core / "guidance/code.md").read_text(), "A changed guidance.\n")
        self.assertFalse((core / "guidance/obsolete.md").exists())
        self.assertEqual({path: path.read_bytes() for path in retained}, retained_bytes)
        self.assertEqual(tomllib.loads((self.home / "config.toml").read_text())["core"]["version"], "8.0.0")
        self.assertEqual(orchflows.doctor(self.home)["status"], "ready")

    def test_failed_swap_restores_previous_core(self) -> None:
        first = self.install()
        core = Path(first["core"]["package_root"])
        before = snapshot(core)
        write(self.source / "guidance/code.md", "Upstream change.\n")
        replace, failed = os.replace, []

        def fail_once(source, destination):
            if Path(destination) == core and not failed:
                failed.append(destination)
                raise OSError("disk failure")
            return replace(source, destination)

        with patch.object(os, "replace", side_effect=fail_once):
            with self.assertRaisesRegex(OSError, "disk failure"):
                orchflows.setup(self.home, self.source)
        self.assertEqual(snapshot(core), before)
        self.assertEqual(list(core.parent.iterdir()), [core])
        self.assertEqual(orchflows.doctor(self.home)["status"], "ready")

    def test_failed_rename_of_previous_core_or_example_leaves_nothing_behind(self) -> None:
        first = self.install()
        core = Path(first["core"]["package_root"])
        before = snapshot(core)
        write(self.source / "guidance/code.md", "Upstream change.\n")
        replace = os.replace

        def fail_moving_aside(source, destination):
            if "-previous-" in Path(destination).name:
                raise OSError("disk failure")
            return replace(source, destination)

        with patch.object(os, "replace", side_effect=fail_moving_aside):
            with self.assertRaisesRegex(OSError, "disk failure"):
                orchflows.setup(self.home, self.source)
        self.assertEqual(snapshot(core), before)
        self.assertEqual(list(core.parent.iterdir()), [core])

        def fail_example(source, destination):
            if Path(destination) == self.home / "libraries/social-search":
                raise OSError("disk failure")
            return replace(source, destination)

        with patch.object(os, "replace", side_effect=fail_example):
            with self.assertRaisesRegex(OSError, "disk failure"):
                orchflows.setup(self.home, self.source, "social-search")
        self.assertEqual(list((self.home / "libraries").iterdir()), [])
        self.assertEqual(orchflows.doctor(self.home)["status"], "ready")

    def test_existing_setup_lock_prevents_upgrade(self) -> None:
        self.install()
        write(self.home / ".local/packages/.setup.lock", "")
        write(self.source / "guidance/code.md", "Upstream change.\n")
        before = snapshot(self.home)
        with self.assertRaisesRegex(ValueError, "Core setup lock exists"):
            orchflows.setup(self.home, self.source)
        self.assertEqual(snapshot(self.home), before)

    def test_installed_cli_repeats_setup_without_source_or_cwd_dependency(self) -> None:
        first = self.install()
        core = Path(first["core"]["package_root"])
        self.source.rename(self.root / "source-no-longer-at-original-path")
        environment = dict(os.environ, ORCHFLOWS_HOME=str(self.home))
        repeat = self.cli(core / "scripts/orchflows.py", "setup", python=first["runtime_python"], env=environment)
        self.assertEqual(repeat.returncode, 0, repeat.stderr + repeat.stdout)
        self.assertEqual(json.loads(repeat.stdout)["core"]["status"], "reused")
        resolved = self.cli(core / "scripts/orchflows.py", "resolve", "orchflows-light", "--resource", "guidance/code.md", python=first["runtime_python"], env=environment)
        self.assertEqual(resolved.returncode, 0, resolved.stderr)
        self.assertEqual(json.loads(resolved.stdout)["resource_path"], str(core / "guidance/code.md"))
        explicit = self.cli(core / "scripts/orchflows.py", "doctor", "--home", str(self.home), python=first["runtime_python"], env=dict(environment, ORCHFLOWS_HOME=str(self.root / "wrong")))
        self.assertEqual(explicit.returncode, 0, explicit.stderr + explicit.stdout)

    def test_clone_restore_uses_supplied_bundle_and_preserves_portable_files(self) -> None:
        self.install(example=True)
        clone = self.root / "clone"
        shutil.copytree(self.home, clone, ignore=shutil.ignore_patterns(".local", ".git"))
        before = snapshot(clone)
        bundle = self.root / "supplied-core-bundle"
        shutil.copytree(self.home / ".local/packages/orchflows-light", bundle)
        self.source.rename(self.root / "source-unavailable")
        result = orchflows.setup(clone, bundle)
        self.assertEqual(result["status"], "ready", result)
        self.assertEqual({name: (clone / name).read_bytes() for name in before}, before)
        resolved = orchflows.resolve(clone, "social-search", skill="sample")
        self.assertEqual(resolved["skill_path"], str(clone / "libraries/social-search/skills/sample/SKILL.md"))
        self.assertEqual(result["runtime_python"], resolved["runtime_python"])
        self.assertEqual(orchflows.doctor(clone)["status"], "ready")

    def test_clone_restore_can_install_a_newer_supplied_core(self) -> None:
        self.install(example=True)
        clone = self.root / "clone"
        shutil.copytree(self.home, clone, ignore=shutil.ignore_patterns(".local", ".git"))
        write(self.source / "plugin.json", json.dumps({"name": "orchflows-light", "version": "9.0.0"}))
        result = orchflows.setup(clone, self.source)
        self.assertEqual(result["status"], "ready", result)
        self.assertEqual(result["core"]["status"], "installed")
        self.assertEqual(tomllib.loads((clone / "config.toml").read_text())["core"]["version"], "9.0.0")
        self.assertEqual(snapshot(clone / "libraries"), snapshot(self.home / "libraries"))

    def test_missing_example_in_installed_core_is_an_explicit_gap(self) -> None:
        result = self.install()
        repeat = orchflows.setup(self.home, Path(result["core"]["package_root"]), "social-search")
        self.assertEqual(repeat["status"], "partial")
        self.assertEqual(repeat["example"]["status"], "unavailable")
        self.assertFalse((self.home / "libraries/social-search").exists())
        self.assertIn("absent from this core source", " ".join(repeat["issues"]))

    def test_cli_installs_any_named_example_and_catalogs_all_valid_libraries(self) -> None:
        example = self.source / "example-workflows/research-acquire"
        package(example, "research-acquire")
        package(self.home / "libraries/my-folder", "custom-research")
        installed = self.cli(SCRIPT, "setup", "--home", str(self.home), "--source", str(self.source), "--example", "research-acquire")
        self.assertEqual(installed.returncode, 0, installed.stdout + installed.stderr)
        self.assertEqual(json.loads(installed.stdout)["example"]["status"], "installed")
        self.assertEqual(snapshot(example), snapshot(self.home / "libraries/research-acquire"))
        expected = {"orchflows-light": "./.local/packages/orchflows-light", "custom-research": "./libraries/my-folder",
                    "research-acquire": "./libraries/research-acquire"}
        for relative in (".agents/plugins/marketplace.json", ".claude-plugin/marketplace.json"):
            text = (self.home / relative).read_text(encoding="utf-8")
            catalog = json.loads(text)
            self.assertEqual(catalog["name"], "orchflows-home")
            self.assertEqual({entry["name"]: entry["source"]["path"] if isinstance(entry["source"], dict) else entry["source"]
                              for entry in catalog["plugins"]}, expected)
            self.assertNotIn(str(self.home), text)
        self.assertEqual(orchflows.doctor(self.home)["status"], "ready")

    def test_doctor_reports_stale_catalogs_and_setup_regenerates_them(self) -> None:
        self.install(example=True)
        package(self.source / "example-workflows/research-acquire", "research-acquire")
        for relative in (".agents/plugins/marketplace.json", ".claude-plugin/marketplace.json"):
            write(self.home / relative, '{"name":"orchflows-home","plugins":[{"name":"external","source":"./elsewhere"}]}\n')
        report = orchflows.doctor(self.home)
        self.assertEqual(report["status"], "incomplete")
        self.assertIn("rerun setup", " ".join(report["issues"]))
        result = orchflows.setup(self.home, self.source, "research-acquire")
        self.assertEqual(result["status"], "ready", result)
        for relative in (".agents/plugins/marketplace.json", ".claude-plugin/marketplace.json"):
            names = [entry["name"] for entry in json.loads((self.home / relative).read_text())["plugins"]]
            self.assertEqual(names, ["orchflows-light", "research-acquire", "social-search"])
        self.assertEqual(orchflows.doctor(self.home)["status"], "ready")

    def test_resolution_does_not_require_runtime_or_unrelated_core_files(self) -> None:
        first = self.install(example=True)
        core = Path(first["core"]["package_root"])
        (self.home / ".local/runtime").rename(self.home / ".local/runtime-away")
        with patch.object(subprocess, "run", side_effect=AssertionError("Resolution launched a process")):
            resolved = orchflows.resolve(self.home, "orchflows-light", resource="guidance/code.md")
            self.assertEqual(Path(resolved["resource_path"]), core / "guidance/code.md")
            self.assertEqual(resolved["runtime_python"], first["runtime_python"])
            self.assertTrue(Path(orchflows.resolve(self.home, "social-search", skill="sample")["skill_path"]).is_file())
        self.assertEqual(orchflows.doctor(self.home)["status"], "incomplete")

    def test_example_names_reject_traversal_and_invalid_names_before_mutation(self) -> None:
        for name in ("../outside", "..\\outside", "/outside", "C:\\outside", "C:outside", "..", "", "sample.dot", "x" * 65):
            with self.subTest(name=name):
                result = self.cli(SCRIPT, "setup", "--home", str(self.home), "--source", str(self.source), "--example", name)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertIn("Invalid example name", json.loads(result.stderr)["error"])
                self.assertFalse(self.home.exists())

    def test_example_manifest_must_match_before_setup_mutates_home(self) -> None:
        for manifest in ('{"name":"different","version":"1"}', '{malformed'):
            with self.subTest(manifest=manifest):
                write(self.example / "plugin.json", manifest)
                with self.assertRaisesRegex(ValueError, "Example identity differs|Malformed package manifest"):
                    orchflows.setup(self.home, self.source, "social-search")
                self.assertFalse(self.home.exists())

    def test_catalogs_exclude_malformed_and_ambiguous_libraries_without_changing_them(self) -> None:
        package(self.home / "libraries/first", "duplicate")
        package(self.home / "libraries/second", "duplicate")
        package(self.home / "libraries/shadow-core", "orchflows-light")
        write(self.home / "libraries/broken/plugin.json", "{broken")
        package(self.home / "libraries/valid", "valid")
        before = snapshot(self.home / "libraries")
        report = orchflows.setup(self.home, self.source)
        self.assertEqual(report["status"], "partial")
        self.assertEqual(snapshot(self.home / "libraries"), before)
        for result in (report, orchflows.doctor(self.home)):
            issues = " ".join(result["issues"])
            self.assertIn("Ambiguous library name: duplicate", issues)
            self.assertIn("Ambiguous library name: orchflows-light", issues)
            self.assertIn("Malformed package manifest", issues)
        for relative in (".agents/plugins/marketplace.json", ".claude-plugin/marketplace.json"):
            catalog = json.loads((self.home / relative).read_text(encoding="utf-8"))
            self.assertEqual([item["name"] for item in catalog["plugins"]], ["orchflows-light", "valid"])

    def test_resolve_rejects_traversal_absolute_paths_and_ambiguous_names(self) -> None:
        self.install(example=True)
        for resource in ("../config.toml", "skills/../../config.toml", "..\\config.toml", "/etc/passwd", "C:\\Windows\\win.ini", "C:win.ini", "//server/share", "guidance/file:stream", ""):
            with self.subTest(resource=resource), self.assertRaisesRegex(ValueError, "safe relative"):
                orchflows.resolve(self.home, "orchflows-light", resource=resource)
        with self.assertRaisesRegex(ValueError, "Invalid skill"):
            orchflows.resolve(self.home, "social-search", skill="../sample")
        for name in ("sample.dot", "x" * 65):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "Invalid library"):
                orchflows.resolve(self.home, name)
        package(self.home / "libraries/another-directory", "social-search")
        with self.assertRaisesRegex(ValueError, "Ambiguous library"):
            orchflows.resolve(self.home, "social-search")
        package(self.home / "libraries/shadow-core", "orchflows-light")
        with self.assertRaisesRegex(ValueError, "Ambiguous library"):
            orchflows.resolve(self.home, "orchflows-light")

    def test_links_are_never_copied_or_resolved_through(self) -> None:
        outside = self.root / "outside"
        outside.mkdir()
        linked = self.source / "skills/linked"
        try:
            linked.symlink_to(outside, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"Symlink creation unavailable: {exc}")
        with self.assertRaisesRegex(ValueError, "does not follow links"):
            orchflows.setup(self.home, self.source)
        self.assertFalse((self.home / ".local/packages/orchflows-light").exists())
        linked.unlink()
        self.install()
        escape = self.home / ".local/packages/orchflows-light/guidance/escape"
        escape.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "escapes"):
            orchflows.resolve(self.home, "orchflows-light", resource="guidance/escape")
        self.assertEqual(list(outside.iterdir()), [])

    def test_setup_never_writes_through_links_in_the_home(self) -> None:
        outside = self.root / "outside"
        outside.mkdir()
        self.home.mkdir()
        try:
            (self.home / "README.md").symlink_to(outside / "missing-readme.md")
            (self.home / "libraries").symlink_to(outside, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"Symlink creation unavailable: {exc}")
        with self.assertRaisesRegex(ValueError, "does not write through links"):
            orchflows.setup(self.home, self.source, "social-search")
        self.assertEqual(list(outside.iterdir()), [])
        (self.home / "libraries").unlink()
        result = orchflows.setup(self.home, self.source)
        self.assertEqual(result["files"]["README.md"], "preserved")
        self.assertTrue((self.home / "README.md").is_symlink())
        self.assertEqual(list(outside.iterdir()), [])

    def test_doctor_is_read_only_and_lists_invalid_libraries_and_runtime(self) -> None:
        self.install()
        write(self.home / "config.toml", "broken = [\n")
        write(self.home / "libraries/broken/plugin.json", "{broken")
        before = snapshot(self.home)
        report = orchflows.doctor(self.home)
        self.assertEqual(report["status"], "incomplete")
        self.assertIn("Malformed configuration", " ".join(report["issues"]))
        self.assertIn("Malformed package manifest", " ".join(report["issues"]))
        self.assertEqual(snapshot(self.home), before)
        missing = self.root / "does-not-exist"
        self.assertEqual(orchflows.doctor(missing)["status"], "incomplete")
        self.assertFalse(missing.exists())

    def test_home_git_ignores_runtime_and_artifacts_but_tracks_libraries(self) -> None:
        git = shutil.which("git")
        if not git:
            self.skipTest("Git unavailable")
        self.install(example=True)
        write(self.home / "artifacts/report.html", "Generated output")
        result = subprocess.run([git, "-C", str(self.home), "status", "--porcelain", "--untracked-files=all"], text=True, capture_output=True, check=True)
        status = result.stdout
        self.assertIn("config.toml", status)
        self.assertIn("libraries/social-search/README.md", status)
        self.assertNotIn(".local/", status)
        self.assertNotIn("artifacts/report.html", status)
        commits = subprocess.run([git, "-C", str(self.home), "rev-parse", "--verify", "HEAD"], text=True, capture_output=True, check=False)
        self.assertNotEqual(commits.returncode, 0)

    def test_setup_preserves_existing_logs_reports_and_git_attributes(self) -> None:
        write(self.home / "logs/2026-09/old-run/summary.md", "Saved report.\n")
        write(self.home / ".gitattributes", "*.md text eol=crlf\n")
        before = snapshot(self.home)
        self.install()
        self.assertEqual({name: (self.home / name).read_bytes() for name in before}, before)
        self.assertEqual(orchflows.doctor(self.home)["status"], "ready")


if __name__ == "__main__":
    unittest.main()
