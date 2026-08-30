"""Render run worklogs and validate ticket-template graphs."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re

if __package__:
    from .tickets_format import (
        REQUIRED_SECTIONS, ROOT_EXECUTOR, SECTION_RANK, TEMPLATE_FILE,
        TERMINAL_STATES, _executor_of, _parse_frontmatter, _read_utf8,
        _sections, lease_of, ticket_defects,
    )
    from .tickets_store import (
        NO_SINK_ERROR, _load_ticket, _runs_root, _segment_error, _tickets_root,
    )
else:
    from tickets_format import (
        REQUIRED_SECTIONS, ROOT_EXECUTOR, SECTION_RANK, TEMPLATE_FILE,
        TERMINAL_STATES, _executor_of, _parse_frontmatter, _read_utf8,
        _sections, lease_of, ticket_defects,
    )
    from tickets_store import (
        NO_SINK_ERROR, _load_ticket, _runs_root, _segment_error, _tickets_root,
    )

PACKS_DIR = "packs"
WORKLOG_NAME = "worklog.md"
WORKLOG_RENDER_MARKER = "<!-- rendered by tickets.py worklog -->"
WORKLOG_SECTIONS = ("goal", "iterations", "failed approaches", "queued scope", "terminal")
ITERATION_ID_RE = re.compile(r"^.+\.iter\.\d+$")
GATE_VERIFY_SUFFIX = ".gate.verify"
WORKLOG_USAGE = "worklog <run> [--write]"


def _packs_root(directory):
    directory = Path(directory).resolve()
    for parent in (directory, *directory.parents):
        candidate = parent / PACKS_DIR
        if candidate.is_dir():
            return candidate
    return None


def _upstream(stubs: dict) -> dict:
    upstream = {stub_id: set(deps) for stub_id, (_, deps) in stubs.items()}
    changed = True
    while changed:
        changed = False
        for stub_id, dependencies in upstream.items():
            expanded = set(dependencies)
            for dependency in dependencies:
                expanded.update(upstream.get(dependency, ()))
            expanded.discard(stub_id)
            if expanded != dependencies:
                upstream[stub_id] = expanded
                changed = True
    return upstream


def _template_order(stubs: dict):
    """Return topological order for a closed graph with one terminal."""
    for stub_id, (_, dependencies) in stubs.items():
        for dependency in dependencies:
            if dependency not in stubs:
                return None, {"error": f"stub {stub_id} depends on '{dependency}', which is not a stub in this template"}
    remaining = {stub_id: set(dependencies) for stub_id, (_, dependencies) in stubs.items()}
    ordered = []
    while remaining:
        ready = sorted(stub_id for stub_id, dependencies in remaining.items() if not dependencies)
        if not ready:
            return None, {"error": f"template is cyclic: no stub in {sorted(remaining)} is free of dependencies"}
        ordered.extend(ready)
        for stub_id in ready:
            del remaining[stub_id]
        for dependencies in remaining.values():
            dependencies.difference_update(ready)
    depended_on = {dependency for _, dependencies in stubs.values() for dependency in dependencies}
    terminals = sorted(set(stubs) - depended_on)
    if len(terminals) != 1:
        return None, {"error": f"template has {len(terminals)} terminal stubs {terminals}; exactly one stub is terminal"}
    return ordered, None


def template_defects(directory) -> list:
    """Validate ticket shape and dependency closure for one template."""
    directory = Path(directory)
    manifest = directory / TEMPLATE_FILE
    paths = sorted(path for path in directory.glob("*.md") if path.name != TEMPLATE_FILE)
    if not paths:
        return [(manifest, f"template {directory.name} holds no stub")]
    defects = []
    stubs = {}
    for path in paths:
        text, failure = _read_utf8(path, f"stub {path.name}", encoding="utf-8-sig")
        if failure is not None:
            defects.append((path, failure["error"]))
            continue
        defects.extend((path, defect) for defect in ticket_defects(text, stub=True))
        data = _parse_frontmatter(text)
        declared_id = str(data.get("id") or "").strip()
        if declared_id and declared_id != path.stem:
            defects.append((path, f"stub {path.name} names id '{declared_id}': a stub's id is its file stem"))
        dependencies = data.get("depends_on")
        if not isinstance(dependencies, list):
            defects.append((path, "'depends_on' is not a list; write [] when the stub names none"))
            dependencies = []
        ordered = [SECTION_RANK[name.strip().lower()] for name in _sections(text) if name.strip().lower() in SECTION_RANK]
        if ordered != sorted(ordered):
            defects.append((path, "stub body sections are out of contract order; expected " + ", ".join(REQUIRED_SECTIONS)))
        stubs[path.stem] = (text, dependencies)
    _, error = _template_order(stubs)
    if error is not None:
        defects.append((manifest, error["error"]))
    return defects


def _run_tickets(run: str):
    tickets_root = _tickets_root()
    if tickets_root is None:
        return None, {"error": NO_SINK_ERROR}
    invalid = _segment_error("run id", run)
    if invalid is not None:
        return None, invalid
    run_dir = tickets_root / run
    items = []
    for path in sorted(run_dir.glob("*.md")) if run_dir.is_dir() else []:
        loaded = _load_ticket(path)
        text, failure = _read_utf8(path)
        loaded["sections"] = {} if failure is not None else _sections(text)
        items.append(loaded)
    if not items:
        return None, {"error": f"run '{run}' holds no ticket to render: {run_dir}"}
    return items, None


def _run_goal(items: list) -> tuple:
    ordered = sorted(items, key=lambda item: item["id"])
    ids = {item["id"] for item in ordered}
    depended = {dependency for item in ordered for dependency in item.get("depends_on") or []}
    free = [item for item in ordered if item["id"] not in depended]
    roots = [item for item in ordered if _executor_of(item) == ROOT_EXECUTOR]
    top_level = [item for item in ordered if "." not in item["id"]]
    graph = len(roots) > 1 or any(
        dependency in ids
        for item in top_level
        for dependency in item.get("depends_on") or []
        if "." not in str(dependency)
    )
    if graph and len(free) == 1:
        return free[0], "terminal"
    if roots:
        return roots[0], "root"
    if len(free) == 1:
        return free[0], "terminal"
    return ordered[0], "root"


def _quoted(body: str) -> list:
    text = str(body or "").strip()
    return [f"> {line}" if line.strip() else ">" for line in text.splitlines()] if text else ["> (empty)"]


def _claim_order(items: list) -> list:
    def opened(item):
        return lease_of(item)[1]
    return sorted(items, key=lambda item: (not opened(item).strip(), opened(item), item["id"]))


def _on_offer(item: dict) -> str:
    try:
        written = datetime.fromtimestamp(Path(item["path"]).stat().st_mtime, timezone.utc)
    except (KeyError, OSError):
        return ""
    minutes = int(max(0.0, (datetime.now(timezone.utc) - written).total_seconds()) // 60)
    return f", on offer {minutes}m" if minutes else ", on offer under a minute"


def _render_worklog(run: str, items: list, root: dict, kind: str = "root") -> str:
    sections = root.get("sections") or {}
    lines = [
        WORKLOG_RENDER_MARKER, "", f"# run {run}", "",
        f"Rendered from this run's tickets by `tickets.py worklog {run}`.", "",
        "## goal", "", f"{kind.capitalize()} ticket `{root['id']}` — executor `{_executor_of(root) or 'none'}`.", "",
        *_quoted(sections.get("Goal")), "", "Context:", "", *_quoted(sections.get("Context")), "", "## iterations", "",
    ]
    for item in _claim_order(items):
        stamp = lease_of(item)[1].strip()
        waiting = _on_offer(item) if not stamp and item.get("status") == "ready" else ""
        claim = f"claimed {stamp}" if stamp else "never claimed" + waiting
        lines.append(f"- `{item['id']}` — executor `{_executor_of(item) or 'none'}` — status `{item.get('status') or 'none'}` — {claim}")
    lines.extend(["", "## failed approaches", "", "None recorded.", "", "## queued scope", "", "None recorded.", "", "## terminal", ""])
    status = str(root.get("status") or "").strip()
    if status in TERMINAL_STATES:
        lines.append(f"`{status}` — the {kind} ticket `{root['id']}`'s status.")
    return "\n".join(lines) + "\n"


def _write_rendered_worklog(run: str, markdown: str):
    runs_root = _runs_root()
    if runs_root is None:
        return None, {"error": NO_SINK_ERROR}
    path = runs_root / run / WORKLOG_NAME
    if path.exists():
        existing, failure = _read_utf8(path, f"worklog {path}")
        if failure is not None:
            return None, failure
        if not existing.lstrip("\ufeff").startswith(WORKLOG_RENDER_MARKER):
            return None, {"error": f"{path} was not rendered by this subcommand: refusing to overwrite it"}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        # `open`, not `Path.write_text(newline=...)`: that keyword arrived
        # in 3.10 and this library's floor is 3.9, where the same call is a
        # TypeError -- and the rendered worklog is exactly the artifact a
        # host standing on the floor would fail to write.
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(markdown)
    except OSError as error:
        return None, {"error": f"unwritable worklog: {error}"}
    return path, None


def _cmd_worklog(rest):
    args = list(rest)
    write = "--write" in args
    args = [argument for argument in args if argument != "--write"]
    if len(args) != 1:
        return {"error": f"usage: {WORKLOG_USAGE}"}
    run = args[0]
    items, error = _run_tickets(run)
    if error is not None:
        return error
    root, kind = _run_goal(items)
    markdown = _render_worklog(run, items, root, kind)
    path = None
    if write:
        path, error = _write_rendered_worklog(run, markdown)
        if error is not None:
            return error
    return {"worklog": {"run": run, "root": root["id"], "goal_kind": kind, "tickets": len(items), "path": str(path) if path else None, "markdown": markdown}}
