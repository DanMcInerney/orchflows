"""Read native Claude/Codex history without writing logs or resuming agents."""

from __future__ import annotations

import base64
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sqlite3


def native_home(host, override=None):
    key = "CODEX_HOME" if host == "codex" else "CLAUDE_CONFIG_DIR"
    return Path(override or os.environ.get(key) or Path.home() / ("." + host)).expanduser().resolve()


def _json(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _text(value):
    return value if isinstance(value, str) else _json(value)


def _clean(value):
    if isinstance(value, str) and value.startswith("gAAAA"):
        return {"unavailable": "encrypted", "characters": len(value)}
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_clean(v) for v in value]
    return value


def _decoded(value):
    if isinstance(value, str):
        try:
            return _clean(json.loads(value))
        except ValueError:
            pass
    return _clean(value)


def _catalog(host, home, identifier=None):
    entries, gaps = {}, []
    if host == "codex":
        databases = sorted(home.glob("state_*.sqlite"), key=lambda p: int(p.stem.split("_")[-1])
                           if p.stem.split("_")[-1].isdigit() else -1, reverse=True)
        if not databases:
            raise ValueError(f"Codex index not found under {home}")
        try:
            with closing(sqlite3.connect(databases[0].as_uri() + "?mode=ro", uri=True)) as db:
                db.execute("BEGIN")
                for row in db.execute("SELECT id, rollout_path, cwd, title, created_at, updated_at FROM threads"):
                    entries[row[0]] = {"id": row[0], "path": str(row[1]), "parent_id": None, "cwd": row[2],
                                       "title": row[3], "created_at": row[4], "updated_at": row[5]}
                for parent, child in db.execute("SELECT parent_thread_id, child_thread_id FROM thread_spawn_edges"):
                    if child in entries:
                        entries[child]["parent_id"] = parent
                    else:
                        gaps.append({"kind": "missing_child_record", "id": child, "parent_id": parent})
        except sqlite3.Error as exc:
            raise ValueError(f"Codex index unreadable: {databases[0]}: {exc}") from exc
    else:
        parents = list((home / "projects").glob(f"*/{identifier or '*'}.jsonl"))
        if identifier and not parents:
            matches = list((home / "projects").glob(f"*/*/subagents/agent-{identifier}.jsonl"))
            parents = [path.parent.parent.with_suffix(".jsonl") for path in matches]
        for path in parents:
            if path.stem in entries:
                raise ValueError(f"Ambiguous native session ID {path.stem}")
            entries[path.stem] = {"id": path.stem, "path": str(path), "parent_id": None}
        child_paths = (list((home / "projects").glob("*/*/subagents/agent-*.jsonl")) if identifier is None else
                       [child for parent in parents for child in parent.with_suffix("").joinpath("subagents").glob("agent-*.jsonl")])
        for path in child_paths:
            child = path.stem.removeprefix("agent-")
            entry = {"id": child, "path": str(path), "parent_id": path.parent.parent.name}
            try:
                meta = json.loads(path.with_suffix(".meta.json").read_text(encoding="utf-8"))
                entry["parent_id"] = meta.get("parentAgentId") or entry["parent_id"]
                entry["name"] = meta.get("name") or meta.get("description") or meta.get("agentType")
                entry["agent_type"], entry["spawn_call_id"] = meta.get("agentType"), meta.get("toolUseId")
            except (OSError, ValueError, AttributeError) as exc:
                gaps.append({"kind": "metadata_unavailable", "id": child, "detail": str(exc)})
            if child in entries:
                raise ValueError(f"Ambiguous native agent ID {child}")
            entries[child] = entry
    return entries, gaps


def _locate(host, identifier, home):
    if host not in {"claude", "codex"} or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", identifier):
        raise ValueError("Supply a native host and session/agent ID, not a path")
    entries, gaps = _catalog(host, home, identifier)
    if identifier not in entries:
        raise ValueError(f"Native ID {identifier} not found under {home}" + (f"; {gaps[:3]}" if gaps else ""))
    return entries, gaps


def _records(path, offset=0, line_number=1):
    with path.open("rb") as stream:
        stream.seek(offset)
        while raw := stream.readline():
            start = stream.tell() - len(raw)
            try:
                value = json.loads(raw)
                if not isinstance(value, dict):
                    raise ValueError("Record is not an object")
            except (ValueError, UnicodeError) as exc:
                value = {"_gap": "incomplete_tail" if not raw.endswith(b"\n") else "malformed_record",
                         "detail": str(exc)}
            yield start, line_number, raw, value
            line_number += 1


