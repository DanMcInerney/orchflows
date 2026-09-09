"""Read bounded source snapshots and index explicit session ancestry."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from improve_common import identity, now, project


def ticket_records(text):
    """Read the documented ticket envelope as evidence, never as instructions."""
    header, separator, body = text.removeprefix("---\n").partition("\n---\n")
    if not separator:
        raise ValueError("unsupported ticket envelope")
    fields = dict(re.findall(r"^([a-z_0-9]+): (.*)$", header, re.M))
    base = {k: fields.get(k) for k in ("run", "id", "session", "project")}
    records = []
    if "dispatch_v1" in fields:
        dispatch = json.loads(fields["dispatch_v1"])
        for attempt in dispatch.get("attempts", []):
            for record in attempt.get("records", []):
                records.append(dict(base, type="ticket_report", ts=record.get("committed_at"),
                                    dispatch_id=attempt.get("dispatch_id"),
                                    record_id=record.get("record_id"), content=record.get("content")))
    if "## Report" in body:
        # The projection can repeat dispatch records; keep it separately labelled.
        records.append(dict(base, type="ticket_projection", ts=None,
                            content=body.split("## Report", 1)[1], copied_from="dispatch records when present"))
    return records


def snapshot(path, kind):
    source = {"path": identity(path), "format": kind, "read_at": now(), "sha256": None,
              "size": 0, "counts": {"lines": 0, "malformed": 0, "unsupported": 0,
                                      "truncated": 0, "skipped": 0}, "gaps": []}
    records = []
    try:
        before = path.stat()
        with path.open("rb") as stream:
            data = stream.read(before.st_size)
        after = path.stat()
    except OSError:
        source.update(coverage="unavailable", gaps=["source unreadable"])
        return source, records
    source["size"] = len(data)
    source["sha256"] = hashlib.sha256(data).hexdigest()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns) or len(data) != before.st_size:
        source["gaps"].append("source changed during snapshot; inspected prefix only")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeError:
        text = data.decode("utf-8-sig", errors="replace")
        source["gaps"].append("invalid UTF-8")
    if kind == "tickets" or path.suffix == ".json":
        try:
            values = ticket_records(text.replace("\r\n", "\n")) if kind == "tickets" else [json.loads(text)]
            for index, value in enumerate(values, 1):
                if not isinstance(value, dict):
                    raise ValueError()
                records.append(("record:" + str(index), value))
        except (ValueError, TypeError, AttributeError):
            source["counts"]["malformed"] += 1
    else:
        lines = text.splitlines()
        source["counts"]["lines"] = len(lines)
        for index, line in enumerate(lines, 1):
            if not line.strip():
                source["counts"]["skipped"] += 1
                continue
            try:
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError()
                records.append(("line:" + str(index), value))
            except ValueError:
                source["counts"]["malformed"] += 1
                if index == len(lines) and not text.endswith("\n"):
                    source["counts"]["truncated"] += 1
    for failure in ("malformed", "truncated"):
        if source["counts"][failure]:
            source["gaps"].append(failure + " records: " + str(source["counts"][failure]))
    source["coverage"] = "partial" if source["gaps"] or source["counts"]["malformed"] else "complete" if data else "empty"
    return source, records


def discover(selection):
    found, declarations = {}, []
    for source in selection["sources"]:
        root = Path(source["path"])
        kind = source["kind"]
        if root.is_file():
            files = [root]
        elif root.is_dir():
            suffixes = ("*.md",) if kind == "tickets" else ("*.json", "*.jsonl") if kind == "runs" else ("*.jsonl",)
            files = sorted({p for pattern in suffixes for p in root.rglob(pattern) if p.is_file()})
        else:
            files = []
        declarations.append(dict(source, files=len(files), coverage="complete" if files else "empty" if root.is_dir() else "unavailable"))
        for path in files:
            key = (kind, identity(path))
            if key not in found:
                found[key] = snapshot(path, kind)
    return declarations, list(found.values())


def metadata(source, records):
    kind, path = source["format"], Path(source["path"])
    node = {"session": None, "parent": None, "project": None, "gaps": []}
    sessions, parents, projects = set(), set(), set()
    for _, row in records:
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        if kind == "codex" and row.get("type") == "session_meta":
            sid = payload.get("id") or payload.get("session_id")
            source_meta = payload.get("source")
            spawn = source_meta.get("subagent", {}) if isinstance(source_meta, dict) else {}
            spawn = spawn.get("thread_spawn", {}) if isinstance(spawn, dict) else {}
            parent = spawn.get("parent_thread_id") if isinstance(spawn, dict) else None
            cwd = payload.get("cwd")
        elif kind == "claude":
            sid = row.get("agentId") if row.get("isSidechain") else row.get("sessionId")
            parent = row.get("parentSessionId")
            if row.get("isSidechain") and "subagents" in path.parts:
                sid = row.get("agentId") or path.stem.removeprefix("agent-")
                parent = parent or row.get("sessionId")
            cwd = row.get("cwd")
        else:
            continue
        if isinstance(sid, str) and sid:
            sessions.add(sid)
        if isinstance(parent, str) and parent:
            parents.add(parent)
        if isinstance(cwd, str) and Path(cwd).is_absolute():
            projects.add(project(cwd))
    for key, values in (("session", sessions), ("parent", parents), ("project", projects)):
        if len(values) == 1:
            node[key] = next(iter(values))
        elif len(values) > 1:
            node["gaps"].append("contradictory " + key + " metadata")
    if kind in ("codex", "claude") and not node["session"]:
        node["gaps"].append("missing session metadata")
    return node


def ancestry(snapshots):
    nodes = [metadata(source, records) for source, records in snapshots]
    by_id = {}
    for node in nodes:
        if node["session"]:
            by_id.setdefault(node["session"], []).append(node)
    for matches in by_id.values():
        if len(matches) > 1:
            for node in matches:
                node["gaps"].append("duplicate session identity")
    for node in nodes:
        seen, chain, parent = {node["session"]}, [], node["parent"]
        while parent:
            if parent in seen:
                node["gaps"].append("ancestry cycle")
                break
            seen.add(parent)
            matches = by_id.get(parent, [])
            if len(matches) != 1:
                node["gaps"].append("orphan or ambiguous parent")
                break
            ancestor = matches[0]
            chain.append(ancestor)
            parent = ancestor["parent"]
        node["ancestors"] = [n["session"] for n in chain]
        inherited = {n["project"] for n in chain if n["project"]}
        if not node["project"] and len(inherited) == 1 and not node["gaps"]:
            node["project"] = next(iter(inherited))
            node["project_basis"] = "confirmed ancestor"
        if len(inherited | ({node["project"]} if node["project"] else set())) > 1:
            node["gaps"].append("contradictory ancestor project")
    return nodes
