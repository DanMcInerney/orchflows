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

from tests.test_installer_cases.support import seed_user_frontend, setUpModule, tearDownModule
from tests.test_installer_cases.planning.day_zero import TestDayZeroBootstrap


# Keep the historical module identity: unittest keys module fixtures and stable
# test identifiers from each class's ``__module__``, even when a facade imports
# the class. Explicit assignments preserve both seams without duplicating setup.
TestDayZeroBootstrap.__module__ = __name__


_day_zero_setup = TestDayZeroBootstrap.setUp


def _day_zero_setup_with_user_frontend(self):
    _day_zero_setup(self)
    seed_user_frontend(self.home)


TestDayZeroBootstrap.setUp = _day_zero_setup_with_user_frontend


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
        self.assertIn(
            (install.REPO_ROOT / "THIRD_PARTY_NOTICES.md", user_plan.lib_home / "THIRD_PARTY_NOTICES.md"),
            user_plan.lib_copies,
        )

    def test_project_frontend_refusal_prevents_a_success_receipt(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            plan = install.Plan(
                scope="project", project_root=root, scope_home=root / ".orchflows",
                lib_home=root / ".orchflows" / "lib", bin_dir=root / ".orchflows" / "bin",
                receipt_path=root / ".orchflows" / "receipt.json",
                frontend_home=root / "missing-ui", frontend_manifest_sha256="expected",
                frontend_action="refuse", manage_host_surfaces=False,
            )
            with self.assertRaisesRegex(RuntimeError, "healthy frontend assets"):
                install.apply_plan(plan)
            self.assertFalse(plan.receipt_path.exists())

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

    def test_failed_swap_and_failed_restore_keep_the_prior_backup(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "source"
            source.mkdir()
            (source / "index.html").write_text("new", encoding="utf-8")
            plan = self._frontend_plan(root, source)
            plan.frontend_home.mkdir(parents=True)
            (plan.frontend_home / "index.html").write_text("prior", encoding="utf-8")
            real_replace = Path.replace

            def fail_swaps(path, target):
                if path.name.startswith((".ui-stage-", ".ui-backup-")):
                    raise OSError("forced replacement failure")
                return real_replace(path, target)

            with patch.object(Path, "replace", fail_swaps):
                with self.assertRaisesRegex(OSError, "forced replacement failure"):
                    install.apply_plan(plan)
            backups = list(plan.frontend_home.parent.glob(".ui-backup-*"))
            self.assertEqual(1, len(backups))
            self.assertEqual("prior", (backups[0] / "index.html").read_text(encoding="utf-8"))

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

    def test_frontend_uninstall_dry_run_is_one_consistent_preview(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "source"
            source.mkdir()
            (source / "index.html").write_text("observe", encoding="utf-8")
            plan = self._frontend_plan(root, source)
            install.apply_plan(plan)
            with patch.object(install.Path, "home", return_value=root / "home"):
                report = install.run_uninstall("user", None, dry_run=True)
            self.assertTrue(plan.frontend_home.is_dir())
            self.assertFalse(any("review frontend distribution" in item["action"] for item in report["manual_actions"]))
            self.assertEqual("would remove empty frontend distribution", report["skill_actions"][-1]["action"])