def _timestamp(value):
    try:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return datetime.fromtimestamp(value, timezone.utc)
        if isinstance(value, str):
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if len(value) == 10:
                parsed = parsed.replace(tzinfo=timezone.utc)
            if parsed.tzinfo is not None:
                return parsed.astimezone(timezone.utc)
    except (ValueError, OverflowError, OSError):
        pass
    return None


def _window(since, until):
    start, end = _timestamp(since), _timestamp(until)
    if (since is not None and start is None) or (until is not None and end is None):
        raise ValueError("Dates must be YYYY-MM-DD (UTC) or ISO timestamps with a timezone")
    if start and end and start >= end:
        raise ValueError("--since must be earlier than --until")
    return start, end


def _file_metadata(path, project=None):
    metadata = {}
    for _, line, _, record in _records(path):
        if record.get("cwd"):
            metadata["cwd"] = record["cwd"]
        if _timestamp(record.get("timestamp")):
            metadata.setdefault("created_at", record["timestamp"])
        if (metadata.get("cwd") and metadata.get("created_at")) or line >= 100:
            break
    if project and metadata.get("cwd") and project not in metadata["cwd"].replace("\\", "/").casefold():
        return metadata
    with path.open("rb") as stream:
        position = stream.seek(0, 2)
        remainder = b""
        while position or remainder:
            start = max(0, position - 65536)
            stream.seek(start)
            lines = (stream.read(position - start) + remainder).split(b"\n")
            remainder = lines.pop(0) if start else b""
            for raw in reversed(lines):
                try:
                    record = json.loads(raw)
                except (ValueError, UnicodeError):
                    continue
                if isinstance(record, dict) and _timestamp(record.get("timestamp")):
                    metadata["updated_at"] = record["timestamp"]
                    return metadata
            position = start
    return metadata


def find(host, home, since=None, until=None, project=None, limit=30, after=None):
    start, end = _window(since, until)
    project = project.replace("\\", "/").casefold().rstrip("/") if project else None
    if project == "":
        raise ValueError("--project must contain a recorded path or name fragment")
    scope = [host, str(home), start.isoformat() if start else None, end.isoformat() if end else None, project]
    last = ""
    if after:
        try:
            old_scope, last = json.loads(base64.urlsafe_b64decode(after))
            if old_scope != scope or not isinstance(last, str):
                raise ValueError()
        except (ValueError, TypeError) as exc:
            raise ValueError("Invalid discovery cursor or changed filters; find from the start") from exc
    entries, gaps = _catalog(host, home)
    matches, scanned = [], 0
    for entry in sorted(entries.values(), key=lambda item: item["id"]):
        if entry["id"] <= last:
            continue
        scanned += 1
        entry = entry.copy()
        if host == "claude":
            try:
                entry.update(_file_metadata(Path(entry["path"]), project))
            except OSError as exc:
                entry["read_gap"] = str(exc)
        first, latest = _timestamp(entry.get("created_at")), _timestamp(entry.get("updated_at"))
        # These are candidate bounds. A long-lived session may have no events
        # inside the window; history read applies the exact timestamp filter.
        if (start and latest and latest < start) or (end and first and first >= end):
            continue
        cwd = entry.get("cwd")
        if project and cwd and project not in cwd.replace("\\", "/").casefold():
            continue
        entry["scope_unknown"] = (["project"] if project and not cwd else []) + (
            ["dates"] if (start or end) and not (first and latest) else [])
        entry["created_at"] = first.isoformat() if first else None
        entry["updated_at"] = latest.isoformat() if latest else None
        entry["transcript_available"] = Path(entry["path"]).is_file()
        matches.append(entry)
        if len(matches) > limit:
            break
    page = matches[:limit]
    return {"host": host, "native_home": str(home), "since": scope[2], "until": scope[3], "project": project,
            "candidates": page, "page_count": len(page), "scanned_count": scanned,
            "next_cursor": base64.urlsafe_b64encode(_json([scope, page[-1]["id"]]).encode()).decode()
            if len(matches) > limit else None,
            "discovery_gaps": gaps[:20], "discovery_gap_count": len(gaps),
            "note": "Candidates include sessions and subagents; their date bounds may hold no events in the window, so read "
                    "with the same dates. Project matches recorded cwd text, not repository identity."}


