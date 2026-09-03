#!/usr/bin/env python3
"""Deterministic harvest command. Stdlib-only, cross-platform.

The read sibling of ``scripts/friction.py``: read-only over the state sink
except the one digest file it writes at ``--out``. Sink resolution and
console discipline go through the same deferred, guarded imports
``friction.py`` uses. Nothing here has that file's never-fail bar -- an
ordinary error is allowed to be an ordinary error.

Usage::

    python harvest.py --out <digest.json>
        [--since <ts|Nd>] [--until <ts>] [--on <date>]...
        [--session <id>]... [--run <id>]... [--project <name>]
        [--workflow <name>] [--skill <orch-name>] [--host <host>]

    python harvest.py --list-runs [window flags]

Selectors compose AND across kinds, OR within one repeated flag. Each
``--on <date>`` is one whole UTC day. No selector at all means everything
since the newest watermark in ``improvement/covered.jsonl`` -- this default
applies only when literally no flag was given, never as a fallback for one
flag with no match.

What it does, in order:

1. Slice ``friction/*.jsonl`` and ``events/*.jsonl`` by the window and the
   non-time selectors. An absent events directory reads as empty.
2. Exclude covered: a friction entry at or before a covered entry's
   watermark and matching any of its patterns is dropped and counted --
   never one after, so a matcher does not eat a fresh recurrence.
3. Cluster the remaining friction entries by observed-text similarity
   (``scripts/harvest_cluster.py``). Deterministic given stream order,
   which is file-name order then line order within a file.
4. Compute ``rules/improvement.md`` rule 4's recurrence arithmetic per
   cluster and mark ``recurrence_met``.

The digest header's ``watermark`` is the newest ``ts`` among the entries
this run selected before covered exclusion, so a covered line built from
this digest never eats a recurrence past what was read. An empty selection
falls back to the window's own closing edge, else ``null``.

``--list-runs`` never writes ``--out``; it prints one tab-separated line
per run in the window, a missing field spelled literally ``null``. It is
the resolver a fuzzy window turns into exact flags before calling harvest
again -- no fuzzy matching happens in this file.

Never: read anything beyond ``friction/``, ``events/`` and
``improvement/covered.jsonl``; write anything but the one ``--out`` file;
import beyond the standard library.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import namedtuple
from datetime import datetime, timedelta, timezone
from pathlib import Path

EVENTS_DIRNAME = "events"
COVERED_NAME = "covered.jsonl"
FRAME_OPEN_EVENT = "frame-open"
USAGE_EXIT = 2


class _UsageError(Exception):
    """A call this tool refuses before touching the sink or writing anything."""


def _console():
    """Deferred import, guarded, same shape as ``friction.py``'s own."""

    try:
        from scripts import console
    except ImportError:  # pragma: no cover - the installed copy's path
        import console
    return console


def _state_root():
    """Deferred import of the one sink-root resolver. See ``console``."""

    try:
        from scripts import state_root
    except ImportError:  # pragma: no cover - the installed copy's path
        import state_root
    return state_root


def _cluster():
    """Deferred import of the clustering seam, same guarded shape: a
    partial install costs a clean error, never a traceback."""

    try:
        from scripts import harvest_cluster
    except ImportError:  # pragma: no cover - the installed copy's path
        import harvest_cluster
    return harvest_cluster




def _parse_timestamp(value):
    """Parse a friction/event ``ts``-shaped ISO string; ``None`` if
    malformed or absent, which every caller reads as outside every window."""

    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ") if dt is not None else None


def _parse_since(value, now):
    match = re.fullmatch(r"(\d+)d", value)
    if match:
        return now - timedelta(days=int(match.group(1)))
    parsed = _parse_timestamp(value)
    if parsed is None:
        raise _UsageError(f"--since: not an ISO timestamp or <N>d: {value!r}")
    return parsed


def _parse_until(value):
    parsed = _parse_timestamp(value)
    if parsed is None:
        raise _UsageError(f"--until: not an ISO timestamp: {value!r}")
    return parsed


def _parse_on(value):
    try:
        day = datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        raise _UsageError(f"--on: not a YYYY-MM-DD date: {value!r}")
    return day, day + timedelta(days=1)



_Window = namedtuple(
    "_Window",
    "since_dt until_dt on_ranges session run project workflow skill host",
)


def _in_time_window(ts_dt, window: _Window) -> bool:
    if ts_dt is None:
        return False
    if window.since_dt is not None and ts_dt < window.since_dt:
        return False
    if window.until_dt is not None and ts_dt >= window.until_dt:
        return False
    if window.on_ranges and not any(start <= ts_dt < end for start, end in window.on_ranges):
        return False
    return True


def _matches_selectors(entry: dict, window: _Window, run_workflow_map: dict) -> bool:
    if window.session and entry.get("session") not in window.session:
        return False
    if window.run and entry.get("run") not in window.run:
        return False
    if window.project:
        project = entry.get("project") or {}
        if not isinstance(project, dict) or project.get("name") != window.project:
            return False
    if window.skill and entry.get("skill") != window.skill:
        return False
    if window.host and entry.get("host") != window.host:
        return False
    if window.workflow and run_workflow_map.get(entry.get("run")) != window.workflow:
        return False
    return True




