"""Observable transcript parity: retained captions, typed failures, bounded fallback."""

from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import inspect_source as source
import inspect_youtube as youtube
from super_research import transport

FIXTURES = Path(__file__).parent / "fixtures" / "youtube"
VIDEO = "7pQm3nXkT2a"


class TranscriptTests(unittest.TestCase):
    def fake_download(self, status=0, timeout=False, track_metadata=None):
        def run(args, **kwargs):
            self.assertIn("--ignore-config", args)
            self.assertIn("--no-cookies", args)
            self.assertIn("--no-cookies-from-browser", args)
            self.assertIn("--no-plugin-dirs", args)
            self.assertIn("--no-playlist", args)
            self.assertIn("--skip-download", args)
            self.assertEqual(args[args.index("--extractor-args") + 1], "youtube:player_client=android")
            for option in ("--retries", "--extractor-retries", "--fragment-retries", "--file-access-retries"):
                self.assertEqual(args[args.index(option) + 1], "0")
            directory = Path(args[args.index("-o") + 1]).parent
            (directory / (VIDEO + ".en.vtt")).write_bytes((FIXTURES / "inspection.vtt").read_bytes())
            (directory / (VIDEO + ".info.json")).write_text(json.dumps({
                "id": VIDEO, "upload_date": "20260910", "title": "Fixture caption", "channel": "Fixture",
                **(track_metadata or {})}))
            if timeout:
                raise subprocess.TimeoutExpired(args, kwargs["timeout"])
            if status:
                kwargs["stderr"].write(b"ERROR: HTTP Error 429: Too Many Requests")
            return SimpleNamespace(returncode=status)
        return run

    def test_completed_caption_survives_later_failure_or_timeout(self):
        for code, timeout, expected in ((0, False, "ok"), (1, False, "rate_limited"), (0, True, "timeout")):
            with self.subTest(code=code, timeout=timeout), tempfile.TemporaryDirectory() as directory:
                result = youtube.read_ytdlp(VIDEO, "en", directory, 10, command=["yt-dlp"],
                                             run=self.fake_download(code, timeout))
                self.assertEqual(result["status"], "ok")
                self.assertEqual(result["process_status"], expected)
                self.assertEqual(result["text"], "Hello & welcome.\nAnother thought.\nHello & welcome.")
                self.assertEqual(result["metadata"]["upload_date"], "20260910")
                self.assertIn("00:00:05.000", result["_raw_caption"])

    def test_missing_executable_is_not_no_captions(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(youtube.read_ytdlp(VIDEO, "en", directory, 10, command=[])["status"],
                             "dependency_missing")

    def test_empty_successful_extractor_is_only_no_matching_captions(self):
        with tempfile.TemporaryDirectory() as directory:
            result = youtube.read_ytdlp(VIDEO, "en", directory, 10, command=["yt-dlp"],
                                        run=lambda *a, **k: SimpleNamespace(returncode=0))
            self.assertEqual(result["status"], "no_matching_captions")

    def test_innertube_handoff_retains_track_metadata_in_public_packet(self):
        calls = []
        def opener(request):
            calls.append(request)
            fixture = "player_with_caption_tracks.json" if len(calls) == 1 else "timedtext_json3.json"
            return 200, (FIXTURES / fixture).read_text(), "application/json"
        result = youtube.read_innertube(VIDEO, "en", opener=opener)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["requests"], 2)
        self.assertEqual(calls[0].route_id, transport.YOUTUBE_INNERTUBE_ROUTE)
        self.assertEqual(calls[1].route_id, transport.YOUTUBE_TIMEDTEXT_ROUTE)
        self.assertIn("SpaceX", result["text"])
        self.assertEqual(result["metadata"]["published_at"], "2026-07-04")
        packet = source.inspect(VIDEO, ytdlp_read=lambda *a: {"status": "dependency_missing"},
                                run=lambda *a, **k: SimpleNamespace(returncode=0, stdout=json.dumps(result).encode()))
        self.assertEqual(packet["caption_track"], {
            "language": "en", "kind": "asr", "automatic": True, "cue_count": 3, "duration_ms": 1155720})

    def test_ytdlp_public_track_status_requires_selected_url_match(self):
        selected = {"url": "https://www.youtube.com/api/timedtext?v=" + VIDEO + "&lang=en", "ext": "vtt"}
        cases = (
            ({"requested_subtitles": {"en": selected}, "automatic_captions": {"en": [selected]}}, None, True),
            ({"requested_subtitles": {"en": selected}, "subtitles": {"en": [selected]}}, None, False),
            ({"requested_subtitles": {"en": selected}, "subtitles": {"en": [selected]},
              "automatic_captions": {"en": [selected]}}, None, None),
            ({"requested_subtitles": {"en": {"url": "https://example.invalid/other"}},
              "automatic_captions": {"en": [selected]}}, None, None),
            ({"automatic_captions": {"en": [selected]}}, None, None),
        )
        for metadata, kind, automatic in cases:
            with self.subTest(metadata=metadata):
                def read(*args):
                    return youtube.read_ytdlp(*args, command=["yt-dlp"],
                                              run=self.fake_download(track_metadata=metadata))
                packet = source.inspect(VIDEO, ytdlp_read=read)
                track = packet["caption_track"]
                self.assertEqual(track["language"], "en")
                self.assertEqual(track.get("kind"), kind)
                self.assertIs(track["automatic"], automatic)
                self.assertEqual(track["cue_count"], 3)
                self.assertEqual(track["duration_ms"], 6000)

    def test_translation_of_manual_captions_does_not_become_asr(self):
        language = "en-es"
        selected = {"url": "https://www.youtube.com/api/timedtext?v=" + VIDEO + "&lang=es&tlang=en"}
        metadata = {"requested_subtitles": {language: selected},
                    "automatic_captions": {language: [selected]}}
        def read(*args):
            return youtube.read_ytdlp(*args, command=["yt-dlp"],
                                      run=self.fake_download(track_metadata=metadata))
        packet = source.inspect(VIDEO, language=language, ytdlp_read=read)
        self.assertIs(packet["caption_track"]["automatic"], True)
        self.assertNotIn("kind", packet["caption_track"])

    def test_public_track_omits_arbitrary_or_unbounded_attributes(self):
        packet = source.inspect(VIDEO, ytdlp_read=lambda *a: {
            "status": "ok", "text": "Caption", "attributes": {
                "languageCode": "en" * 10000, "kind": "asr" * 10000,
                "cue_count": True, "duration_ms": "9" * 16, "arbitrary": {"untrusted": "value"}}})
        self.assertEqual(packet["caption_track"], {"automatic": None})
        self.assertNotIn("attributes", packet)

    def test_empty_http_200_caption_is_failure_not_video_text(self):
        calls = []
        def opener(request):
            calls.append(request)
            return 200, ((FIXTURES / "player_with_caption_tracks.json").read_text() if len(calls) == 1 else ""), "application/json"
        result = youtube.read_innertube(VIDEO, "en", opener=opener)
        self.assertEqual(result["status"], "unavailable")
        self.assertNotIn("text", result)
        self.assertIn("malformed_json", result["pages"][-1]["loss"])

    def test_fallback_receives_only_remaining_wall_budget(self):
        moment = [0.0]
        def first(*args):
            moment[0] = 30
            return {"status": "rate_limited"}
        def fallback(args, **kwargs):
            self.assertEqual(kwargs["timeout"], 15)
            moment[0] = 45
            raise subprocess.TimeoutExpired(args, kwargs["timeout"])
        result = source.inspect(VIDEO, timeout_seconds=45, clock=lambda: moment[0], ytdlp_read=first, run=fallback)
        self.assertEqual([row["status"] for row in result["attempts"]], ["rate_limited", "timeout"])
        self.assertEqual(result["elapsed_seconds"], 45)
        self.assertFalse(result["audience_opinion"])

    def test_success_skips_fallback_and_marks_truncation(self):
        def fallback(*args, **kwargs):
            self.fail("a retained caption must not trigger more reads")
        result = source.inspect(VIDEO, max_chars=4, ytdlp_read=lambda *a: {
            "status": "ok", "text": "one two three", "metadata": {}}, run=fallback)
        self.assertEqual(result["text"], "one ")
        self.assertTrue(result["truncated"])
        self.assertEqual(len(result["attempts"]), 1)
        self.assertEqual(result["publication"]["precision"], "unknown")

    def test_exhausted_deadline_never_starts_fallback(self):
        moment = [0.0]
        def first(*args):
            moment[0] = 45
            return {"status": "timeout"}
        with patch.object(source.subprocess, "run") as fallback:
            result = source.inspect(VIDEO, clock=lambda: moment[0], ytdlp_read=first, run=fallback)
            fallback.assert_not_called()
        self.assertEqual(result["fallback_skipped"], "deadline")
        self.assertEqual(len(result["attempts"]), 1)

    def test_missing_optional_dependency_can_use_public_fallback(self):
        result = source.inspect(VIDEO, ytdlp_read=lambda *a: {"status": "dependency_missing"},
                                run=lambda *a, **k: SimpleNamespace(returncode=0, stdout=json.dumps({
                                    "status": "ok", "text": "Public caption", "metadata": {}}).encode()))
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["backend"], "youtube_innertube")
        self.assertEqual(result["attempts"][0]["status"], "dependency_missing")

    def test_oversized_support_is_typed_and_not_retained(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(youtube, "MAX_BYTES", 10):
            result = youtube.read_ytdlp(VIDEO, "en", directory, 10, command=["yt-dlp"], run=self.fake_download())
            self.assertEqual(result["status"], "caption_too_large")
            self.assertNotIn("_raw_caption", result)


class SourceContractTests(unittest.TestCase):
    def test_single_video_url_normalization_removes_playlist_and_comment_arguments(self):
        for url in (VIDEO, "https://youtu.be/" + VIDEO, "https://www.youtube.com/watch?v=" + VIDEO + "&list=abc&lc=comment",
                    "https://youtube.com/shorts/" + VIDEO):
            self.assertEqual(source.video_id(url), VIDEO)
        for url in ("https://youtube.com.attacker.test/watch?v=" + VIDEO, "http://youtube.com/watch?v=" + VIDEO,
                    "https://user@youtube.com/watch?v=" + VIDEO, "https://youtube.com/playlist?list=x", "--exec=anything"):
            with self.assertRaises(ValueError):
                source.video_id(url)

    def test_day_precision_cannot_establish_inside_at_exact_cutoff(self):
        start, end = source.instant("2026-08-12T14:56:12Z"), source.instant("2026-09-11T14:56:12Z")
        cases = (("20260812", "boundary_uncertain"), ("20260911", "boundary_uncertain"),
                 ("20260910", "inside"), ("20260912", "outside"), (None, "unknown"))
        for day, relation in cases:
            self.assertEqual(source.date_relation(source.publication({"upload_date": day}), start, end), relation)
        exact_end = source.publication({"timestamp": end.timestamp()})
        self.assertEqual(source.date_relation(exact_end, start, end), "outside")
        native_day = source.publication({"published_at": "2026-08-13"})
        self.assertEqual(native_day["timezone"], "unspecified")
        self.assertEqual(source.date_relation(native_day, start, end), "boundary_uncertain")

    def test_bad_arguments_fail_before_any_backend_runs(self):
        for flags in (["--timeout-seconds", "0"], ["--timeout-seconds", "nan"], ["--max-chars", "0"],
                      ["--language", "en,all"], ["--window-start", "2026-09-01"],
                      ["--start-date", "2026-09-11", "--end-date", "2026-09-01"]):
            with self.subTest(flags=flags), patch.object(source, "inspect") as call, redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    source.main(["youtube-transcript", "--url", VIDEO, "--output", "unused.json"] + flags)
                self.assertEqual(error.exception.code, 2)
                call.assert_not_called()

    def test_cli_writes_inspectable_support_and_receipt_even_for_empty_window_match(self):
        raw = (FIXTURES / "inspection.vtt").read_text()
        fake = {"status": "ok", "backend": "yt-dlp", "text": "Fixture", "caption_format": "vtt",
                "publication": source.publication({}), "_raw_caption": raw}
        with tempfile.TemporaryDirectory() as directory, patch.object(source, "inspect", return_value=fake), redirect_stdout(io.StringIO()):
            output = Path(directory) / "evidence.json"
            code = source.main(["youtube-transcript", "--url", VIDEO, "--output", str(output),
                                "--start-date", "2026-09-01", "--end-date", "2026-09-11"])
            result = json.loads(output.read_text())
            self.assertEqual(code, 0)
            self.assertEqual(result["date_relation"], "unknown")
            self.assertEqual(Path(result["caption_support"]).read_text(), raw)
            self.assertNotIn("_raw_caption", result)


if __name__ == "__main__":
    unittest.main()