def _events(host, record):
    if "_gap" in record:
        return [{"kind": "gap", "data": record}]
    timestamp = record.get("timestamp")
    result = []
    if host == "claude":
        message = record.get("message", {})
        blocks = message.get("content", []) if isinstance(message, dict) else []
        if isinstance(blocks, str):
            blocks = [{"type": "text", "text": blocks}]
        if not isinstance(blocks, list):
            return [{"kind": "unsupported", "record_type": record.get("type"), "timestamp": timestamp}]
        for block in blocks:
            if not isinstance(block, dict):
                continue
            kind = block.get("type")
            if kind == "tool_use":
                result.append({"kind": "tool_call", "call_id": block.get("id"), "tool": block.get("name"),
                               "data": _clean(block.get("input"))})
            elif kind == "tool_result":
                result.append({"kind": "tool_result", "call_id": block.get("tool_use_id"),
                               "is_error": bool(block.get("is_error")), "presented_output": _clean(block.get("content")),
                               "data": _clean(record.get("toolUseResult"))})
            elif kind == "text":
                result.append({"kind": "message", "role": record.get("type"), "data": block.get("text", "")})
            elif kind not in {"thinking", "redacted_thinking"}:
                result.append({"kind": "native_content", "data": _clean(block)})
        if not blocks:
            result.append({"kind": "native_record", "record_type": record.get("type"),
                           "subtype": record.get("subtype"), "available_keys": list(record)})
    else:
        payload = record.get("payload", {})
        if not isinstance(payload, dict):
            return [{"kind": "unsupported", "record_type": record.get("type"), "timestamp": timestamp}]
        kind = payload.get("type")
        if record.get("type") == "response_item":
            if kind in {"function_call", "custom_tool_call"}:
                result.append({"kind": "tool_call", "call_id": payload.get("call_id"), "tool": payload.get("name"),
                               "data": _decoded(payload.get("arguments", payload.get("input")))})
            elif kind in {"function_call_output", "custom_tool_call_output"}:
                result.append({"kind": "tool_result", "call_id": payload.get("call_id"),
                               "presented_output": _decoded(payload.get("output"))})
            elif kind == "agent_message" or (kind == "message" and payload.get("role") in {"user", "assistant"}):
                result.append({"kind": kind, "role": payload.get("role"), "author": payload.get("author"),
                               "recipient": payload.get("recipient"), "data": _clean(payload.get("content"))})
            elif kind not in {"reasoning", "message"}:
                result.append({"kind": "unsupported", "record_type": kind, "available_keys": list(payload)})
        elif record.get("type") == "event_msg":
            item = payload.get("item", {})
            if kind in {"item_started", "item_completed"}:
                if not isinstance(item, dict):
                    return [{"kind": "unsupported", "record_type": kind, "timestamp": timestamp}]
                item_kind = item.get("type")
                if item_kind == "CommandExecution":
                    result.append({"kind": "command", "native_id": item.get("id"), "status": item.get("status"),
                                   "exit_code": item.get("exit_code"), "data": {k: item.get(k) for k in ["command", "cwd", "duration"]},
                                   "captured_output": item.get("stdout", ""),
                                   "stderr": item.get("stderr", ""), "presented_output": item.get("formatted_output")})
                elif item_kind not in {"AgentMessage", "UserMessage", "Reasoning"}:
                    item_result = item.get("result")
                    failed = item.get("status") == "failed" or (isinstance(item_result, dict) and bool(item_result.get("isError")))
                    result.append({"kind": "agent_activity" if item_kind in {"SubAgentActivity", "CollabAgentToolCall"} else "native_activity",
                                   "native_id": item.get("id"), "record_type": item_kind,
                                   "is_error": failed,
                                   "data": _clean(item)})
            elif kind in {"task_started", "task_complete", "turn_aborted", "error", "agent_message", "user_message"}:
                result.append({"kind": "lifecycle" if kind not in {"agent_message", "user_message"} else "message",
                               "record_type": kind, "data": _clean(payload)})
            elif kind not in {"token_count", "thread_settings_applied"}:
                result.append({"kind": "unsupported", "record_type": kind, "available_keys": list(payload)})
        elif record.get("type") in {"session_meta", "turn_context", "world_state", "compacted"}:
            result.append({"kind": "context", "record_type": record.get("type"), "available_keys": list(payload)})
        elif record.get("type") not in {"token_usage_record", "inter_agent_communication_metadata"}:
            result.append({"kind": "unsupported", "record_type": record.get("type"), "available_keys": list(record)})
    for event in result:
        event["timestamp"] = timestamp
    return result


