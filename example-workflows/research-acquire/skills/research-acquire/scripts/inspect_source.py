"""Read one known YouTube video's captions through a single yt-dlp invocation and save a receipt."""

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.parse import parse_qs, urlsplit

PACKAGE = Path(__file__).resolve().parents[3]
MAX_BYTES = 8 * 1024 * 1024
STDERR_TAIL = 2000
VIDEO_ID = re.compile(r"[A-Za-z0-9_-]{11}\Z")
LANGUAGE = re.compile(r"[a-zA-Z]{2,3}(?:-[a-zA-Z0-9]{2,8})?\Z")
LIMITATIONS = [
    "Captions represent video speech, not viewer comments; speaker identity is unverified.",
    "Caption text may repeat rolling captions or contain recognition errors.",
    "Publication time belongs to the video; the caption track has no independent publication date.",
]


def video_id(value):
    if VIDEO_ID.fullmatch(value):
        return value
    parsed = urlsplit(value)
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port:
        raise ValueError("expected an HTTPS YouTube video URL or 11-character video ID")
    host = parsed.hostname
    if host == "youtu.be":
        result = parsed.path.strip("/")
    elif host in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
        parts = parsed.path.strip("/").split("/")
        result = (parse_qs(parsed.query).get("v", [""])[0] if parsed.path == "/watch" else
                  parts[1] if len(parts) == 2 and parts[0] in {"shorts", "embed", "live"} else "")
    else:
        result = ""
    if not VIDEO_ID.fullmatch(result):
        raise ValueError("expected a single YouTube video, not a channel or playlist")
    return result


