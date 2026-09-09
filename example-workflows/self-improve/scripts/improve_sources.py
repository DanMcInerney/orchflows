"""Read bounded source snapshots and index explicit session ancestry."""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from pathlib import Path

from improve_common import identity, now, project, redact
from improve_spool import Rows


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
        # New runtimes own section parsing; preserve reads against older installs.
        import tickets
        page = getattr(tickets, "section_page", None)
        if page is None:
            records.append(dict(base, type="ticket_projection", ts=None,
                                content=body.split("## Report", 1)[1], copied_from="dispatch records when present"))
        else:
            offset = 0
            while offset is not None:
                result = page(text, "Report", offset, 4096)
                if "error" in result:
                    raise ValueError("ticket Report section refused")
                records.append(dict(base, type="ticket_projection", ts=None,
                                    content=result["text"], section_offset=offset,
                                    copied_from="dispatch records when present"))
                offset = result["next_offset"]
    return records


def snapshot(path, kind, budget=None, record_budget=8388608):
    source = {"path": identity(path), "format": kind, "read_at": now(), "sha256": None,
              "size": 0, "counts": {"lines": 0, "malformed": 0, "unsupported": 0,
                                      "truncated": 0, "skipped": 0}, "gaps": []}
    records = Rows()
    try:
        before = path.stat()
        hasher = hashlib.sha256()
        remaining = before.st_size
        with path.open("rb") as stream:
            document = kind == "tickets" or path.suffix == ".json"
            if document and remaining > min(record_budget, budget[0] if budget else record_budget):
                source["continuation"] = {"byte": 0, "record": 1, "reason": "document byte budget"}
                source["gaps"].append("document byte budget exhausted; continuation byte:0 record:1")
                while remaining:
                    chunk = stream.read(min(remaining, 1024 * 1024))
                    if not chunk:
                        break
                    hasher.update(chunk)
                    source["size"] += len(chunk)
                    remaining -= len(chunk)
            elif document:
                data = stream.read(remaining)
                hasher.update(data)
                source["size"] = len(data)
                if budget is not None:
                    budget[0] -= len(data)
                try:
                    text = data.decode("utf-8-sig")
                    values = ticket_records(text.replace("\r\n", "\n")) if kind == "tickets" else [json.loads(text)]
                    for index, value in enumerate(values, 1):
                        if not isinstance(value, dict):
                            raise ValueError()
                        records.append(("record:" + str(index), redact(value)))
                except (ValueError, TypeError, AttributeError):
                    source["counts"]["malformed"] += 1
            else:
                # Freeze the byte boundary before reading. Growth is never chased.
                index = 0
                while remaining:
                    offset = source["size"]
                    allowance = min(remaining, record_budget + 1, budget[0] + 1 if budget is not None else remaining)
                    raw = stream.readline(allowance)
                    if not raw:
                        break
                    remaining -= len(raw)
                    source["size"] += len(raw)
                    hasher.update(raw)
                    index += 1
                    exhausted = "disk budget" if budget is not None and len(raw) > budget[0] else "record byte budget" if len(raw) > record_budget else None
                    if exhausted:
                        source["gaps"].append(exhausted + " exhausted; continuation byte:" + str(offset) + " line:" + str(index))
                        source["continuation"] = {"byte": offset, "line": index, "reason": exhausted}
                        # Finish the exact frozen-prefix hash without retaining payload.
                        while remaining:
                            chunk = stream.read(min(remaining, 1024 * 1024))
                            if not chunk:
                                break
                            remaining -= len(chunk)
                            source["size"] += len(chunk)
                            hasher.update(chunk)
                        break
                    if budget is not None:
                        budget[0] -= len(raw)
                    source["counts"]["lines"] = index
                    if not raw.strip():
                        source["counts"]["skipped"] += 1
                        continue
                    try:
                        value = json.loads(raw.decode("utf-8-sig" if index == 1 else "utf-8"))
                        if not isinstance(value, dict):
                            raise ValueError()
                        records.append(("line:" + str(index), redact(value)))
                    except ValueError:
                        source["counts"]["malformed"] += 1
                        if not remaining and not raw.endswith(b"\n"):
                            source["counts"]["truncated"] += 1
        source["sha256"] = hasher.hexdigest()
        after = path.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns) or source["size"] != before.st_size:
            source["gaps"].append("source changed during snapshot; inspected prefix only")
    except sqlite3.Error:
        source["sha256"] = hasher.hexdigest()
        source["continuation"] = {"byte": source["size"], "reason": "spool write failed; retry frozen source from start"}
        source["gaps"].append("spool storage failed; acquisition partial")
        source["coverage"] = "partial"
        return source, records
    except OSError:
        source.update(coverage="unavailable", gaps=["source unreadable"])
        return source, records
    for failure in ("malformed", "truncated"):
        if source["counts"][failure]:
            source["gaps"].append(failure + " records: " + str(source["counts"][failure]))
    source["coverage"] = "partial" if source["gaps"] or source["counts"]["malformed"] else "complete" if source["size"] else "empty"
    return source, records


def discover(selection, disk_budget=2147483648, record_budget=8388608):
    budget = [disk_budget]
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
                found[key] = snapshot(path, kind, budget, record_budget)
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


class Nodes(Rows):
    """On-disk ancestry index, including metadata outside the selected window."""
    def matches(self, session):
        return [self[index] for index, in self.db.execute("SELECT position FROM sessions WHERE session=?", (session,))]

    def get(self, session, default=None):
        matches = self.matches(session) if isinstance(session, str) else []
        return matches[0] if len(matches) == 1 and not matches[0]["gaps"] else default


def ancestry(snapshots):
    nodes = Nodes()
    nodes.db.execute("CREATE TABLE sessions (session TEXT, position INTEGER)")
    nodes.db.execute("CREATE INDEX sessions_identity ON sessions(session)")
    for source, records in snapshots:
        node = metadata(source, records)
        nodes.db.execute("INSERT INTO sessions VALUES (?,?)", (node["session"], len(nodes)))
        nodes.append(node)
    for index, node in enumerate(nodes):
        if node["session"] and len(nodes.matches(node["session"])) > 1:
            node["gaps"].append("duplicate session identity")
            nodes[index] = node
    for index, node in enumerate(nodes):
        seen, chain, parent = {node["session"]}, [], node["parent"]
        while parent:
            if parent in seen:
                node["gaps"].append("ancestry cycle")
                break
            seen.add(parent)
            matches = nodes.matches(parent)
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
        nodes[index] = node
    return nodes
