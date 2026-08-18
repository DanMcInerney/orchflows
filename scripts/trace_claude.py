"""Claude Code session extraction support for the trace facade."""

from __future__ import annotations

import json
from pathlib import Path

try:  # in-repo package import
    from scripts.trace_render import (
    EXIT_CODE_RE,
    HARNESS_TEXT_MARKERS,
    HOST_CLAUDE,
    _duration_ms,
    _empty_trace,
    _finalize,
    _read_lines,
    _tag_file_errors,
    _text_fields,
)
except ImportError:  # installed flat beside trace.py
    from trace_render import (
    EXIT_CODE_RE,
    HARNESS_TEXT_MARKERS,
    HOST_CLAUDE,
    _duration_ms,
    _empty_trace,
    _finalize,
    _read_lines,
    _tag_file_errors,
    _text_fields,
)

def _claude_tool_command(name, tool_input):
    if isinstance(tool_input, dict):
        command = tool_input.get("command")
        if isinstance(command, str) and command:
            return command
        file_path = tool_input.get("file_path")
        if isinstance(file_path, str) and file_path:
            return f"{name}:{file_path}"
        pattern = tool_input.get("pattern")
        if isinstance(pattern, str) and pattern and name in ("Glob", "Grep"):
            return f"{name}:{pattern}"
    return name


def _resolve_claude_exit(block, tool_use_result):
    if block.get("is_error"):
        content = block.get("content")
        text = content if isinstance(content, str) else ""
        if isinstance(tool_use_result, str):
            text = tool_use_result + "\n" + text
        match = EXIT_CODE_RE.search(text)
        if match:
            return int(match.group(1))
        # An error result without exit-code text is still a failure; only
        # Bash prints codes, and "unknown" here would hide every other
        # tool's errors from the miner's isinstance(int) filters.
        return 1
    return 0


def _handle_claude_user_line(obj, ts, events, pending):
    message = obj.get("message")
    if not isinstance(message, dict):
        return False
    content = message.get("content")
    if isinstance(content, str):
        if not any(marker in content for marker in HARNESS_TEXT_MARKERS):
            events.append(_text_fields({"type": "request", "ts": ts}, content))
        return True
    if isinstance(content, list):
        # A turn carrying tool_result blocks is a result turn; its sibling
        # text blocks are harness-injected (reminders), never user input.
        has_tool_result = any(
            isinstance(b, dict) and b.get("type") == "tool_result" for b in content
        )
        if not has_tool_result:
            texts = [
                b.get("text", "")
                for b in content
                if isinstance(b, dict) and b.get("type") == "text"
            ]
            texts = [
                t for t in texts
                if t and not any(marker in t for marker in HARNESS_TEXT_MARKERS)
            ]
            joined = "\n".join(texts)
            if joined:
                events.append(_text_fields({"type": "request", "ts": ts}, joined))
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") != "tool_result":
                continue
            tool_use_id = block.get("tool_use_id")
            ev = pending.pop(tool_use_id, None) if tool_use_id else None
            if ev is None:
                continue
            ev["exit"] = _resolve_claude_exit(block, obj.get("toolUseResult"))
            start_ts = ev.pop("_start_ts", None)
            if start_ts and ts:
                dur = _duration_ms(start_ts, ts)
                if dur is not None:
                    ev["duration_ms"] = dur
        return True
    return False


def _handle_claude_assistant_line(obj, ts, events, pending):
    message = obj.get("message")
    if not isinstance(message, dict):
        return False
    content = message.get("content")
    if not isinstance(content, list):
        return False
    usage = message.get("usage")
    tokens = None
    if isinstance(usage, dict):
        in_tok, out_tok = usage.get("input_tokens"), usage.get("output_tokens")
        if isinstance(in_tok, int) and isinstance(out_tok, int):
            tokens = in_tok + out_tok
    narration = [
        b.get("text", "")
        for b in content
        if isinstance(b, dict) and b.get("type") == "text"
    ]
    joined = "\n".join(t for t in narration if t)
    if joined:
        ev = _text_fields({"type": "narration", "ts": ts}, joined)
        if tokens is not None:
            ev["tokens"] = tokens
        events.append(ev)
    for block in content:
        if not isinstance(block, dict) or block.get("type") != "tool_use":
            continue
        name = block.get("name") or "unknown"
        tool_input = block.get("input") if isinstance(block.get("input"), dict) else {}
        tool_id = block.get("id")
        if name == "Skill":
            ev = {"type": "skill_invocation", "name": tool_input.get("skill") or "unknown", "ts": ts}
        elif name == "Agent":
            ev = {
                "type": "subagent",
                "agent_type": tool_input.get("name") or tool_input.get("description") or "unknown",
                "model": tool_input.get("model") or "unknown",
                "effort": "unknown",
                "ts": ts,
            }
        else:
            ev = {"type": "tool_call", "command": _claude_tool_command(name, tool_input), "exit": "unknown", "ts": ts}
            if ts:
                ev["_start_ts"] = ts
            if tool_id:
                pending[tool_id] = ev
        if tokens is not None:
            ev["tokens"] = tokens
        events.append(ev)
    return True


