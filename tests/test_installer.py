"""Compatibility seam for the complete installer regression collection."""

from __future__ import annotations

import hashlib
import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

import install

from tests.test_installer_cases.support import setUpModule, tearDownModule


class LegacyProjectCleanupTest(unittest.TestCase):
    """One scope is installed. ``--project PATH --uninstall`` is the whole
    remaining project surface: it cleans up what an older version wrote and
    plans nothing."""

    def test_planning_takes_no_scope_argument(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            home = root / "home"
            home.mkdir()
            with patch.object(install.Path, "home", return_value=home), patch.object(
                install.shutil, "which", return_value="mock-host"
            ):
                user_plan = install.build_plan()
                with self.assertRaises(TypeError):
                    install.build_plan("project", root)
            self.assertGreater(install.plan_entry_count(user_plan), 0)
            self.assertFalse(hasattr(install, "_build_project_plan"))

    def test_an_applied_plan_records_the_one_scope_in_its_receipt(self):
        with tempfile.TemporaryDirectory() as raw:
            scope_home = Path(raw) / "user" / ".orchflows"
            plan = install.Plan(
                lib_home=scope_home / "lib",
                scope_home=scope_home,
                bin_dir=scope_home / "bin",
                receipt_path=scope_home / "receipt.json",
                manage_host_surfaces=False,
            )
            with patch.object(install, "resolve_source_commit", return_value="test-commit"):
                receipt = install.apply_plan(plan, accepted_source=install.resolve_source_commit())
            self.assertEqual("user", receipt["scope"])
            self.assertIsNone(receipt["project_root"])
            self.assertTrue(plan.receipt_path.is_file())

    def test_cli_rejects_project_install_and_dry_run_but_keeps_legacy_uninstall(self):
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            adapter = project / ".claude" / "skills" / "legacy" / "SKILL.md"
            adapter.parent.mkdir(parents=True)
            adapter.write_text("legacy\n", encoding="utf-8")
            receipt = project / ".orchflows" / "receipt.json"
            receipt.parent.mkdir()
            receipt.write_text(
                json.dumps(
                    {
                        "scope": "project",
                        "files": [
                            {
                                "path": str(adapter),
                                "kind": "adapter",
                                "install_action": "created",
                                "sha256": hashlib.sha256(adapter.read_bytes()).hexdigest(),
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            error = io.StringIO()
            with patch.object(
                install,
                "build_plan",
                side_effect=AssertionError("planning reached"),
            ) as planner, patch.object(
                install,
                "apply_plan",
                side_effect=AssertionError("application reached"),
            ) as application, redirect_stderr(error):
                self.assertEqual(2, install.main(["--project", str(project)]))
                self.assertEqual(
                    2,
                    install.main(["--project", str(project), "--dry-run"]),
                )
            planner.assert_not_called()
            application.assert_not_called()
            self.assertIn("only available with --uninstall", error.getvalue())
            self.assertTrue(adapter.is_file())
            self.assertTrue(receipt.is_file())

            output = io.StringIO()
            with patch.object(
                install,
                "build_plan",
                side_effect=AssertionError("planning reached"),
            ) as planner, patch.object(
                install,
                "apply_plan",
                side_effect=AssertionError("application reached"),
            ) as application, redirect_stdout(output):
                self.assertEqual(
                    0,
                    install.main(["--project", str(project), "--uninstall"]),
                )
            planner.assert_not_called()
            application.assert_not_called()
            self.assertFalse(adapter.exists())
            self.assertTrue(receipt.is_file())
            self.assertIn("removed unchanged skill", output.getvalue())

    def test_legacy_project_uninstall_normalizes_in_boundary_receipt_paths(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "alias").mkdir()
            project = root / "alias" / ".."
            adapter = project / ".claude" / "skills" / "legacy" / "SKILL.md"
            adapter.parent.mkdir(parents=True)
            adapter.write_text("legacy\n", encoding="utf-8")
            receipt = project / ".orchflows" / "receipt.json"
            receipt.parent.mkdir()
            receipt.write_text(
                json.dumps(
                    {
                        "scope": "project",
                        "files": [
                            {
                                "path": str(adapter),
                                "kind": "adapter",
                                "install_action": "created",
                                "sha256": hashlib.sha256(adapter.read_bytes()).hexdigest(),
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            self.assertEqual(
                0,
                install.main(["--project", str(project), "--uninstall"]),
            )

            self.assertFalse(adapter.exists())
            self.assertTrue(receipt.is_file())


class TestFrontendDistribution(unittest.TestCase):
    def _frontend_plan(self, root: Path, source: Path) -> install.Plan:
        home = root / "home"
        scope_home = home / ".orchflows"
        frontend_home = scope_home / "ui"
        identity = install._frontend_manifest_identity(source)
        return install.Plan(
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

    def test_user_plan_carries_the_exact_distribution(self):
        source_root = install.REPO_ROOT / "reader" / "web" / "dist"
        expected_files = {
            path.relative_to(source_root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(source_root.rglob("*"))
            if path.is_file()
        }
        encoded = json.dumps(expected_files, sort_keys=True, separators=(",", ":"))
        expected_identity = hashlib.sha256(encoded.encode("utf-8")).hexdigest()

        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw) / "home"
            home.mkdir()
            with patch.object(install.Path, "home", return_value=home), patch.object(
                install.shutil, "which", return_value="mock-host"
            ):
                user_plan = install.build_plan()

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
        self.assertIn(
            (install.REPO_ROOT / "THIRD_PARTY_NOTICES.md", user_plan.lib_home / "THIRD_PARTY_NOTICES.md"),
            user_plan.lib_copies,
        )

    def test_frontend_refusal_prevents_a_success_receipt(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            plan = install.Plan(
                scope_home=root / ".orchflows",
                lib_home=root / ".orchflows" / "lib", bin_dir=root / ".orchflows" / "bin",
                receipt_path=root / ".orchflows" / "receipt.json",
                frontend_home=root / "missing-ui", frontend_manifest_sha256="expected",
                frontend_action="refuse", manage_host_surfaces=False,
            )
            with self.assertRaisesRegex(RuntimeError, "healthy frontend assets"):
                install.apply_plan(plan, accepted_source=install.resolve_source_commit())
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
                receipt = install.apply_plan(plan, accepted_source=install.resolve_source_commit())

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
                    install.apply_plan(broken_plan, accepted_source=install.resolve_source_commit())
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
                    install.apply_plan(plan, accepted_source=install.resolve_source_commit())
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
            install.apply_plan(plan, accepted_source=install.resolve_source_commit())

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
            install.apply_plan(plan, accepted_source=install.resolve_source_commit())
            with patch.object(install.Path, "home", return_value=root / "home"):
                report = install.run_uninstall("user", None, dry_run=True)
            self.assertTrue(plan.frontend_home.is_dir())
            self.assertFalse(any("review frontend distribution" in item["action"] for item in report["manual_actions"]))
            self.assertEqual("would remove empty frontend distribution", report["skill_actions"][-1]["action"])
