# Direct source inspection

Resolve `research-acquire --resource skills/research-acquire/scripts/inspect_source.py` through the home CLI and run it with a Python that can import `yt_dlp`; see [dependencies](../../../README.md):

```text
python <script> youtube-transcript --url <video URL or ID> --output <outside-package>/caption.json [--language en] [--timeout-seconds 45] [--max-chars 24000] [--window-start <instant> --window-end <instant> | --start-date <date> --end-date <date>]
```

One known video, one route: a single yt-dlp invocation with a fixed argument list (Android player client, cookies and user configuration disabled, no playlist, no retries) writes the requested caption track and the video's metadata to a scratch directory. Completed valid captions survive a later process failure; `process_status` records that failure. Captions are video speech, not viewer comments, and speaker identity is unverified; use native source access for discovery and comments.

## Flags

- `--url`: HTTPS watch, `youtu.be`, shorts, embed or live URL, or a bare 11-character ID. Channels and playlists are refused; a playlist parameter on a watch URL is ignored.
- `--language` (default `en`): one yt-dlp language code, matched exactly; a manual track wins over an automatic one when both exist.
- `--timeout-seconds` (default 45, range 1–120): the wall budget for the invocation.
- `--max-chars` (default 24000, range 1–100000): bounds `text`; a cut prefix sets `truncated`.
- `--output`: receipt path, outside the installed package.

## Receipt

`schema`, `source`, `operation`, `url`, `video_id`, `content_kind`, `audience_opinion`, `observed_at`, `status`, `route`, `bounds`, `metadata` (`id`, `title`, `channel`, `upload_date`, `timestamp` as yt-dlp reports them), `publication`, `window`, `date_relation`, `language`, `caption_track` (`language`, `automatic`, `cue_count`, `duration_ms`; null when no track was read), `text`, `truncated`, `limitations`, and when text was retained `caption_format` (`json3`), `caption_sha256` and `caption_support`. `exit_code` is present only once an invocation completed; absent when the dependency is missing, the invocation timed out or launch failed. `automatic` is true when the language is listed only under yt-dlp's automatic captions, false when a manual track exists (yt-dlp writes the manual one), null when provenance is unknown. On process failure, `stderr` holds the last 2,000 characters yt-dlp wrote, or `error` names the local fault.

`caption_support` is the sidecar `<output>.json3`, the track exactly as yt-dlp wrote it, cue timing included, at most 8 MiB. `process_status` records `ok`, `backend_error` or `timeout` when an invocation was attempted, independently of whether captions were retained. Missing or unreadable metadata leaves publication unknown; unreadable metadata also records `error`.

## Statuses and exit codes

- `ok`: valid caption text retained. Exit 0, including after a later process failure; inspect `process_status` and diagnostics for that failure.
- `dependency_missing`: `yt_dlp` is not importable by the interpreter running the script.
- `no_matching_captions`: yt-dlp succeeded but wrote no track in the requested language, or an empty one.
- `backend_error`: no usable captions were retained because yt-dlp or its output failed; read `stderr` or `error` for the reason.
- `timeout`: the wall budget was spent without usable captions.
- `caption_too_large`: the track exceeds the sidecar ceiling; nothing retained.

Exit 2 is a usage error and writes nothing. Every status other than `ok` exits 3 with the receipt written. `ok` does not mean the video is inside the window.

## Dates

`--window-start`/`--window-end` are `[start, end)` instants with a UTC offset or `Z`; `--start-date`/`--end-date` are inclusive UTC calendar dates. Pass one complete pair or neither. `publication` is `instant` from `timestamp`, else `day` from `upload_date` (a UTC date), else `unknown`. `date_relation` is `inside`, `outside`, `boundary_uncertain` (a day interval overlapping a cutoff), `unknown` or `not_requested`. Collection time never dates a caption.

## Tests

From the skill directory with `PYTHONPATH` set to its absolute `scripts`: `python -m unittest tests.test_inspect_source`. An injected command stands in for yt-dlp; nothing runs it or reaches the network.
