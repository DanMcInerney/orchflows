"""Compatibility seam for the complete installer regression collection."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
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
