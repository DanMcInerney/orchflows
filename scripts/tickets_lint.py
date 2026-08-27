#!/usr/bin/env python3
"""Report current ticket-shape and sealed-admission findings."""

from __future__ import annotations

from pathlib import Path

if __package__:
    from .tickets_commands import LINT_USAGE
    from .tickets_context import graded_admission, run_snapshot
    from .tickets_format import (
        GATE_ID_MARKER, INSTRUCTION_BUDGET, ROOT_EXECUTOR, _executor_of,
        _extract_flag, _parse_frontmatter, _read_utf8, _set_frontmatter_field,
        instruction_words,
    )
    from .tickets_issue import NEW_DEFAULT_BOUND, _issue_defects
    from .tickets_store import (
        NO_SINK_ERROR, _run_lock, _segment_error, _tickets_root,
        _write_text_atomically,
    )
else:
    from tickets_commands import LINT_USAGE
    from tickets_context import graded_admission, run_snapshot
    from tickets_format import (
        GATE_ID_MARKER, INSTRUCTION_BUDGET, ROOT_EXECUTOR, _executor_of,
        _extract_flag, _parse_frontmatter, _read_utf8, _set_frontmatter_field,
        instruction_words,
    )
    from tickets_issue import NEW_DEFAULT_BOUND, _issue_defects
    from tickets_store import (
        NO_SINK_ERROR, _run_lock, _segment_error, _tickets_root,
        _write_text_atomically,
    )

SYNTACTIC = "syntactic"
SEMANTIC = "semantic"
DEFAULTABLE = {"depends_on": "[]", "bound": NEW_DEFAULT_BOUND, "status": "pending"}


def _finding(code, message, kind=SEMANTIC, severity="error", fix=None) -> dict:
    return {"code": code, "severity": severity, "kind": kind, "message": message, "fix": fix}


def _ceiling_finding(ticket_id: str, text: str, data: dict):
    if GATE_ID_MARKER in str(ticket_id or "") or _executor_of(data) == ROOT_EXECUTOR:
        return None
    count = instruction_words(text)
    if count <= INSTRUCTION_BUDGET:
        return None
    return _finding(
        "instruction-ceiling",
        f"{count}-word semantic assignment exceeds the {INSTRUCTION_BUDGET}-word ceiling",
    )


def lint_findings(text: str, *, ticket_id: str, siblings=None, tree=None, issued: bool = False) -> list:
    """Return all shape, ceiling, binding, and seal findings."""
    del tree
    data = _parse_frontmatter(text)
    if not data:
        return [_finding("no-frontmatter", "a ticket opens with a '---' block (contracts/work-item.md)")]
    findings = [_finding("ticket-defect", defect) for defect in _issue_defects(text, issued=issued)]
    ceiling = _ceiling_finding(ticket_id, text, data)
    if ceiling is not None:
        findings.append(ceiling)
    admission = graded_admission(ticket_id, text, dict(siblings or {}), data.get("run"))
    findings.extend(
        _finding(str(item.get("code") or "admission"), f"{item.get('field')}: {item.get('detail')}")
        for item in admission.get("findings", ())
    )
    unique = {(item["code"], item["message"]): item for item in findings}
    return [unique[key] for key in sorted(unique)]


def apply_fixes(text: str, findings) -> tuple:
    """Apply only missing system defaults whose values are contract-owned."""
    applied = []
    for item in findings:
        message = str(item.get("message") or "")
        for key, value in DEFAULTABLE.items():
            if message == f"frontmatter has no '{key}'":
                text = _set_frontmatter_field(text, key, value)
                applied.append("frontmatter-default-missing")
    return text, applied


def _draft_target(file_arg: str, executor, pack):
    path = Path(file_arg)
    text, failure = _read_utf8(path, "draft")
    if failure is not None:
        return None, {**failure, "exit_code": 2}
    for key, value in (("executor", executor), ("pack", pack)):
        if value is not None:
            text = _set_frontmatter_field(text, key, value)
    ticket_id = str(_parse_frontmatter(text).get("id") or path.stem).strip()
    return (path, ticket_id, text, {}), None


def _ticket_target(run: str, ticket_id: str):
    for kind, value in (("run id", run), ("ticket id", ticket_id)):
        refusal = _segment_error(kind, value)
        if refusal is not None:
            return None, {**refusal, "exit_code": 2}
    root = _tickets_root()
    if root is None:
        return None, {"error": NO_SINK_ERROR, "exit_code": 2}
    run_dir = root / run
    path = run_dir / f"{ticket_id}.md"
    text, failure = _read_utf8(path, f"ticket {run}/{ticket_id}")
    if failure is not None:
        return None, {**failure, "exit_code": 2}
    siblings, failures = run_snapshot(run_dir)
    if failures:
        return None, {"error": "run snapshot is unreadable", "failures": failures, "exit_code": 2}
    return (path, ticket_id, text, siblings), None


def _cmd_lint(rest):
    args = list(rest)
    file_arg = _extract_flag(args, "--file")
    executor = _extract_flag(args, "--executor")
    pack = _extract_flag(args, "--pack")
    fix = "--fix" in args
    args = [argument for argument in args if argument != "--fix"]
    if file_arg:
        if args:
            return {"error": f"usage: {LINT_USAGE}", "exit_code": 2}
        target, error = _draft_target(file_arg, executor, pack)
        issued = False
    else:
        if len(args) != 2 or executor is not None or pack is not None:
            return {"error": f"usage: {LINT_USAGE}", "exit_code": 2}
        target, error = _ticket_target(args[0], args[1])
        issued = True
    if error is not None:
        return error
    path, ticket_id, text, siblings = target
    findings = lint_findings(text, ticket_id=ticket_id, siblings=siblings, issued=issued)
    applied = []
    if fix:
        updated, applied = apply_fixes(text, findings)
        if updated != text:
            try:
                if issued:
                    with _run_lock(args[0]):
                        _write_text_atomically(path, updated)
                else:
                    _write_text_atomically(path, updated)
            except OSError as write_error:
                return {"error": f"unable to apply lint fixes: {write_error}", "exit_code": 2}
            findings = lint_findings(updated, ticket_id=ticket_id, siblings=siblings, issued=issued)
    return {"lint": {"id": ticket_id, "path": str(path), "findings": findings, "applied": applied}, "exit_code": 1 if any(item["severity"] == "error" for item in findings) else 0}
