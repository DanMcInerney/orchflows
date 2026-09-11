"""Bounded caption backends for inspect_source; no discovery or account access."""

import hashlib
import html
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

MAX_BYTES = 8 * 1024 * 1024
VIDEO_ID = re.compile(r"[A-Za-z0-9_-]{11}\Z")
LANGUAGE = re.compile(r"[a-zA-Z]{2,3}(?:-[a-zA-Z0-9]{2,8})?\Z")


def ytdlp_command():
    if importlib.util.find_spec("yt_dlp") is not None:
        return [sys.executable, "-m", "yt_dlp"]
    executable = shutil.which("yt-dlp")
    return [executable] if executable else None


def classify_error(stderr):
    text = stderr.lower()
    if "429" in text or "too many requests" in text:
        return "rate_limited"
    if "sign in" in text or "not a bot" in text or "po token" in text:
        return "access_blocked"
    if "requested subtitles" in text or "no subtitles" in text:
        return "no_matching_captions"
    return "backend_error"


def parse_vtt(raw):
    """Keep cue order and timing; only remove adjacent duplicate captions."""
    cues = []
    for block in re.split(r"\n\s*\n", raw.replace("\r\n", "\n")):
        lines = block.splitlines()
        timing = next((i for i, line in enumerate(lines) if " --> " in line), None)
        if timing is None:
            continue
        match = re.match(r"([\d:.]+) --> ([\d:.]+)", lines[timing])
        if not match:
            continue
        def seconds(value):
            result = 0.0
            for part in value.split(":"):
                result = result * 60 + float(part)
            return round(result, 3)
        try:
            start, end = map(seconds, match.groups())
        except ValueError:
            continue
        text = html.unescape(re.sub(r"<[^>]*>", "", " ".join(lines[timing + 1:])))
        text = " ".join(text.split())
        if text and end >= start:
            if cues and cues[-1]["text"] == text and start <= cues[-1]["end_seconds"]:
                cues[-1]["end_seconds"] = max(end, cues[-1]["end_seconds"])
            else:
                cues.append({"start_seconds": start, "end_seconds": end, "text": text})
    return cues


def caption_result(raw, format_name, text, language, metadata, **extra):
    if len(raw.encode("utf-8")) > MAX_BYTES:
        return {"status": "caption_too_large", "metadata": metadata, **extra}
    return {"status": "ok", "text": text, "language": language,
            "metadata": metadata, "caption_format": format_name,
            "caption_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
            "_raw_caption": raw, **extra}


def ytdlp_track_automatic(payload, language):
    """Identify automatic generation; translated manual tracks are not necessarily ASR."""
    requested = payload.get("requested_subtitles")
    selected = requested.get(language) if isinstance(requested, dict) else None
    url = selected.get("url") if isinstance(selected, dict) else None
    if not isinstance(url, str) or not 0 < len(url) <= 8192:
        return None
    matches = []
    for collection, automatic in (("subtitles", False), ("automatic_captions", True)):
        languages = payload.get(collection)
        tracks = languages.get(language) if isinstance(languages, dict) else None
        if isinstance(tracks, list) and any(isinstance(track, dict) and track.get("url") == url for track in tracks):
            matches.append(automatic)
    return matches[0] if len(matches) == 1 else None


