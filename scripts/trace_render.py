"""Canonical trace normalization and Mermaid rendering support."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

HOST_CLAUDE = "claude-code"
HOST_CODEX = "codex"

EXIT_CODE_RE = re.compile(r"[Ee]xit code:?\s*(-?\d+)")
SHELL_COMMAND_RE = re.compile(r'command["\']?\s*:\s*"((?:[^"\\]|\\.)*)"')
# Both roots a run-state path can carry. The sink is where every writer
# lands (``scripts/state_root.py``); the repository shape stays matched
# because a trace may cover a session that predates the migration.
# ``\.orch`` cannot swallow ``.orchflows``: the separator after it is
# required, and ``.orchflows`` has an ``f`` there.
STATE_ROOT_RE = r"(?:\.orch|\.orchflows[/\\]state)"
RUN_ID_RE = re.compile(
    STATE_ROOT_RE + r"[/\\](?:runs|tickets)[/\\]([A-Za-z0-9][A-Za-z0-9._-]*)"
)
TEXT_CLIP = 2000  # chars kept of request/narration text; one owner
HARNESS_TEXT_MARKERS = ("<system-reminder>", "<command-name>", "<local-command-stdout>")

CODEX_BOILERPLATE_MARKERS = (
    "<recommended_plugins>",
    "<environment_context>",
    "AGENTS.md instructions",
    "<apps_instructions>",
    "<plugins_instructions>",
    "<permissions instructions>",
    "<multi_agent_mode>",
    "<skills_instructions>",
)



def _parse_ts(value):
    if not isinstance(value, str) or not value:
        return None
    text = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _duration_ms(start, end):
    start_dt = _parse_ts(start)
    end_dt = _parse_ts(end)
    if start_dt is None or end_dt is None:
        return None
    delta = (end_dt - start_dt).total_seconds() * 1000
    return int(delta) if delta >= 0 else None


def _tag_file_errors(errors, path):
    tagged = []
    for err in errors:
        entry = dict(err)
        entry["file"] = str(path)
        tagged.append(entry)
    return tagged


def _empty_trace(host, session_id, error):
    return {
        "host": host,
        "session_id": session_id,
        "schema_confidence": 0.0,
        "events": [],
        "parse_errors": [{"line": None, "file": None, "error": error}],
    }


def _clip(text: str):
    """Return (clipped_text, truncated_flag) under the TEXT_CLIP cap."""
    text = str(text)
    if len(text) > TEXT_CLIP:
        return text[:TEXT_CLIP], True
    return text, False


def _text_fields(ev: dict, text: str) -> dict:
    clipped, truncated = _clip(text)
    ev["text"] = clipped
    if truncated:
        ev["truncated"] = True
    return ev


def _runs_touched(events):
    runs = set()
    for ev in events:
        if ev.get("type") != "tool_call":
            continue
        for match in RUN_ID_RE.finditer(str(ev.get("command", ""))):
            runs.add(match.group(1))
    return sorted(runs)


def _finalize(host, session_id, events, clean, total, parse_errors):
    events.sort(key=lambda ev: ev.get("ts") or "")
    for ev in events:
        ev.pop("_start_ts", None)
    # Two zero totals, two answers: a transcript that is there and empty has
    # nothing to distrust, while a total of zero standing next to a parse
    # error is a file nothing was read from -- and 1.0 there would claim full
    # trust in no data.
    confidence = round(clean / total, 4) if total else (0.0 if parse_errors else 1.0)
    return {
        "host": host,
        "session_id": session_id,
        "schema_confidence": confidence,
        "runs_touched": _runs_touched(events),
        "events": events,
        "parse_errors": parse_errors,
    }


def _read_lines(path: Path):
    """Yield (lineno, raw_text) for each non-blank line, or raise OSError."""
    # utf-8-sig: BOM-prefixed files (PowerShell Out-File default) read clean.
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    for lineno, raw in enumerate(text.splitlines(), start=1):
        raw = raw.strip()
        if raw:
            yield lineno, raw


_MERMAID_UNSAFE_RE = re.compile(r'["\[\]{}()\n\r]')


def _mermaid_sanitize(text: str, limit: int = 80) -> str:
    text = _MERMAID_UNSAFE_RE.sub(" ", str(text))
    text = " ".join(text.split())
    return text[:limit]


def _mermaid_label(ev: dict) -> str:
    etype = ev.get("type", "unknown")
    if etype == "request":
        text = ev.get("text")
        return f"request: {_mermaid_sanitize(text)}" if text else "request"
    if etype == "narration":
        return f"narration: {_mermaid_sanitize(ev.get('text', ''))}"
    if etype == "skill_invocation":
        return f"skill: {_mermaid_sanitize(ev.get('name', 'unknown'))}"
    if etype == "subagent":
        return f"subagent: {_mermaid_sanitize(ev.get('agent_type', 'unknown'))} model={_mermaid_sanitize(ev.get('model', 'unknown'))}"
    if etype == "tool_call":
        return f"tool: {_mermaid_sanitize(ev.get('command', 'unknown'))} exit={ev.get('exit', 'unknown')}"
    return _mermaid_sanitize(etype)


def render_mermaid(trace: dict) -> str:
    lines = ["flowchart TD"]
    events = trace.get("events") or []
    if not events:
        lines.append('    n0["(no events)"]')
        return "\n".join(lines) + "\n"
    previous = None
    for idx, ev in enumerate(events):
        node = f"n{idx}"
        lines.append(f'    {node}["{_mermaid_label(ev)}"]')
        if previous is not None:
            lines.append(f"    {previous} --> {node}")
        previous = node
    return "\n".join(lines) + "\n"
