"""Compatibility seam for the complete installer regression collection."""

from __future__ import annotations

import hashlib
import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import install

from tests.test_installer_cases.support import setUpModule, tearDownModule
from tests.test_installer_cases.application.configuration import (
    TestClaudeConfigDir,
    TestCodexHome,
    TestCodexHooksPreflight,
)
from tests.test_installer_cases.application.partial_apply import TestPartialApplyAfterRmtree
from tests.test_installer_cases.managed_text.claude_import import TestClaudeAlwaysOnImport
from tests.test_installer_cases.managed_text.host_block import (
    TestHostBlockDemands,
    TestHostBlockRendering,
)
from tests.test_installer_cases.managed_text.markers import TestMarkerEngineMisuse
from tests.test_installer_cases.managed_text.roles import TestRoleAgentInstructions
from tests.test_installer_cases.planning.day_zero import TestDayZeroBootstrap
from tests.test_installer_cases.planning.host_detection import DryRunOracleTest, TestHostAutoDetection
from tests.test_installer_cases.planning.runtime import TestClaudeAdapterSet, TestRuntimeDirsSeedTheSink
from tests.test_installer_cases.planning.private_runtime import RuntimeVenvTests
from tests.test_installer_cases.planning.scoped_hosts import (
    RoleProfileRefusalTest,
    TestScopedHostConfiguration,
)
from tests.test_installer_cases.planning.script_inventory import TestScriptNames
from tests.test_installer_cases.planning.wrappers import (
    TestBootstrapWrappers,
    TestDeclaredPythonFloor,
    TestPluginSubsystemRemoved,
)
from tests.test_installer_cases.receipt.install_receipt import TestInstallReceipt
from tests.test_installer_cases.receipt.source_commit import TestSourceCommit, TestUnreadableReceipt
from tests.test_installer_cases.uninstall.conservative import TestConservativeUninstall


# Keep the historical module identity: unittest keys module fixtures and stable
# test identifiers from each class's ``__module__``, even when a facade imports
# the class. Explicit assignments preserve both seams without duplicating setup.
TestClaudeConfigDir.__module__ = __name__
TestCodexHome.__module__ = __name__
TestCodexHooksPreflight.__module__ = __name__
TestPartialApplyAfterRmtree.__module__ = __name__
TestClaudeAlwaysOnImport.__module__ = __name__
TestHostBlockDemands.__module__ = __name__
TestHostBlockRendering.__module__ = __name__
TestMarkerEngineMisuse.__module__ = __name__
TestRoleAgentInstructions.__module__ = __name__
TestDayZeroBootstrap.__module__ = __name__
DryRunOracleTest.__module__ = __name__
TestHostAutoDetection.__module__ = __name__
TestClaudeAdapterSet.__module__ = __name__
TestRuntimeDirsSeedTheSink.__module__ = __name__
RuntimeVenvTests.__module__ = __name__
RoleProfileRefusalTest.__module__ = __name__
TestScopedHostConfiguration.__module__ = __name__
TestScriptNames.__module__ = __name__
TestBootstrapWrappers.__module__ = __name__
TestDeclaredPythonFloor.__module__ = __name__
TestPluginSubsystemRemoved.__module__ = __name__
TestInstallReceipt.__module__ = __name__
TestSourceCommit.__module__ = __name__
TestUnreadableReceipt.__module__ = __name__
TestConservativeUninstall.__module__ = __name__


