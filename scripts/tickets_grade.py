"""Deterministic routing grades.

The state-derived routing information that is safe to compute without
making a model decision: graph shape, declared standard coverage, and adapter
capability. It does not decide whether a Goal is adequate or a review lens
sufficient.
"""

from __future__ import annotations


if __package__:
    from .tickets_adapters import AdapterError, adapter_for_ticket
    from .tickets_markdown import _parse_frontmatter, _sections, dequote
    from .tickets_store import NO_SINK_ERROR, _run_lock, _segment_error, _tickets_root
    from .tickets_context import run_snapshot
else:
    from tickets_adapters import AdapterError, adapter_for_ticket
    from tickets_markdown import _parse_frontmatter, _sections, dequote
    from tickets_store import NO_SINK_ERROR, _run_lock, _segment_error, _tickets_root
    from tickets_context import run_snapshot


GRADE_USAGE = "grade <run> <root>"


class GradeError(ValueError):
    """The durable ticket projection cannot receive a deterministic grade."""


def _ticket_data(value):
    if isinstance(value, dict):
        return value
    return _parse_frontmatter(str(value or ""))


def _ticket_text(value):
    return value if isinstance(value, str) else ""


def _executor(value):
    return dequote(_ticket_data(value).get("executor"))


def _member_ids(root_id: str, snapshot: dict) -> list[str]:
    """Return the root's executor-result members."""

    members = []
    for ticket_id in sorted(snapshot):
        if not ticket_id.startswith(root_id + "."):
            continue
        executor = _executor(snapshot[ticket_id])
        members.append(ticket_id)
    return members


def grade_snapshot(root_id: str, snapshot: dict) -> dict:
    """Grade one exact ticket snapshot into the closed routing answer."""

    if not isinstance(snapshot, dict) or root_id not in snapshot:
        raise GradeError(f"root ticket not found in exact snapshot: {root_id}")
    root_value = snapshot[root_id]
    root_data = _ticket_data(root_value)
    if not root_data:
        raise GradeError(f"root ticket has no readable frontmatter: {root_id}")
    if str(root_data.get("id") or root_id).strip() != root_id:
        raise GradeError(f"root ticket id differs from requested id: {root_id}")
    members = _member_ids(root_id, snapshot)
    if members:
        raise GradeError(f"root {root_id} is a direct root with executor-result members")
    shape, width = "single", 1
    try:
        adapter = adapter_for_ticket(root_data)
        deterministic_gate = bool(adapter.deterministic_gate)
    except AdapterError as error:
        raise GradeError(error.detail) from error
    return {
        "width": width,
        "shape": shape,
        "unmentioned_spec_fields": [],
        "deterministic_gate": deterministic_gate,
    }


def _cmd_grade(rest):
    args = list(rest)
    if len(args) != 2:
        return {"error": f"usage: {GRADE_USAGE}"}
    run, root_id = args
    for kind, value in (("run id", run), ("ticket id", root_id)):
        invalid = _segment_error(kind, value)
        if invalid is not None:
            return invalid
    tickets_root = _tickets_root()
    if tickets_root is None:
        return {"error": NO_SINK_ERROR}
    run_dir = tickets_root / run
    try:
        with _run_lock(run):
            snapshot, failures = run_snapshot(run_dir) if run_dir.is_dir() else ({}, [])
            if failures:
                return {"error": f"unreadable ticket: {failures[0][0]}"}
            try:
                grade = grade_snapshot(root_id, snapshot)
            except GradeError as error:
                return {"error": str(error)}
    except OSError as error:
        return {"error": f"unable to grade: {error}"}
    return {"grade": {"run": run, "root": root_id, **grade}}


__all__ = (
    "GRADE_USAGE", "GradeError", "_cmd_grade", "grade_snapshot",
)