def _sidecars(event, home):
    # Only explicit native spill markers are followed, never arbitrary paths in a tool response.
    value = event.get("presented_output", "")
    text = value if isinstance(value, str) else "\n".join(_strings(value))
    found = []
    for name in re.findall(r"Full output saved to: ([^\r\n]+)", text):
        path = Path(name.strip()).expanduser().resolve()
        state = "available" if path.is_file() else "missing"
        if not path.is_relative_to(home):
            state = "outside_native_home"
        found.append({"path": str(path), "state": state})
    return found


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _strings(child)


def _flags(event):
    text = _json(event)
    flags = []
    if '"unavailable":"encrypted"' in text:
        flags.append("encrypted_content")
    output = "\n".join(_strings(event.get("presented_output", "")))
    if re.search(r"Warning: truncated output|Output truncated|\d+ (?:chars|tokens) truncated|<persisted-output>", output):
        flags.append("output_shortened_or_spilled")
    if event["kind"] in {"gap", "unsupported"}:
        flags.append(event["kind"])
    return flags


def _preview(event, size=600):
    result = event.copy()
    for field in ("data", "captured_output", "presented_output", "stderr"):
        if field in result:
            text = _text(result[field])
            result[field] = {"text": text[:size], "characters": len(text), "truncated": len(text) > size}
    return result


def _runtime(host, record):
    """Model and effort a record says ran; launch requests and subagent metadata are not evidence."""
    if host == "claude":
        message = record.get("message")
        if record.get("type") != "assistant" or not isinstance(message, dict):
            return None
        return message.get("model") or "unknown", record.get("effort") or "unknown"
    payload = record.get("payload")
    if record.get("type") != "turn_context" or not isinstance(payload, dict):
        return None
    return payload.get("model") or "unknown", payload.get("effort") or "unknown"


# A child is fresh when it starts from only its assignment and inherited when it starts with parent history.
# Omitted arguments take each host's own declared default: Codex multi-agent v1 declares that `fork_context`
# false or omitted starts with only the initial prompt; v2 declares that omitted or "all" `fork_turns` is a
# full-history fork; Claude Code's built-in `fork` type is selected only explicitly and is never the default.
_OMITTED_DEFAULT = {"codex-v1": "fresh", "codex-v2": "inherited", "claude": "fresh"}


def _js_code(source):
    """Blank string, template and comment contents so brackets and keys reflect code only.

    A quoted property name (`"fork_context": true`) keeps its identifier so the key stays visible."""
    chars, index, size = list(source), 0, len(source)
    while index < size:
        char = source[index]
        if char in "\"'`":
            end = index + 1
            while end < size and source[end] != char:
                end += 2 if source[end] == "\\" else 1
            start, stop, index = index + 1, min(end, size), end + 1
            if (char != "`" and re.fullmatch(r"[A-Za-z_$][\w$]*", source[start:stop])
                    and re.match(r"\s*:", source[index:])):
                continue
        elif source.startswith(("//", "/*"), index):
            close = "\n" if source[index + 1] == "/" else "*/"
            found = source.find(close, index + 2)
            start, stop = index, size if found < 0 else found
            index = stop + len(close)
        else:
            index += 1
            continue
        chars[start:stop] = " " * (stop - start)
    return "".join(chars)


def _v1_forks(source):
    """`fork_context` of each multi-agent v1 spawn site in exec code: true, false, omitted or expression."""
    code, sites = _js_code(source), []
    for match in re.finditer(r"\bmulti_agent_v1__spawn_agent\s*\(\s*", code):
        depth, top = 0, []
        for char in code[match.end():]:
            depth += (char in "{[(") - (char in "}])")
            if depth <= 0:
                break
            top.append(char if depth == 1 else " ")
        text = "".join(top)
        value = re.search(r"\bfork_context[\"']?\s*:\s*(true|false)\b", text)
        if not text.startswith("{") or (not value and re.search(r"\bfork_context\b|\.\.\.", text)):
            sites.append("expression")
        else:
            sites.append(value.group(1) == "true" if value else "omitted")
    return sites