def _process_claude_file(path: Path, skip_sidechain: bool):
    events, parse_errors = [], []
    clean = total = 0
    session_id = None
    pending = {}
    try:
        lines = list(_read_lines(path))
    except OSError as exc:
        return events, 0, 0, [{"line": None, "error": f"cannot read file: {exc}"}], None
    for lineno, raw in lines:
        total += 1
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError as exc:
            parse_errors.append({"line": lineno, "error": f"invalid JSON: {exc}"})
            continue
        if not isinstance(obj, dict):
            parse_errors.append({"line": lineno, "error": "line is not a JSON object"})
            continue
        if session_id is None:
            sid = obj.get("sessionId")
            if isinstance(sid, str) and sid:
                session_id = sid
        line_type = obj.get("type")
        if line_type is None:
            parse_errors.append({"line": lineno, "error": "missing 'type' key"})
            continue
        ts = obj.get("timestamp")
        if skip_sidechain and obj.get("isSidechain") is True:
            # In the MAIN transcript only: inline sidechain echoes duplicate
            # content that the dedicated subagents/*.jsonl file (processed
            # separately, with skip_sidechain=False) carries authoritatively.
            clean += 1
            continue
        if line_type == "user":
            ok = _handle_claude_user_line(obj, ts, events, pending)
        elif line_type == "assistant":
            ok = _handle_claude_assistant_line(obj, ts, events, pending)
        else:
            ok = True  # recognized-but-unmapped harness bookkeeping record
        if ok:
            clean += 1
        else:
            parse_errors.append({"line": lineno, "error": f"'{line_type}' line missing expected message shape"})
    return events, clean, total, parse_errors, session_id


def extract_claude(path: Path) -> dict:
    path = Path(path)
    if path.is_dir():
        main_path = path / "main.jsonl"
        subagents_dir = path / "subagents"
    else:
        main_path = path
        subagents_dir = path.parent / path.stem / "subagents"

    session_id_default = path.name if path.is_dir() else path.stem
    agent_files = sorted(subagents_dir.rglob("agent-*.jsonl")) if subagents_dir.is_dir() else []
    if not main_path.is_file() and not agent_files:
        # Nothing readable at all: honest zero-confidence, matching
        # extract_codex's "no rollout file(s) found" fallback -- a bare
        # schema_confidence of 1.0 here would claim full trust in zero data.
        return _empty_trace(HOST_CLAUDE, session_id_default, f"no transcript file(s) found at {main_path}")

    all_events, parse_errors = [], []
    clean_total = line_total = 0
    session_id = None

    if main_path.is_file():
        events, clean, total, errs, sid = _process_claude_file(main_path, skip_sidechain=True)
        all_events.extend(events)
        clean_total += clean
        line_total += total
        parse_errors.extend(_tag_file_errors(errs, main_path))
        session_id = session_id or sid
    else:
        parse_errors.append({"line": None, "file": str(main_path), "error": "main transcript not found"})

    if subagents_dir.is_dir():
        for agent_file in agent_files:
            events, clean, total, errs, sid = _process_claude_file(agent_file, skip_sidechain=False)
            all_events.extend(events)
            clean_total += clean
            line_total += total
            parse_errors.extend(_tag_file_errors(errs, agent_file))
            session_id = session_id or sid

    if session_id is None:
        session_id = path.name if path.is_dir() else path.stem

    return _finalize(HOST_CLAUDE, session_id, all_events, clean_total, line_total, parse_errors)
