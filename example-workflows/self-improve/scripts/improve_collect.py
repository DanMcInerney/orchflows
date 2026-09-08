"""Selection, correlation and trace normalization over immutable snapshots."""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from improve_common import EvidenceError, digest, identity, instant, project, redact, record_type
from improve_sources import ancestry, discover
from improve_spool import Rows
import trace
import improve_codex
import improve_claude


def ticket_key(row, field):
    values = (row.get("run"), row.get(field))
    return values if all(isinstance(value, str) and value for value in values) else None


def invalid_identities(kind, row):
    fields = ("run", "ticket", "id") if kind in {"runs", "tickets"} else ("run", "ticket")
    return [key for key in fields if row.get(key) is not None
            and (not isinstance(row[key], str) or not row[key])]


def known(kind, row):
    if invalid_identities(kind, row):
        return False
    rtype = record_type(row)
    if kind == "codex":
        current = improve_codex.shape(row)
        if current is not None:
            return current
        if rtype == "response_item":
            payload = row.get("payload")
            return isinstance(payload, dict) and record_type(payload) in {
                "message", "function_call", "function_call_output", "custom_tool_call",
                "custom_tool_call_output", "reasoning", "compaction"}
        if rtype == "event_msg":
            payload = row.get("payload")
            return isinstance(payload, dict) and record_type(payload) in {
                "token_count", "task_started", "task_complete", "agent_reasoning",
                "agent_message", "user_message", "turn_aborted", "context_compacted"}
        return rtype in {"session_meta", "turn_context", "compacted"} and isinstance(row.get("payload"), dict)
    if kind == "claude":
        return improve_claude.shape(row)
    if kind == "friction":
        return "observed" in row and "expected" in row
    if kind == "events":
        return isinstance(row.get("event"), str) and row["event"] in {"frame-open", "frame-close", "land", "stalled"}
    if kind == "tickets":
        return rtype in {"ticket_report", "ticket_projection"}
    if kind == "runs":
        return bool(row.get("run") or row.get("id"))
    return record_type(row) in {"observation", "success", "failure"} and bool(row.get("ts") or row.get("timestamp"))


def links(row):
    payload = row.get("payload") if isinstance(row.get("payload"), dict) else row
    result = []
    item = improve_codex.completed_item(row)
    if item is not None:
        result.append({"kind": "completed_item", "id": item["id"]})
    if payload.get("call_id"):
        result.append({"kind": "tool_call", "id": payload["call_id"]})
    content = row.get("message", {}).get("content", []) if isinstance(row.get("message"), dict) else []
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and record_type(block) in {"tool_use", "tool_result"}:
                result.append({"kind": "tool_call", "id": block.get("id") or block.get("tool_use_id")})
    for key in ("copied_from", "incident_id", "record_id", "dispatch_id"):
        if row.get(key):
            result.append({"kind": key, "id": row[key]})
    return [link for link in result if isinstance(link["id"], str) and link["id"]]


def row_project(row):
    value = row.get("project") or row.get("cwd")
    if isinstance(value, dict):
        value = value.get("root") or value.get("path")
    return project(value) if isinstance(value, str) and Path(value).is_absolute() else None