def _indicates(api, arguments):
    """Launch context one spawn site's arguments select, or None when they do not determine it."""
    key = {"codex-v1": "fork_context", "codex-v2": "fork_turns", "claude": "subagent_type"}.get(api)
    value = arguments.get(key, "omitted")
    if key is None or value == "omitted":
        return _OMITTED_DEFAULT.get(api)
    if api == "codex-v1":
        return "inherited" if value is True else "fresh" if value is False else None
    if api == "codex-v2":
        return "fresh" if value == "none" else "inherited" if value == "all" or str(value).isdigit() else None
    return ("inherited" if value == "fork" else "fresh") if isinstance(value, str) else None


def _item_indicates(item, version):
    api = item["api"] or (f"codex-{version}" if version in {"v1", "v2"} else None)
    options = {_indicates(api, arguments) for arguments in item["arguments"]}
    return options.pop() if len(options) == 1 else None


class _Spawns:
    """Spawn calls in one transcript, each linked to the child it created where the records name it."""

    def __init__(self, host):
        self.host, self.items, self.exec_calls, self.pending = host, [], {}, {}

    def _add(self, call_id, line, api, tool, arguments, pending=True, **extra):
        item = {"source": "spawn_call", "api": api, "tool": tool, "call_id": call_id, "line": line,
                "arguments": arguments, **extra}
        self.items.append(item)
        if pending and call_id:
            self.pending[call_id] = item

    def feed(self, record, line):
        if self.host == "claude":
            message = record.get("message")
            blocks = message.get("content") if isinstance(message, dict) else None
            blocks = [b for b in blocks if isinstance(b, dict)] if isinstance(blocks, list) else []
            for block in blocks:
                if block.get("type") == "tool_use" and block.get("name") in {"Agent", "Task"}:
                    data = block.get("input") if isinstance(block.get("input"), dict) else {}
                    self._add(block.get("id"), line, "claude", block.get("name"),
                              [{"subagent_type": data.get("subagent_type", "omitted")}])
            results = [b.get("tool_use_id") for b in blocks if b.get("type") == "tool_result"]
            outcome = record.get("toolUseResult")
            # One toolUseResult per record, so only a single-result record names its child.
            if len(results) == 1 and results[0] in self.pending and isinstance(outcome, dict) and outcome.get("agentId"):
                self.pending.pop(results[0])["child_id"] = outcome["agentId"]
            return
        payload = record.get("payload")
        if not isinstance(payload, dict):
            return
        kind, call = payload.get("type"), payload.get("call_id")
        if record.get("type") == "response_item":
            if kind == "custom_tool_call" and payload.get("name") == "exec":
                source = payload.get("input")
                self.exec_calls[call] = (line, _v1_forks(source) if isinstance(source, str) else [])
            elif kind == "custom_tool_call_output":
                self.exec_calls.pop(call, None)
            elif kind == "function_call" and payload.get("name") == "spawn_agent":
                data = _decoded(payload.get("arguments"))
                data = data if isinstance(data, dict) else {}
                api = "codex-v1" if "fork_context" in data else "codex-v2" if "fork_turns" in data else None
                self._add(call, line, api, "spawn_agent",
                          [{k: data[k] for k in ("fork_context", "fork_turns") if k in data}])
            elif kind == "function_call_output" and call in self.pending:
                output, item = _decoded(payload.get("output")), self.pending.pop(call)
                if isinstance(output, dict):
                    item.update(child_id=output.get("agent_id"), agent_path=output.get("task_name"))
            return
        item = payload.get("item")
        if not (record.get("type") == "event_msg" and kind == "item_completed" and isinstance(item, dict)
                and item.get("type") == "CollabAgentToolCall" and item.get("tool") == "spawn_agent"):
            return
        for child in item.get("receiver_thread_ids") or []:
            if len(self.exec_calls) == 1:
                call, (call_line, sites) = next(iter(self.exec_calls.items()))
                self._add(call, call_line, "codex-v1", "exec", [{"fork_context": s} for s in sites],
                          pending=False, child_id=child)
            elif self.exec_calls:
                self._add(None, line, "codex-v1", "exec", [], pending=False, child_id=child,
                          detail=f"spawned while {len(self.exec_calls)} exec calls were open")
            elif len(self.pending) == 1:
                next(iter(self.pending.values())).setdefault("child_id", child)


