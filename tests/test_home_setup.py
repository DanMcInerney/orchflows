"""Observable setup/resolve behavior, always using disposable homes."""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import tomllib
import types
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/orchflows.py"
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
        self.host_environment = {"CODEX_HOME": str(self.root / "codex"),
                                 "CLAUDE_CONFIG_DIR": str(self.root / "claude")}
        self.environment_patch = patch.dict(os.environ, self.host_environment)
        self.environment_patch.start()
        self.addCleanup(self.environment_patch.stop)
        self.home = self.root / "home"
        self.source = self.root / "source"
        package(self.source, "orchflows-light", "7.8.9")
        write(self.source / ".codex-plugin/plugin.json", json.dumps({"name": "orchflows-light", "version": "7.8.9+cache"}))
        write(self.source / ".claude-plugin/plugin.json", json.dumps({"name": "orchflows-light", "version": "7.8.9"}))
        write(self.source / "standards/code.md", "Local coding standard.\n")
        write(self.source / "docs/native-hosts.md", "Fixture host docs.\n")
        write(self.source / "README.md", "Fixture core.\n")
        (self.source / "scripts").mkdir()
        shutil.copy2(SCRIPT, self.source / "scripts/orchflows.py")
        shutil.copy2(SCRIPT.with_name("host_config.py"), self.source / "scripts/host_config.py")
        shutil.copy2(SCRIPT.with_name("native_logs.py"), self.source / "scripts/native_logs.py")
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
        return subprocess.run(
            [python or sys.executable, "-B", str(script), *arguments], cwd=unrelated,
            env=env, text=True, capture_output=True, timeout=45, check=False,
        )

    def test_first_setup_has_portable_identity_complete_core_and_runtime(self) -> None:
        write(self.source / ".git/config", "never copy source git")
        write(self.source / "tests/large-output.json", "never copy root tests")
        write(self.source / "scripts/__pycache__/discard.pyc", "never copy cache")
        write(self.source / "scripts/test-output/generated.json", "never copy generated output")
        result = self.install(example=True)
        core = Path(result["core"]["package_root"])
        self.assertTrue((core / ".codex-plugin/plugin.json").is_file())
        self.assertTrue((core / ".claude-plugin/plugin.json").is_file())
        self.assertFalse((core / ".git").exists())
        self.assertFalse((core / "tests").exists())
        self.assertFalse((core / "example-workflows").exists())
        self.assertFalse((core / "scripts/__pycache__").exists())
        self.assertFalse((core / "scripts/test-output").exists())
        self.assertEqual(snapshot(self.example), snapshot(self.home / "libraries/social-search"))
        config_text = (self.home / "config.toml").read_text(encoding="utf-8")
        config = tomllib.loads(config_text)
        self.assertEqual(config["core"]["version"], "7.8.9")
        self.assertEqual(len(config["core"]["content_sha256"]), 64)
        self.assertNotIn(str(self.source), config_text)
        local = tomllib.loads((self.home / ".local/config.toml").read_text(encoding="utf-8"))
        self.assertEqual(local["source"], str(self.source))
        self.assertEqual(local["runtime_python"], result["runtime_python"])
        self.assertEqual(orchflows.doctor(self.home)["status"], "ready")
        # Setup does not install pip or third-party dependencies.
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

    def test_runpy_load_finds_its_own_host_helper(self) -> None:
        import runpy

        loaded = runpy.run_path(str(SCRIPT))
        result = loaded["setup"](self.home, self.source)
        self.assertEqual(result["host_config_status"], "configured")

    def test_repeat_preserves_custom_config_library_and_venv(self) -> None:
        first = self.install(example=True)
        custom = self.home / "libraries/social-search/README.md"
        write(custom, "User's altered example.\n")
        with (self.home / "config.toml").open("a", encoding="utf-8") as stream:
            stream.write('\n[projects.my_project]\nnote = "portable user setting"\n')
        write(self.home / "README.md", "My user-owned README.\n")
        runtime = self.home / ".local/runtime"
        marker = runtime / "user-marker.txt"
        write(marker, "Keep installed environment content.\n")
        before = {path: path.read_bytes() for path in (custom, self.home / "config.toml", self.home / "README.md", marker, runtime / "pyvenv.cfg")}
        interpreter_mtime = Path(first["runtime_python"]).stat().st_mtime_ns
        second = self.install(example=True)
        self.assertEqual(second["core"]["status"], "reused")
        self.assertEqual(second["runtime"]["status"], "preserved")
        self.assertEqual(second["example"]["status"], "preserved")
        self.assertEqual({path: path.read_bytes() for path in before}, before)
        self.assertEqual(Path(first["runtime_python"]).stat().st_mtime_ns, interpreter_mtime)

    def test_malformed_configs_fail_before_mutation_and_stay_unchanged(self) -> None:
        for relative in ("config.toml", ".local/config.toml"):
            with self.subTest(relative=relative):
                home = self.root / relative.replace("/", "-")
                write(home / relative, "broken = [not valid TOML\n")
                before = snapshot(home)
                with self.assertRaisesRegex(ValueError, "Malformed configuration preserved"):
                    orchflows.setup(home, self.source)
                self.assertEqual(snapshot(home), before)

    def test_incomplete_existing_runtime_is_not_repaired(self) -> None:
        marker = self.home / ".local/runtime/my-environment.txt"
        write(marker, "not a venv; leave this directory alone\n")
        before = snapshot(marker.parent)
        result = orchflows.setup(self.home, self.source)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["runtime"]["status"], "unavailable")
        self.assertEqual(snapshot(marker.parent), before)
        self.assertIn("existing contents preserved", " ".join(result["issues"]))

    def test_changed_source_preserves_existing_managed_snapshot(self) -> None:
        first = self.install()
        core = Path(first["core"]["package_root"])
        before = snapshot(core)
        write(self.source / "standards/code.md", "A changed standard.\n")
        result = orchflows.setup(self.home, self.source)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["core"]["status"], "preserved")
        self.assertIn("not an upgrade command", " ".join(result["issues"]))
        self.assertEqual(snapshot(core), before)

    def test_installed_cli_repeats_setup_without_source_or_cwd_dependency(self) -> None:
        first = self.install()
        core = Path(first["core"]["package_root"])
        self.source.rename(self.root / "source-no-longer-at-original-path")
        environment = dict(os.environ, ORCHFLOWS_HOME=str(self.home))
        repeat = self.cli(core / "scripts/orchflows.py", "setup", python=first["runtime_python"], env=environment)
        self.assertEqual(repeat.returncode, 0, repeat.stderr + repeat.stdout)
        self.assertEqual(json.loads(repeat.stdout)["core"]["status"], "reused")
        resolved = self.cli(core / "scripts/orchflows.py", "resolve", "orchflows-light", "--resource", "standards/code.md", python=first["runtime_python"], env=environment)
        self.assertEqual(resolved.returncode, 0, resolved.stderr)
        self.assertEqual(json.loads(resolved.stdout)["resource_path"], str(core / "standards/code.md"))
        explicit = self.cli(core / "scripts/orchflows.py", "--home", str(self.home), "doctor", python=first["runtime_python"], env=dict(environment, ORCHFLOWS_HOME=str(self.root / "wrong")))
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

    def test_missing_example_in_installed_core_is_an_explicit_gap(self) -> None:
        result = self.install()
        repeat = orchflows.setup(self.home, Path(result["core"]["package_root"]), "social-search")
        self.assertEqual(repeat["status"], "partial")
        self.assertEqual(repeat["example"]["status"], "unavailable")
        self.assertFalse((self.home / "libraries/social-search").exists())
        self.assertIn("absent from this core source", " ".join(repeat["issues"]))
        self.assertNotIn("needs registration for social-search", " ".join(repeat["issues"]))

    def test_cli_installs_any_named_example_and_catalogs_all_valid_libraries(self) -> None:
        example = self.source / "example-workflows/research-acquire"
        package(example, "research-acquire")
        package(self.home / "libraries/my-folder", "custom-research")
        installed = self.cli(
            SCRIPT, "setup", "--home", str(self.home), "--source", str(self.source),
            "--example", "research-acquire",
        )
        self.assertEqual(installed.returncode, 0, installed.stdout + installed.stderr)
        self.assertEqual(json.loads(installed.stdout)["example"]["status"], "installed")
        self.assertEqual(snapshot(example), snapshot(self.home / "libraries/research-acquire"))
        expected = {
            "orchflows-light": "./.local/packages/orchflows-light",
            "custom-research": "./libraries/my-folder",
            "research-acquire": "./libraries/research-acquire",
        }
        for relative in (".agents/plugins/marketplace.json", ".claude-plugin/marketplace.json"):
            catalog = json.loads((self.home / relative).read_text(encoding="utf-8"))
            actual = {entry["name"]: entry["source"]["path"] if isinstance(entry["source"], dict)
                      else entry["source"] for entry in catalog["plugins"]}
            self.assertEqual(actual, expected)
        self.assertEqual(orchflows.doctor(self.home)["status"], "ready")

    def test_second_example_preserves_catalogs_and_reports_missing_registration(self) -> None:
        self.install(example=True)
        package(self.source / "example-workflows/research-acquire", "research-acquire")
        paths = [self.home / relative for relative in
                 (".agents/plugins/marketplace.json", ".claude-plugin/marketplace.json")]
        before = {path: path.read_bytes() for path in paths}
        report = orchflows.setup(self.home, self.source, "research-acquire")
        self.assertEqual(report["status"], "partial")
        self.assertEqual(report["example"]["status"], "installed")
        self.assertEqual({path: path.read_bytes() for path in paths}, before)
        for result in (report, orchflows.doctor(self.home)):
            for path in paths:
                self.assertIn(
                    f"Catalog {path.relative_to(self.home).as_posix()} needs registration for research-acquire at ./libraries/research-acquire",
                    " ".join(result["issues"]),
                )
        resolved = orchflows.resolve(self.home, "research-acquire", skill="sample")
        self.assertEqual(Path(resolved["skill_path"]), self.home / "libraries/research-acquire/skills/sample/SKILL.md")

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
        for resource in ("../config.toml", "skills/../../config.toml", "..\\config.toml", "/etc/passwd", "C:\\Windows\\win.ini", "C:win.ini", "//server/share", "standards/file:stream", ""):
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

    def test_nested_reparse_point_is_not_copied_without_isjunction_api(self) -> None:
        nested = self.source / "skills/nested-link"
        write(nested / "do-not-copy.md", "Keep this content outside the copied package.\n")
        before = snapshot(self.source)
        destination = self.root / "copied-core"
        original_lstat = Path.lstat

        def lstat(path, *args, **kwargs):
            observed = original_lstat(path, *args, **kwargs)
            if path == nested:
                return types.SimpleNamespace(
                    st_mode=observed.st_mode,
                    st_file_attributes=stat.FILE_ATTRIBUTE_REPARSE_POINT,
                )
            return observed

        # Python 3.11 has no os.path.isjunction. Simulate reparse attributes on
        # an ordinary directory so the regression needs no real junction.
        legacy_os = types.SimpleNamespace(path=types.SimpleNamespace())
        with patch.object(orchflows, "os", legacy_os), patch.object(Path, "lstat", lstat):
            with self.assertRaisesRegex(ValueError, "does not follow links"):
                orchflows._copy_package(self.source, destination, core=True)
        self.assertFalse(destination.exists())
        self.assertEqual(snapshot(self.source), before)

    def test_symlink_escapes_are_rejected_without_touching_outside_content(self) -> None:
        outside = self.root / "outside"
        outside.mkdir()
        link = self.home / ".local"
        self.home.mkdir()
        try:
            link.symlink_to(outside, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"Symlink creation unavailable: {exc}")
        with self.assertRaisesRegex(ValueError, "escapes"):
            orchflows.setup(self.home, self.source)
        self.assertEqual(list(outside.iterdir()), [])
        link.unlink()
        self.install()
        escape = self.home / ".local/packages/orchflows-light/standards/escape"
        escape.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "links|escapes"):
            orchflows.resolve(self.home, "orchflows-light", resource="standards/escape")

    def test_doctor_is_read_only_and_lists_invalid_libraries_and_runtime(self) -> None:
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

    def test_native_catalogs_are_portable_and_existing_catalogs_are_preserved(self) -> None:
        self.install(example=True)
        for relative in (".agents/plugins/marketplace.json", ".claude-plugin/marketplace.json"):
            text = (self.home / relative).read_text(encoding="utf-8")
            catalog = json.loads(text)
            self.assertEqual(catalog["name"], "orchflows-home")
            self.assertEqual({item["name"] for item in catalog["plugins"]}, {"orchflows-light", "social-search"})
            self.assertNotIn(str(self.home), text)
            self.assertNotIn(str(self.source), text)
        codex = self.home / ".agents/plugins/marketplace.json"
        write(codex, '{"name":"my-own-catalog","plugins":[]}\n')
        before = codex.read_bytes()
        report = orchflows.setup(self.home, self.source, "social-search")
        self.assertEqual(report["status"], "partial")
        self.assertEqual(codex.read_bytes(), before)
        self.assertIn("needs registration for social-search", " ".join(report["issues"]))

    def test_home_git_ignores_runtime_and_bulk_but_tracks_sources_and_summaries(self) -> None:
        git = shutil.which("git")
        if not git:
            self.skipTest("Git unavailable")
        self.install(example=True)
        run = self.home / "logs/2026-09/20260911T000000Z-test"
        write(run / "run.json", "{}\n")
        write(run / "summary.md", "Actual compact summary.\n")
        write(run / "raw/source.json", "raw body")
        write(run / "artifacts/large.html", "large artifact")
        write(run / "other-output.bin", "arbitrary output")
        result = subprocess.run([git, "-C", str(self.home), "status", "--porcelain", "--untracked-files=all"], text=True, capture_output=True, check=True)
        status = result.stdout
        self.assertIn("config.toml", status)
        self.assertIn(".gitattributes", status)
        self.assertIn("libraries/social-search/README.md", status)
        self.assertIn("run.json", status)
        self.assertIn("summary.md", status)
        for excluded in (".local/", "raw/source.json", "artifacts/large.html", "other-output.bin"):
            self.assertNotIn(excluded, status)
        commits = subprocess.run([git, "-C", str(self.home), "rev-parse", "--verify", "HEAD"], text=True, capture_output=True, check=False)
        self.assertNotEqual(commits.returncode, 0)

    def test_existing_gitignore_is_preserved_and_missing_rules_are_reported(self) -> None:
        if not shutil.which("git"):
            self.skipTest("Git unavailable")
        write(self.home / ".gitignore", "my-user-pattern\n")
        before = (self.home / ".gitignore").read_bytes()
        report = orchflows.setup(self.home, self.source)
        self.assertEqual(report["status"], "partial")
        self.assertEqual((self.home / ".gitignore").read_bytes(), before)
        self.assertIn("Git does not ignore .local/config.toml", " ".join(report["issues"]))
        self.assertEqual(orchflows.doctor(self.home)["status"], "incomplete")

    def test_git_clones_preserve_run_bytes_and_hashes_with_both_autocrlf_settings(self) -> None:
        git = shutil.which("git")
        if not git:
            self.skipTest("Git unavailable")
        logger_spec = importlib.util.spec_from_file_location("run_log", SCRIPT.with_name("run_log.py"))
        logger = importlib.util.module_from_spec(logger_spec)
        logger_spec.loader.exec_module(logger)

        def run_git(directory, *arguments):
            return subprocess.run(
                [git, "-C", str(directory), *arguments], capture_output=True,
                text=True, check=True, timeout=30,
            )

        # Keep developer/global Git settings out of these disposable repositories.
        with patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}):
            self.install()
            run_git(self.home, "config", "core.autocrlf", "true")
            expected = {}
            for ending in (b"\n", b"\r\n"):
                summary = self.root / "actual-summary.md"
                summary.write_bytes(ending.join((b"Observed outcome.", b"One limitation remains.", b"")))
                started = logger.start_run(self.home, "personal:check")
                finished = logger.finish_run(self.home, Path(started["run_dir"]), "complete", summary)
                for field in ("run_json", "summary_file"):
                    path = Path(finished[field])
                    expected[path.relative_to(self.home)] = path.read_bytes()
            run_git(self.home, "add", ".")
            run_git(self.home, "-c", "user.name=Orchflows test", "-c", "user.email=test@example.invalid",
                    "-c", "commit.gpgsign=false", "commit", "--quiet", "-m", "Portable run fixtures")
            for autocrlf in ("true", "false"):
                with self.subTest(core_autocrlf=autocrlf):
                    clone = self.root / f"clone-{autocrlf}"
                    run_git(self.root, "clone", "--quiet", "--no-hardlinks", "-c", f"core.autocrlf={autocrlf}",
                            str(self.home), str(clone))
                    self.assertEqual(run_git(clone, "config", "--get", "core.autocrlf").stdout.strip(), autocrlf)
                    self.assertTrue((clone / ".gitattributes").is_file())
                    for relative, contents in expected.items():
                        self.assertEqual((clone / relative).read_bytes(), contents, str(relative))
                        if relative.name == "run.json":
                            metadata = json.loads((clone / relative).read_bytes())
                            copied_summary = clone / relative.parent / metadata["summary"]["path"]
                            self.assertEqual(metadata["summary"]["sha256"],
                                             hashlib.sha256(copied_summary.read_bytes()).hexdigest())
                            repeated = logger.finish_run(clone, copied_summary.parent, "complete", copied_summary)
                            self.assertEqual(repeated["finished_at"], metadata["finished_at"])

    def test_existing_gitattributes_are_preserved_and_missing_rules_are_reported(self) -> None:
        if not shutil.which("git"):
            self.skipTest("Git unavailable")
        self.home.mkdir()
        attributes = self.home / ".gitattributes"
        custom = b"# My user rules\r\n*.md text eol=crlf\r\n"
        attributes.write_bytes(custom)
        report = orchflows.setup(self.home, self.source)
        self.assertEqual(report["status"], "partial")
        self.assertEqual(report["files"][".gitattributes"], "preserved")
        self.assertEqual(attributes.read_bytes(), custom)
        for filename in ("run.json", "summary.md"):
            self.assertIn(f"add /logs/**/{filename} -text", " ".join(report["issues"]))
        report = orchflows.doctor(self.home)
        self.assertEqual(report["status"], "incomplete")
        self.assertIn("Git does not preserve exact bytes", " ".join(report["issues"]))
        self.assertEqual(attributes.read_bytes(), custom)
        # An equivalent user policy is accepted without replacing its bytes.
        custom += b"/logs/** -text\r\n"
        attributes.write_bytes(custom)
        self.assertEqual(self.install()["files"][".gitattributes"], "preserved")
        self.assertEqual(orchflows.doctor(self.home)["status"], "ready")
        self.assertEqual(attributes.read_bytes(), custom)

    def test_setup_seeds_missing_attributes_in_an_existing_home(self) -> None:
        self.install()
        attributes = self.home / ".gitattributes"
        attributes.unlink()
        report = orchflows.doctor(self.home)
        self.assertIn("Missing home file: .gitattributes", " ".join(report["issues"]))
        self.assertFalse(attributes.exists())
        self.assertEqual(self.install()["files"][".gitattributes"], "created")
        self.assertEqual(attributes.read_bytes(), orchflows.HOME_GITATTRIBUTES.encode("utf-8"))

    def test_escaping_gitattributes_are_rejected_before_setup_mutation(self) -> None:
        attributes = self.home / ".gitattributes"
        write(attributes, "User attributes.\n")
        outside = self.root / "outside-attributes"
        write(outside, "Outside content.\n")
        before = snapshot(self.home)
        original_resolve = Path.resolve

        def resolve(path, *args, **kwargs):
            return outside if path == attributes else original_resolve(path, *args, **kwargs)

        # Simulate a redirect without creating a live symlink or junction.
        with patch.object(Path, "resolve", resolve):
            with self.assertRaisesRegex(ValueError, "escapes"):
                orchflows.setup(self.home, self.source)
            self.assertIn("escapes", " ".join(orchflows.doctor(self.home)["issues"]))
        self.assertEqual(snapshot(self.home), before)
        self.assertEqual(outside.read_text(), "Outside content.\n")

    def test_run_dispatch_is_lazy_and_passes_the_shared_interface(self) -> None:
        calls = []
        fake = types.ModuleType("run_log")
        fake.start_run = lambda *args: calls.append(("start", args)) or {"status": "running"}
        fake.finish_run = lambda *args: calls.append(("finish", args)) or {"status": "complete"}
        summary = self.root / "summary.md"
        run_dir = self.home / "logs/run"
        with patch.dict(sys.modules, {"run_log": fake}), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(orchflows.main(["run", "start", "--home", str(self.home), "--workflow", "social-search:sample", "--project", "example"]), 0)
            self.assertEqual(orchflows.main(["run", "finish", str(run_dir), "--home", str(self.home), "--status", "complete", "--summary", str(summary)]), 0)
        self.assertEqual(calls, [("start", (self.home, "social-search:sample", "example")), ("finish", (self.home, run_dir, "complete", summary))])
        # setup/doctor/resolve load normally with no run_log module in the bundle.
        self.assertFalse((self.source / "scripts/run_log.py").exists())


if __name__ == "__main__":
    unittest.main()
