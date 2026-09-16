"""Concurrency and process-level JSON CLI contract tests."""

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import log_archive
from log_archive import search_logs
from test_contract import record, write_records


class ConcurrentArchives(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "archive.ndjson"

    def test_simultaneous_first_load_reload_and_result_mutation(self):
        for generation in range(3):
            items = [record(str(index), message=f"generation{generation}", extra={"values": [index]})
                     for index in range(180)]
            write_records(self.path, items)
            barrier = threading.Barrier(12)
            def read(index):
                barrier.wait(timeout=10)
                result = search_logs(self.path, limit=500)
                self.assertEqual(result, {"total": len(items), "items": items})
                result["items"][0]["extra"]["values"].append(index)
                return result["total"]
            with ThreadPoolExecutor(max_workers=12) as pool:
                self.assertEqual(list(pool.map(read, range(12))), [len(items)] * 12)
            self.assertEqual(search_logs(self.path, limit=500)["items"], items)

    def test_atomic_replacements_never_mix_versions(self):
        versions = [[record(f"{version}{index:03}", message=f"version{version}")
                     for index in range(100)] for version in ("a", "b")]
        write_records(self.path, versions[0])
        original = self.path.stat()
        failures = []
        start = threading.Barrier(7)
        def reader(_):
            start.wait(timeout=10)
            for _ in range(50):
                result = search_logs(self.path, limit=1000)
                if result not in [{"total": 100, "items": items} for items in versions]:
                    failures.append(result)
        def writer():
            start.wait(timeout=10)
            for index in range(30):
                replacement = self.path.with_name(f"replace-{index}")
                write_records(replacement, versions[index % 2])
                os.utime(replacement, ns=(original.st_atime_ns, original.st_mtime_ns))
                # Windows may briefly prohibit replacing a file opened by the
                # reader. Retry that OS contention; every successful operation
                # remains a single atomic replacement.
                for attempt in range(1000):
                    try:
                        os.replace(replacement, self.path)
                        break
                    except PermissionError:
                        time.sleep(0.001)
                else:
                    self.fail("atomic replacement stayed blocked")
                self.assertEqual(search_logs(self.path, limit=1000)["items"], versions[index % 2])
        with ThreadPoolExecutor(max_workers=7) as pool:
            futures = [pool.submit(reader, index) for index in range(6)] + [pool.submit(writer)]
            for future in futures:
                future.result(timeout=30)
        self.assertEqual(failures, [])

    def test_replacement_after_stat_before_open_is_coherent(self):
        old, new = [record("old")], [record("new")]
        write_records(self.path, old)
        replacement = self.path.with_name("replacement")
        write_records(replacement, new)
        real_stat = os.stat
        replaced = False
        def replace_after_stat(path, *args, **kwargs):
            nonlocal replaced
            result = real_stat(path, *args, **kwargs)
            if os.fspath(path) == str(self.path) and not replaced:
                replaced = True
                os.replace(replacement, self.path)
            return result
        with patch.object(log_archive.os, "stat", side_effect=replace_after_stat):
            self.assertEqual(search_logs(self.path)["items"], new)
        self.assertEqual(search_logs(self.path)["items"], new)


class CommandLine(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "unicode archive.ndjson"
        self.item = record(message="éERRORé timeout", extra={"nested": ["東京"]})
        write_records(self.path, [self.item])
        self.script = Path(log_archive.__file__).resolve()

    def invoke(self, *args):
        return subprocess.run([sys.executable, str(self.script), *args], capture_output=True,
                              text=True, encoding="utf-8", timeout=15)

    def test_cli_success_and_help(self):
        completed = self.invoke("--file", str(self.path), "--query", "ERROR timeout", "--limit", "1")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stderr, "")
        self.assertEqual(json.loads(completed.stdout), {"total": 1, "items": [self.item]})
        help_result = self.invoke("--help")
        self.assertEqual(help_result.returncode, 0)
        self.assertIn("--file", help_result.stdout)

    def test_cli_user_errors_are_useful_without_tracebacks(self):
        for args in [("--file", str(self.path), "--limit", "-1"),
                     ("--file", str(self.path), "--offset", "not-integer"),
                     ("--file", str(self.path), "--since", "bad-date"),
                     ("--file", str(self.path.with_name("missing"))), ()]:
            with self.subTest(args=args):
                completed = self.invoke(*args)
                self.assertNotEqual(completed.returncode, 0)
                self.assertEqual(completed.stdout, "")
                self.assertIn("error", completed.stderr.lower())
                self.assertNotIn("Traceback", completed.stderr)


if __name__ == "__main__":
    unittest.main()
