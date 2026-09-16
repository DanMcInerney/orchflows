"""Additional host limits preserve native settings and expose unsupported tuning."""

import json
import os
from pathlib import Path
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import host_config


class AdditionalConcurrencyTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="orchflows-concurrency-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.zcode = self.root / ".zcode/cli/config.json"
        self.kimi = self.root / "kimi/config.toml"
        self.grok = self.root / "grok/config.toml"
        for context in (
            patch.object(Path, "home", return_value=self.root),
            patch.dict(os.environ, {"KIMI_CODE_HOME": str(self.kimi.parent), "GROK_HOME": str(self.grok.parent),
                                   "ZCODE_HOME": str(self.root / "unused-zcode-root"),
                                   "ZCODE_MAX_TOOL_CONCURRENCY": "", "KIMI_CODE_BACKGROUND_MAX_RUNNING_TASKS": "",
                                   "GROK_MAX_CONCURRENT_SUBAGENTS": ""}),
        ):
            context.start()
            self.addCleanup(context.stop)

    def write(self, path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))

    def apply(self, host, value=7):
        results, issues = host_config.apply_host_configs(host_config.prepare_host_configs(value, (host,)))
        self.assertEqual(issues, [])
        return results[host]

    def test_new_zcode_and_kimi_files_use_native_paths_and_leave_siblings_absent(self):
        for host, path, section, key, loader in (
            ("zcode", self.zcode, "toolConcurrency", "maxConcurrency", json.loads),
            ("kimi", self.kimi, "background", "max_running_tasks", tomllib.loads),
        ):
            with self.subTest(host=host):
                result = self.apply(host)
                self.assertEqual(result["status"], "created")
                self.assertEqual(result["path"], str(path))
                self.assertEqual(loader(path.read_text())[section][key], 7)
        for sibling in (".codex", ".claude", "grok", "unused-zcode-root"):
            self.assertFalse((self.root / sibling).exists())

    def test_preservation_backup_and_repeat_for_each_host(self):
        originals = {
            "zcode": (self.zcode, '{"plugins":{"enabled":["keep"]},"toolConcurrency":{"maxConcurrency":2,"other":true}}\n'),
            "kimi": (self.kimi, '# keep\r\n[background]\r\nmax_running_tasks = 2 # limit\r\nkeep = "yes"\r\n'),
            "grok": (self.grok, '# keep\n[subagents]\nenabled = false\nlimit_behavior = "fail"\nmax_concurrent = 2\n'),
        }
        for host, (path, original) in originals.items():
            with self.subTest(host=host):
                self.write(path, original)
                result = self.apply(host)
                self.assertEqual(Path(result["backup"]).read_bytes(), original.encode())
                loader = json.loads if host == "zcode" else tomllib.loads
                before, after = loader(original), loader(path.read_text())
                section, key = result["setting"].split(".")
                before[section][key] = 7
                self.assertEqual(after, before)
                snapshot = (path.read_bytes(), path.stat().st_mtime_ns, list(path.parent.glob("*.bak")))
                self.assertEqual(self.apply(host)["status"], "unchanged")
                self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns, list(path.parent.glob("*.bak"))), snapshot)

    def test_zcode_boolean_and_float_limits_become_integers(self):
        for value in (True, 1.0):
            with self.subTest(value=value):
                self.write(self.zcode, json.dumps({"toolConcurrency": {"maxConcurrency": value}}))
                self.apply("zcode", 1)
                actual = json.loads(self.zcode.read_text())["toolConcurrency"]["maxConcurrency"]
                self.assertIs(type(actual), int)
                self.assertEqual(actual, 1)

    def test_kimi_synchronizes_existing_preferred_limit_in_either_table_order(self):
        for tables in (("background", "task"), ("task", "background")):
            with self.subTest(tables=tables):
                original = '[other]\nmax_running_tasks = 99\n' + ''.join(
                    f'[{table}] # keep\nmax_running_tasks = {index + 2}\nkeep = true\n'
                    for index, table in enumerate(tables))
                self.write(self.kimi, original)
                self.apply("kimi")
                parsed = tomllib.loads(self.kimi.read_text())
                self.assertEqual(parsed["other"]["max_running_tasks"], 99)
                for table in tables:
                    self.assertEqual(parsed[table], {"max_running_tasks": 7, "keep": True})

    def test_kimi_adds_legacy_limit_without_inventing_a_preferred_override(self):
        self.write(self.kimi, '[task]\nkeep = true\n')
        self.apply("kimi")
        self.assertEqual(tomllib.loads(self.kimi.read_text()),
                         {"task": {"keep": True}, "background": {"max_running_tasks": 7}})

    def test_grok_preserves_explicit_enabled_and_disabled_states(self):
        for enabled in (True, False):
            with self.subTest(enabled=enabled):
                self.write(self.grok, f'[subagents]\nenabled = {str(enabled).lower()}\n')
                self.apply("grok")
                self.assertEqual(tomllib.loads(self.grok.read_text())["subagents"],
                                 {"enabled": enabled, "max_concurrent": 7})

    def test_grok_does_not_infer_or_change_enablement(self):
        for original in (None, '# no section\n', '[subagents]\nlimit_behavior = "queue"\n'):
            with self.subTest(original=original):
                if original is not None:
                    self.write(self.grok, original)
                with self.assertRaisesRegex(ValueError, "explicit.*enabled"):
                    host_config.prepare_host_configs(7, ("grok",))
                self.assertEqual(self.grok.read_text() if self.grok.exists() else None, original)
                self.assertEqual(list(self.root.rglob("*.bak")), [])

    def test_malformed_configs_and_unsupported_layouts_are_preserved(self):
        for host, path, original in (
            ("zcode", self.zcode, '{"toolConcurrency":null}'),
            ("zcode", self.zcode, '{"toolConcurrency":{"maxConcurrency":2,"maxConcurrency":3}}'),
            ("zcode", self.zcode, '{"custom":NaN}'),
            ("kimi", self.kimi, 'task = 3\n'),
            ("kimi", self.kimi, '[background]\nmax_running_tasks = 2\nmax_running_tasks = 3\n'),
            ("kimi", self.kimi, 'background = { max_running_tasks = 2 }\n'),
            ("grok", self.grok, '[subagents]\nenabled = "true"\n'),
        ):
            with self.subTest(host=host, original=original):
                self.write(path, original)
                with self.assertRaises(ValueError):
                    host_config.prepare_host_configs(7, (host,))
                self.assertEqual(path.read_bytes(), original.encode())
                self.assertEqual(list(self.root.rglob("*.bak")), [])

    def test_environment_overrides_are_not_misreported_as_success(self):
        for host, variable in (("zcode", "ZCODE_MAX_TOOL_CONCURRENCY"),
                               ("kimi", "KIMI_CODE_BACKGROUND_MAX_RUNNING_TASKS"),
                               ("grok", "GROK_MAX_CONCURRENT_SUBAGENTS")):
            for value in ("3", "invalid"):
                with self.subTest(host=host, value=value), patch.dict(os.environ, {variable: value}):
                    with self.assertRaisesRegex(ValueError, variable):
                        host_config.prepare_host_configs(7, (host,))
            self.assertEqual(list(self.root.iterdir()), [])
        with patch.dict(os.environ, {"ZCODE_MAX_TOOL_CONCURRENCY": "7"}):
            self.assertEqual(self.apply("zcode")["status"], "created")

    def test_unverified_host_is_not_silently_ignored(self):
        with self.assertRaisesRegex(ValueError, "No verified concurrency"):
            host_config.prepare_host_configs(7, ("agy",))
        self.assertEqual(list(self.root.iterdir()), [])

    def test_out_of_range_native_integers_are_rejected_before_writing(self):
        for host, value in (("zcode", 2**53), ("kimi", 2**53), ("grok", 2**63)):
            with self.subTest(host=host), self.assertRaisesRegex(ValueError, "integer range"):
                host_config.prepare_host_configs(value, (host,))
        self.assertEqual(list(self.root.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
