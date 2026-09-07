"""Selection, correlation and trace normalization over immutable snapshots."""
from __future__ import annotations

import json
import os
import re
import tempfile
from collections import Counter
from pathlib import Path

from improve_common import EvidenceError, canonical, digest, instant, project, redact
from improve_sources import ancestry, discover
import trace
import improve_codex


def known(kind, row):
    rtype = row.get("type")
    if kind == "codex":
        current = improve_codex.shape(row)
        if current is not None:
            return current
        if rtype == "response_item":
            payload = row.get("payload")
            return isinstance(payload, dict) and payload.get("type") in {
                "message", "function_call", "function_call_output", "custom_tool_call",
                "custom_tool_call_output", "reasoning", "compaction"}
        if rtype == "event_msg":
            payload = row.get("payload")
            return isinstance(payload, dict) and payload.get("type") in {
                "token_count", "task_started", "task_complete", "agent_reasoning",
                "agent_message", "user_message", "turn_aborted", "context_compacted"}
        return rtype in {"session_meta", "turn_context", "compacted"} and isinstance(row.get("payload"), dict)
    if kind == "claude":
        if rtype in {"user", "assistant"}:
            return isinstance(row.get("message"), dict)
        return rtype in {"summary", "system", "progress", "file-history-snapshot", "queue-operation"}
    if kind == "friction":
        return "observed" in row and "expected" in row
    if kind == "events":
        return row.get("event") in {"frame-open", "frame-close", "land"}
    if kind == "tickets":
        return rtype in {"ticket_report", "ticket_projection"}
    if kind == "runs":
        return bool(row.get("run") or row.get("id"))
    return row.get("type") in {"observation", "success", "failure"} and bool(row.get("ts") or row.get("timestamp"))


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
            if isinstance(block, dict) and block.get("type") in {"tool_use", "tool_result"}:
                result.append({"kind": "tool_call", "id": block.get("id") or block.get("tool_use_id")})
    for key in ("copied_from", "incident_id", "record_id", "dispatch_id"):
        if row.get(key):
            result.append({"kind": key, "id": row[key]})
    return result


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


