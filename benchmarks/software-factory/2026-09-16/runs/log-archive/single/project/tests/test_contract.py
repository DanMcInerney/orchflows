"""Contract and reload regressions, including differential and concurrent reads."""

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from baseline_reference import search_logs as reference
import log_archive
from log_archive import search_logs


ROOT = Path(__file__).resolve().parents[1]
STAMP = "2026-07-01T00:00:00.000Z"


def record(identifier="a", **changes):
    item = dict(id=identifier, service="api", level="INFO", message="ready", timestamp=STAMP)
    item.update(changes)
    return item


def write(path, items):
    path.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in items),
                    encoding="utf-8")


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "archive.ndjson"

    def test_ascii_tokens_literal_and_matching(self):
        items = [record("a", message="ERROR-timeout foo_bar café İABC abKcd"),
                 record("b", message="error timeouts foo bar"),
                 record("c", message="")]
        write(self.path, items)
        for query, ids in [("ERROR timeout", ["a"]), ("err", []),
                           ("foo_bar", ["a"]), ("foo bar", ["b"]),
                           ("café", ["a"]), ("İABC", ["a"]),
                           ("abc", ["a"]), ("ab cd", ["a"]),
                           ("abkcd", []), ("error error", ["a", "b"]),
                           (".* OR", []), ("!!!", ["a", "b", "c"]),
                           ("é😀", ["a", "b", "c"]), ("", ["a", "b", "c"])]:
            with self.subTest(query=query):
                self.assertEqual([item["id"] for item in search_logs(self.path, query)["items"]], ids)

    def test_invalid_records_are_skipped_and_extras_preserved(self):
        valid = record(extra={"list": [1, {"a": True}, None]}, message="")
        invalid = [None, [], 3, "text", {}, record(id=""), record(service=""),
                   record(level=""), record(message=1), record(message=None)]
        for field in ("id", "service", "level", "message", "timestamp"):
            item = record()
            del item[field]
            invalid.append(item)
        for field in ("id", "service", "level"):
            invalid.extend(record(**{field: value}) for value in (None, 0, True, [], {}))
        invalid.extend(record(timestamp=value) for value in
                       (None, 1, "2026-02-29T00:00:00.000Z", "0000-01-01T00:00:00.000Z",
                        "2026-01-01T24:00:00.000Z", "2026-01-01T00:00:60.000Z",
                        "2026-01-01T00:00:00.0000Z", "2026-01-01T00:00:00.00Z",
                        "2026-01-01T00:00:00.000Z\n", "２０２６-01-01T00:00:00.000Z"))
        write(self.path, invalid + [valid])
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write("\n{bad json}\n   \n")
        self.assertEqual(search_logs(self.path), {"total": 1, "items": [valid]})

    def test_order_ties_duplicates_bounds_filters_and_pages(self):
        early = "0001-01-01T00:00:00.000Z"
        middle = "2000-02-29T12:59:59.999Z"
        late = "9999-12-31T23:59:59.999Z"
        items = [record("late", timestamp=late), record("duplicate", timestamp=middle),
                 record("early", timestamp=early), record("tie", timestamp=middle),
                 record("duplicate", timestamp=middle),
                 record("case", timestamp=middle, service="API", level="info")]
        write(self.path, items)
        ordered = [items[i] for i in (2, 1, 3, 4, 5, 0)]
        self.assertEqual(search_logs(self.path, limit=999)["items"], ordered)
        self.assertEqual(search_logs(self.path, since=middle, until=late, service="api", level="INFO"),
                         {"total": 3, "items": [items[i] for i in (1, 3, 4)]})
        self.assertEqual(search_logs(self.path, since=middle, until=middle), {"total": 0, "items": []})
        for filters in ({"service": ""}, {"level": ""}, {"service": "Api"}, {"level": "Info"}):
            self.assertEqual(search_logs(self.path, **filters)["total"], 0)
        for offset in (0, 1, 5, 6, 100, 10**100):
            for limit in (0, 1, 2, 100, 10**100):
                with self.subTest(offset=offset, limit=limit):
                    self.assertEqual(search_logs(self.path, limit=limit, offset=offset),
                                     {"total": 6, "items": ordered[offset:offset + limit]})

    def test_argument_errors_even_when_archive_empty(self):
        write(self.path, [])
        for field in ("query", "service", "level", "since", "until"):
            values = (1, True, [], {}, b"x") if field != "query" else (None, 1, True, [], b"x")
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaises(TypeError):
                    search_logs(self.path, **{field: value})
        for field in ("limit", "offset"):
            for value in (True, False, 1.0, "2", None, []):
                with self.subTest(field=field, value=value), self.assertRaises(TypeError):
                    search_logs(self.path, **{field: value})
            with self.assertRaises(ValueError):
                search_logs(self.path, **{field: -1})
        for value in ("", "yesterday", "2026-02-30T00:00:00.000Z", STAMP[:-1] + "+00:00"):
            for field in ("since", "until"):
                with self.assertRaises(ValueError):
                    search_logs(self.path, **{field: value})
        with self.assertRaises(ValueError):
            search_logs(self.path, since="2027-01-01T00:00:00.000Z", until=STAMP)
        class BytesPath:
            def __fspath__(self):
                return b"archive.ndjson"
        for path in (None, 1, b"archive.ndjson", BytesPath()):
            with self.assertRaises(TypeError):
                search_logs(path)
        with self.assertRaises(FileNotFoundError):
            search_logs(self.path.with_name("missing"))

    def test_mutation_cannot_change_future_results_or_duplicate_records(self):
        item = record(extra={"nested": [{"value": "original"}]})
        write(self.path, [item, item])
        first = search_logs(self.path)
        first["items"][0]["extra"]["nested"][0]["value"] = "changed"
        self.assertEqual(first["items"][1], item)
        first["items"][0]["message"] = "changed"
        first["items"].append({})
        first["total"] = -1
        self.assertEqual(search_logs(self.path), {"total": 2, "items": [item, item]})

    def test_warm_queries_do_not_reparse_unchanged_file(self):
        item = record()
        write(self.path, [item])
        # Distinguish creation time from modification time on Windows.
        os.utime(self.path, ns=(1600000000000000000, 1600000000000000000))
        expected = {"total": 1, "items": [item]}
        self.assertEqual(search_logs(self.path), expected)
        with patch.object(log_archive.json, "loads", side_effect=AssertionError("unexpected reparse")):
            self.assertEqual(search_logs(self.path, "ready", service="api"), expected)
            self.assertEqual(search_logs(self.path, limit=0), {"total": 1, "items": []})

    def test_completed_append_truncate_replace_and_deletion(self):
        a, b = record("a"), record("b")
        write(self.path, [a])
        self.assertEqual(search_logs(self.path)["items"], [a])
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(b) + "\n")
        self.assertEqual(search_logs(self.path)["items"], [a, b])
        write(self.path, [b])
        self.assertEqual(search_logs(self.path)["items"], [b])
        old = self.path.stat()
        replacement = self.path.with_name("replacement")
        write(replacement, [a])
        self.assertEqual(replacement.stat().st_size, old.st_size)
        os.utime(replacement, ns=(old.st_atime_ns, old.st_mtime_ns))
        os.replace(replacement, self.path)
        self.assertEqual(self.path.stat().st_mtime_ns, old.st_mtime_ns)
        self.assertEqual(search_logs(self.path)["items"], [a])
        self.path.write_text("", encoding="utf-8")
        self.assertEqual(search_logs(self.path), {"total": 0, "items": []})
        self.path.unlink()
        with self.assertRaises(FileNotFoundError):
            search_logs(self.path)

    def test_different_paths_and_relative_paths(self):
        second = self.path.with_name("second")
        write(self.path, [record("a")])
        write(second, [record("b")])
        self.assertEqual(search_logs(self.path)["items"][0]["id"], "a")
        self.assertEqual(search_logs(second)["items"][0]["id"], "b")
        original = os.getcwd()
        try:
            for directory, identifier in ((self.path.parent / "one", "a"),
                                          (self.path.parent / "two", "b")):
                directory.mkdir()
                write(directory / "logs", [record(identifier)])
                os.chdir(directory)
                self.assertEqual(search_logs("logs")["items"][0]["id"], identifier)
        finally:
            os.chdir(original)

    def test_concurrent_cold_load_and_reload(self):
        for version in ("old", "new"):
            items = [record(str(i), message=version) for i in range(150)]
            write(self.path, items)
            barrier = threading.Barrier(8)
            def search(_):
                barrier.wait(timeout=10)
                return search_logs(self.path, version, limit=1000)
            with ThreadPoolExecutor(max_workers=8) as pool:
                for result in pool.map(search, range(8)):
                    self.assertEqual(result, {"total": 150, "items": items})

    def test_replace_between_stat_and_open_uses_complete_version(self):
        write(self.path, [record("old")])
        replacement = self.path.with_name("replacement")
        items = [record("new"), record("new")]
        write(replacement, items)
        original_load = log_archive._load
        def replace_and_load(path):
            os.replace(replacement, self.path)
            return original_load(path)
        with patch.object(log_archive, "_load", side_effect=replace_and_load):
            self.assertEqual(search_logs(self.path), {"total": 2, "items": items})
        self.assertEqual(search_logs(self.path)["items"], items)

    def test_concurrent_atomic_replacements_never_mix_versions(self):
        count = 120
        def version(label):
            return [record(str(i), message=label) for i in range(count)]
        write(self.path, version("old"))
        search_logs(self.path)
        barrier = threading.Barrier(5)
        def read_many(_):
            barrier.wait(timeout=10)
            for _ in range(50):
                result = search_logs(self.path, limit=1000)
                self.assertEqual(result["total"], count)
                labels = {item["message"] for item in result["items"]}
                self.assertIn(labels, ({"old"}, {"new"}))
                self.assertEqual([item["id"] for item in result["items"]], [str(i) for i in range(count)])
        def replace_many():
            barrier.wait(timeout=10)
            for i in range(20):
                replacement = self.path.with_name("replacement")
                write(replacement, version("new" if i % 2 == 0 else "old"))
                old = self.path.stat()
                os.utime(replacement, ns=(old.st_atime_ns, old.st_mtime_ns))
                deadline = time.monotonic() + 10
                while True:
                    try:
                        os.replace(replacement, self.path)
                        break
                    except PermissionError:
                        # Windows can temporarily prohibit renames of open files.
                        if time.monotonic() >= deadline:
                            raise
                        time.sleep(0.001)
            self.assertEqual(search_logs(self.path)["items"][0]["message"], "old")
        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = [pool.submit(read_many, i) for i in range(4)] + [pool.submit(replace_many)]
            for future in futures:
                future.result(timeout=30)

    def test_seeded_differential_queries(self):
        rng = random.Random(37127)
        messages = ["error timeout retry", "ERROR-timeout", "café cat_2", "ready", "", "İABC abKcd"]
        stamps = [f"2026-07-{day:02d}T00:00:00.000Z" for day in range(1, 8)]
        items = [record(str(i % 50), timestamp=rng.choice(stamps), message=rng.choice(messages),
                        service=rng.choice(["api", "API", "worker"]), level=rng.choice(["INFO", "ERROR"]),
                        extra={"row": i, "nested": [i % 5, False, None]}) for i in range(320)]
        write(self.path, items + [None, {}, record(timestamp="invalid")])
        for _ in range(100):
            start, end = sorted(rng.sample(stamps, 2))
            kwargs = dict(query=rng.choice(messages + ["", "!!!", "absent", "time", "retry ERROR"]),
                          service=rng.choice([None, "api", "API", "", "unknown"]),
                          level=rng.choice([None, "INFO", "ERROR", ""]),
                          since=rng.choice([None, start]), until=rng.choice([None, end]),
                          limit=rng.choice([0, 1, 17, 500]), offset=rng.choice([0, 3, 100]))
            with self.subTest(kwargs=kwargs):
                self.assertEqual(search_logs(self.path, **kwargs), reference(self.path, **kwargs))

    def test_cli_success_help_and_useful_errors(self):
        write(self.path, [record(extra="café 😀")])
        def cli(*arguments):
            return subprocess.run([sys.executable, str(ROOT / "log_archive.py"), *arguments],
                                  capture_output=True, text=True, encoding="utf-8")
        result = cli("--file", str(self.path), "--query", "ready")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), search_logs(self.path))
        self.assertEqual(result.stderr, "")
        self.assertEqual(cli("--help").returncode, 0)
        for arguments in [("--file", str(self.path), "--limit", "-1"),
                          ("--file", str(self.path), "--offset", "two"),
                          ("--file", str(self.path), "--since", "yesterday"),
                          ("--file", str(self.path.with_name("missing"))), ()]:
            with self.subTest(arguments=arguments):
                result = cli(*arguments)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")
                self.assertIn("error", result.stderr.lower())
                self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
