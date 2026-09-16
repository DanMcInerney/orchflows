"""Named black-box functional assertions, using only the documented interface."""

from concurrent.futures import ThreadPoolExecutor
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

from oracle import expected, small_rows, write_archive


def equal(actual, wanted):
    assert isinstance(actual, dict) and set(actual) == {"total", "items"}, "bad result shape"
    assert type(actual["total"]) is int and isinstance(actual["items"], list), "bad result types"
    assert actual == wanted, f"answer mismatch: wanted {wanted!r}, got {actual!r}"


def raises(kind, call):
    try:
        call()
    except kind:
        return
    raise AssertionError("expected " + kind.__name__)


def check_contract(search, project, scratch, record):
    rows = small_rows()
    path = scratch / "small.ndjson"
    write_archive(path, rows)

    def queries(*cases):
        for options in cases:
            equal(search(path, **options), expected(rows, **options))

    record("tokens_and_case", lambda: queries(dict(query="GATEWAY TIMEOUT"), dict(query="error timeout")))
    record("tokens_whole_words", lambda: queries(dict(query="err"), dict(query="gate"), dict(query="timeout2")))
    record("tokens_punctuation_repeat_empty", lambda: queries(dict(query="ERROR-timeout error"), dict(query="!!!"), dict(query="")))
    record("tokens_ascii_unicode_boundaries", lambda: queries(dict(query="caf"), dict(query="straße"), dict(query="foo_bar"), dict(query="K"), dict(query="İ")))
    record("service_filter_exact", lambda: queries(dict(service="api"), dict(service="API"), dict(service=""), dict(service="missing")))
    record("level_filter_exact", lambda: queries(dict(level="ERROR"), dict(level="error"), dict(level="")))
    record("bounds_half_open_and_combined", lambda: queries(
        dict(since="2026-07-14T10:02:00.000Z", until="2026-07-14T10:02:00.001Z"),
        dict(query="gateway", service="api", level="ERROR", since="2026-07-14T10:00:00.000Z", until="2026-07-14T10:02:00.001Z"),
        dict(since="2026-07-14T10:02:00.000Z", until="2026-07-14T10:02:00.000Z")))
    record("chronological_source_order_ties_duplicates", lambda: queries(dict(limit=999)))
    record("pagination_total_and_edges", lambda: queries(dict(offset=2, limit=3), dict(offset=1, limit=0), dict(offset=999, limit=5)))

    def malformed():
        corrupt = [None, [], 3, "text", {}, dict(rows[0], id=""), dict(rows[0], service=7),
                   dict(rows[0], level=""), dict(rows[0], message=None),
                   dict(rows[0], timestamp="2026-02-30T00:00:00.000Z"),
                   dict(rows[0], timestamp="2026-07-14T10:00:60.000Z"),
                   dict(rows[0], timestamp="2026-07-14T10:00:00Z"),
                   dict(rows[0], timestamp="0000-01-01T00:00:00.000Z")]
        absent = dict(rows[0]); absent.pop("message"); corrupt.append(absent)
        oldest = dict(rows[0], id="oldest", timestamp="0001-01-01T00:00:00.000Z")
        latest = dict(rows[0], id="latest", timestamp="9999-12-31T23:59:59.999Z")
        all_rows = rows + corrupt + [oldest, latest]
        target = scratch / "malformed.ndjson"
        write_archive(target, all_rows, ("", " ", "broken json", '{"id":'))
        equal(search(target, limit=999), expected(all_rows, limit=999))
    record("malformed_lines_skipped_extras_preserved", malformed)

    def bad_args(values, kind):
        for options in values:
            raises(kind, lambda options=options: search(path, **options))
    record("errors_query_and_filter_types", lambda: bad_args(
        [dict(query=None), dict(query=12), dict(service=2), dict(level=[])], TypeError))
    record("errors_timestamp_types", lambda: bad_args([dict(since=1), dict(until=False)], TypeError))
    record("errors_timestamp_values", lambda: bad_args([
        dict(since="2026-02-30T00:00:00.000Z"), dict(until="2026-07-14T10:00:00Z"),
        dict(since="2026-07-14T10:00:00.000+00:00"), dict(until="yesterday"),
        dict(since="2026-07-15T00:00:00.000Z", until="2026-07-14T00:00:00.000Z")], ValueError))
    record("errors_pagination_types", lambda: bad_args([dict(limit=True), dict(offset=False), dict(limit=1.0), dict(offset="1")], TypeError))
    record("errors_pagination_negative", lambda: bad_args([dict(limit=-1), dict(offset=-1)], ValueError))
    record("errors_path_types", lambda: [raises(TypeError, lambda value=value: search(value)) for value in (3, None, b"path")])
    record("errors_missing_archive", lambda: raises(FileNotFoundError, lambda: search(scratch / "missing.ndjson")))

    def mutation():
        answer = search(path, limit=999)
        next(row for row in answer["items"] if row["id"] == "z")["nested"]["tags"].append("changed")
        answer["items"].clear()
        equal(search(path, limit=999), expected(rows, limit=999))
    record("returned_objects_owned_by_caller", mutation)

    def append():
        target = scratch / "append.ndjson"
        write_archive(target, rows[:2]); search(target)
        with target.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(rows[2]) + "\n")
        equal(search(target), expected(rows[:3]))
    record("freshness_append", append)

    def truncate():
        target = scratch / "truncate.ndjson"
        write_archive(target, rows); search(target)
        write_archive(target, rows[:1])
        equal(search(target), expected(rows[:1]))
        write_archive(target, [])
        equal(search(target), {"total": 0, "items": []})
    record("freshness_truncate_and_empty", truncate)

    def replace_same_size():
        target = scratch / "replace.ndjson"
        before = [dict(rows[0], id="old")]
        after = [dict(rows[0], id="new")]
        write_archive(target, before); search(target)
        stat = target.stat()
        swap = scratch / "replacement.tmp"
        write_archive(swap, after)
        assert stat.st_size == swap.stat().st_size
        os.utime(swap, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        os.replace(swap, target)
        equal(search(target), expected(after))
    record("freshness_same_size_rotation_preserved_mtime", replace_same_size)

    def isolation():
        other = scratch / "other.ndjson"
        write_archive(other, rows[3:5])
        equal(search(other), expected(rows[3:5]))
        equal(search(str(path)), expected(rows))
    record("archives_and_pathlike_isolation", isolation)

    def concurrent_reload():
        target = scratch / "concurrent.ndjson"
        options = [dict(query="gateway"), dict(level="ERROR"), dict(limit=1, offset=1), dict(query="")] * 6
        for selected in (rows, list(reversed(rows[:5]))):
            write_archive(target, selected)
            with ThreadPoolExecutor(max_workers=12) as pool:
                actual = list(pool.map(lambda opts: search(target, **opts), options))
            for result, opts in zip(actual, options):
                equal(result, expected(selected, **opts))
    record("concurrent_cold_reads_and_reloads", concurrent_reload)

    def concurrent_rotation():
        target = scratch / "rotating.ndjson"
        versions = [[dict(row, id=f"{prefix}{index}") for index, row in enumerate(rows)] for prefix in ("a", "b")]
        answers = [expected(version, limit=999) for version in versions]
        write_archive(target, versions[0]); search(target)
        barrier = threading.Barrier(7)
        def reader(_):
            barrier.wait(timeout=10)
            for _ in range(20):
                for attempt in range(200):
                    try:
                        result = search(target, limit=999)
                        break
                    except PermissionError:
                        # Windows may briefly reject opens while os.replace marks
                        # the old file for deletion. Ordinary OS errors are allowed
                        # by the public contract; check every successful snapshot.
                        if os.name != "nt" or attempt == 199:
                            raise
                        time.sleep(0.005)
                assert result in answers, "mixed or corrupt snapshot during rotation"
        def writer():
            barrier.wait(timeout=10)
            for i in range(12):
                swap = scratch / f"swap-{i}.tmp"
                write_archive(swap, versions[i % 2])
                for attempt in range(200):
                    try:
                        os.replace(swap, target)
                        break
                    except PermissionError:
                        if attempt == 199:
                            raise
                        time.sleep(0.005)
                time.sleep(0.001)
        with ThreadPoolExecutor(max_workers=7) as pool:
            futures = [pool.submit(reader, i) for i in range(6)] + [pool.submit(writer)]
            for future in futures:
                future.result(timeout=30)
        equal(search(target, limit=999), answers[1])
    record("concurrent_atomic_rotation_snapshot_consistency", concurrent_rotation)

    def cli():
        args = [sys.executable, "-B", str(project / "log_archive.py"), "--file", str(path),
                "--query", "gateway", "--service", "api", "--level", "ERROR",
                "--since", "2026-07-14T10:00:00.000Z", "--until", "2026-07-14T10:04:00.000Z",
                "--limit", "1", "--offset", "1"]
        process = subprocess.run(args, capture_output=True, text=True, timeout=20, cwd=scratch)
        assert process.returncode == 0, process.stderr
        equal(json.loads(process.stdout), expected(rows, query="gateway", service="api", level="ERROR",
              since="2026-07-14T10:00:00.000Z", until="2026-07-14T10:04:00.000Z", limit=1, offset=1))
    record("cli_search_parity", cli)

    def cli_errors():
        base = [sys.executable, "-B", str(project / "log_archive.py")]
        help_run = subprocess.run(base + ["--help"], capture_output=True, text=True, timeout=20, cwd=scratch)
        assert help_run.returncode == 0 and help_run.stdout.strip()
        for args in (["--file", str(path), "--limit", "-1"], ["--file", str(scratch / "absent")],
                     ["--file", str(path), "--since", "bad"]):
            run = subprocess.run(base + args, capture_output=True, text=True, timeout=20, cwd=scratch)
            assert run.returncode != 0 and run.stderr.strip() and "Traceback" not in run.stderr
    record("cli_help_and_useful_errors", cli_errors)
