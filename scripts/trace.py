#!/usr/bin/env python3
"""Session trace extractor. Stdlib-only, read-only, cross-platform.

Normalizes one Claude Code session or one Codex thread tree into a
single ordered trace: ``request``, ``narration``, ``skill_invocation``,
``subagent``, and ``tool_call`` events, plus durations and token counts
where the source data carries them. ``request`` and ``narration`` carry
``text`` (user prompt / agent's user-visible explanation), clipped at
``TEXT_CLIP`` with a ``truncated`` flag; harness-injected text
(system reminders, command wrappers) is never a request. The trace also
carries top-level ``runs_touched``: run ids harvested from ``.orch``
paths in tool calls, the join key to run state. Never writes under
``~/.claude`` or
``~/.codex``. Never raises past ``main`` and always exits 0 -- host
schemas drift, and nothing downstream may depend on this parser being
perfectly current (see ``schema_confidence`` and ``parse_errors``
below).

Degradation bar: a malformed or drifted input line is skipped and
recorded in ``parse_errors``; it never aborts extraction. Records with
an unrecognized-but-valid shape (harness bookkeeping, new event kinds)
are counted as cleanly parsed but simply produce no event -- schema
drift that adds new record kinds is not an error, only a record kind we
fail to interpret at all (bad JSON, or a message/response_item missing
its required shape) is.

Usage:
    trace.py --claude <session.jsonl-or-dir>       -> trace JSON on stdout
    trace.py --codex <rollout.jsonl-or-dir>        -> trace JSON on stdout
    trace.py --claude <path> --mermaid             -> Mermaid flowchart
    trace.py --codex <path> --mermaid              -> Mermaid flowchart
    trace.py --observations <trace.json...> [--run-state <repo>]
                                                    -> one finding per
                                                       line, friction-entry
                                                       shape, on stdout

``--claude PATH``: PATH is either the main transcript file (its sibling
directory ``<stem>/subagents/`` is read too, matching the live
``~/.claude/projects/<project>/<session-id>.jsonl`` +
``<session-id>/subagents/`` layout), or a self-contained directory
holding ``main.jsonl`` and ``subagents/``.

``--codex PATH``: PATH is one rollout file (one thread) or a directory
of rollout files (one thread per file; parent/child linked by
``source.subagent.thread_spawn.parent_thread_id``).

``--observations``: PATH arguments are already-extracted trace JSON
files (the output of ``--claude``/``--codex``). Mines three finding
classes -- repeated tool failure, pack/deliverable-kind misrouting
(needs ``--run-state``), and machinery ratio against a fixture-declared
budget (a sibling ``<trace>.budget.json`` with ``expected_event_budget``
and optional ``threshold``, default 1.0).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HOST_CLAUDE = "claude-code"
HOST_CODEX = "codex"

EXIT_CODE_RE = re.compile(r"[Ee]xit code:?\s*(-?\d+)")
SHELL_COMMAND_RE = re.compile(r'command["\']?\s*:\s*"((?:[^"\\]|\\.)*)"')
PACK_KIND_RE = re.compile(r"pack `orch-([a-z]+)-pack`")
RUN_ID_RE = re.compile(r"\.orch[/\\](?:runs|tickets)[/\\]([A-Za-z0-9][A-Za-z0-9._-]*)")
TEXT_CLIP = 2000  # chars kept of request/narration text; one owner
HARNESS_TEXT_MARKERS = ("<system-reminder>", "<command-name>", "<local-command-stdout>")
CODE_EXTENSIONS = (".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".rb", ".c", ".cpp", ".sh", ".ps1")
CONTENT_EXTENSIONS = (".md", ".docx", ".txt")
# Markup/style is ambiguous between the design and code kinds; both are
# observed so neither declaration false-positives. Research has no
# extension signal at all and is never inferred.
DESIGN_EXTENSIONS = (".html", ".css", ".scss", ".sass", ".less", ".svg")
ORCH_STATE_RE = re.compile(r"\.orch[/\\](?:runs|tickets)[/\\]")

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


# --------------------------------------------------------------------------
# shared helpers
# --------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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
    confidence = round(clean / total, 4) if total else 1.0
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


# --------------------------------------------------------------------------
# Claude Code adapter
# --------------------------------------------------------------------------

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


# --------------------------------------------------------------------------
# Codex adapter
# --------------------------------------------------------------------------

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


# --------------------------------------------------------------------------
# Mermaid rendering (criterion 5)
# --------------------------------------------------------------------------

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


# --------------------------------------------------------------------------
# Observations miner (criterion 4)
# --------------------------------------------------------------------------

def _kind_tokens(command: str):
    # Suffix matching over whitespace-split tokens: substring containment
    # would read ".css" as ".c" and ".config" as ".c".
    for raw in command.replace('"', " ").replace("'", " ").split():
        yield raw.rstrip(".,;:)]}").lower()


def _observed_kinds(trace: dict):
    kinds = set()
    for ev in trace.get("events", []):
        if ev.get("type") != "tool_call":
            continue
        command = str(ev.get("command", ""))
        if ORCH_STATE_RE.search(command):
            # Ticket and run bookkeeping is not deliverable work; every
            # executor writes its .md ticket regardless of pack.
            continue
        for token in _kind_tokens(command):
            if token.endswith(CODE_EXTENSIONS):
                kinds.add("code")
            if token.endswith(CONTENT_EXTENSIONS):
                kinds.add("content")
            if token.endswith(DESIGN_EXTENSIONS):
                kinds.add("design")
                kinds.add("code")
    return kinds


def _sole_host(hosts):
    hosts = {h for h in hosts if h}
    return hosts.pop() if len(hosts) == 1 else "unknown"


def _find_repeated_tool_failures(traces):
    # Total-count semantics: a command failing twice anywhere — inside one
    # trace or spread across several — is a repeat. Per-trace dedup would
    # make single-session mining unable to fire at all.
    counts = {}
    trace_paths_in = {}
    hosts_in = {}
    for path, trace in traces:
        for ev in trace.get("events", []):
            if ev.get("type") != "tool_call":
                continue
            exit_code = ev.get("exit")
            if isinstance(exit_code, int) and exit_code != 0:
                command = ev.get("command", "unknown")
                counts[command] = counts.get(command, 0) + 1
                trace_paths_in.setdefault(command, set()).add(str(path))
                hosts_in.setdefault(command, set()).add(trace.get("host", "unknown"))
    now = _now_iso()
    findings = []
    for command, count in sorted(counts.items()):
        if count >= 2:
            n_traces = len(trace_paths_in[command])
            unit = "traces" if n_traces != 1 else "trace"
            findings.append({
                "ts": now,
                "observed": f"command `{command}` failed with a nonzero exit {count} times across {n_traces} {unit}",
                "expected": "a repeated tool failure is fixed before reuse, not repeated unchanged",
                "category": "tool-failure",
                "host": _sole_host(hosts_in.get(command, set())),
                "source": "trace",
            })
    return findings


def _declared_pack_kinds(run_state: Path, run_ids=None):
    kinds = set()
    for spec_file in sorted(run_state.glob(".orch/runs/*/spec-*.md")):
        if run_ids is not None and spec_file.parent.name not in run_ids:
            continue
        try:
            text = spec_file.read_text(encoding="utf-8-sig")
        except OSError:
            continue
        match = PACK_KIND_RE.search(text)
        if match:
            kinds.add(match.group(1))
    return kinds


def _find_misrouting_pack(traces, run_state: Path):
    # A trace carrying runs_touched is judged against its own runs'
    # declared pack; one without keeps the all-runs unambiguity guard.
    # More than one declared kind in scope stays silent — never guess.
    findings = []
    global_kinds = None
    for _path, trace in traces:
        raw = trace.get("runs_touched")
        run_ids = [str(r) for r in raw] if isinstance(raw, list) else []
        if run_ids:
            kinds = _declared_pack_kinds(run_state, set(run_ids))
            scope = f"run(s) {sorted(run_ids)}"
        else:
            if global_kinds is None:
                global_kinds = _declared_pack_kinds(run_state)
            kinds = global_kinds
            scope = "run-state"
        if len(kinds) != 1:
            continue
        declared = next(iter(kinds))
        if declared not in ("code", "content", "design"):
            # research (and any future kind) has no extension signal; an
            # uninferable declaration is never judged.
            continue
        observed = _observed_kinds(trace)
        if observed and declared not in observed:
            findings.append({
                "ts": _now_iso(),
                "observed": f"trace shows deliverable kind(s) {sorted(observed)} but {scope} declares pack `orch-{declared}-pack`",
                "expected": "observed deliverable work matches the declared pack",
                "category": "misrouting",
                "host": trace.get("host", "unknown"),
                "source": "trace",
            })
    return findings


def _machinery_count(trace: dict) -> float:
    total = 0
    max_depth = 0
    for ev in trace.get("events", []):
        etype = ev.get("type")
        if etype in ("tool_call", "subagent", "skill_invocation"):
            total += 1
        if etype == "subagent":
            depth = ev.get("depth")
            if isinstance(depth, int):
                max_depth = max(max_depth, depth)
            else:
                max_depth = max(max_depth, 1)
    return total + max_depth


def _find_machinery_ratio(trace_paths):
    findings = []
    now = _now_iso()
    for path in trace_paths:
        budget_path = path.with_suffix(path.suffix + ".budget.json") if path.suffix != ".json" else path.with_name(path.stem + ".budget.json")
        if not budget_path.is_file():
            continue
        try:
            budget = json.loads(budget_path.read_text(encoding="utf-8"))
            trace = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        expected = budget.get("expected_event_budget")
        if not isinstance(expected, (int, float)) or expected <= 0:
            continue
        threshold = budget.get("threshold", 1.0)
        ratio = _machinery_count(trace) / expected
        if ratio > threshold:
            findings.append({
                "ts": now,
                "observed": f"machinery ratio {ratio:.2f} exceeds threshold {threshold} for {path.name}",
                "expected": f"mechanical event volume stays within the declared budget ({expected})",
                "category": "misrouting",
                "host": trace.get("host", "unknown"),
                "source": "trace",
            })
    return findings


def mine_observations(trace_paths, run_state):
    traces = []
    findings = []
    for p in trace_paths:
        p = Path(p)
        try:
            data = json.loads(p.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as exc:
            # An unreadable input must be visible in the output: a silent
            # skip makes "nothing read" indistinguishable from "no findings".
            findings.append({
                "ts": _now_iso(),
                "observed": f"trace input {p} unreadable: {exc}",
                "expected": "every mining input is read; an unreadable input is reported, never silently skipped",
                "category": "tool-failure",
                "host": "unknown",
                "source": "miner",
            })
            continue
        traces.append((p, data))

    findings.extend(_find_repeated_tool_failures(traces))
    if run_state is not None:
        findings.extend(_find_misrouting_pack(traces, Path(run_state)))
    findings.extend(_find_machinery_ratio([Path(p) for p in trace_paths]))
    return findings


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--claude", metavar="PATH", help="extract a trace from one Claude Code session")
    parser.add_argument("--codex", metavar="PATH", help="extract a trace from one Codex thread tree")
    parser.add_argument("--observations", nargs="+", metavar="TRACE", help="mine already-extracted trace JSON files")
    parser.add_argument("--run-state", metavar="REPO", help="repo root, for pack/deliverable-kind misrouting checks")
    parser.add_argument("--mermaid", action="store_true", help="render the extracted trace as a Mermaid flowchart")
    return parser


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    # Windows consoles default stdout to a legacy codepage (e.g. cp1252) that
    # cannot encode arbitrary transcript content (emoji, non-Latin text).
    # ensure_ascii keeps JSON output byte-safe regardless; this reconfigure
    # additionally protects the Mermaid text path.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.observations:
            for finding in mine_observations(args.observations, args.run_state):
                print(json.dumps(finding, ensure_ascii=True))
            return 0
        if args.claude:
            trace = extract_claude(Path(args.claude))
        elif args.codex:
            trace = extract_codex(Path(args.codex))
        else:
            parser.print_usage(sys.stderr)
            return 2
        if args.mermaid:
            sys.stdout.write(render_mermaid(trace))
        else:
            print(json.dumps(trace, ensure_ascii=True, indent=2))
        return 0
    except Exception as exc:  # degradation bar: never crash, never non-zero
        host = HOST_CODEX if args.codex else HOST_CLAUDE
        session_id = Path(args.codex or args.claude or "unknown").stem
        print(json.dumps(_empty_trace(host, session_id, f"unexpected failure: {exc}"), ensure_ascii=True))
        return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