class TestFrontendDistribution(unittest.TestCase):
    def _frontend_plan(self, root: Path, source: Path) -> install.Plan:
        home = root / "home"
        scope_home = home / ".orchflows"
        frontend_home = scope_home / "ui"
        identity = install._frontend_manifest_identity(source)
        return install.Plan(
            scope="user",
            project_root=None,
            lib_home=scope_home / "lib",
            scope_home=scope_home,
            bin_dir=scope_home / "bin",
            receipt_path=scope_home / "receipt.json",
            frontend_home=frontend_home,
            frontend_assets=[
                (path, frontend_home / path.relative_to(source))
                for path in sorted(source.rglob("*"))
                if path.is_file()
            ],
            frontend_manifest_sha256=identity,
            frontend_action="repair" if frontend_home.exists() else "create",
            manage_host_surfaces=False,
        )

    def test_user_plan_carries_the_exact_distribution_and_project_borrows_it(self):
        source_root = install.REPO_ROOT / "web" / "dist"
        expected_files = {
            path.relative_to(source_root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(source_root.rglob("*"))
            if path.is_file()
        }
        encoded = json.dumps(expected_files, sort_keys=True, separators=(",", ":"))
        expected_identity = hashlib.sha256(encoded.encode("utf-8")).hexdigest()

        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw) / "home"
            project = Path(raw) / "project"
            home.mkdir()
            project.mkdir()
            with patch.object(install.Path, "home", return_value=home), patch.object(
                install.shutil, "which", return_value="mock-host"
            ):
                user_plan = install.build_plan("user", None)
                project_plan = install.build_plan("project", project)

        planned_files = {
            destination.relative_to(user_plan.frontend_home).as_posix(): hashlib.sha256(
                source.read_bytes()
            ).hexdigest()
            for source, destination in user_plan.frontend_assets
        }
        self.assertEqual(planned_files, expected_files)
        self.assertEqual(user_plan.frontend_manifest_sha256, expected_identity)
        self.assertEqual(user_plan.frontend_action, "create")
        self.assertEqual(user_plan.frontend_home, home / ".orchflows" / "ui")
        self.assertEqual(project_plan.frontend_assets, [])
        self.assertEqual(project_plan.frontend_home, user_plan.frontend_home)
        self.assertEqual(project_plan.frontend_manifest_sha256, expected_identity)
        self.assertEqual(project_plan.frontend_action, "refuse")

    def test_apply_repairs_receipts_and_reports_without_a_javascript_toolchain(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "source"
            (source / "assets").mkdir(parents=True)
            (source / "index.html").write_text("<main>observe</main>", encoding="utf-8")
            (source / "assets" / "app-deadbeef.js").write_text("boot()", encoding="utf-8")
            plan = self._frontend_plan(root, source)
            plan.frontend_home.mkdir(parents=True)
            (plan.frontend_home / "index.html").write_text("corrupt", encoding="utf-8")
            (plan.frontend_home / "stale.js").write_text("stale", encoding="utf-8")

            with patch("subprocess.run", side_effect=AssertionError("Node/pnpm process invoked")):
                receipt = install.apply_plan(plan)

            self.assertEqual(
                install._frontend_manifest_identity(plan.frontend_home),
                plan.frontend_manifest_sha256,
            )
            self.assertFalse((plan.frontend_home / "stale.js").exists())
            self.assertEqual(receipt["frontend"]["manifest_sha256"], plan.frontend_manifest_sha256)
            self.assertEqual(
                {entry["kind"] for entry in receipt["files"]}, {"frontend-asset"}
            )

            output = io.StringIO()
            with redirect_stdout(output):
                install.print_plan(plan)
                install.print_summary(plan)
            report = output.getvalue()
            self.assertIn(str(plan.frontend_home), report)
            self.assertIn(plan.frontend_manifest_sha256, report)

            old_identity = install._frontend_manifest(plan.frontend_home)
            broken_source = root / "broken-source"
            shutil.copytree(source, broken_source)
            (broken_source / "assets" / "second-cafebabe.js").write_text(
                "second()", encoding="utf-8"
            )
            broken_plan = self._frontend_plan(root, broken_source)
            real_copy = shutil.copy2
            copy_count = 0

            def interrupted_copy(source_path, destination_path):
                nonlocal copy_count
                copy_count += 1
                if copy_count == 2:
                    raise OSError("interrupted staging")
                return real_copy(source_path, destination_path)

            with patch("installer.application.shutil.copy2", side_effect=interrupted_copy):
                with self.assertRaisesRegex(OSError, "interrupted staging"):
                    install.apply_plan(broken_plan)
            self.assertEqual(install._frontend_manifest(plan.frontend_home), old_identity)

    def test_uninstall_removes_an_unchanged_receipted_distribution(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "source"
            source.mkdir()
            (source / "index.html").write_text("<main>observe</main>", encoding="utf-8")
            plan = self._frontend_plan(root, source)
            install.apply_plan(plan)

            with patch.object(install.Path, "home", return_value=root / "home"):
                report = install.run_uninstall("user", None, dry_run=False)

            self.assertFalse(plan.frontend_home.exists())
            self.assertEqual(
                report["skill_actions"],
                [
                    {
                        "path": str(plan.frontend_home / "index.html"),
                        "action": "removed unchanged frontend asset",
                    },
                    {
                        "path": str(plan.frontend_home),
                        "action": "removed empty frontend distribution",
                    },
                ],
            )
            self.assertTrue(plan.receipt_path.is_file())
