"""Codex rollout extraction support for the trace facade."""

from __future__ import annotations

import json
from pathlib import Path

try:  # in-repo package import
    from scripts.trace_render import (
    CODEX_BOILERPLATE_MARKERS,
    EXIT_CODE_RE,
    HOST_CODEX,
    SHELL_COMMAND_RE,
    _duration_ms,
    _empty_trace,
    _finalize,
    _read_lines,
    _tag_file_errors,
    _text_fields,
)
except ImportError:  # installed flat beside trace.py
    from trace_render import (
    CODEX_BOILERPLATE_MARKERS,
    EXIT_CODE_RE,
    HOST_CODEX,
    SHELL_COMMAND_RE,
    _duration_ms,
    _empty_trace,
    _finalize,
    _read_lines,
    _tag_file_errors,
    _text_fields,
)

def _is_codex_boilerplate(text: str) -> bool:
    return any(marker in text for marker in CODEX_BOILERPLATE_MARKERS)


def _extract_codex_command(payload):
    name = payload.get("name") or "unknown"
    arguments = payload.get("arguments")
    if isinstance(arguments, str):
        try:
            parsed = json.loads(arguments)
        except (json.JSONDecodeError, TypeError):
            parsed = None
        if isinstance(parsed, dict):
            command = parsed.get("command")
            if isinstance(command, list):
                return " ".join(str(part) for part in command)
            if isinstance(command, str) and command:
                return command
    tool_input = payload.get("input")
    if isinstance(tool_input, str):
        match = SHELL_COMMAND_RE.search(tool_input)
        if match:
            return match.group(1)
    return name


def _extract_codex_exit(payload):
    output = payload.get("output")
    parts = []
    if isinstance(output, str):
        parts.append(output)
    elif isinstance(output, list):
        for item in output:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
    match = EXIT_CODE_RE.search("\n".join(parts))
    if match:
        return int(match.group(1))
    return "unknown"


def _handle_codex_response_item(payload, ts, events, pending):
    ptype = payload.get("type")
    if ptype == "message":
        content = payload.get("content")
        if not isinstance(content, list):
            return False
        if payload.get("role") == "user":
            texts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "input_text"]
            joined = "\n".join(t for t in texts if t)
            if joined and not _is_codex_boilerplate(joined):
                events.append(_text_fields({"type": "request", "ts": ts}, joined))
        elif payload.get("role") == "assistant":
            texts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "output_text"]
            joined = "\n".join(t for t in texts if t)
            if joined:
                events.append(_text_fields({"type": "narration", "ts": ts}, joined))
        return True
    if ptype in ("custom_tool_call", "function_call"):
        call_id = payload.get("call_id")
        ev = {"type": "tool_call", "command": _extract_codex_command(payload), "exit": "unknown", "ts": ts}
        if ts:
            ev["_start_ts"] = ts
        events.append(ev)
        if call_id:
            pending[call_id] = ev
        return True
    if ptype in ("custom_tool_call_output", "function_call_output"):
        call_id = payload.get("call_id")
        ev = pending.pop(call_id, None) if call_id else None
        if ev is not None:
            ev["exit"] = _extract_codex_exit(payload)
            start_ts = ev.pop("_start_ts", None)
            if start_ts and ts:
                dur = _duration_ms(start_ts, ts)
                if dur is not None:
                    ev["duration_ms"] = dur
        return True
    return True  # reasoning, agent_message, and future kinds: recognized, unmapped


def _process_codex_file(path: Path):
    events, parse_errors = [], []
    clean = total = 0
    thread_meta = None
    spawn_event = None
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
        rtype = obj.get("type")
        if rtype is None:
            parse_errors.append({"line": lineno, "error": "missing 'type' key"})
            continue
        ts = obj.get("timestamp")
        payload = obj.get("payload")

        if rtype == "session_meta" and isinstance(payload, dict):
            thread_id = payload.get("id") or payload.get("session_id")
            source = payload.get("source")
            subagent_info = source.get("subagent") if isinstance(source, dict) else None
            thread_spawn = subagent_info.get("thread_spawn") if isinstance(subagent_info, dict) else None
            is_subagent = isinstance(thread_spawn, dict)
            thread_meta = {"thread_id": thread_id, "is_subagent": is_subagent}
            if is_subagent:
                depth = thread_spawn.get("depth")
                spawn_event = {
                    "type": "subagent",
                    "agent_type": thread_spawn.get("agent_nickname") or thread_spawn.get("agent_path") or "unknown",
                    "model": "unknown",
                    "effort": "unknown",
                    "parent": thread_spawn.get("parent_thread_id") or "unknown",
                    "depth": depth if isinstance(depth, int) else "unknown",
                    "ts": ts,
                }
                events.append(spawn_event)
            clean += 1
        elif rtype == "turn_context" and isinstance(payload, dict):
            model = payload.get("model")
            effort = payload.get("effort")
            if spawn_event is not None:
                if isinstance(model, str) and model and spawn_event["model"] == "unknown":
                    spawn_event["model"] = model
                if isinstance(effort, str) and effort and spawn_event["effort"] == "unknown":
                    spawn_event["effort"] = effort
            clean += 1
        elif rtype == "event_msg":
            clean += 1  # token_count / task_started / agent_reasoning: not mapped
        elif rtype == "response_item":
            if not isinstance(payload, dict):
                parse_errors.append({"line": lineno, "error": "response_item missing payload"})
                continue
            if _handle_codex_response_item(payload, ts, events, pending):
                clean += 1
            else:
                parse_errors.append({"line": lineno, "error": "response_item message with non-list content"})
        else:
            clean += 1  # world_state / compacted / future kinds: recognized, unmapped
    return events, clean, total, parse_errors, thread_meta


def extract_codex(path: Path) -> dict:
    path = Path(path)
    if path.is_file():
        files = [path]
    elif path.is_dir():
        files = sorted(path.rglob("*.jsonl"))
    else:
        files = []
    if not files:
        return _empty_trace(HOST_CODEX, path.stem, f"no rollout file(s) found at {path}")

    all_events, parse_errors = [], []
    clean_total = line_total = 0
    root_ids = []
    fallback_id = None
    for f in files:
        events, clean, total, errs, meta = _process_codex_file(f)
        all_events.extend(events)
        clean_total += clean
        line_total += total
        parse_errors.extend(_tag_file_errors(errs, f))
        if meta:
            if fallback_id is None:
                fallback_id = meta["thread_id"]
            if not meta["is_subagent"] and meta["thread_id"]:
                root_ids.append(meta["thread_id"])

    session_id = root_ids[0] if root_ids else (fallback_id or files[0].stem)
    return _finalize(HOST_CODEX, session_id, all_events, clean_total, line_total, parse_errors)