def collect(frozen):
    declarations, snapshots = discover(frozen)
    nodes = ancestry(snapshots)
    session_nodes = {}
    for node in nodes:
        if node["session"] and not node["gaps"]:
            session_nodes[node["session"]] = node
    run_projects = {}
    ticket_paths, ticket_sessions = {}, {}
    for source, rows in snapshots:
        if source["format"] == "tickets" and rows:
            row = rows[0][1]
            ticket_paths[source["path"].replace("\\", "/")] = (row.get("run"), row.get("id"))
    for (_, rows), node in zip(snapshots, nodes):
        if node["session"] and not node["gaps"]:
            for _, row in rows:
                content = record_text(row)
                for path, key in ticket_paths.items():
                    if path in content or os.name == "nt" and path.lower() in content.lower():
                        ticket_sessions.setdefault(key, set()).add(node["session"])
                if row.get("run") and row.get("ticket"):
                    ticket_sessions.setdefault((row["run"], row["ticket"]), set()).add(node["session"])
    for source, rows in snapshots:
        if source["format"] == "runs":
            for _, row in rows:
                run = row.get("run") or row.get("id")
                root = row_project(row)
                if isinstance(run, str) and root:
                    run_projects.setdefault(run, set()).add(root)
    observations, structural, excluded, gaps = {}, [], Counter(), []
    selected_sessions = set(frozen["sessions"])
    start, end = instant(frozen["start"]), instant(frozen["end"])
    for (source, rows), node in zip(snapshots, nodes):
        kind = source["format"]
        if rows:
            source["gaps"].extend(node["gaps"])
        selected_rows = []
        timestamp_ids = {}
        for locator, row in rows:
            location = {"path": source["path"], "sha256": source["sha256"], "locator": locator}
            if not known(kind, row):
                source["counts"]["unsupported"] += 1
                source["gaps"].append("unsupported record at " + locator)
            message = improve_codex.agent_message(row) if kind == "codex" else None
            if message and any(x.get("type") == "encrypted_content" for x in message["content"]):
                source["gaps"].append("opaque encrypted agent message content at " + locator)
            sid = node["session"] or row.get("session") or row.get("session_id")
            if sid is not None and not isinstance(sid, str):
                source["gaps"].append("invalid session identity at " + locator)
                sid = None
            if not sid and kind == "tickets":
                associated = ticket_sessions.get((row.get("run"), row.get("id")), set())
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
                excluded[reason] += 1
                if reason.startswith("unknown"):
                    source["gaps"].append(reason + " at " + locator)
                continue
            stamp = row.get("timestamp") or row.get("ts") or row.get("opened_at")
            try:
                when = instant(stamp)
            except EvidenceError:
                when = None
            context = row.get("type") in {"session_meta", "ticket_projection"} or kind == "runs"
            if when is None or not start <= when < end:
                excluded["unknown time" if when is None else "outside window"] += 1
                if context:
                    structural.append({"source": location, "role": "structural context, excluded from counts",
                                       "session": sid, "project": root, "runs": sorted(runs), "record": redact(row)})
                    if when is None and row.get("type") == "ticket_projection" and not any(r.get("type") == "ticket_report" for _, r in rows):
                        source["gaps"].append("legacy ticket report has unknown time")
                elif when is None:
                    source["gaps"].append("unknown time at " + locator)
                continue
            metadata = improve_codex.metadata_kind(row) if kind == "codex" else None
            if metadata:
                label = "usage" if metadata == "token_usage_record" else metadata
                excluded["non-diagnostic " + label] += 1
                structural.append({"source": location, "role": "non-diagnostic context, excluded from counts",
                                   "session": sid, "project": root, "runs": sorted(runs), "record": redact(row)})
                continue
            oid = "o-" + digest({"format": kind, "record": row})
            observation = observations.setdefault(oid, {"id": oid, "session": sid, "project": root,
                "runs": sorted(runs), "timestamp": when.isoformat(), "format": kind,
                "host": row.get("host") or kind,
                "supported_shape": known(kind, row),
                "sources": [], "record": redact(row), "links": links(row),
                "normalized": redact(improve_codex.events(row)) if kind == "codex" else []})
            observation["sources"].append(location)
            selected_rows.append(redact(row))
            timestamp_ids.setdefault(stamp, []).append(oid)
        if kind in {"codex", "claude"} and selected_rows:
            # Private temporary copies contain redacted selected rows only. Claude's
            # implicit sibling discovery cannot import unselected originals here.
            with tempfile.TemporaryDirectory(prefix="orch-improve-trace-") as temporary:
                path = Path(temporary) / "main.jsonl"
                if kind == "claude" and node["parent"]:
                    path.write_text("", encoding="utf-8")
                    child = Path(temporary) / "main" / "subagents" / "agent-selected.jsonl"
                    child.parent.mkdir(parents=True)
                    child.write_text("\n".join(canonical(r) for r in selected_rows) + "\n", encoding="utf-8")
                else:
                    path.write_text("\n".join(canonical(r) for r in selected_rows) + "\n", encoding="utf-8")
                try:
                    normalized = trace.extract_codex(path) if kind == "codex" else trace.extract_claude(path)
                except (TypeError, ValueError, AttributeError, KeyError):
                    normalized = {"events": [], "parse_errors": ["unsupported trace field shape"]}
            if normalized.get("parse_errors"):
                source["gaps"].append("trace normalization degraded")
            for event in normalized.get("events", []):
                ids = timestamp_ids.get(event.get("ts"), [])
                for oid in ids:
                    observations[oid]["normalized"].append(dict(event, observation_ids=ids))
        if source["gaps"] or source["counts"]["unsupported"]:
            source["coverage"] = "partial"
        gaps.extend({"path": source["path"], "reason": message} for message in sorted(set(source["gaps"])))
    for declared in declarations:
        if declared["coverage"] == "unavailable":
            gaps.append({"path": declared["path"], "reason": "expected source missing"})
    indexed = {n["session"] for n in nodes if n["session"]}
    for sid in sorted(selected_sessions - indexed):
        gaps.append({"session": sid, "reason": "selected session not discovered"})
    coverage = "partial" if gaps else "complete" if observations else "empty"
    if declarations and all(d["coverage"] == "unavailable" for d in declarations):
        coverage = "unavailable"
    return redact({"selection": frozen, "coverage": coverage, "gaps": gaps,
                   "declarations": declarations, "sources": [s for s, _ in snapshots],
                   "observations": sorted(observations.values(), key=lambda o: (o["timestamp"], o["id"])),
                   "structural_context": structural, "excluded": dict(sorted(excluded.items())),
                   "legacy": {"history": "unchanged; harvest and tickets improvement remain readable",
                              "suppression": "none; covered patterns and watermarks are never consulted"}})
