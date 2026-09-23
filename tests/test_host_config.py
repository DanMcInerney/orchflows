"""Host config edits use disposable directories and retain recoverable original bytes."""

import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import host_config


class HostConfigTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="orchflows-host-config-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.codex = self.root / "codex/config.toml"
        self.claude = self.root / "claude/settings.json"
        environment = patch.dict(os.environ, {
            "CODEX_HOME": str(self.codex.parent), "CLAUDE_CONFIG_DIR": str(self.claude.parent),
        })
        environment.start()
        self.addCleanup(environment.stop)

    def write(self, path, content):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode("utf-8"))

    def apply(self, concurrency=15):
        results, issues = host_config.apply_host_configs(host_config.prepare_host_configs(concurrency))
        self.assertEqual(issues, [])
        return results

    def test_new_homes_and_repeat_have_no_backups_or_rewrites(self):
        first = self.apply()
        self.assertEqual(tomllib.loads(self.codex.read_text())["agents"], {"max_threads": 15})
        self.assertEqual(json.loads(self.claude.read_text())["env"][host_config.CLAUDE_KEY], "15")
        for host in ("codex", "claude"):
            self.assertEqual(first[host]["status"], "created")
            self.assertIsNone(first[host]["backup"])
        before = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in (self.codex, self.claude)}
        second = self.apply()
        self.assertEqual({path: (path.read_bytes(), path.stat().st_mtime_ns) for path in before}, before)
        self.assertTrue(all(value["status"] == "unchanged" for value in second.values()))
        self.assertEqual(list(self.root.rglob("*.bak")), [])

    def test_settings_and_original_backup_bytes_survive_override_and_repeat(self):
        codex = '# Keep comments\r\nmodel = "personal-model"\r\n[agents] # workers\r\nmax_threads = 4 # old cap\r\nmax_depth = 2\r\n[projects."C:/work"]\r\ntrust_level = "trusted"\r\n'
        claude = '{"permissions":{"allow":["Read"]},"enabledPlugins":{"sample":true},"env":{"KEEP":"café","CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY":"6"}}\r\n'
        self.write(self.codex, codex)
        self.write(self.claude, claude)
        results = self.apply(21)
        self.assertEqual(self.codex.read_bytes(), codex.replace("max_threads = 4", "max_threads = 21").encode())
        expected = json.loads(claude)
        expected["env"][host_config.CLAUDE_KEY] = "21"
        self.assertEqual(json.loads(self.claude.read_bytes()), expected)
        for host, original in (("codex", codex), ("claude", claude)):
            self.assertEqual(Path(results[host]["backup"]).read_bytes(), original.encode())
        before = {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        self.apply(21)
        self.assertEqual({path: path.read_bytes() for path in before}, before)
        self.assertEqual(len(list(self.root.rglob("*.bak"))), 2)

    def test_default_paths_and_environment_overrides_are_independent_of_orchflows_home(self):
        with patch.dict(os.environ, {"CODEX_HOME": "", "CLAUDE_CONFIG_DIR": "", "ORCHFLOWS_HOME": str(self.root / "library")}), patch.object(Path, "home", return_value=self.root):
            results = self.apply()
        self.assertEqual(results["codex"]["path"], str(self.root / ".codex/config.toml"))
        self.assertEqual(results["claude"]["path"], str(self.root / ".claude/settings.json"))
        self.assertFalse((self.root / "library").exists())

    def test_plain_codex_layouts_are_edited_in_place(self):
        for original in ('# personal configuration\nmodel = "x"', '[agents] # workers', '[agents.reviewer]\ndescription = "sample"\n',
                         '[agents]\nmax_threads = 4\nmax_depth = 2\n[tools]\nenabled = true\n', '["agents"]\nmax_threads = 4\n',
                         '[agents]\nmax_threads = true\n', '[agents]\nmax_threads = 15.0\n', '', '[agents] # workers\r\nmax_depth = 2\r\n', '[agents]\r\n'):
            with self.subTest(original=original):
                expected = tomllib.loads(original)
                expected.setdefault("agents", {})[host_config.CODEX_KEY] = 15
                updated = host_config._codex(original, 15)
                self.assertEqual(tomllib.loads(updated), expected)
                self.assertIs(type(tomllib.loads(updated)["agents"][host_config.CODEX_KEY]), int)
                self.assertNotIn("\r\r", updated)
                self.assertEqual(host_config._codex(updated, 15), updated)
        self.assertEqual(tomllib.loads(host_config._codex('[agents]\nmax_threads = true\n', 1))["agents"], {"max_threads": 1})

    def test_byte_order_marks_are_accepted(self):
        self.codex.parent.mkdir(parents=True)
        self.codex.write_bytes(b'\xef\xbb\xbfmodel = "x"\n')
        self.claude.parent.mkdir(parents=True)
        self.claude.write_bytes(b'\xef\xbb\xbf{"env":{}}\n')
        results = self.apply(7)
        self.assertEqual({host: value["status"] for host, value in results.items()}, {"codex": "updated", "claude": "updated"})
        self.assertEqual(tomllib.loads(self.codex.read_text(encoding="utf-8"))["agents"]["max_threads"], 7)
        self.assertEqual(json.loads(self.claude.read_text(encoding="utf-8"))["env"][host_config.CLAUDE_KEY], "7")

    def test_already_correct_files_with_byte_order_marks_are_not_rewritten(self):
        self.write(self.codex, "﻿[agents]\nmax_threads = 7\n")
        self.write(self.claude, '﻿{"env":{"CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY":"7"}}\n')
        before = {path: path.read_bytes() for path in (self.codex, self.claude)}
        results = self.apply(7)
        self.assertEqual({host: value["status"] for host, value in results.items()}, {"codex": "unchanged", "claude": "unchanged"})
        self.assertEqual({path: path.read_bytes() for path in before}, before)
        self.assertEqual(list(self.root.rglob("*.bak")), [])

    def test_out_of_range_json_numbers_preserve_the_file_with_an_issue(self):
        original = '{"env":{},"limit":1e400}\n'
        self.write(self.claude, original)
        with self.assertRaisesRegex(ValueError, "Host configuration preserved at .*settings.json"):
            host_config.prepare_host_configs(7, ("claude",))
        self.assertEqual(self.claude.read_text(encoding="utf-8"), original)

    def test_a_stale_lock_names_the_next_step(self):
        self.write(self.codex, 'model = "x"\n')
        lock = self.codex.with_name("config.toml.orchflows.lock")
        lock.write_text("")
        results, issues = host_config.apply_host_configs(host_config.prepare_host_configs(7, ("codex",)))
        self.assertEqual(results["codex"]["status"], "unavailable")
        self.assertRegex(issues[0], r"Lock exists: .*config\.toml\.orchflows\.lock; if no setup is running, remove it")
        self.assertTrue(lock.exists())
        self.assertEqual(self.codex.read_text(encoding="utf-8"), 'model = "x"\n')

    def test_equal_boolean_or_float_is_replaced_without_changing_other_tables(self):
        for value in ("true", "1.0"):
            original = f"[other]\nmax_threads = 1\n[agents]\nmax_threads = {value}\n"
            with self.subTest(value=value):
                self.write(self.codex, original)
                self.apply(1)
                parsed = tomllib.loads(self.codex.read_text())
                self.assertEqual(parsed["other"], {"max_threads": 1})
                self.assertIs(type(parsed["agents"]["max_threads"]), int)
                self.assertEqual(parsed["agents"]["max_threads"], 1)

    def test_layouts_that_cannot_be_edited_safely_are_refused_unchanged(self):
        for original in ('agents.max_threads = 1_0\nagents.max_depth = 2\n', 'agents.max_depth = 2\n[tools]\nenabled = true\n',
                         'note = """\n[agents]\nmax_threads = 42\n"""\n[agents]\nmax_depth = 2\n',
                         'agents = { max_threads = 4, max_depth = 2 }\n'):
            with self.subTest(original=original), self.assertRaises(ValueError):
                host_config._codex(original, 15)

    def test_malformed_files_fail_before_either_host_is_written(self):
        cases = [
            (self.codex, 'agents = "invalid"\n'), (self.codex, '[agents]\nmax_threads = 4\nmax_threads = 5\n'), (self.codex, 'model = [\n'),
            (self.claude, '{bad'), (self.claude, '[]'), (self.claude, '{"env":null}'), (self.claude, '{"env":{},"env":{"SECRET":"hidden"}}'),
            (self.claude, '{"custom":NaN}'), (self.claude, '{"custom":Infinity}'), (self.claude, '{"custom":-Infinity}'),
        ]
        for path, invalid in cases:
            with self.subTest(path=path, invalid=invalid):
                self.write(self.codex, 'model = "safe"\n')
                self.write(self.claude, '{}\n')
                self.write(path, invalid)
                before = {p: p.read_bytes() for p in (self.codex, self.claude)}
                with self.assertRaisesRegex(ValueError, "preserved"):
                    host_config.prepare_host_configs()
                self.assertEqual({p: p.read_bytes() for p in before}, before)
                self.assertEqual(list(self.root.rglob("*.bak")), [])

    def test_invalid_concurrency_creates_nothing(self):
        for value in (0, -1, True, 1.5, "15"):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "positive integer"):
                host_config.prepare_host_configs(value)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_changed_file_is_not_clobbered_and_sibling_result_is_reported(self):
        self.write(self.codex, 'model = "before"\n')
        plans = host_config.prepare_host_configs()
        self.write(self.codex, 'model = "editor changed this"\n')
        results, issues = host_config.apply_host_configs(plans)
        self.assertIn("changed during setup", issues[0])
        self.assertEqual(results["codex"]["status"], "unavailable")
        self.assertEqual(results["claude"]["status"], "created")
        self.assertEqual(self.codex.read_text(), 'model = "editor changed this"\n')

    def test_failed_atomic_replace_retains_original_and_cleans_staging_and_backup(self):
        original = 'model = "keep"\n'
        self.write(self.codex, original)
        plans = host_config.prepare_host_configs()
        with patch.object(host_config.os, "replace", side_effect=PermissionError("simulated write failure")):
            results, issues = host_config.apply_host_configs(plans)
        self.assertEqual(results["codex"]["status"], "unavailable")
        self.assertIn("simulated write failure", issues[0])
        self.assertEqual(self.codex.read_text(), original)
        self.assertEqual(list(self.codex.parent.iterdir()), [self.codex])

    def test_host_save_during_staging_is_preserved_for_new_and_existing_files(self):
        for original in (None, 'model = "original"\n'):
            with self.subTest(original=original):
                self.codex.unlink(missing_ok=True)
                if original is not None:
                    self.write(self.codex, original)
                plans = host_config.prepare_host_configs()
                fsync = os.fsync
                saved = 'model = "saved while setup was staging"\n'

                def editor_save(descriptor):
                    fsync(descriptor)
                    self.write(self.codex, saved)

                with patch.object(host_config.os, "fsync", side_effect=editor_save):
                    results, issues = host_config.apply_host_configs(plans)
                self.assertEqual(results["codex"]["status"], "unavailable")
                self.assertIn("changed during setup", " ".join(issues))
                self.assertEqual(self.codex.read_bytes(), saved.encode())
                self.assertEqual(list(self.codex.parent.iterdir()), [self.codex])

    def test_config_created_after_final_check_is_not_overwritten(self):
        plans = host_config.prepare_host_configs()
        link = os.link
        saved = 'model = "concurrently created"\n'

        def editor_create(source, destination):
            if destination == self.codex:
                self.write(destination, saved)
            return link(source, destination)

        with patch.object(host_config.os, "link", side_effect=editor_create):
            results, issues = host_config.apply_host_configs(plans)
        self.assertEqual(results["codex"]["status"], "unavailable")
        self.assertTrue(issues)
        self.assertEqual(self.codex.read_bytes(), saved.encode())
        self.assertEqual(list(self.codex.parent.iterdir()), [self.codex])

    def test_existing_installer_lock_preserves_original(self):
        self.write(self.codex, 'model = "keep"\n')
        lock = self.codex.with_name("config.toml.orchflows.lock")
        self.write(lock, "another installer")
        results, issues = host_config.apply_host_configs(host_config.prepare_host_configs())
        self.assertEqual(results["codex"]["status"], "unavailable")
        self.assertTrue(issues)
        self.assertEqual(lock.read_text(), "another installer")
        self.assertEqual(self.codex.read_text(), 'model = "keep"\n')

    @unittest.skipIf(os.name == "nt", "POSIX mode bits")
    def test_existing_mode_and_private_backup_permissions_are_preserved(self):
        self.write(self.codex, 'model = "keep"\n')
        self.codex.chmod(0o640)
        result = self.apply()
        for path in (self.codex, Path(result["codex"]["backup"])):
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o640)

    def test_symlink_config_is_preserved(self):
        outside = self.root / "linked-config"
        self.write(outside, 'model = "keep"\n')
        self.codex.parent.mkdir()
        try:
            self.codex.symlink_to(outside)
        except OSError as exc:
            self.skipTest(f"Symlinks unavailable: {exc}")
        with self.assertRaisesRegex(ValueError, "ordinary file"):
            host_config.prepare_host_configs()
        self.assertEqual(outside.read_text(), 'model = "keep"\n')
        self.assertTrue(self.codex.is_symlink())


if __name__ == "__main__":
    unittest.main()
