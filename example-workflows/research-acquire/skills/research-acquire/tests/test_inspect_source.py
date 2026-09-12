"""The transcript reader runs yt-dlp once through an injected command; nothing here reaches the network."""

import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import inspect_source as reader

JSON3 = json.dumps({"events": [
    {"tStartMs": 1000, "dDurationMs": 2000, "segs": [{"utf8": "Hello"}, {"utf8": " & welcome", "tOffsetMs": 600}]},
    {"tStartMs": 2500, "dDurationMs": 100, "aAppend": 1, "segs": [{"utf8": "\n"}]},
    {"tStartMs": 4000, "dDurationMs": 2500, "segs": [{"utf8": "Second line"}]},
    {"tStartMs": 7000, "dDurationMs": 10, "segs": [{"utf8": "  "}]}]})
INFO = {"id": "dQw4w9WgXcQ", "title": "Sample", "channel": "Channel", "upload_date": "20260901", "timestamp": 1788264000,
        "subtitles": {}, "automatic_captions": {"en": [{"ext": "json3", "url": "https://www.youtube.com/api/timedtext?caps=asr"}]}}


def fake_run(files=None, returncode=0, stderr=b"", timeout=False):
    def run(args, **options):
        if timeout:
            raise subprocess.TimeoutExpired(args, options["timeout"])
        directory = Path(args[args.index("-o") + 1]).parent
        for name, content in (files or {}).items():
            (directory / name).write_text(content, encoding="utf-8")
        return subprocess.CompletedProcess(args, returncode, stdout=b"", stderr=stderr)
    return run


class TranscriptReaderTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="research-inspect-")
        self.addCleanup(temporary.cleanup)
        self.output = Path(temporary.name) / "evidence" / "caption.json"
        self.command = lambda: ["fake-yt-dlp"]

    def inspect(self, run, **options):
        return reader.inspect("dQw4w9WgXcQ", run=run, command=self.command, **options)

    def test_single_invocation_yields_text_track_metadata_and_publication(self):
        calls = []

        def run(args, **options):
            calls.append(args)
            return fake_run({"dQw4w9WgXcQ.en.json3": JSON3, "dQw4w9WgXcQ.info.json": json.dumps(INFO)})(args, **options)

        packet, raw = self.inspect(run)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][:1], ["fake-yt-dlp"])
        for flag in ("--no-playlist", "--no-cookies", "--ignore-config", "json3"):
            self.assertIn(flag, calls[0])
        self.assertEqual(packet["status"], "ok")
        self.assertEqual(packet["text"], "Hello & welcome\nSecond line")
        self.assertEqual(packet["caption_track"], {"language": "en", "automatic": True, "cue_count": 2, "duration_ms": 6500})
        self.assertEqual(packet["metadata"]["title"], "Sample")
        self.assertEqual(packet["publication"]["precision"], "instant")
        self.assertEqual(packet["caption_format"], "json3")
        self.assertEqual(len(packet["caption_sha256"]), 64)
        self.assertEqual(raw, JSON3)
        self.assertEqual(packet["bounds"]["invocations"], 1)

    def test_truncation_bounds_text_and_marks_it(self):
        packet, _ = self.inspect(fake_run({"dQw4w9WgXcQ.en.json3": JSON3}), max_chars=5)
        self.assertEqual(packet["text"], "Hello")
        self.assertTrue(packet["truncated"])
        self.assertEqual(packet["publication"], {"precision": "unknown"})
        self.assertIsNone(packet["caption_track"]["automatic"])

    def test_missing_or_empty_track_is_no_matching_captions(self):
        for files in ({}, {"dQw4w9WgXcQ.en.json3": '{"events": []}'}, {"dQw4w9WgXcQ.en.json3": '{"events": [{"tStartMs": 1, "dDurationMs": 1, "segs": [{"utf8": "\\n"}]}]}'}):
            with self.subTest(files=list(files.values())):
                packet, raw = self.inspect(fake_run(files))
                self.assertEqual(packet["status"], "no_matching_captions")
                self.assertEqual(packet["exit_code"], 0)
                self.assertIsNone(raw)
                self.assertNotIn("caption_sha256", packet)

    def test_failures_are_reported_never_retried(self):
        packet, _ = self.inspect(fake_run({"dQw4w9WgXcQ.en.json3": JSON3}, returncode=1, stderr=b"ERROR: HTTP Error 429: Too Many Requests"))
        self.assertEqual(packet["status"], "backend_error")
        self.assertEqual(packet["exit_code"], 1)
        self.assertIn("429", packet["stderr"])
        self.assertEqual(packet["text"], "")
        self.assertEqual(self.inspect(fake_run(timeout=True))[0]["status"], "timeout")
        self.assertEqual(reader.inspect("dQw4w9WgXcQ", run=fake_run(), command=lambda: None)[0]["status"], "dependency_missing")
        self.assertEqual(self.inspect(fake_run({"dQw4w9WgXcQ.en.json3": "x" * (reader.MAX_BYTES + 1)}))[0]["status"], "caption_too_large")
        for files in ({"dQw4w9WgXcQ.en.json3": JSON3, "dQw4w9WgXcQ.info.json": "{broken"}, {"dQw4w9WgXcQ.en.json3": "not json"}):
            with self.subTest(files=files):
                packet, _ = self.inspect(fake_run(files))
                self.assertEqual(packet["status"], "backend_error")
                self.assertIn("unreadable", packet["error"])

    def test_track_provenance_comes_from_which_collection_lists_the_language(self):
        self.assertIs(reader.track_automatic(INFO, "en"), True)
        self.assertIs(reader.track_automatic({**INFO, "subtitles": {"en": [{"ext": "json3"}]}}, "en"), False)
        self.assertIs(reader.track_automatic({"subtitles": {"fr": []}, "automatic_captions": {"fr": []}}, "en"), None)
        self.assertIs(reader.track_automatic({}, "en"), None)

    def test_video_ids_are_extracted_only_from_single_video_forms(self):
        for value in ("dQw4w9WgXcQ", "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PL1", "https://youtu.be/dQw4w9WgXcQ",
                      "https://m.youtube.com/shorts/dQw4w9WgXcQ", "https://www.youtube.com/live/dQw4w9WgXcQ"):
            self.assertEqual(reader.video_id(value), "dQw4w9WgXcQ", value)
        for value in ("http://www.youtube.com/watch?v=dQw4w9WgXcQ", "https://www.youtube.com/@channel", "https://www.youtube.com/playlist?list=PL1",
                      "https://example.com/watch?v=dQw4w9WgXcQ", "https://user:pw@youtu.be/dQw4w9WgXcQ", "short"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                reader.video_id(value)

    def test_date_relation_covers_every_case(self):
        start, end = reader.instant("2026-09-01T00:00:00Z"), reader.instant("2026-09-02T00:00:00Z")
        instant_inside = reader.publication({"timestamp": 1788264000})
        self.assertEqual(instant_inside["earliest"], "2026-09-01T12:00:00+00:00")
        self.assertEqual(reader.date_relation(instant_inside, start, end), "inside")
        self.assertEqual(reader.date_relation(reader.publication({"timestamp": 1756900000}), start, end), "outside")
        day = reader.publication({"upload_date": "20260901"})
        self.assertEqual(day["timezone"], "UTC")
        self.assertEqual(reader.date_relation(day, start, end), "inside")
        self.assertEqual(reader.date_relation(day, start, reader.instant("2026-09-01T12:00:00Z")), "boundary_uncertain")
        self.assertEqual(reader.date_relation(reader.publication({}), start, end), "unknown")
        self.assertEqual(reader.date_relation(instant_inside, None, None), "not_requested")
        self.assertEqual(reader.publication({"upload_date": "yesterday", "timestamp": float("nan")}), {"precision": "unknown"})

    def test_cli_writes_receipt_and_sidecar_and_exits_by_status(self):
        original = subprocess.run
        subprocess.run = fake_run({"dQw4w9WgXcQ.en.json3": JSON3, "dQw4w9WgXcQ.info.json": json.dumps(INFO)})
        self.addCleanup(setattr, subprocess, "run", original)
        original_command = reader.find_command
        reader.find_command = self.command
        self.addCleanup(setattr, reader, "find_command", original_command)
        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            code = reader.main(["youtube-transcript", "--url", "dQw4w9WgXcQ", "--output", str(self.output),
                                "--start-date", "2026-09-01", "--end-date", "2026-09-01"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout.getvalue())["status"], "ok")
        packet = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(packet["date_relation"], "inside")
        self.assertEqual(packet["window"], {"start": "2026-09-01T00:00:00+00:00", "end_exclusive": "2026-09-02T00:00:00+00:00"})
        self.assertEqual(Path(packet["caption_support"]).read_text(encoding="utf-8"), JSON3)
        self.assertTrue(packet["caption_support"].endswith(".json3"))
        subprocess.run = fake_run({})
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(reader.main(["youtube-transcript", "--url", "dQw4w9WgXcQ", "--output", str(self.output)]), 3)
        self.assertEqual(json.loads(self.output.read_text(encoding="utf-8"))["status"], "no_matching_captions")

    def test_usage_errors_write_nothing(self):
        inside = reader.PACKAGE / "references" / "caption.json"
        for arguments in (["--url", "https://www.youtube.com/@channel"], ["--language", "english"], ["--timeout-seconds", "0"],
                          ["--timeout-seconds", "121"], ["--max-chars", "0"], ["--window-start", "2026-09-01T00:00:00Z"],
                          ["--start-date", "2026-09-02", "--end-date", "2026-09-01"], ["--window-start", "2026-09-01T00:00:00", "--window-end", "2026-09-02T00:00:00Z"],
                          ["--start-date", "2026-09-01", "--end-date", "2026-09-02", "--window-end", "2026-09-02T00:00:00Z"]):
            with self.subTest(arguments=arguments), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
                reader.main(["youtube-transcript", "--url", "dQw4w9WgXcQ", "--output", str(self.output)] + arguments)
            self.assertEqual(raised.exception.code, 2)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            reader.main(["youtube-transcript", "--url", "dQw4w9WgXcQ", "--output", str(inside)])
        self.assertEqual(raised.exception.code, 2)
        self.assertFalse(self.output.exists())
        self.assertFalse(inside.exists())

    def test_reader_imports_nothing_from_the_acquisition_library(self):
        probe = subprocess.run([sys.executable, "-c", "import sys, inspect_source; print(sorted(m for m in sys.modules if m.startswith(('super_research', 'acquire'))))"],
                               capture_output=True, text=True, cwd=str(Path(reader.__file__).parent),
                               env={**os.environ, "PYTHONPATH": str(Path(reader.__file__).parent)}, check=True)
        self.assertEqual(probe.stdout.strip(), "[]")


if __name__ == "__main__":
    unittest.main()