def _iter_jsonl(root_dir: Path):
    """Every JSON object line under ``root_dir/*.jsonl``, file-name order
    then line order -- ``YYYY-MM`` names sort chronologically, which is what
    makes clustering deterministic. A missing directory yields nothing; a
    malformed line is skipped, since other processes append to this sink."""

    if not root_dir.is_dir():
        return
    for path in sorted(root_dir.glob("*.jsonl")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if isinstance(entry, dict):
                yield entry


def _file_count(root_dir: Path) -> int:
    return len(list(root_dir.glob("*.jsonl"))) if root_dir.is_dir() else 0


def _run_workflow_map(event_entries) -> dict:
    """Run id -> workflow name, from the first ``frame-open`` event per run."""

    mapping = {}
    for entry in event_entries:
        if entry.get("event") != FRAME_OPEN_EVENT:
            continue
        run = entry.get("run")
        workflow = entry.get("workflow")
        if run and workflow and run not in mapping:
            mapping[run] = workflow
    return mapping




def _read_covered(path: Path):
    """Every parseable ``covered.jsonl`` entry as ``{watermark_dt, compiled}``."""

    entries = []
    if not path.is_file():
        return entries
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        if not isinstance(obj, dict):
            continue
        matcher = obj.get("matcher")
        compiled = []
        for pattern in matcher if isinstance(matcher, list) else []:
            try:
                compiled.append(re.compile(pattern, re.IGNORECASE))
            except (re.error, TypeError):
                continue
        entries.append({
            "watermark_dt": _parse_timestamp(obj.get("watermark")),
            "compiled": compiled,
        })
    return entries


def _default_since_from_covered(covered):
    marks = [c["watermark_dt"] for c in covered if c["watermark_dt"] is not None]
    return max(marks) if marks else None


def _window_end(until_dt, on_ranges):
    """The window's closing edge if the caller bounded one, else ``None``."""

    ends = [dt for dt in [until_dt] if dt is not None]
    if on_ranges:
        ends.append(max(end for _, end in on_ranges))
    return max(ends) if ends else None


def _newest_ts(entries):
    """The latest parseable ``ts`` among ``entries``, else ``None``."""

    stamps = [_parse_timestamp(e.get("ts")) for e in entries]
    stamps = [dt for dt in stamps if dt is not None]
    return max(stamps) if stamps else None


def _apply_covered_exclusion(entries, covered):
    """``(kept, dropped_count)``. A candidate is dropped by the first covered
    entry at or before whose watermark it falls and whose pattern matches;
    an entry with no readable ``ts`` is never "at or before" anything."""

    entry_text = _cluster().entry_text
    kept = []
    dropped = 0
    for entry in entries:
        ts_dt = _parse_timestamp(entry.get("ts"))
        text = None
        excluded = False
        for cov in covered:
            if ts_dt is None or cov["watermark_dt"] is None or ts_dt > cov["watermark_dt"]:
                continue
            if not cov["compiled"]:
                continue
            if text is None:
                text = entry_text(entry)
            if any(pattern.search(text) for pattern in cov["compiled"]):
                excluded = True
                break
        if excluded:
            dropped += 1
        else:
            kept.append(entry)
    return kept, dropped




def _list_run_rows(friction_entries, event_entries, window: _Window, run_workflow_map: dict):
    rows = {}
    for kind, entries in (("friction", friction_entries), ("event", event_entries)):
        for entry in entries:
            ts_dt = _parse_timestamp(entry.get("ts"))
            if not _in_time_window(ts_dt, window):
                continue
            if not _matches_selectors(entry, window, run_workflow_map):
                continue
            run = entry.get("run")
            if not run:
                continue
            row = rows.setdefault(run, {"friction": 0, "event": 0, "earliest": None, "latest": None})
            row[kind] += 1
            if row["earliest"] is None or ts_dt < row["earliest"]:
                row["earliest"] = ts_dt
            if row["latest"] is None or ts_dt > row["latest"]:
                row["latest"] = ts_dt
    return rows


def _goal_first_lines(event_entries) -> dict:
    goals = {}
    for entry in event_entries:
        if entry.get("event") != FRAME_OPEN_EVENT:
            continue
        run = entry.get("run")
        if run and run not in goals:
            goals[run] = entry.get("goal_head")
    return goals


def _list_runs_lines(friction_entries, event_entries, window: _Window, run_workflow_map: dict):
    rows = _list_run_rows(friction_entries, event_entries, window, run_workflow_map)
    goals = _goal_first_lines(event_entries)
    ordered = sorted(
        rows,
        key=lambda run: rows[run]["latest"] or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    lines = []
    for run in ordered:
        row = rows[run]
        lines.append("\t".join([
            run,
            run_workflow_map.get(run) or "null",
            goals.get(run) or "null",
            _iso(row["earliest"]) or "null",
            _iso(row["latest"]) or "null",
            str(row["friction"]),
            str(row["event"]),
        ]))
    return lines




def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="harvest.py", add_help=True)
    parser.add_argument("--out")
    parser.add_argument("--list-runs", action="store_true")
    parser.add_argument("--since")
    parser.add_argument("--until")
    parser.add_argument("--on", action="append", default=[])
    parser.add_argument("--session", action="append", default=[])
    parser.add_argument("--run", action="append", default=[])
    parser.add_argument("--project")
    parser.add_argument("--workflow")
    parser.add_argument("--skill")
    parser.add_argument("--host")
    return parser


def _no_selector_given(args) -> bool:
    return not any([
        args.since, args.until, args.on, args.session, args.run,
        args.project, args.workflow, args.skill, args.host,
    ])


def _window_echo(args, since_dt, until_dt, on_ranges, defaulted) -> dict:
    return {
        "since": _iso(since_dt),
        "since_defaulted_from_covered_watermark": defaulted,
        "until": _iso(until_dt),
        "on": [_iso(start) for start, _ in on_ranges],
        "session": sorted(args.session),
        "run": sorted(args.run),
        "project": args.project,
        "workflow": args.workflow,
        "skill": args.skill,
        "host": args.host,
    }


def _resolve_window(args, now):
    since_dt = _parse_since(args.since, now) if args.since else None
    until_dt = _parse_until(args.until) if args.until else None
    on_ranges = [_parse_on(v) for v in args.on]
    covered = _read_covered(_state_root().improvement_root() / COVERED_NAME)
    defaulted = False
    if _no_selector_given(args):
        default_since = _default_since_from_covered(covered)
        if default_since is not None:
            since_dt = default_since
            defaulted = True
    window = _Window(
        since_dt=since_dt, until_dt=until_dt, on_ranges=on_ranges,
        session=set(args.session), run=set(args.run),
        project=args.project, workflow=args.workflow,
        skill=args.skill, host=args.host,
    )
    return window, covered, since_dt, until_dt, on_ranges, defaulted


def _run(argv, now=None) -> int:
    now = now or datetime.now(timezone.utc)
    args = _build_parser().parse_args(argv)
    if args.list_runs and args.out:
        raise _UsageError("--list-runs takes no --out")
    if not args.list_runs and not args.out:
        raise _UsageError("--out is required unless --list-runs")

    root = _state_root()
    friction_dir = root.friction_root()
    events_dir = root.state_root() / EVENTS_DIRNAME
    friction_entries = list(_iter_jsonl(friction_dir))
    event_entries = list(_iter_jsonl(events_dir))
    run_workflow_map = _run_workflow_map(event_entries)

    window, covered, since_dt, until_dt, on_ranges, defaulted = _resolve_window(args, now)

    if args.list_runs:
        for line in _list_runs_lines(friction_entries, event_entries, window, run_workflow_map):
            print(line)
        return 0

    selected = [
        e for e in friction_entries
        if _in_time_window(_parse_timestamp(e.get("ts")), window)
        and _matches_selectors(e, window, run_workflow_map)
    ]
    kept, dropped = _apply_covered_exclusion(selected, covered)
    cluster = _cluster()
    records = cluster.build_cluster_records(cluster.cluster_entries(kept))

    watermark_dt = _newest_ts(selected)
    if watermark_dt is None:
        watermark_dt = _window_end(until_dt, on_ranges)

    digest = {
        "generated_at": _iso(now),
        "watermark": _iso(watermark_dt),
        "window": _window_echo(args, since_dt, until_dt, on_ranges, defaulted),
        "streams_read": {
            "friction_files": _file_count(friction_dir),
            "event_files": _file_count(events_dir),
        },
        "totals": {
            "friction_entries": len(friction_entries),
            "event_entries": len(event_entries),
            "friction_selected": len(selected),
            "covered_dropped": dropped,
            "clustered_entries": len(kept),
            "cluster_count": len(records),
        },
        "clusters": records,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(digest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"harvest written: {len(records)} clusters, {dropped} covered-dropped, "
        f"{len(kept)} of {len(friction_entries)} friction entries -> {out_path}"
    )
    return 0


def main(argv=None) -> int:
    try:
        _console().harden()
    except Exception:  # pragma: no cover - the console is not the harvest
        pass
    try:
        return _run(sys.argv[1:] if argv is None else argv)
    except _UsageError as exc:
        print(f"harvest.py: {exc}", file=sys.stderr)
        return USAGE_EXIT
    except Exception as exc:
        print(f"harvest.py: failed: {exc}", file=sys.stderr)
        return 1


def _guarded(argv):
    try:
        console = _console()
    except ImportError:  # pragma: no cover - a partial install
        return main(argv)
    return console.run(main, argv)


if __name__ == "__main__":
    raise SystemExit(_guarded(sys.argv[1:]))