def instant(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("window instants require a UTC offset or Z")
    return parsed.astimezone(timezone.utc)


def publication(metadata):
    """An instant from yt-dlp's timestamp, else a UTC day from upload_date, else unknown."""
    stamp = metadata.get("timestamp")
    if isinstance(stamp, (int, float)) and not isinstance(stamp, bool) and math.isfinite(stamp):
        point = datetime.fromtimestamp(stamp, timezone.utc).isoformat()
        return {"precision": "instant", "field": "timestamp", "earliest": point, "latest": point}
    date = metadata.get("upload_date")
    if isinstance(date, str) and len(date) == 8 and date.isdigit():
        lower = datetime.strptime(date, "%Y%m%d").replace(tzinfo=timezone.utc)
        return {"precision": "day", "field": "upload_date", "timezone": "UTC",
                "earliest": lower.isoformat(), "latest_exclusive": (lower + timedelta(days=1)).isoformat()}
    return {"precision": "unknown"}


def date_relation(published, start, end):
    if start is None:
        return "not_requested"
    if published["precision"] == "unknown":
        return "unknown"
    lower = instant(published["earliest"])
    upper = instant(published.get("latest_exclusive", published.get("latest")))
    if published["precision"] == "day":
        if upper <= start or lower >= end:
            return "outside"
    elif lower < start or lower >= end:
        return "outside"
    return "inside" if lower >= start and upper <= end else "boundary_uncertain"


def parse_json3(raw):
    """One cue per timed event; the newline-only events of a rolling window carry no text and are skipped."""
    payload = json.loads(raw)
    if not isinstance(payload, dict) or not isinstance(payload.get("events", []), list):
        raise ValueError("caption document must be an object with an events array")
    cues = []
    for event in payload.get("events", []):
        if not isinstance(event, dict):
            continue
        segments = event.get("segs", [])
        if not isinstance(segments, list):
            raise ValueError("caption event segs must be an array")
        parts = [seg.get("utf8", "") for seg in segments if isinstance(seg, dict)]
        if any(not isinstance(part, str) for part in parts):
            raise ValueError("caption segment utf8 must be a string")
        text = " ".join("".join(parts).split())
        start, duration = event.get("tStartMs"), event.get("dDurationMs", 0)
        if text and type(start) is int and type(duration) is int and duration >= 0:
            cues.append({"start_ms": start, "end_ms": start + duration, "text": text})
    return cues


def track_automatic(info, language):
    """yt-dlp writes the manual track when one exists, so the track is automatic only when the language is listed solely under automatic captions."""
    manual = isinstance(info.get("subtitles"), dict) and language in info["subtitles"]
    automatic = isinstance(info.get("automatic_captions"), dict) and language in info["automatic_captions"]
    return False if manual else True if automatic else None


def find_command():
    return [sys.executable, "-m", "yt_dlp"] if importlib.util.find_spec("yt_dlp") else None


def read(video, language, timeout_seconds, directory, *, run=None, command=None):
    """One yt-dlp invocation with a fixed argument list; any failure is reported, never retried."""
    argv = (command or find_command)()
    if not argv:
        return {"status": "dependency_missing"}
    directory = Path(directory)
    args = argv + [
        "--ignore-config", "--no-plugin-dirs", "--no-cookies", "--no-cookies-from-browser",
        "--no-playlist", "--skip-download", "--write-subs", "--write-auto-subs",
        "--extractor-args", "youtube:player_client=android",
        "--sub-langs", language, "--sub-format", "json3", "--write-info-json",
        "--retries", "0", "--extractor-retries", "0", "--fragment-retries", "0", "--file-access-retries", "0",
        "--socket-timeout", str(min(10, timeout_seconds)), "--no-progress", "--no-warnings",
        "-o", str(directory / "%(id)s.%(ext)s"), "https://www.youtube.com/watch?v=" + video,
    ]
    try:
        completed = (run or subprocess.run)(args, capture_output=True, timeout=timeout_seconds,
                                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except subprocess.TimeoutExpired as error:
        result = {"status": "timeout", "process_status": "timeout"}
        stderr = error.stderr
    except OSError as error:
        return {"status": "backend_error", "process_status": "backend_error", "error": str(error)}
    else:
        result = {"exit_code": completed.returncode, "process_status": "ok"}
        stderr = completed.stderr if completed.returncode else None
        if completed.returncode:
            result["status"] = "backend_error"
            result["process_status"] = "backend_error"
    if stderr:
        stderr = stderr.decode("utf-8", errors="replace") if isinstance(stderr, bytes) else str(stderr)
        result["stderr"] = stderr[-STDERR_TAIL:]
    # A later failure cannot erase a completed caption track. The receipt keeps
    # the process failure even when the bounded output below is usable.
    paths = sorted(directory.glob(video + ".*.json3"))
    if not paths:
        return {"status": "no_matching_captions", **result}
    path = paths[0]
    if path.stat().st_size > MAX_BYTES:
        return {"status": "caption_too_large", **result}
    raw = path.read_text(encoding="utf-8", errors="replace")
    info_path = directory / (video + ".info.json")
    try:
        cues = parse_json3(raw)
    except ValueError as error:
        return {"status": "backend_error", "error": f"yt-dlp output unreadable: {error}", **result}
    if not cues:
        return {"status": "no_matching_captions", **result}
    try:
        info = json.loads(info_path.read_text(encoding="utf-8")) if info_path.is_file() and info_path.stat().st_size <= MAX_BYTES else {}
    except ValueError as error:
        info = {}
        result["error"] = f"yt-dlp metadata unreadable: {error}"
    info = info if isinstance(info, dict) else {}
    return {**result, "status": "ok", "text": "\n".join(cue["text"] for cue in cues), "raw": raw,
            "metadata": {key: info[key] for key in ("id", "title", "channel", "upload_date", "timestamp") if key in info},
            "caption_track": {"language": path.name[len(video) + 1:-len(".json3")], "automatic": track_automatic(info, language),
                              "cue_count": len(cues), "duration_ms": max(cue["end_ms"] for cue in cues)}}


def inspect(video, language="en", timeout_seconds=45, max_chars=24000, *, run=None, command=None):
    with tempfile.TemporaryDirectory(prefix="research-caption-") as directory:
        result = read(video, language, timeout_seconds, directory, run=run, command=command)
    text = result.get("text", "")
    packet = {"schema": "research-acquire/source-inspection/v2", "source": "youtube", "operation": "youtube-transcript",
              "url": "https://www.youtube.com/watch?v=" + video, "video_id": video, "content_kind": "transcript",
              "audience_opinion": False, "status": result["status"], "route": "yt-dlp",
              "observed_at": datetime.now(timezone.utc).isoformat(),
              "bounds": {"timeout_seconds": timeout_seconds, "max_chars": max_chars, "invocations": 1,
                         "caption_support_bytes_max": MAX_BYTES},
              "metadata": result.get("metadata", {}), "language": result.get("caption_track", {}).get("language", language),
              "caption_track": result.get("caption_track"), "text": text[:max_chars], "truncated": len(text) > max_chars,
              "limitations": LIMITATIONS}
    for key in ("process_status", "exit_code", "stderr", "error"):
        if key in result:
            packet[key] = result[key]
    if "raw" in result:
        packet.update(caption_format="json3", caption_sha256=hashlib.sha256(result["raw"].encode("utf-8")).hexdigest())
    packet["publication"] = publication(packet["metadata"])
    return packet, result.get("raw")


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    os.replace(temporary, path)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    operations = parser.add_subparsers(dest="operation", required=True)
    parse = operations.add_parser("youtube-transcript", help="fetch captions for one known YouTube video")
    parse.add_argument("--url", required=True)
    parse.add_argument("--output", required=True, type=Path)
    parse.add_argument("--language", default="en")
    parse.add_argument("--timeout-seconds", type=float, default=45)
    parse.add_argument("--max-chars", type=int, default=24000)
    parse.add_argument("--window-start")
    parse.add_argument("--window-end")
    parse.add_argument("--start-date")
    parse.add_argument("--end-date")
    args = parser.parse_args(argv)
    try:
        video = video_id(args.url)
        if not LANGUAGE.fullmatch(args.language):
            raise ValueError("language must be one language code, such as en or pt-BR")
        if not math.isfinite(args.timeout_seconds) or not 1 <= args.timeout_seconds <= 120:
            raise ValueError("timeout-seconds must be between 1 and 120")
        if not 1 <= args.max_chars <= 100000:
            raise ValueError("max-chars must be between 1 and 100000")
        start = end = None
        if args.start_date or args.end_date:
            if args.window_start or args.window_end or not (args.start_date and args.end_date):
                raise ValueError("use one complete window pair: instants or dates")
            start = datetime.strptime(args.start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            end = datetime.strptime(args.end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)
        elif args.window_start or args.window_end:
            if not (args.window_start and args.window_end):
                raise ValueError("both window instants are required")
            start, end = instant(args.window_start), instant(args.window_end)
        if start is not None and start >= end:
            raise ValueError("window start must precede end")
        output = args.output.resolve()
        if output == PACKAGE or PACKAGE in output.parents:
            raise ValueError("evidence output must be outside the installed package")
    except ValueError as error:
        parser.error(str(error))
    packet, raw = inspect(video, args.language, args.timeout_seconds, args.max_chars)
    packet["window"] = {"start": start.isoformat(), "end_exclusive": end.isoformat()} if start else None
    packet["date_relation"] = date_relation(packet["publication"], start, end)
    if raw is not None:
        support = output.with_name(output.name + ".json3")
        support.parent.mkdir(parents=True, exist_ok=True)
        with support.open("w", encoding="utf-8", newline="") as stream:
            stream.write(raw)
        packet["caption_support"] = str(support)
    atomic_json(output, packet)
    print(json.dumps({"status": packet["status"], "output": str(output), "characters": len(packet["text"]),
                      "date_relation": packet["date_relation"]}))
    return 0 if packet["status"] == "ok" else 3


if __name__ == "__main__":
    raise SystemExit(main())