def record_text(value):
    if isinstance(value, dict):
        return "\n".join(record_text(v) for v in value.values())
    if isinstance(value, list):
        return "\n".join(record_text(v) for v in value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except ValueError:
            parsed = None
        if isinstance(parsed, (dict, list)):
            return record_text(parsed)
        return re.sub(r"/+", "/", value.replace("\\", "/"))
    return ""


def ticket_references(content):
    # Resolve transcript aliases by the same identity as snapshotted sources.
    pattern = r"(?:[A-Za-z]:/|/)[^\n\r`\"<>|\x00]*?\.md(?=$|[\s`\"'.,;:)])"
    for match in re.finditer(pattern, content, re.IGNORECASE):
        try:
            yield identity(match.group())
        except (OSError, ValueError, RuntimeError):
            continue


def collect(frozen, disk_budget=2147483648, record_budget=8388608):
    if type(disk_budget) is not int or disk_budget < 1:
        raise EvidenceError("disk budget must be a positive byte count")
    if type(record_budget) is not int or record_budget < 1:
        raise EvidenceError("record budget must be a positive byte count")
    declarations, snapshots = discover(frozen, disk_budget, record_budget)
    for source, _ in snapshots:
        source["acquisition_gaps"] = list(source["gaps"])
        selected_gaps = Rows()
        selected_gaps.extend(source["gaps"])
        source["gaps"] = selected_gaps
    nodes = ancestry(snapshots)
    session_nodes = nodes
    run_projects = {}
    ticket_paths, ticket_sessions = {}, {}
    for source, rows in snapshots:
        if source["format"] == "tickets" and rows:
            row = rows[0][1]
            key = ticket_key(row, "id")
            if key is not None:
                ticket_paths[source["path"]] = key
    for (_, rows), node in zip(snapshots, nodes):
        if node["session"] and not node["gaps"]:
            for _, row in rows:
                content = record_text(row)
                for path in ticket_references(content):
                    if path in ticket_paths:
                        ticket_sessions.setdefault(ticket_paths[path], set()).add(node["session"])
                key = ticket_key(row, "ticket")
                if key is not None:
                    ticket_sessions.setdefault(key, set()).add(node["session"])
    for source, rows in snapshots:
        if source["format"] == "runs":
            for _, row in rows:
                run = row.get("run") or row.get("id")
                root = row_project(row)
                if isinstance(run, str) and root:
                    run_projects.setdefault(run, set()).add(root)
    observations, structural, excluded, gaps = Rows(), Rows(), Counter(), Rows()
    selected_sessions = set(frozen["sessions"])
    start, end = instant(frozen["start"]), instant(frozen["end"])
    for (source, rows), node in zip(snapshots, nodes):
        kind = source["format"]
        if rows:
            source["gaps"].extend(node["gaps"])
        pending = Rows()
        pending.db.execute("CREATE TABLE calls (call TEXT PRIMARY KEY, observation INTEGER, event INTEGER)")
        for locator, row in rows:
            location = {"path": source["path"], "sha256": source["sha256"], "locator": locator}
            sid = node["session"] or row.get("session") or row.get("session_id")
            if sid is not None and not isinstance(sid, str):
                source["gaps"].append("invalid session identity at " + locator)
                sid = None
            if not sid and kind == "tickets":
                associated = ticket_sessions.get(ticket_key(row, "id"), set())
                if len(associated) == 1:
                    sid = next(iter(associated))
            correlated_node = session_nodes.get(sid, node)
            run = row.get("run") or (row.get("id") if kind == "runs" else None)
            runs = {run} if isinstance(run, str) and run else set()
            # A literal run-state path is a record association, never a tree selector.
            runs.update(match.group(1) for match in trace.RUN_ID_RE.finditer(record_text(row)))
            root = row_project(row) or correlated_node["project"]
            candidates = set().union(*(run_projects.get(r, set()) for r in runs)) if runs else set()
            if root and candidates and candidates != {root}:
                source["gaps"].append("contradictory run/project association at " + locator)
                root = None
            elif not root and len(candidates) == 1:
                root = next(iter(candidates))
            reason = None
            if frozen["projects"] and root not in frozen["projects"]:
                reason = "project mismatch" if root else "unknown project"
            if frozen["runs"] and not runs.intersection(frozen["runs"]):
                reason = "run mismatch" if runs else "unknown run"
            membership = {sid}
            if frozen["descendants"] and not correlated_node["gaps"]:
                membership.update(correlated_node["ancestors"])
            if selected_sessions and not membership.intersection(selected_sessions):
                reason = "session mismatch" if sid else "unknown session"
            if reason:
                if not known(kind, row):
                    source["counts"]["excluded_unsupported"] = source["counts"].get("excluded_unsupported", 0) + 1
                excluded[reason] += 1
                if reason.startswith("unknown"):
                    source["gaps"].append(reason + " at " + locator)
                continue
            stamp = row.get("timestamp") or row.get("ts") or row.get("opened_at")
            try:
                when = instant(stamp)
            except EvidenceError:
                when = None
            context = record_type(row) in {"session_meta", "ticket_projection"} or kind == "runs"
            if when is None or not start <= when < end:
                if not known(kind, row):
                    source["counts"]["excluded_unsupported"] = source["counts"].get("excluded_unsupported", 0) + 1
                excluded["unknown time" if when is None else "outside window"] += 1
                if context:
                    structural.append({"source": location, "role": "structural context, excluded from counts",
                                       "session": sid, "project": root, "runs": sorted(runs), "record": redact(row)})
                    if when is None and record_type(row) == "ticket_projection" and not any(record_type(r) == "ticket_report" for _, r in rows):
                        source["gaps"].append("legacy ticket report has unknown time")
                elif when is None:
                    source["gaps"].append("unknown time at " + locator)
                continue
            source["gaps"].extend("invalid " + key + " identity at " + locator
                                  for key in invalid_identities(kind, row))
            if not known(kind, row):
                source["counts"]["unsupported"] += 1
                source["gaps"].append("unsupported record at " + locator)
            if kind == "codex" and improve_codex.opaque(row) or kind == "claude" and improve_claude.opaque(row):
                source["gaps"].append("opaque encrypted content at " + locator)
            metadata = improve_codex.metadata_kind(row) if kind == "codex" else None
            if metadata:
                label = "usage" if metadata == "token_usage_record" else metadata
                excluded["non-diagnostic " + label] += 1
                structural.append({"source": location, "role": "non-diagnostic context, excluded from counts",
                                   "session": sid, "project": root, "runs": sorted(runs), "record": redact(row)})
                continue
            oid = "o-" + digest({"format": kind, "source": location, "session": sid})
            observation = {"id": oid, "session": sid, "project": root,
                "runs": sorted(runs), "timestamp": when.isoformat(), "format": kind,
                "host": row.get("host") or kind,
                "supported_shape": known(kind, row),
                "sources": [], "record": redact(row), "links": links(row),
                "normalized": []}
            observation["sources"].append(location)
            try:
                normalize(row, kind, observation, observations, pending)
            except (TypeError, ValueError, AttributeError, KeyError):
                source["gaps"].append("trace normalization degraded at " + locator)
            observations.append(observation, observation["timestamp"] + oid)
        pending.close()
        if source["gaps"] or source["counts"]["unsupported"]:
            source["coverage"] = "partial"
        for message in source["gaps"]:
            gaps.append({"path": source["path"], "reason": message,
                         "scope": "source-integrity" if message in source["acquisition_gaps"] else "selection-or-diagnostic"})
    for declared in declarations:
        if declared["coverage"] == "unavailable":
            gaps.append({"path": declared["path"], "reason": "expected source missing"})
    for sid in sorted(sid for sid in selected_sessions if not nodes.matches(sid)):
        gaps.append({"session": sid, "reason": "selected session not discovered"})
    coverage = "partial" if gaps else "complete" if observations else "empty"
    if declarations and all(d["coverage"] == "unavailable" for d in declarations):
        coverage = "unavailable"
    ordered = Rows()
    for observation in observations.ordered():
        ordered.append(observation)
    observations.close()
    sources = Rows()
    for source, rows in snapshots:
        sources.append(redact(dict(source, gaps=source["acquisition_gaps"], gap_count=len(source["gaps"]), gaps_section="gaps")))
        rows.close()
        source["gaps"].close()
    nodes.close()
    return {"acquisition": {"payload_disk_budget": disk_budget, "record_byte_budget": record_budget}, "selection": redact(frozen), "coverage": coverage, "gaps": gaps,
                   "declarations": redact(declarations), "sources": sources,
                   "observations": ordered,
                   "structural_context": structural, "excluded": dict(sorted(excluded.items())),
                   "occurrence_identity": "source-locator-session-v1", "legacy": {"history": "unchanged; harvest and tickets improvement remain readable",
                              "suppression": "none; covered patterns and watermarks are never consulted"}}


def normalize(row, kind, observation, observations, pending):
    """Correlate outputs to their source-local call, never a timestamp bucket."""
    events, calls = [], {}
    stamp = row.get("timestamp")
    payload = row.get("payload", {})
    output_ids = []
    if kind == "codex":
        events.extend(improve_codex.events(row))
        if record_type(row) == "response_item" and isinstance(payload, dict):
            if record_type(payload) in {"function_call_output", "custom_tool_call_output"}:
                output_ids.append(payload.get("call_id"))
            else:
                trace._handle_codex_response_item(payload, stamp, events, calls)
    elif kind == "claude":
        if record_type(row) == "assistant":
            trace._handle_claude_assistant_line(row, stamp, events, calls)
        elif record_type(row) == "user":
            content = row.get("message", {}).get("content", [])
            if isinstance(content, list):
                output_ids.extend(b.get("tool_use_id") for b in content
                                  if isinstance(b, dict) and record_type(b) == "tool_result")
            trace._handle_claude_user_line(row, stamp, events, calls)
    for call in output_ids:
        if not isinstance(call, str):
            continue
        found = pending.db.execute("SELECT observation,event FROM calls WHERE call=?", (call,)).fetchone()
        if found is None:
            observation.setdefault("attribution_gaps", []).append("call origin unavailable: " + call)
            continue
        index, event_index = found
        origin = observations[index]
        event = origin["normalized"][event_index]
        active = {call: event}
        if kind == "codex":
            trace._handle_codex_response_item(payload, stamp, [], active)
        else:
            trace._handle_claude_user_line(row, stamp, [], active)
        event["result_observation_id"] = observation["id"]
        observations[index] = origin
        pending.db.execute("DELETE FROM calls WHERE call=?", (call,))
    for event_index, event in enumerate(events):
        event["observation_ids"] = [observation["id"]]
        for call, value in calls.items():
            if value is event and isinstance(call, str):
                previous = pending.db.execute("SELECT 1 FROM calls WHERE call=?", (call,)).fetchone()
                if previous:
                    observation.setdefault("attribution_gaps", []).append("duplicate pending call: " + call)
                    pending.db.execute("DELETE FROM calls WHERE call=?", (call,))
                else:
                    pending.db.execute("INSERT INTO calls VALUES (?,?,?)", (call, len(observations), event_index))
    observation["normalized"] = redact(events)
