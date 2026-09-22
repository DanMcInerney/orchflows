"""Antigravity's observed native contracts, using disposable profiles only."""

import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import agy_integration as agy
import host_integration as hosts
import package_files


def contents(root):
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in package_files.files(root)}


class AntigravityTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="orchflows-agy-tests-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        environment = patch.dict(os.environ, {"HOME": str(self.root), "USERPROFILE": str(self.root),
                                               "LOCALAPPDATA": str(self.root / "AppData/Local")})
        environment.start()
        self.addCleanup(environment.stop)
        self.home = self.root / "orchflows home"
        self.source = self.home / ".local/packages/orchflows"
        self.cache = self.root / ".gemini/config/plugins/orchflows"
        (self.source / "skills/orch-work").mkdir(parents=True)
        (self.source / "skills/orch-work/SKILL.md").write_text("Current skill instructions\n")
        (self.source / "references").mkdir()
        (self.source / "references/context.md").write_text("Package-relative resource\n")
        (self.source / "plugin.json").write_text(json.dumps({"name": "orchflows", "version": "1.0.0", "skills": "./skills/"}))
        self.package = {"name": "orchflows", "package_root": str(self.source)}
        self.detected = {"agy": {"status": "available", "version": "1.0.14", "executable": "agy"}}
        self.imports = []
        self.actions = []
        cli = patch.object(hosts, "_run", side_effect=self.native)
        cli.start()
        self.addCleanup(cli.stop)

    def native(self, executable, *arguments, cwd=None):
        self.assertEqual(executable, "agy")
        self.actions.append(arguments)
        if arguments == ("plugin", "list"):
            return json.dumps({"imports": self.imports}) if self.imports else "No imported plugins.\n"
        if arguments == ("plugin", "validate", str(self.source)):
            return "[ok] orchflows; skills: 1 processed"
        if arguments == ("plugin", "uninstall", "orchflows"):
            shutil.rmtree(self.cache)
            self.imports = []
            return "Uninstalled orchflows"
        if arguments == ("plugin", "install", str(self.source)):
            # Match old agy's overlay behavior: uninstall must remove obsolete files.
            shutil.copytree(self.source, self.cache, dirs_exist_ok=True)
            self.imports = [{"name": "orchflows", "source": "antigravity", "importedAt": "2026-09-16T16:45:07Z", "components": ["skills"]}]
            return "[ok] orchflows"
        self.fail(f"Unexpected native command: {arguments}")

    def integrate(self, install=True):
        return hosts.integrate(self.home, [self.package], self.detected, install=install)["agy"]

    def install(self):
        result = self.integrate()
        self.assertEqual(result["status"], "ready", result)
        self.actions.clear()

    def assert_read_only(self):
        self.assertTrue(all(command == ("plugin", "list") for command in self.actions), self.actions)

    def test_discovery_includes_agy_and_finds_standard_install_without_path(self):
        self.assertIn("agy", hosts.select_hosts(None))
        self.assertEqual(hosts.select_hosts(["agy"]), ("agy",))
        executable = (self.root / "AppData/Local/agy/bin/agy.exe") if os.name == "nt" else (self.root / ".local/bin/agy")
        executable.parent.mkdir(parents=True)
        executable.write_bytes(b"fixture")
        with patch.object(hosts.shutil, "which", return_value=None), patch.object(hosts, "_run", return_value="1.0.14\n"):
            result = hosts.detect(["agy"])
        self.assertEqual(result["agy"]["status"], "available")
        self.assertEqual(result["agy"]["executable"], str(executable))

    def test_install_preserves_complete_package_and_records_ownership(self):
        result = self.integrate()
        self.assertEqual(result["status"], "ready", result)
        self.assertTrue(package_files.same(self.source, self.cache))
        receipts = json.loads((self.home / ".local/agy-installs.json").read_text())
        self.assertNotIn("version", receipts)
        receipt = receipts["installs"][str(self.cache)]
        self.assertEqual(receipt["source"], str(self.source))
        skill = self.cache / "skills/orch-work/SKILL.md"
        self.assertEqual(receipt["files"]["skills/orch-work/SKILL.md"],
                         {"size": skill.stat().st_size, "mtime_ns": skill.stat().st_mtime_ns})
        self.assertEqual(receipt["record"], self.imports[0])
        self.assertIn("no manual-only", result["warnings"][0])

    def test_repeat_and_doctor_do_not_reinstall_or_rewrite_receipts(self):
        self.install()
        receipt = self.home / ".local/agy-installs.json"
        before = (receipt.read_bytes(), receipt.stat().st_mtime_ns)
        for install in (True, False):
            self.assertEqual(self.integrate(install)["status"], "ready")
        self.assert_read_only()
        self.assertEqual(before, (receipt.read_bytes(), receipt.stat().st_mtime_ns))

    def test_refresh_removes_deleted_resources_using_native_uninstall(self):
        self.install()
        (self.source / "references/context.md").unlink()
        (self.source / "skills/orch-work/SKILL.md").write_text("Updated instructions\n")
        result = self.integrate()
        self.assertEqual(result["status"], "updated", result)
        self.assertFalse((self.cache / "references/context.md").exists())
        self.assertIn(("plugin", "uninstall", "orchflows"), self.actions)
        self.assertTrue(package_files.same(self.source, self.cache))

    def test_digest_receipts_from_before_plain_facts_ask_for_reinstall(self):
        self.install()
        path = self.home / ".local/agy-installs.json"
        receipts = json.loads(path.read_text())
        receipt = receipts["installs"][str(self.cache)]
        receipt["files"] = {name: "0" * 64 for name in receipt["files"]}
        path.write_text(json.dumps({"version": 1, **receipts}))
        result = self.integrate()
        self.assertEqual(result["status"], "needs_action")
        self.assertIn("earlier setup format", result["packages"]["orchflows"]["message"])
        self.assert_read_only()

    def test_disabled_owned_installation_is_preserved(self):
        self.install()
        (self.cache / "plugin.json").rename(self.cache / "plugin.json.disabled")
        self.assertEqual(self.integrate()["status"], "needs_action")
        self.assert_read_only()
        self.assertTrue((self.cache / "plugin.json.disabled").is_file())

    def test_untracked_manual_plugin_is_not_overwritten_even_with_identical_content(self):
        shutil.copytree(self.source, self.cache)
        result = self.integrate()
        self.assertEqual(result["status"], "needs_action")
        self.assertIn("earlier setup format", result["packages"]["orchflows"]["message"])
        self.assert_read_only()
        self.assertFalse((self.home / ".local/agy-installs.json").exists())

    def test_occupied_destination_without_matching_inventory_is_preserved(self):
        shutil.copytree(self.source, self.cache)
        (self.cache / "skills/orch-work/SKILL.md").write_text("Foreign user instructions")
        before = contents(self.cache)
        with patch.object(agy, "inventory", return_value=[]):
            result = self.integrate()
        self.assertEqual(result["status"], "needs_action")
        self.assertIn("destination already exists", result["packages"]["orchflows"]["message"])
        self.assertEqual(before, contents(self.cache))
        self.assert_read_only()

    def test_case_colliding_native_plugin_is_preserved(self):
        foreign = self.cache.with_name("Orchflows")
        shutil.copytree(self.source, foreign)
        if not self.cache.exists():
            self.skipTest("Case-sensitive filesystem has no alias collision")
        (foreign / "plugin.json").write_text(json.dumps({"name": "Orchflows"}))
        (foreign / "skills/orch-work/SKILL.md").write_text("Foreign user instructions")
        self.imports = [{"name": "Orchflows", "source": "antigravity", "components": ["skills"]}]
        before = contents(foreign)
        result = self.integrate()
        self.assertEqual(result["status"], "needs_action")
        self.assertEqual(before, contents(foreign))
        self.assert_read_only()

    def test_foreign_native_registration_and_external_edits_are_preserved(self):
        self.install()
        original = self.imports[0]["source"]
        self.imports[0]["source"] = "claude"
        self.assertEqual(self.integrate()["status"], "needs_action")
        self.imports[0]["source"] = original
        (self.cache / "personal-note.txt").write_text("Preserve my added file")
        (self.source / "references/context.md").write_text("Updated source")
        result = self.integrate()
        self.assertEqual(result["status"], "needs_action")
        self.assertIn("changed outside setup", result["packages"]["orchflows"]["message"])
        self.assert_read_only()
        self.assertEqual((self.cache / "personal-note.txt").read_text(), "Preserve my added file")

    def test_duplicate_native_records_require_action(self):
        self.install()
        self.imports.append(dict(self.imports[0]))
        result = self.integrate()
        self.assertEqual(result["status"], "needs_action")
        self.assertIn("Multiple installations", result["packages"]["orchflows"]["message"])
        self.assert_read_only()

    def test_doctor_reports_absent_and_stale_without_creating_receipts(self):
        self.assertEqual(self.integrate(False)["status"], "needs_action")
        self.assertFalse((self.home / ".local/agy-installs.json").exists())
        self.assertFalse(self.cache.exists())
        self.assert_read_only()
        self.install()
        (self.source / "references/context.md").write_text("Updated source")
        self.assertEqual(self.integrate(False)["status"], "needs_action")
        self.assert_read_only()

    def test_malformed_native_registry_is_preserved_instead_of_treated_as_empty(self):
        registry = self.root / ".gemini/config/import_manifest.json"
        registry.parent.mkdir(parents=True)
        registry.write_text("not-json")
        self.assertEqual(self.integrate()["status"], "failed")
        self.assert_read_only()
        self.assertEqual(registry.read_text(), "not-json")

    def test_malformed_receipts_and_unsafe_inventory_names_never_install(self):
        (self.home / ".local/agy-installs.json").write_text("[]")
        self.assertEqual(self.integrate()["status"], "failed")
        self.assert_read_only()
        self.imports = [{"name": "../outside", "source": "antigravity"}]
        self.assertEqual(self.integrate()["status"], "failed")
        self.assert_read_only()

    def test_native_success_with_incomplete_copy_cannot_be_reported_ready(self):
        def incomplete(executable, *arguments, cwd=None):
            result = self.native(executable, *arguments, cwd=cwd)
            if arguments[:2] == ("plugin", "install"):
                (self.cache / "references/context.md").unlink()
            return result
        with patch.object(hosts, "_run", side_effect=incomplete):
            result = self.integrate()
        self.assertEqual(result["status"], "failed")
        self.assertFalse((self.home / ".local/agy-installs.json").exists())

    def test_linked_native_directory_is_preserved(self):
        self.cache.parent.mkdir(parents=True)
        outside = self.root / "outside"
        outside.mkdir()
        try:
            self.cache.symlink_to(outside, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"Symlinks unavailable: {exc}")
        self.assertEqual(self.integrate()["status"], "failed")
        self.assert_read_only()
        self.assertEqual(list(outside.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