def _child_record(host, entry):
    """What a child's own records say about its start, with its multi-agent version and path (Codex)."""
    if host == "claude":
        kind = entry.get("agent_type")
        return {"source": "child_record", "agent_type": kind,
                "indicates": None if kind is None else "inherited" if kind == "fork" else "fresh"}, None, None
    meta = {}
    try:
        for _, line, _, record in _records(Path(entry["path"])):
            if record.get("type") == "session_meta" and isinstance(record.get("payload"), dict):
                meta = record["payload"]
            if meta or line >= 5:
                break
    except OSError:
        pass
    forked = meta.get("forked_from_id")
    # Absent fork markers are not proof of a fresh start; only the spawn call can show that.
    return {"source": "child_record", "forked_from_id": forked,
            "history_start_ordinal": meta.get("subagent_history_start_ordinal"),
            "multi_agent_version": meta.get("multi_agent_version"),
            "indicates": "inherited" if forked else None}, meta.get("multi_agent_version"), meta.get("agent_path")


def _own_history_line(record):
    """First line of a forked Codex child's own records; earlier lines replay its parent's history.

    Codex writes the child's session_meta on line 1 and counts `subagent_history_start_ordinal` from the
    record after it, so the child's own history starts on line ordinal + 2."""
    ordinal = record.get("history_start_ordinal")
    if record.get("forked_from_id") and type(ordinal) is int and ordinal >= 0:
        return ordinal + 2
    return 1


def _links(item, entry, agent_path):
    return (item.get("child_id") == entry["id"] or bool(item["call_id"] and item["call_id"] == entry.get("spawn_call_id"))
            or bool(agent_path and item.get("agent_path") == agent_path))


def _launch(entry, header, spawns):
    """Launch context from the child's records and linked spawn calls; any inherited evidence wins."""
    record, version, agent_path = header
    evidence = [record] + [{**item, "indicates": _item_indicates(item, version)}
                           for item in spawns if _links(item, entry, agent_path)]
    says = {item["indicates"] for item in evidence}
    return ("inherited" if "inherited" in says else "fresh" if "fresh" in says else "unknown"), evidence


def _record_events(path, host, start, number, record):
    for index, event in enumerate(_events(host, record)):
        event["event_id"] = f"{start}:{index}"
        event["source"] = {"path": str(path), "line": number, "byte_offset": start}
        event["flags"] = _flags(event)
        yield event, index


def _located_events(path, host, offset=0, line=1):
    for start, number, raw, record in _records(path, offset, line):
        for event, index in _record_events(path, host, start, number, record):
            yield event, raw, index