def read_ytdlp(video_id, language, directory, timeout, *, command=None, run=subprocess.run):
    command = ytdlp_command() if command is None else command
    if not command:
        return {"status": "dependency_missing", "dependency": "yt-dlp"}
    directory = Path(directory)
    args = command + [
        "--ignore-config", "--no-plugin-dirs", "--no-cookies", "--no-cookies-from-browser",
        "--no-playlist", "--skip-download", "--write-subs", "--write-auto-subs",
        "--extractor-args", "youtube:player_client=android",
        "--sub-langs", language, "--sub-format", "vtt", "--write-info-json",
        "--retries", "0", "--extractor-retries", "0", "--fragment-retries", "0",
        "--file-access-retries", "0", "--socket-timeout", str(min(10, timeout)),
        "--no-progress", "--no-warnings", "-o", str(directory / "%(id)s.%(ext)s"),
        "https://www.youtube.com/watch?v=" + video_id,
    ]
    process_status, code = "ok", None
    with (directory / "stderr.txt").open("w+b") as errors:
        try:
            result = run(args, stdout=subprocess.DEVNULL, stderr=errors, timeout=timeout,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            code = result.returncode
        except subprocess.TimeoutExpired:
            process_status = "timeout"
        except OSError:
            return {"status": "dependency_unavailable", "dependency": "yt-dlp"}
        errors.seek(0, 2)
        errors.seek(max(0, errors.tell() - 4096))
        error_text = errors.read().decode("utf-8", errors="replace")
    if code:
        process_status = classify_error(error_text)
    # A later extractor error or timeout must not discard a completed caption file.
    candidates = sorted(directory.glob(video_id + ".*.vtt"))
    too_large = False
    for path in candidates:
        if path.stat().st_size > MAX_BYTES:
            too_large = True
            continue
        raw = path.read_text(encoding="utf-8", errors="replace")
        if len(raw.encode("utf-8")) > MAX_BYTES:
            too_large = True
            continue
        cues = parse_vtt(raw)
        if not cues:
            continue
        metadata = {}
        attributes = {"languageCode": language, "cue_count": len(cues)}
        duration = max(cue["end_seconds"] for cue in cues)
        if 0 <= duration < 10 ** 12:
            attributes["duration_ms"] = round(duration * 1000)
        info = directory / (video_id + ".info.json")
        if info.is_file() and info.stat().st_size <= MAX_BYTES:
            try:
                payload = json.loads(info.read_text(encoding="utf-8"))
                if payload.get("id") == video_id:
                    metadata = {key: payload[key] for key in
                                ("id", "title", "channel", "upload_date", "timestamp", "release_timestamp")
                                if key in payload}
                    metadata["provenance"] = "yt-dlp info.json"
                    automatic = ytdlp_track_automatic(payload, language)
                    if automatic is not None:
                        attributes["automatic"] = automatic
            except (ValueError, AttributeError):
                pass
        return caption_result(raw, "vtt", "\n".join(cue["text"] for cue in cues), language,
                              metadata, process_status=process_status, exit_code=code,
                              attributes=attributes,
                              dependency={"command": command, "player_client": "android",
                                          "cookies": "disabled", "configuration": "ignored"})
    return {"status": "caption_too_large" if too_large else
            process_status if process_status != "ok" else "no_matching_captions",
            "exit_code": code}


def read_innertube(video_id, language, *, opener=None):
    """Reuse the library's player-to-timedtext handoff, at most two reads."""
    from super_research import transport
    from super_research.adapters import AdapterRequest, youtube_innertube
    responses = []
    def capture(request):
        result = (opener or transport.urlopen_read)(request)
        responses.append((request.route_id, result[0], result[1]))
        return result
    carrier = transport.Transport(opener=capture)
    target = "transcript:" + video_id + ":" + language
    pages, metadata = [], {}
    cursor = ""
    for _ in range(2):
        page = youtube_innertube.fetch_native_page(
            carrier, AdapterRequest(step_id="inspect", target_ids=(target,), cursor=cursor))
        pages.append({"route_id": page.route_id, "status": page.outcome,
                      "loss": list(page.loss), "warnings": list(page.warnings)})
        for record in page.records:
            if record.canonical_content_kind == "video":
                metadata.update({"id": record.native_item_id, "title": record.title,
                                 "channel": record.author, "provenance": "youtube_innertube player"})
            if record.canonical_content_kind == "transcript" and record.body:
                attrs = dict(record.attributes)
                return caption_result(responses[-1][2], "json3", record.body,
                                      attrs.get("languageCode", language), metadata,
                                      pages=pages, requests=len(responses), attributes=attrs)
        if responses:
            try:
                payload = json.loads(responses[-1][2])
                published = payload.get("microformat", {}).get("playerMicroformatRenderer", {}).get("publishDate")
                if published:
                    metadata["published_at"] = published
            except (ValueError, AttributeError):
                pass
        if not page.cursor_out:
            break
        cursor = page.cursor_out
    loss = {code for page in pages for code in page["loss"]}
    status = "access_blocked" if loss & {"auth_required", "attestation_required"} else "unavailable"
    return {"status": status, "pages": pages, "requests": len(responses), "metadata": metadata}


if __name__ == "__main__":
    # A private bounded child isolates urllib's socket timeout from the caller's wall deadline.
    if len(sys.argv) != 3 or not VIDEO_ID.fullmatch(sys.argv[1]) or not LANGUAGE.fullmatch(sys.argv[2]):
        raise SystemExit(2)
    try:
        result = read_innertube(sys.argv[1], sys.argv[2])
    except Exception as error:
        result = {"status": "backend_error", "error_type": type(error).__name__}
    print(json.dumps(result, ensure_ascii=True))
