"""Read native Claude/Codex history without writing logs or resuming agents."""

from __future__ import annotations

import base64
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
import hashlib
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
        if databases:
            try:
                with closing(sqlite3.connect(databases[0].as_uri() + "?mode=ro", uri=True)) as db:
                    db.execute("BEGIN")
                    columns = {row[1] for row in db.execute("PRAGMA table_info(threads)")}
                    extra = [key for key in ("cwd", "title", "created_at", "updated_at") if key in columns]
                    for row in db.execute("SELECT id, rollout_path" + "".join(", " + key for key in extra) + " FROM threads"):
                        entries[row[0]] = {"id": row[0], "path": str(row[1]), "parent_id": None,
                                           **dict(zip(extra, row[2:]))}
                    for parent, child in db.execute("SELECT parent_thread_id, child_thread_id FROM thread_spawn_edges"):
                        if child in entries:
                            entries[child]["parent_id"] = parent
                        else:
                            gaps.append({"kind": "missing_child_record", "id": child, "parent_id": parent})
                return entries, gaps
            except sqlite3.Error as exc:
                gaps.append({"kind": "index_unavailable", "detail": str(exc)})
                entries.clear()
        # Header-only fallback also supports copied rollouts without a native index.
        for folder in (home / "sessions", home / "archived_sessions"):
            for path in folder.rglob("*.jsonl"):
                try:
                    with path.open(encoding="utf-8") as stream:
                        meta = json.loads(stream.readline())["payload"]
                    identifier = meta.get("id") or meta["session_id"]
                    entry = {"id": identifier, "path": str(path), "parent_id": meta.get("parent_thread_id")}
                    source = meta.get("source")
                    if not entry["parent_id"] and isinstance(source, dict):
                        subagent = source.get("subagent")
                        spawn = subagent.get("thread_spawn") if isinstance(subagent, dict) else None
                        if isinstance(spawn, dict):
                            entry["parent_id"] = spawn.get("parent_thread_id")
                    if identifier in entries:
                        raise ValueError(f"Duplicate native ID {identifier}")
                    entries[identifier] = entry
                except (OSError, ValueError, KeyError, TypeError) as exc:
                    gaps.append({"kind": "header_unavailable", "path": str(path), "detail": str(exc)})
    else:
        # Locate the requested session first; do not open every unrelated agent's
        # metadata on each page of a read.
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
            identifier = path.stem.removeprefix("agent-")
            entry = {"id": identifier, "path": str(path), "parent_id": path.parent.parent.name}
            meta_path = path.with_suffix(".meta.json")
            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                    entry["parent_id"] = meta.get("parentAgentId") or entry["parent_id"]
                    entry["name"] = meta.get("name") or meta.get("description") or meta.get("agentType")
                except (OSError, ValueError, AttributeError) as exc:
                    entry["metadata_gap"] = str(exc)
            if identifier in entries:
                raise ValueError(f"Ambiguous native agent ID {identifier}")
            entries[identifier] = entry
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


def _file_metadata(path, host, project=None):
    # Read the opening metadata and the last dated record, not every tool output.
    metadata = {"metadata_source": "transcript_endpoints"}
    for _, line, _, record in _records(path):
        payload = record.get("payload") if host == "codex" and record.get("type") == "session_meta" else record
        if isinstance(payload, dict) and payload.get("cwd"):
            metadata["cwd"] = payload["cwd"]
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
        if not all(entry.get(key) is not None for key in ("cwd", "created_at", "updated_at")):
            try:
                entry.update(_file_metadata(Path(entry["path"]), host, project))
            except OSError as exc:
                entry["read_gap"] = str(exc)
        else:
            entry["metadata_source"] = "native_index"
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
            "note": "Candidates include sessions and subagents. Dates overlap native index or transcript endpoint bounds; "
                    "read with the same dates to select actual events. Project matches recorded cwd text, not repository identity. "
                    "Missing metadata stays visible in scope_unknown. Discovery does not prove complete native retention."}


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
                                   "captured_output": item.get("stdout", item.get("aggregated_output", "")),
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


def _located_events(path, host, offset=0, line=1):
    for start, number, raw, record in _records(path, offset, line):
        for index, event in enumerate(_events(host, record)):
            event["event_id"] = f"{start}:{index}"
            event["source"] = {"path": str(path), "line": number, "byte_offset": start}
            event["flags"] = _flags(event)
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
    agents = []
    for current in selected_page:
        entry = entries[current].copy()
        counts, tools, flags = Counter(), Counter(), Counter()
        calls, results, errors, gap_events = {}, set(), [], []
        latest = None
        try:
            for event, _, _ in _located_events(Path(entry["path"]), host):
                counts[event["kind"]] += 1
                flags.update(event["flags"])
                latest = _preview(event, 180)
                if event["kind"] == "tool_call":
                    calls[event["call_id"]] = {k: event.get(k) for k in ("call_id", "tool", "event_id", "source")}
                    tools[event["tool"]] += 1
                elif event["kind"] == "tool_result":
                    results.add(event["call_id"])
                sidecars = _sidecars(event, home)
                for sidecar in sidecars:
                    if sidecar["state"] != "available":
                        flags[sidecar["state"]] += 1
                if event.get("is_error") or event.get("exit_code") not in {None, 0} or event.get("record_type") == "error":
                    errors.append(_preview(event, 160))
                if event["kind"] in {"gap", "unsupported"}:
                    gap_events.append(_preview(event, 160))
        except OSError as exc:
            entry["read_gap"] = str(exc)
        unmatched = [v for k, v in calls.items() if k not in results]
        entry.update(events=dict(counts), tools=dict(tools), flags=dict(flags), latest_recorded=latest,
                     calls_without_recorded_results=unmatched[:20], unmatched_count=len(unmatched),
                     errors=errors[-5:], error_count=len(errors), gaps=gap_events[:5], gap_count=len(gap_events))
        agents.append(entry)
    return {"host": host, "root_id": identifier, "native_home": str(home), "agents": agents,
            "agent_count": len(selected), "discovery_gaps": gaps[:20], "discovery_gap_count": len(gaps),
            "next_cursor": selected_page[-1] if selected_page and selected_page[-1] != selected[-1] else None,
            "note": "Recorded activity is not proof of current process state or workflow success. Rerun inspect to discover newly spawned agents."}


def _cursor(path, event, raw, index):
    data = [str(path), event["source"]["byte_offset"], event["source"]["line"], index + 1, hashlib.sha256(raw).hexdigest()]
    return base64.urlsafe_b64encode(_json(data).encode()).decode()


def read(host, identifier, home, limit=30, after=None, event_id=None, field="data", offset=0, chars=12000,
         since=None, until=None):
    window_start, window_end = _window(since, until)
    entries, gaps = _locate(host, identifier, home)
    path = Path(entries[identifier]["path"])
    start, line, skip = 0, 1, 0
    if after:
        try:
            old_path, start, line, skip, digest = json.loads(base64.urlsafe_b64decode(after))
            if old_path != str(path) or not all(type(x) is int and x >= 0 for x in (start, line, skip)) or line < 1:
                raise ValueError()
            with path.open("rb") as stream:
                stream.seek(start)
                if hashlib.sha256(stream.readline()).hexdigest() != digest:
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
        # Locate its true line number; event IDs remain independent of pagination.
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
                cursor = _cursor(path, event, raw, index)
                continue
        if len(events) == limit:
            has_more = True
            break
        event["sidecars"] = _sidecars(event, home)
        events.append(_preview(event))
        cursor = _cursor(path, event, raw, index)
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
