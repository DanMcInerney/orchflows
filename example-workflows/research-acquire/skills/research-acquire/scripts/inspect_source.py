"""Inspect one known source URL and save evidence without a research plan."""

import argparse
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from urllib.parse import parse_qs, urlsplit

from acquire_checkpoint import atomic_json
import inspect_youtube as youtube

PACKAGE = Path(__file__).resolve().parents[3]


def video_id(value):
    if youtube.VIDEO_ID.fullmatch(value):
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
    if not youtube.VIDEO_ID.fullmatch(result):
        raise ValueError("expected a single YouTube video, not a channel or playlist")
    return result


def instant(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("window instants require a UTC offset or Z")
    return parsed.astimezone(timezone.utc)


def publication(metadata):
    """Return an observed publication interval, preserving day-only uncertainty."""
    raw = metadata.get("published_at")
    origin = "published_at"
    if not raw:
        stamp = metadata.get("timestamp")
        if isinstance(stamp, (int, float)) and not isinstance(stamp, bool) and math.isfinite(stamp):
            try:
                raw = datetime.fromtimestamp(stamp, timezone.utc).isoformat()
                origin = "timestamp"
            except (ValueError, OverflowError, OSError):
                pass
    if not raw and metadata.get("upload_date"):
        raw = metadata["upload_date"]
        origin = "upload_date"
        if isinstance(raw, str) and len(raw) == 8 and raw.isdigit():
            raw = raw[:4] + "-" + raw[4:6] + "-" + raw[6:]
    if not isinstance(raw, str):
        return {"precision": "unknown", "raw": raw, "field": origin}
    try:
        if len(raw) == 10:
            lower = datetime.strptime(raw, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            upper = lower + timedelta(days=1)
            # yt-dlp upload_date is a UTC date; a native date-only publishDate
            # has no stated zone, so allow the full UTC-12 through UTC+14 range.
            zone = "UTC" if origin == "upload_date" else "unspecified"
            if zone == "unspecified":
                lower -= timedelta(hours=14)
                upper += timedelta(hours=12)
            return {"precision": "day", "raw": raw, "field": origin,
                    "timezone": zone,
                    "earliest": lower.isoformat(), "latest_exclusive": upper.isoformat()}
        point = instant(raw).isoformat()
        return {"precision": "instant", "raw": raw, "field": origin, "earliest": point, "latest": point}
    except ValueError:
        return {"precision": "unknown", "raw": raw, "field": origin}


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


def caption_track(result, requested_language):
    """Expose only bounded, understood track facts from either backend."""
    attributes = result.get("attributes", {})
    attributes = attributes if isinstance(attributes, dict) else {}
    track = {"automatic": None}
    if type(attributes.get("automatic")) is bool:
        track["automatic"] = attributes["automatic"]
    language = attributes.get("languageCode", result.get("language", requested_language))
    if isinstance(language, str) and youtube.LANGUAGE.fullmatch(language):
        track["language"] = language
    kind = attributes.get("kind")
    if kind in ("asr", "published"):
        track.update(kind=kind, automatic=kind == "asr")
    for key in ("cue_count", "duration_ms"):
        value = attributes.get(key)
        if type(value) is int and 0 <= value < 10 ** 15:
            track[key] = value
        elif isinstance(value, str) and 1 <= len(value) <= 15 and value.isascii() and value.isdecimal():
            track[key] = int(value)
    return track


def inspect(video, language="en", timeout_seconds=45, max_chars=24000, *,
            clock=time.monotonic, ytdlp_read=youtube.read_ytdlp, run=subprocess.run):
    started = clock()
    attempts, result = [], {}
    with tempfile.TemporaryDirectory(prefix="research-caption-") as temp:
        attempt_start = clock()
        result = ytdlp_read(video, language, temp, min(30, timeout_seconds * 0.7))
        attempts.append({"backend": "yt-dlp", "status": result["status"],
                         "process_status": result.get("process_status"), "exit_code": result.get("exit_code"),
                         "elapsed_seconds": round(clock() - attempt_start, 3)})
        remaining = timeout_seconds - (clock() - started)
        if result["status"] != "ok" and remaining > 0:
            attempt_start = clock()
            try:
                child = run([sys.executable, str(Path(youtube.__file__).resolve()), video, language],
                            capture_output=True, timeout=remaining,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                result = json.loads(child.stdout) if child.returncode == 0 else {"status": "backend_error"}
            except subprocess.TimeoutExpired:
                result = {"status": "timeout"}
            except (ValueError, OSError):
                result = {"status": "backend_error"}
            attempts.append({"backend": "youtube_innertube", "status": result["status"],
                             "pages": result.get("pages", []), "requests": result.get("requests"),
                             "elapsed_seconds": round(clock() - attempt_start, 3)})
        elif result["status"] != "ok":
            result["fallback_skipped"] = "deadline"
    text = result.get("text", "")
    truncated = len(text) > max_chars
    packet = {"schema": "research-acquire/source-inspection/v1", "source": "youtube",
              "operation": "youtube-transcript", "url": "https://www.youtube.com/watch?v=" + video,
              "video_id": video, "content_kind": "transcript", "audience_opinion": False,
              "status": result["status"], "observed_at": datetime.now(timezone.utc).isoformat(),
              "backend": attempts[-1]["backend"], "attempts": attempts,
              "elapsed_seconds": round(clock() - started, 3),
              "bounds": {"timeout_seconds": timeout_seconds, "max_chars": max_chars,
                         "videos": 1, "yt_dlp_attempts": 1, "innertube_requests_max": 2,
                         "caption_support_bytes_max": youtube.MAX_BYTES},
              "metadata": result.get("metadata", {}), "language": result.get("language", language),
              "caption_track": caption_track(result, language),
              "text": text[:max_chars], "truncated": truncated,
              "limitations": ["Captions represent video speech, not viewer comments; speaker identity is unverified.",
                              "Caption text may repeat rolling captions or contain recognition errors.",
                              "Publication time belongs to the video; the transcript track has no independent publication date.",
                              "yt-dlp has internal requests; the receipt counts backend attempts, not every HTTP request."]}
    for key in ("caption_sha256", "caption_format", "_raw_caption", "dependency", "fallback_skipped"):
        if key in result:
            packet[key] = result[key]
    packet["publication"] = publication(packet["metadata"])
    return packet


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    operations = parser.add_subparsers(dest="operation", required=True)
    command = operations.add_parser("youtube-transcript", help="fetch captions for one known YouTube video")
    command.add_argument("--url", required=True)
    command.add_argument("--output", required=True, type=Path)
    command.add_argument("--language", default="en")
    command.add_argument("--timeout-seconds", type=float, default=45)
    command.add_argument("--max-chars", type=int, default=24000)
    command.add_argument("--window-start")
    command.add_argument("--window-end")
    command.add_argument("--start-date")
    command.add_argument("--end-date")
    args = parser.parse_args(argv)
    try:
        video = video_id(args.url)
        if not youtube.LANGUAGE.fullmatch(args.language):
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
    packet = inspect(video, args.language, args.timeout_seconds, args.max_chars)
    packet["window"] = {"start": start.isoformat(), "end_exclusive": end.isoformat()} if start else None
    packet["date_relation"] = date_relation(packet["publication"], start, end)
    raw = packet.pop("_raw_caption", None)
    if raw is not None:
        support = output.with_name(output.name + "." + packet["caption_format"])
        support.parent.mkdir(parents=True, exist_ok=True)
        with support.open("w", encoding="utf-8", newline="") as stream:
            stream.write(raw)
        packet["caption_support"] = str(support)
    atomic_json(output, packet)
    print(json.dumps({"status": packet["status"], "output": str(output),
                      "backend": packet["backend"], "characters": len(packet["text"]),
                      "date_relation": packet["date_relation"]}))
    return 0 if packet["status"] == "ok" else 3


if __name__ == "__main__":
    raise SystemExit(main())