def inspect(host, identifier, home, limit=30, after=None):
    entries, gaps = _locate(host, identifier, home)
    children = {}
    for entry in entries.values():
        children.setdefault(entry["parent_id"], []).append(entry["id"])
    pending, selected, seen = [identifier], [], set()
    while pending:
        current = pending.pop(0)
        if current in seen:
            gaps.append({"kind": "cyclic_parent_link", "id": current})
            continue
        seen.add(current)
        selected.append(current)
        pending.extend(sorted(children.get(current, [])))
    if after:
        if after not in selected:
            raise ValueError("Inspection cursor is not in this agent tree")
        selected_page = selected[selected.index(after) + 1:][:limit]
    else:
        selected_page = selected[:limit]
    spawn_cache, header_cache = {}, {}

    def spawns_of(agent):
        if agent not in spawn_cache:
            collector = _Spawns(host)
            try:
                for _, number, _, record in _records(Path(entries[agent]["path"])):
                    collector.feed(record, number)
            except OSError:
                pass
            spawn_cache[agent] = collector.items
        return spawn_cache[agent]

    def header_of(agent):
        if agent not in header_cache:
            header_cache[agent] = _child_record(host, entries[agent])
        return header_cache[agent]

    agents = []
    for current in selected_page:
        entry = entries[current].copy()
        counts, tools, flags, models, efforts = Counter(), Counter(), Counter(), Counter(), Counter()
        calls, results, errors, gap_events = {}, set(), [], []
        latest = None
        path = Path(entry["path"])
        collector = _Spawns(host)
        own_from = _own_history_line(header_of(current)[0]) if host == "codex" else 1
        try:
            for start, number, _, record in _records(path):
                collector.feed(record, number)
                runtime = _runtime(host, record) if number >= own_from else None
                if runtime:
                    models[runtime[0]] += 1
                    efforts[runtime[1]] += 1
                for event, _ in _record_events(path, host, start, number, record):
                    counts[event["kind"]] += 1
                    flags.update(event["flags"])
                    latest = _preview(event, 180)
                    if event["kind"] == "tool_call":
                        calls[event["call_id"]] = {k: event.get(k) for k in ("call_id", "tool", "event_id", "source")}
                        tools[event["tool"]] += 1
                    elif event["kind"] == "tool_result":
                        results.add(event["call_id"])
                    for sidecar in _sidecars(event, home):
                        if sidecar["state"] != "available":
                            flags[sidecar["state"]] += 1
                    if event.get("is_error") or event.get("exit_code") not in {None, 0} or event.get("record_type") == "error":
                        errors.append(_preview(event, 160))
                    if event["kind"] in {"gap", "unsupported"}:
                        gap_events.append(_preview(event, 160))
        except OSError as exc:
            entry["read_gap"] = str(exc)
        spawn_cache[current] = collector.items
        unmatched = [v for k, v in calls.items() if k not in results]
        entry.update(events=dict(counts), tools=dict(tools), models=dict(models), efforts=dict(efforts),
                     flags=dict(flags), latest_recorded=latest,
                     calls_without_recorded_results=unmatched[:20], unmatched_count=len(unmatched),
                     errors=errors[-5:], error_count=len(errors), gaps=gap_events[:5], gap_count=len(gap_events))
        if entry["parent_id"] is not None:
            parent = entry["parent_id"]
            entry["launch_context"], entry["launch_evidence"] = _launch(
                entry, header_of(current), spawns_of(parent) if parent in entries else [])
        unlinked = [{**item, "indicates": _item_indicates(item, None)} for item in collector.items
                    if not any(_links(item, entries[child], header_of(child)[2]) for child in children.get(current, []))]
        entry.update(spawn_count=len(collector.items), unlinked_spawns=unlinked[:10], unlinked_spawn_count=len(unlinked))
        agents.append(entry)
    return {"host": host, "root_id": identifier, "native_home": str(home), "agents": agents,
            "agent_count": len(selected), "discovery_gaps": gaps[:20], "discovery_gap_count": len(gaps),
            "next_cursor": selected_page[-1] if selected_page and selected_page[-1] != selected[-1] else None,
            "note": "Recorded activity is not proof of current process state or workflow success. Rerun inspect to discover newly spawned agents. "
                    "models/efforts tally what native records say ran; unknown means the record omitted it. "
                    "launch_context is fresh (assignment only), inherited (parent history) or unknown, from the child's records "
                    "and the linked spawn call; unlinked_spawns are spawn calls no recorded child could be tied to."}


def _cursor(path, event, raw, index):
    data = [str(path), event["source"]["byte_offset"], event["source"]["line"], index + 1, len(raw)]
    return base64.urlsafe_b64encode(_json(data).encode()).decode()


