"""Native inventory contracts and safe registration behavior, using disposable homes."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import host_integration as hosts


class HostIntegrationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="orchflows-native-tests-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        environment = patch.dict(os.environ, {"CODEX_HOME": str(self.root / "codex")})
        environment.start()
        self.addCleanup(environment.stop)
        self.home = self.root / "orchflows home"
        self.source = self.home / ".local/packages/orchflows"
        self.cache = self.root / "native cache/orchflows/1.0.0"
        (self.source / "skills/orch-work").mkdir(parents=True)
        (self.source / "skills/orch-work/SKILL.md").write_text("Current instructions\n")
        (self.source / ".codex-plugin").mkdir()
        (self.source / ".codex-plugin/plugin.json").write_text(json.dumps({"name": "orchflows", "version": "1.0.0"}))
        self.package = {"name": "orchflows", "package_root": str(self.source)}

    def copy_current(self):
        shutil.copytree(self.source, self.cache, dirs_exist_ok=True)

    def stale_cache(self):
        self.copy_current()
        (self.cache / "skills/orch-work/SKILL.md").write_text("Previous instructions\n")

    def detected(self, *names):
        return {name: {"executable": name, "status": "available", "version": "fixture"} for name in names}

    def codex_row(self, **changes):
        row = {
            "pluginId": "orchflows@orchflows-home", "name": "orchflows",
            "marketplaceName": "orchflows-home", "version": "1.0.0",
            "installed": True, "enabled": True,
            "source": {"source": "local", "path": str(self.source)},
            "marketplaceSource": {"sourceType": "local", "source": str(self.home)},
            "installPolicy": "AVAILABLE", "authPolicy": "ON_INSTALL",
        }
        row.update(changes)
        return row

    def claude_row(self, **changes):
        row = {
            "id": "orchflows@orchflows-home", "version": "1.0.0", "scope": "user",
            "enabled": True, "installPath": str(self.cache),
            "installedAt": "2026-09-16T16:22:57.249Z", "lastUpdated": "2026-09-16T16:22:57.249Z",
        }
        row.update(changes)
        return row

    def marketplace(self, host):
        if host == "codex":
            return {"marketplaces": [{"name": hosts.MARKETPLACE, "root": str(self.home)}]}
        return [{"name": hosts.MARKETPLACE, "source": "directory", "path": str(self.home), "installLocation": str(self.home)}]

    def cli(self, inventories, *, marketplaces=None, inspect=None, mutate=None):
        """Serve recorded public responses; every unexpected command fails the test."""
        sequences = {host: list(values) for host, values in inventories.items()}

        def run(executable, *arguments, cwd=None):
            if arguments == ("plugin", "list", "--json"):
                sequence = sequences[executable]
                value = sequence.pop(0) if len(sequence) > 1 else sequence[0]
            elif arguments == ("plugin", "marketplace", "list", "--json"):
                value = (marketplaces or {}).get(executable, self.marketplace(executable))
            elif arguments == ("inspect", "--json") and inspect is not None:
                value = inspect
            elif mutate is not None:
                value = mutate(executable, arguments)
            else:
                raise AssertionError(f"Unexpected native mutation: {executable} {arguments}")
            if isinstance(value, Exception):
                raise value
            return value if isinstance(value, str) else json.dumps(value)

        return patch.object(hosts, "_run", side_effect=run)

    def integrate(self, *names, install=True):
        return hosts.integrate(self.home, [self.package], self.detected(*names), install=install)

    def assert_no_mutations(self, mock):
        reads = {("plugin", "list", "--json"), ("plugin", "marketplace", "list", "--json"), ("inspect", "--json")}
        self.assertTrue(all(call.args[1:] in reads for call in mock.call_args_list), mock.call_args_list)

    def test_selection_defaults_explicit_deduplication_and_none(self):
        self.assertEqual(hosts.select_hosts(None), hosts.HOSTS)
        self.assertEqual(hosts.select_hosts(["auto"]), hosts.HOSTS)
        self.assertEqual(hosts.select_hosts(["grok", "codex", "grok"]), ("codex", "grok"))
        self.assertEqual(hosts.select_hosts(["none"]), ())
        for invalid in (["none", "codex"], ["auto", "grok"], ["unknown"]):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                hosts.select_hosts(invalid)

    def test_missing_executables_and_leftover_directories_do_not_write_config(self):
        leftover = self.root / "leftover config"
        leftover.mkdir()
        before = set(self.root.rglob("*"))
        with patch.object(hosts, "_candidates", return_value=iter([leftover])), patch.object(hosts, "_run") as run:
            automatic = hosts.detect(["auto"])
        self.assertTrue(all(report["status"] == "not_detected" for report in automatic.values()))
        with patch.object(hosts, "_candidates", return_value=iter([leftover])), patch.object(hosts, "_run") as explicit_run:
            explicit = hosts.detect(["claude"])
        self.assertEqual(explicit["claude"]["status"], "needs_action")
        run.assert_not_called()
        explicit_run.assert_not_called()
        self.assertEqual(set(self.root.rglob("*")), before)

    def test_detection_probes_cli_but_does_not_launch_zcode_desktop(self):
        executable = self.root / "native.exe"
        executable.write_bytes(b"fixture")
        with patch.object(hosts, "_candidates", side_effect=lambda host: iter([executable])), patch.object(hosts, "_run", return_value="native 1.0\n") as run:
            detected = hosts.detect(["codex", "zcode"])
        self.assertEqual({row["status"] for row in detected.values()}, {"available"})
        run.assert_called_once_with(str(executable), "--version")

    def test_native_timeout_is_reported_without_blocking_next_host(self):
        executable = self.root / "native.exe"
        executable.write_bytes(b"fixture")
        with patch.object(hosts, "_candidates", side_effect=lambda host: iter([executable])), patch.object(hosts, "_run", side_effect=[subprocess.TimeoutExpired("codex", 45), "claude 1.0"]):
            detected = hosts.detect(["codex", "claude"])
        self.assertEqual(detected["codex"]["status"], "failed")
        self.assertEqual(detected["claude"]["status"], "available")

    def test_malformed_plugin_inventory_never_mutates(self):
        cases = [("codex", {"installed": [{}]}), ("claude", {}), ("claude", "not JSON")]
        for host, value in cases:
            with self.subTest(host=host, value=value), self.cli({host: [value]}) as run:
                result = self.integrate(host)
                self.assertEqual(result[host]["status"], "failed")
                self.assert_no_mutations(run)

    def test_fresh_custom_codex_profile_is_created_only_for_install(self):
        profile = self.root / "codex"
        with self.cli({"codex": [{"installed": []}]}):
            self.integrate("codex", install=False)
        self.assertFalse(profile.exists())
        with self.cli({"codex": [{"installed": [{}]}]}):
            self.integrate("codex", install=True)
        self.assertTrue(profile.is_dir())

    def test_malformed_marketplace_rows_never_mutate(self):
        for host, inventory in (("codex", {"installed": []}), ("claude", [])):
            market = {"marketplaces": [{}]} if host == "codex" else [{}]
            with self.subTest(host=host), self.cli({host: [inventory]}, marketplaces={host: market}) as run:
                result = self.integrate(host)
                self.assertEqual(result[host]["status"], "failed")
                self.assert_no_mutations(run)

    def test_disabled_existing_plugins_are_preserved(self):
        for host, inventory in (("codex", {"installed": [self.codex_row(enabled=False)]}), ("claude", [self.claude_row(enabled=False)])):
            with self.subTest(host=host), self.cli({host: [inventory]}) as run:
                result = self.integrate(host)
                self.assertEqual(result[host]["status"], "needs_action")
                self.assertIn("disabled", result[host]["packages"]["orchflows"]["message"])
                self.assert_no_mutations(run)

    def test_foreign_source_and_project_scopes_are_preserved(self):
        cases = [
            ("codex", {"installed": [self.codex_row(marketplaceName="foreign")]}),
            ("codex", {"installed": [self.codex_row(source={"source": "local", "path": str(self.root / "other")})]}),
            ("claude", [self.claude_row(id="orchflows@foreign")]),
            ("claude", [self.claude_row(scope="project")]),
        ]
        for host, inventory in cases:
            with self.subTest(host=host, inventory=inventory), self.cli({host: [inventory]}) as run:
                result = self.integrate(host)
                self.assertEqual(result[host]["status"], "needs_action")
                self.assert_no_mutations(run)

    def test_claude_marketplace_root_conflict_is_not_silently_retargeted(self):
        market = [{"name": hosts.MARKETPLACE, "source": "directory", "path": str(self.root / "other"), "installLocation": str(self.root / "other")}]
        with self.cli({"claude": [[]]}, marketplaces={"claude": market}) as run:
            result = self.integrate("claude")
        self.assertEqual(result["claude"]["status"], "needs_action")
        self.assertIn("points elsewhere", result["claude"]["packages"]["orchflows"]["message"])
        self.assert_no_mutations(run)

    def test_duplicate_installations_require_action(self):
        inventory = [self.claude_row(), self.claude_row(scope="project")]
        with self.cli({"claude": [inventory]}) as run:
            result = self.integrate("claude")
        self.assertEqual(result["claude"]["status"], "needs_action")
        self.assert_no_mutations(run)

    def test_current_claude_payload_is_ready_without_reinstall(self):
        self.copy_current()
        with self.cli({"claude": [[self.claude_row()]]}) as run:
            result = self.integrate("claude")
        self.assertEqual(result["claude"]["status"], "ready")
        self.assert_no_mutations(run)

    def test_same_version_codex_add_refreshes_payload_and_verifies_returned_path(self):
        self.stale_cache()

        def refresh(executable, arguments):
            self.assertEqual(arguments, ("plugin", "add", "orchflows@orchflows-home", "--json"))
            self.copy_current()
            return {"pluginId": "orchflows@orchflows-home", "version": "1.0.0", "installedPath": str(self.cache)}

        with self.cli({"codex": [{"installed": [self.codex_row()]}]}, mutate=refresh):
            result = self.integrate("codex")
        self.assertEqual(result["codex"]["status"], "updated")
        self.assertEqual((self.cache / "skills/orch-work/SKILL.md").read_text(), "Current instructions\n")

    def test_absent_codex_marketplace_and_plugin_are_registered_then_verified(self):
        actions = []

        def install(executable, arguments):
            actions.append(arguments)
            if arguments[:3] == ("plugin", "marketplace", "add"):
                self.assertIn(str(self.home), arguments)
                return "Marketplace added"
            self.assertEqual(arguments, ("plugin", "add", "orchflows@orchflows-home", "--json"))
            self.copy_current()
            return {"pluginId": "orchflows@orchflows-home", "version": "1.0.0", "installedPath": str(self.cache)}

        inventory = {"codex": [{"installed": []}, {"installed": [self.codex_row()]}]}
        with self.cli(inventory, marketplaces={"codex": {"marketplaces": []}}, mutate=install):
            result = self.integrate("codex")
        self.assertEqual(result["codex"]["status"], "ready")
        self.assertEqual(len(actions), 2)

    def test_claude_stale_same_version_update_is_reinstalled_then_verified(self):
        self.stale_cache()
        actions = []

        def refresh(executable, arguments):
            actions.append(arguments)
            if arguments[:2] == ("plugin", "install"):
                self.copy_current()
            return "Success"

        with self.cli({"claude": [[self.claude_row()]]}, mutate=refresh):
            result = self.integrate("claude")
        self.assertEqual(result["claude"]["status"], "updated", result)
        plugin = "orchflows@orchflows-home"
        self.assertEqual(actions, [("plugin", "marketplace", "update", "orchflows-home"),
                                   ("plugin", "uninstall", plugin, "--scope", "user", "--keep-data"),
                                   ("plugin", "install", plugin, "--scope", "user")])

    def test_claude_copy_still_stale_after_reinstall_requires_action_without_a_version_bump(self):
        self.stale_cache()
        with self.cli({"claude": [[self.claude_row()]]}, mutate=lambda *args: "Success"):
            result = self.integrate("claude")
        self.assertEqual(result["claude"]["status"], "needs_action")
        message = result["claude"]["packages"]["orchflows"]["message"]
        self.assertIn("still differ", message)
        self.assertNotIn("version", message.lower())

    def test_payload_compares_every_package_file_but_ignores_host_markers_and_caches(self):
        self.copy_current()
        (self.cache / ".in_use").mkdir()
        (self.cache / ".in_use/4242").write_text("")
        (self.cache / ".orphaned_at").write_text("1758000000000")
        (self.cache / "skills/orch-work/__pycache__").mkdir()
        (self.cache / "skills/orch-work/__pycache__/cached.pyc").write_bytes(b"cache")
        self.assertTrue(hosts._matches(self.source, str(self.cache)))
        for relative in ("assets/diagram.png", "LICENSE", "DESIGN.md", ".kimi-plugin/plugin.json"):
            with self.subTest(relative=relative):
                path = self.source / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("new source file\n")
                self.assertFalse(hosts._matches(self.source, str(self.cache)))
                path.unlink()
        (self.cache / "skills/orch-work/obsolete.md").write_text("removed from source\n")
        self.assertFalse(hosts._matches(self.source, str(self.cache)))

    def test_native_success_without_enabled_inventory_is_failure(self):
        self.copy_current()
        inventories = {"claude": [[], [self.claude_row(enabled=False)]]}
        with self.cli(inventories, mutate=lambda *args: "Installed"):
            result = self.integrate("claude")
        self.assertEqual(result["claude"]["status"], "failed")

    def test_post_install_foreign_registration_cannot_be_reported_ready(self):
        self.copy_current()
        inventories = {"claude": [[], [self.claude_row(id="orchflows@foreign")]]}
        with self.cli(inventories, mutate=lambda *args: "Installed"):
            result = self.integrate("claude")
        self.assertIn(result["claude"]["status"], {"failed", "needs_action"})

    def grok_effective(self):
        return {
            "plugins": [{"name": "orchflows", "path": str(self.cache), "scope": "user", "enabled": True}],
            "skills": [{"name": "orch-work", "disabled": False,
                        "source": {"plugin_name": "orchflows", "path": str(self.cache / "skills/orch-work/SKILL.md")}}],
        }

    def test_grok_inherited_current_plugin_is_not_installed_twice(self):
        self.copy_current()
        with self.cli({"grok": [[]]}, inspect=self.grok_effective()) as run:
            result = self.integrate("grok")
        self.assertEqual(result["grok"]["status"], "ready")
        self.assertIn("compatible plugin discovery", result["grok"]["packages"]["orchflows"]["message"])
        self.assert_no_mutations(run)

    def test_grok_inherited_stale_plugin_requires_owning_host_update(self):
        self.stale_cache()
        with self.cli({"grok": [[]]}, inspect=self.grok_effective()) as run:
            result = self.integrate("grok")
        self.assertEqual(result["grok"]["status"], "needs_action")
        self.assertIn("owning host", result["grok"]["packages"]["orchflows"]["message"])
        self.assert_no_mutations(run)

    def test_grok_owned_stale_local_copy_is_reinstalled_with_persistent_data_preserved(self):
        self.stale_cache()
        inventory = [{"name": "orchflows", "path": str(self.cache), "source": str(self.source)}]
        actions = []

        def refresh(executable, arguments):
            actions.append(arguments)
            if arguments[:2] == ("plugin", "install"):
                self.copy_current()
            return "Success"

        with self.cli({"grok": [inventory]}, inspect=self.grok_effective(), mutate=refresh):
            result = self.integrate("grok")
        self.assertEqual(result["grok"]["status"], "updated")
        self.assertEqual(actions, [("plugin", "uninstall", "orchflows", "--keep-data"),
                                   ("plugin", "install", str(self.source), "--trust")])

    def test_grok_duplicate_native_names_hidden_by_effective_discovery_are_preserved(self):
        self.copy_current()
        inventory = [{"name": "orchflows", "path": str(self.cache), "source": str(self.source)},
                     {"name": "orchflows", "path": str(self.root / "hidden"), "source": str(self.root / "foreign")}]
        with self.cli({"grok": [inventory]}, inspect=self.grok_effective()) as run:
            result = self.integrate("grok")
        self.assertEqual(result["grok"]["status"], "needs_action")
        self.assertIn("Multiple installations", result["grok"]["packages"]["orchflows"]["message"])
        self.assert_no_mutations(run)

    def test_grok_registered_plugin_missing_from_effective_discovery_is_preserved(self):
        inventory = [{"name": "orchflows", "path": str(self.cache), "source": str(self.source)}]
        with self.cli({"grok": [inventory]}, inspect={"plugins": [], "skills": []}) as run:
            result = self.integrate("grok")
        self.assertEqual(result["grok"]["status"], "needs_action")
        self.assert_no_mutations(run)

    @unittest.skipUnless(os.name == "nt", "Windows batch launchers")
    def test_batch_launcher_preserves_metacharacters_without_executing_them(self):
        script = self.root / "arguments.py"
        script.write_text("import json, sys; print(json.dumps(sys.argv[1:]))")
        batch = self.root / "native.cmd"
        batch.write_text(f'@echo off\n"{sys.executable}" "{script}" %*\n')
        arguments = [str(self.root / "home&echo.UNEXPECTED_COMMAND"), str(self.root / "spaces & (parentheses)"),
                     "C:\\", "caret^value", "pipe|value", "less<value", "greater>value"]
        self.assertEqual(json.loads(hosts._run(str(batch), *arguments)), arguments)
        for unsafe in ("%USERNAME%", "!EXPANSION!", 'embedded"quote', "line\nfeed"):
            with self.subTest(unsafe=unsafe), patch.object(hosts.subprocess, "run") as run:
                with self.assertRaisesRegex(ValueError, "cannot safely pass"):
                    hosts._run(str(batch), unsafe)
                run.assert_not_called()

    def test_doctor_inspection_never_installs_absent_or_stale_packages(self):
        for inventory in ([], [self.claude_row()]):
            self.stale_cache()
            with self.subTest(inventory=inventory), self.cli({"claude": [inventory]}) as run:
                result = self.integrate("claude", install=False)
                self.assertEqual(result["claude"]["status"], "needs_action")
                self.assert_no_mutations(run)

    def test_one_host_inventory_failure_does_not_prevent_another_host(self):
        self.copy_current()
        with self.cli({"codex": [ValueError("native unavailable")], "claude": [[self.claude_row()]]}):
            result = self.integrate("codex", "claude")
        self.assertEqual(result["codex"]["status"], "failed")
        self.assertEqual(result["claude"]["status"], "ready")

    def test_manual_hosts_give_absolute_next_steps_without_cli_mutations(self):
        with patch.object(hosts, "_run") as run:
            result = self.integrate("kimi", "zcode")
        self.assertEqual(result["kimi"]["status"], "needs_action")
        self.assertIn(self.source.as_posix(), " ".join(result["kimi"]["next_steps"]))
        self.assertIn(str(self.home), " ".join(result["zcode"]["next_steps"]))
        self.assertIn("orchflows", " ".join(result["zcode"]["next_steps"]))
        self.assertIn("uninstall and reinstall", " ".join(result["zcode"]["next_steps"]))
        run.assert_not_called()

    def test_existing_optional_libraries_refresh_without_installing_unrequested_ones(self):
        packages = [self.package, {"name": "existing", "package_root": str(self.home / "libraries/existing")},
                    {"name": "optional", "package_root": str(self.home / "libraries/optional")}]
        with patch.object(hosts, "_inventory", return_value=[{"name": "existing"}]), \
                patch.object(hosts, "_package", return_value={"status": "ready"}) as register:
            report = hosts.integrate(self.home, packages, self.detected("claude"), install=True)
        self.assertEqual(set(report["claude"]["packages"]), {"orchflows", "existing"})
        self.assertEqual(register.call_count, 2)


if __name__ == "__main__":
    unittest.main()
