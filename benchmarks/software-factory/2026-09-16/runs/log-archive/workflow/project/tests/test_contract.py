"""Observable API edge cases, validated independently of the index design."""

from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import random
import tempfile
import unittest

import baseline_reference
from log_archive import search_logs


def record(identifier="a", stamp="2026-07-01T00:00:00.000Z", message="ready", **extra):
    return dict(id=identifier, timestamp=stamp, service="api", level="INFO",
                message=message, **extra)


def write_records(path, records):
    path.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n"
                            for item in records), encoding="utf-8")


class ArchiveContract(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "archive.ndjson"

    def test_ascii_whole_tokens_and_literal_punctuation(self):
        items = [record("a", message="ERROR-timeout error"),
                 record("b", message="error_timeOut timeout"),
                 record("c", message="terror timeout"),
                 record("d", message="éERRORé ßTIMEOUTß 東京"),
                 record("e", message="İERROK timeout"),
                 record("f", message="")]
        write_records(self.path, items)
        for query, identifiers in [("error TIMEOUT", ["a", "d"]),
                                   ("error error", ["a", "d"]),
                                   ("error_timeout", ["b"]),
                                   ("err", []), ("東京—!?", list("abcdef")),
                                   ("'error' + timeout*", ["a", "d"])]:
            with self.subTest(query=query):
                self.assertEqual([item["id"] for item in search_logs(self.path, query)["items"]],
                                 identifiers)

    def test_invalid_lines_dates_fields_and_complete_extras(self):
        valid = [record("early", "0001-01-01T00:00:00.000Z", "", extra={"x": [1, None]}),
                 record("leap", "2000-02-29T23:59:59.999Z"),
                 record("late", "9999-12-31T23:59:59.999Z")]
        invalid = [None, [], 1, "text", {}, True]
        for field in ("id", "service", "level", "message", "timestamp"):
            missing = record()
            missing.pop(field)
            invalid.append(missing)
            for wrong in (None, 1, True, [], {}):
                item = record()
                item[field] = wrong
                invalid.append(item)
        for field in ("id", "service", "level"):
            item = record()
            item[field] = ""
            invalid.append(item)
        bad_stamps = ["0000-01-01T00:00:00.000Z", "1900-02-29T00:00:00.000Z",
                      "2026-02-30T00:00:00.000Z", "2026-07-01T24:00:00.000Z",
                      "2026-07-01T00:60:00.000Z", "2026-07-01T00:00:60.000Z",
                      "2026-07-01T00:00:00.00Z", "2026-07-01T00:00:00.0000Z",
                      "2026-07-01T00:00:00.000+00:00", "2026-7-01T00:00:00.000Z",
                      "２０２６-07-01T00:00:00.000Z", "2026-07-01T00:00:00.000Z\n"]
        invalid.extend(record(stamp=stamp) for stamp in bad_stamps)
        write_records(self.path, invalid + valid)
        with self.path.open("a", encoding="utf-8") as archive:
            archive.write("\n{broken\n{\"id\": \n")
        self.assertEqual(search_logs(self.path, limit=100), {"total": 3, "items": valid})

    def test_stable_order_duplicates_bounds_filters_and_pagination(self):
        first = "2026-01-01T00:00:00.000Z"
        last = "2026-01-01T00:00:00.001Z"
        items = [record("z", last), record("same", first, "first"),
                 record("same", first, "second"), record("same", first, "first")]
        items[0]["service"] = "API"
        items[0]["level"] = "info"
        write_records(self.path, items)
        ordered = items[1:] + items[:1]
        self.assertEqual(search_logs(self.path)["items"], ordered)
        self.assertEqual(search_logs(self.path, since=first, until=last)["items"], items[1:])
        self.assertEqual(search_logs(self.path, since=last)["items"], items[:1])
        self.assertEqual(search_logs(self.path, since=first, until=first), {"total": 0, "items": []})
        self.assertEqual(search_logs(self.path, service="api", level="INFO")["total"], 3)
        self.assertEqual(search_logs(self.path, service="", level="INFO")["total"], 0)
        self.assertEqual(search_logs(self.path, service="API", level="info")["total"], 1)
        for limit, offset in [(0, 0), (1, 2), (1000, 0), (1000, 1000), (10 ** 100, 1)]:
            with self.subTest(limit=limit, offset=offset):
                self.assertEqual(search_logs(self.path, limit=limit, offset=offset),
                                 {"total": 4, "items": ordered[offset:offset + limit]})

    def test_argument_errors_and_pathlikes(self):
        write_records(self.path, [record()])
        for name in ("query", "service", "level", "since", "until"):
            for value in (False, 1, 1.5, [], {}, b"text"):
                with self.subTest(name=name, value=value), self.assertRaises(TypeError):
                    search_logs(self.path, **{name: value})
        with self.assertRaises(TypeError):
            search_logs(self.path, query=None)
        for name in ("limit", "offset"):
            for value in (None, False, True, 1.0, "1", []):
                with self.subTest(name=name, value=value), self.assertRaises(TypeError):
                    search_logs(self.path, **{name: value})
            with self.assertRaises(ValueError):
                search_logs(self.path, **{name: -1})
        for name in ("since", "until"):
            for value in ("", "yesterday", "2026-02-29T00:00:00.000Z"):
                with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                    search_logs(self.path, **{name: value})
        with self.assertRaises(ValueError):
            search_logs(self.path, since="2026-07-02T00:00:00.000Z", until="2026-07-01T00:00:00.000Z")
        for path in (None, 123, b"archive.ndjson", [], object()):
            with self.subTest(path=path), self.assertRaises(TypeError):
                search_logs(path)
        class BytesPath:
            def __fspath__(self):
                return b"archive.ndjson"
        with self.assertRaises(TypeError):
            search_logs(BytesPath())
        self.assertEqual(search_logs(self.path), search_logs(str(self.path)))
        for missing in (self.path.with_name("missing"), ""):
            with self.subTest(missing=missing), self.assertRaises(FileNotFoundError):
                search_logs(missing)

    def test_results_own_every_nested_object(self):
        original = record(extra={"array": [1, {"nested": ["untouched"]}]})
        write_records(self.path, [original, original])
        one = search_logs(self.path)
        one["items"][0]["extra"]["array"][1]["nested"].append("changed")
        one["items"][0]["id"] = "mutated"
        self.assertEqual(one["items"][1], original)
        one["items"].clear()
        one["total"] = -1
        self.assertEqual(search_logs(self.path), {"total": 2, "items": [original, original]})

    def test_completed_append_truncate_rewrite_and_replacement(self):
        old, new = record("old"), record("new")
        write_records(self.path, [old])
        self.assertEqual(search_logs(self.path)["items"], [old])
        with self.path.open("a", encoding="utf-8") as archive:
            archive.write(json.dumps(new) + "\n")
        self.assertEqual(search_logs(self.path)["items"], [old, new])
        write_records(self.path, [new])
        self.assertEqual(search_logs(self.path)["items"], [new])
        previous = self.path.stat()
        replacement = self.path.with_name("replacement")
        write_records(replacement, [old])
        self.assertEqual(replacement.stat().st_size, previous.st_size)
        os.utime(replacement, ns=(previous.st_atime_ns, previous.st_mtime_ns))
        os.replace(replacement, self.path)
        self.assertEqual(self.path.stat().st_mtime_ns, previous.st_mtime_ns)
        self.assertEqual(search_logs(self.path)["items"], [old])
        self.path.write_text("", encoding="utf-8")
        self.assertEqual(search_logs(self.path), {"total": 0, "items": []})
        self.path.unlink()
        with self.assertRaises(FileNotFoundError):
            search_logs(self.path)

    def test_separate_paths_and_cache_eviction_keep_correct_answers(self):
        for index in range(12):
            write_records(self.path.with_name(str(index)), [record(str(index))])
        for index in list(range(12)) + list(reversed(range(12))):
            self.assertEqual(search_logs(self.path.with_name(str(index)))["items"][0]["id"], str(index))

    def test_deterministic_varied_queries_match_reference(self):
        rng = random.Random(20260916)
        epoch = datetime(2026, 1, 1)
        items = []
        stamps = []
        for index in range(240):
            stamp = (epoch + timedelta(milliseconds=rng.randrange(30))).isoformat(timespec="milliseconds") + "Z"
            stamps.append(stamp)
            item = record(str(index % 31), stamp,
                          rng.choice(["ERROR-timeout gateway", "éerroré worker", "ready", "a_b C3", ""]))
            item.update(service=rng.choice(["api", "API", "jobs"]), level=rng.choice(["INFO", "ERROR"]),
                        extra={"n": [index]})
            items.append(item)
        write_records(self.path, items + [None, {}, record(stamp="bad")])
        for _ in range(60):
            start, end = sorted(rng.sample(stamps, 2))
            kwargs = dict(query=rng.choice(["", "error timeout", "ERROR", "a_b", "—", "missing"]),
                          service=rng.choice([None, "api", "jobs", ""]),
                          level=rng.choice([None, "INFO", "ERROR"]),
                          since=rng.choice([None, start]), until=rng.choice([None, end]),
                          limit=rng.choice([0, 1, 50, 1000]), offset=rng.randrange(10))
            with self.subTest(kwargs=kwargs):
                self.assertEqual(search_logs(self.path, **kwargs), baseline_reference.search_logs(self.path, **kwargs))


if __name__ == "__main__":
    unittest.main()