def read(host, identifier, home, limit=30, after=None, event_id=None, field="data", offset=0, chars=12000,
         since=None, until=None):
    window_start, window_end = _window(since, until)
    entries, gaps = _locate(host, identifier, home)
    path = Path(entries[identifier]["path"])
    start, line, skip = 0, 1, 0
    if after:
        try:
            old_path, start, line, skip, length = json.loads(base64.urlsafe_b64decode(after))
            if (old_path != str(path) or not all(type(x) is int and x >= 0 for x in (start, line, skip, length))
                    or line < 1):
                raise ValueError()
            # The cursor's record must still start a line and keep its length.
            with path.open("rb") as stream:
                stream.seek(max(start - 1, 0))
                if start and stream.read(1) != b"\n":
                    raise ValueError()
                if len(stream.readline()) != length:
                    raise ValueError()
        except (ValueError, TypeError) as exc:
            raise ValueError("Invalid cursor or changed/truncated source; read from the start") from exc
    if event_id:
        try:
            start, wanted = map(int, event_id.split(":"))
            if start < 0 or wanted < 0:
                raise ValueError()
        except ValueError as exc:
            raise ValueError("Event ID must be BYTE_OFFSET:INDEX from a previous read") from exc
        with path.open("rb") as stream:
            while stream.tell() < start:
                if not stream.readline():
                    raise ValueError("Event offset is beyond the transcript")
                line += 1
            if stream.tell() != start:
                raise ValueError("Event offset is not a record boundary")
        for event, _, index in _located_events(path, host, start, line):
            if event["source"]["byte_offset"] != start:
                break
            if index != wanted:
                continue
            sidecars = _sidecars(event, home)
            if field == "sidecar":
                if len(sidecars) != 1 or sidecars[0]["state"] != "available":
                    raise ValueError(f"Expected one available native output sidecar: {sidecars}")
                with Path(sidecars[0]["path"]).open(encoding="utf-8", errors="replace") as stream:
                    remaining = offset
                    while remaining:
                        chunk = stream.read(min(65536, remaining))
                        if not chunk:
                            break
                        remaining -= len(chunk)
                    text = stream.read(chars + 1)
                content, more = text[:chars], len(text) > chars
            else:
                if field not in event:
                    raise ValueError(f"Field {field} unavailable; event fields: {list(event)}")
                text = _text(event[field])
                content, more = text[offset:offset + chars], offset + chars < len(text)
            return {"host": host, "id": identifier, "event_id": event_id, "source": event["source"],
                    "field": field, "offset": offset, "text": content, "next_offset": offset + len(content) if more else None,
                    "flags": event["flags"], "sidecars": sidecars}
        raise ValueError("Event not found")
    events, cursor, has_more = [], None, False
    for event, raw, index in _located_events(path, host, start, line):
        if event["source"]["byte_offset"] == start and index < skip:
            continue
        if window_start or window_end:
            timestamp = _timestamp(event.get("timestamp"))
            if timestamp is None:
                event["flags"].append("timestamp_unavailable")
            elif (window_start and timestamp < window_start) or (window_end and timestamp >= window_end):
                cursor = _cursor(path, event, raw, index) if raw.endswith(b"\n") else cursor
                continue
        if len(events) == limit:
            has_more = True
            break
        event["sidecars"] = _sidecars(event, home)
        events.append(_preview(event))
        # A line still being written changes length when it completes, so the cursor stays before it.
        cursor = _cursor(path, event, raw, index) if raw.endswith(b"\n") else cursor
    # Keep the last cursor even at EOF so a caller can poll an append-only transcript.
    return {"host": host, "id": identifier, "events": events, "next_cursor": cursor or after, "has_more": has_more,
            "since": window_start.isoformat() if window_start else None, "until": window_end.isoformat() if window_end else None,
            "discovery_gaps": gaps[:20], "discovery_gap_count": len(gaps)}


def add_parser(commands):
    parser = commands.add_parser("history", help="Read native agent logs without changing them")
    subcommands = parser.add_subparsers(dest="history_command", required=True)
    for action in ("find", "inspect", "read"):
        child = subcommands.add_parser(action)
        child.add_argument("host", choices=["codex", "claude"])
        if action != "find":
            child.add_argument("identifier", help="Native session or agent ID")
        child.add_argument("--native-home", type=Path, help="Override CODEX_HOME or CLAUDE_CONFIG_DIR")
        child.add_argument("--limit", type=int, default=30, help="Candidates (find), agents (inspect) or events (read), 1-100")
        child.add_argument("--after", help="Continuation cursor from the preceding response")
        if action in {"find", "read"}:
            child.add_argument("--since", help="Inclusive ISO timestamp with timezone, or UTC date")
            child.add_argument("--until", help="Exclusive ISO timestamp with timezone, or UTC date")
        if action == "find":
            child.add_argument("--project", help="Case-insensitive substring of recorded cwd; paths may also be supplied")
        if action == "read":
            child.add_argument("--event", help="Expand one BYTE_OFFSET:INDEX event")
            child.add_argument("--field", default="data", choices=["data", "captured_output", "presented_output", "stderr", "sidecar"])
            child.add_argument("--offset", type=int, default=0, help="Character offset within the expanded field")
            child.add_argument("--chars", type=int, default=12000, help="Expanded characters, 1-50000")


def run(args):
    if not 1 <= args.limit <= 100:
        raise ValueError("--limit must be between 1 and 100")
    home = native_home(args.host, args.native_home)
    if args.history_command == "find":
        return find(args.host, home, args.since, args.until, args.project, args.limit, args.after)
    if args.history_command == "inspect":
        return inspect(args.host, args.identifier, home, args.limit, args.after)
    if args.offset < 0 or not 1 <= args.chars <= 50000 or (args.event and (args.after or args.since or args.until)):
        raise ValueError("Use a nonnegative --offset, --chars 1-50000; --event cannot combine with --after or dates")
    return read(args.host, args.identifier, home, args.limit, args.after, args.event, args.field, args.offset, args.chars,
                args.since, args.until)
