"""Disposable publication and dependency failure controls; no network installs."""

import json
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from installer import application, publication
from installer.models import Plan, _is_build_artifact
from scripts import orchflows_node, workspace_prepare, rings_trust


class PublicationTests(unittest.TestCase):
    def fixture(self, root):
        home = root / "home"
        source = root / "source.py"
        source.write_text("VALUE = 1\n")
        return Plan(lib_home=home / "lib", scope_home=home, bin_dir=home / "bin",
                    receipt_path=home / "receipt.json",
                    lib_copies=[(source, home / "lib" / "module.py")],
                    scripts=[(source, home / "bin" / "module.py")]), source


    def test_copy_and_probe_fail_before_live_payload_changes(self):
        with tempfile.TemporaryDirectory() as raw:
            plan, source = self.fixture(Path(raw))
            application.apply_plan(plan, "old")
            before = plan.receipt_path.read_bytes()
            with patch.object(publication.shutil, "copy2", side_effect=OSError("copy injected")):
                with self.assertRaises(OSError):
                    application.apply_plan(plan, "new")
            source.write_text("not valid python !")
            with self.assertRaises(SyntaxError):
                application.apply_plan(plan, "new")
            self.assertEqual(before, plan.receipt_path.read_bytes())
            self.assertEqual("VALUE = 1\n", (plan.bin_dir / "module.py").read_text())

    def test_second_payload_rename_failure_rolls_back_and_retry_works(self):
        with tempfile.TemporaryDirectory() as raw:
            plan, source = self.fixture(Path(raw))
            application.apply_plan(plan, "old")
            source.write_text("VALUE = 2\n")
            original = Path.replace
            def fail(path, target):
                if path.name == "bin" and path.parent.name.startswith(".install-transaction-"):
                    raise PermissionError("open handle")
                return original(path, target)
            with patch.object(Path, "replace", fail):
                with self.assertRaises(PermissionError):
                    application.apply_plan(plan, "new")
            self.assertEqual("VALUE = 1\n", (plan.lib_home / "module.py").read_text())
            self.assertEqual("VALUE = 1\n", (plan.bin_dir / "module.py").read_text())
            application.apply_plan(plan, "new")
            self.assertEqual("VALUE = 2\n", (plan.bin_dir / "module.py").read_text())

    def test_failed_rollback_retains_intact_backup_and_recovery_map(self):
        with tempfile.TemporaryDirectory() as raw:
            plan, source = self.fixture(Path(raw))
            application.apply_plan(plan, "old")
            source.write_text("VALUE = 2\n")
            original = Path.replace
            def fail(path, target):
                if path.name == "bin" and path.parent.name.startswith(".install-transaction-"):
                    raise PermissionError("publish refused")
                if path.name.endswith("-old"):
                    raise PermissionError("restore refused")
                return original(path, target)
            with patch.object(Path, "replace", fail):
                with self.assertRaisesRegex(RuntimeError, "recovery map retained"):
                    application.apply_plan(plan, "new")
            roots = list(plan.scope_home.glob(".install-transaction-*"))
            self.assertEqual(1, len(roots))
            self.assertTrue((roots[0] / "recovery.json").is_file())
            self.assertEqual("VALUE = 1\n", (roots[0] / "lib-old" / "module.py").read_text())
            self.assertEqual("VALUE = 1\n", (roots[0] / "bin-old" / "module.py").read_text())
            with self.assertRaisesRegex(RuntimeError, "unfinished installation recovery"):
                application.apply_plan(plan, "retry-before-recovery")
            # Replay the documented offline recovery in this disposable home.
            journal = json.loads((roots[0] / "recovery.json").read_text())
            for entry in journal["payloads"]:
                Path(entry["backup"]).replace(Path(entry["live"]))
            for name, backup in journal["surfaces"].items():
                if backup:
                    shutil.copy2(backup, name)
            roots[0].replace(Path(raw) / "recovered-transaction")
            application.apply_plan(plan, "retry-after-recovery")
            self.assertEqual("VALUE = 2\n", (plan.lib_home / "module.py").read_text())

    def test_receipt_failure_restores_adapter_and_payload(self):
        with tempfile.TemporaryDirectory() as raw:
            plan, source = self.fixture(Path(raw))
            adapter = Path(raw) / "adapter.md"
            plan.codex_skills = [(adapter, "old")]
            application.apply_plan(plan, "old")
            source.write_text("VALUE = 2\n")
            plan.codex_skills = [(adapter, "new")]
            with patch.object(application, "_write_json", side_effect=OSError("receipt failed")):
                with self.assertRaises(OSError):
                    application.apply_plan(plan, "new")
            self.assertEqual("old", adapter.read_text())
            self.assertEqual("VALUE = 1\n", (plan.lib_home / "module.py").read_text())


    def test_clean_flat_and_reader_import_and_architecture_link(self):
        with tempfile.TemporaryDirectory() as raw:
            plan, _ = self.fixture(Path(raw))
            repo = Path(__file__).resolve().parents[1]
            plan.scripts = [(repo / "scripts" / name, plan.bin_dir / name)
                            for name in ("state_root.py", "_bootstrap.py")]
            plan.lib_copies = [(repo / "scripts" / name, plan.lib_home / "scripts" / name)
                               for name in ("state_root.py", "_bootstrap.py")]
            plan.lib_copies += [(repo / name, plan.lib_home / name)
                                for name in ("ARCHITECTURE.md", "docs/custom-workflow-authoring.md")]
            application.apply_plan(plan, "fixture")
            code = ("import sys; sys.path[:0] = " + repr([str(plan.bin_dir), str(plan.lib_home)])
                    + "; import state_root, scripts.state_root; print(state_root.__file__); print(scripts.state_root.__file__)")
            result = subprocess.run([sys.executable, "-I", "-c", code], cwd=raw,
                                    capture_output=True, text=True, timeout=20)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn(str(plan.bin_dir), result.stdout)
            self.assertIn(str(plan.lib_home), result.stdout)
            guide = plan.lib_home / "docs" / "custom-workflow-authoring.md"
            link = re.search(r"\[ARCHITECTURE.md\]\(([^)]+)\)", guide.read_text(encoding="utf-8"))
            self.assertIsNotNone(link)
            self.assertEqual((repo / "ARCHITECTURE.md").read_bytes(),
                             (guide.parent / link.group(1)).read_bytes())
            (plan.bin_dir / "_bootstrap.py").unlink()
            (plan.lib_home / "scripts" / "_bootstrap.py").unlink()
            failed = subprocess.run([sys.executable, "-I", "-c", code], cwd=raw,
                                    capture_output=True, text=True, timeout=20)
            self.assertNotEqual(0, failed.returncode)

    @unittest.skipUnless(shutil.which("node"), "Node required for executable consumer control")
    def test_declared_node_payload_is_prepared_without_incidental_dependencies(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            plan, _ = self.fixture(root)
            package = root / "demo"
            package.mkdir()
            for name, text in {"SKILL.md": "demo", "package.json": "{}", "package-lock.json": "{}",
                               "consumer.js": "console.log(require('fixture-dependency'))"}.items():
                (package / name).write_text(text)
            incidental = package / "node_modules" / "incidental.js"
            incidental.parent.mkdir()
            incidental.write_text("must not ship")
            plan.lib_copies = [(path, plan.lib_home / "workflows" / "demo" / path.relative_to(package))
                               for path in package.rglob("*") if path.is_file() and not _is_build_artifact(path)]
            original = orchflows_node.ensure
            def prepare(kind, name, directory):
                def install(path, command):
                    dep = path / "node_modules" / "fixture-dependency"
                    dep.mkdir(parents=True)
                    (dep / "index.js").write_text("module.exports = 'prepared'")
                return original(kind, name, directory, which=lambda n: n, installer=install)
            with patch.object(orchflows_node, "ensure", side_effect=prepare):
                application.apply_plan(plan, "fixture")
            consumer = plan.lib_home / "workflows" / "demo" / "consumer.js"
            self.assertFalse((consumer.parent / "node_modules" / "incidental.js").exists())
            result = subprocess.run([shutil.which("node"), str(consumer)], capture_output=True, text=True, timeout=20)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual("prepared", result.stdout.strip())
            (consumer.parent / "node_modules" / "fixture-dependency" / "index.js").unlink()
            failed = subprocess.run([shutil.which("node"), str(consumer)], capture_output=True, text=True, timeout=20)
            self.assertNotEqual(0, failed.returncode)


class DependencyTests(unittest.TestCase):
    def package(self, root):
        root.mkdir(exist_ok=True)
        (root / "package.json").write_text("{}")
        (root / "package-lock.json").write_text("{}")
        return root

    def test_same_package_ensure_rechecks_under_lock_and_failure_can_retry(self):
        with tempfile.TemporaryDirectory() as raw:
            root = self.package(Path(raw))
            entered, release = threading.Event(), threading.Event()
            installs, results, failures = [], [], []
            def install(path, command):
                installs.append(str(path))
                entered.set()
                self.assertTrue(release.wait(5))
            def ensure():
                try:
                    results.append(orchflows_node.ensure("workflow", "demo", root,
                                   which=lambda name: name, installer=install)["action"])
                except Exception as error:
                    failures.append(error)
            one, two = threading.Thread(target=ensure), threading.Thread(target=ensure)
            one.start()
            self.assertTrue(entered.wait(5))
            two.start()
            release.set()
            one.join(10)
            two.join(10)
            self.assertFalse(one.is_alive() or two.is_alive())
            self.assertEqual([], failures)
            self.assertEqual(1, len(installs))
            self.assertEqual(["install", "reuse"], sorted(results))
            (root / "package-lock.json").write_text('{"changed": true}')
            def broken(path, command):
                (path / "diagnostic.log").write_text("useful failure")
                raise RuntimeError("manager failed")
            with self.assertRaisesRegex(RuntimeError, "manager failed"):
                orchflows_node.ensure("workflow", "demo", root, which=lambda n: n, installer=broken)
            self.assertIsNone(orchflows_node.read_stamp(root))
            self.assertTrue((root / "diagnostic.log").is_file())
            self.assertEqual("install", orchflows_node.ensure("workflow", "demo", root,
                             which=lambda n: n, installer=lambda *a: None)["action"])

    def test_root_npm_and_only_explicit_nested_preparation(self):
        with tempfile.TemporaryDirectory() as raw:
            root = self.package(Path(raw))
            self.package(root / "nested")
            self.package(root / "not-declared")
            calls = []
            def run(argv, cwd, env, timeout):
                calls.append((argv, cwd))
                return subprocess.CompletedProcess(argv, 0, b"", b"")
            with patch.object(workspace_prepare.shutil, "which", side_effect=lambda name, **k: name):
                result = workspace_prepare.prepare(root, env={"PATH": "", "PLAYWRIGHT_BROWSERS_PATH": str(root / "absent")}, run=run, packages=["nested"])
            self.assertEqual("installed", result["frontend"])
            self.assertEqual({"nested": "installed"}, result["packages"])
            self.assertEqual([root, root / "nested"], [cwd for _, cwd in calls])
            self.assertTrue(all(argv == ["npm", "ci"] for argv, _ in calls))

    def test_browser_readiness_rejects_empty_cache_directory_and_failed_binary(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "chromium-empty").mkdir()
            env = {"PLAYWRIGHT_BROWSERS_PATH": str(root)}
            self.assertEqual([], workspace_prepare._cached_browser(env))
            env["ORCHFLOWS_BROWSER_EXECUTABLE"] = str(root)
            run = lambda *args: subprocess.CompletedProcess([], 0)
            self.assertEqual("missing", workspace_prepare._browser(root, None, env, run, True))
            executable = root / "broken"
            executable.write_text("bad executable")
            env["ORCHFLOWS_BROWSER_EXECUTABLE"] = str(executable)
            self.assertEqual("missing", workspace_prepare._browser(root, None, env,
                             lambda *a: subprocess.CompletedProcess([], 1), True))
            self.assertEqual("present", workspace_prepare._browser(root, None, env, run, True))

    def test_bad_declarations_refuse_before_any_install(self):
        with tempfile.TemporaryDirectory() as raw:
            root = self.package(Path(raw))
            with self.assertRaises(ValueError):
                workspace_prepare.prepare(root, packages=["../escape"], run=lambda *a: self.fail("ran install"))
            (root / "package-lock.json").unlink()
            self.assertEqual("skipped: missing-lockfile", workspace_prepare._frontend(root, None, {}, None))
            (root / "yarn.lock").write_text("unsupported")
            self.assertEqual("skipped: unsupported-lockfile yarn.lock", workspace_prepare._frontend(root, None, {}, None))
            with self.assertRaisesRegex(ValueError, "tools.txt"):
                workspace_prepare.prepare(root, tools=["."], run=lambda *a: self.fail("ran install"))

    def test_execution_redirects_bytecode_without_weakening_executable_trust(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            package = root / "workflows" / "demo"
            package.mkdir(parents=True)
            (package / "helper.py").write_text("VALUE = 1\n")
            dependency = package / "node_modules" / "dependency.js"
            dependency.parent.mkdir()
            dependency.write_text("authored dependency")
            before = rings_trust.bundle_digest(root)
            repo = Path(__file__).resolve().parents[1]
            code = ("import sys; sys.path[:0] = " + repr([str(repo), str(package)])
                    + "; import scripts._bootstrap; import helper; print(helper.VALUE)")
            result = subprocess.run([sys.executable, "-I", "-c", code], cwd=raw,
                                    capture_output=True, text=True, timeout=20)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertFalse((package / "__pycache__").exists())
            self.assertEqual(before, rings_trust.bundle_digest(root))
            dependency.write_text("changed executable dependency")
            self.assertNotEqual(before, rings_trust.bundle_digest(root))
