"""Deterministic routing grades.

This module owns the small amount of state-derived routing information that
is safe to compute without making a model decision.  In particular, it does
not decide whether a Goal is adequate or whether a review lens is sufficient;
it only reports graph shape, declared pack coverage, and adapter capability.
"""

from __future__ import annotations

import re

if __package__:
    from .tickets_adapters import AdapterError, adapter_spec, pack_path
    from .tickets_format import ROOT_EXECUTOR, is_review_stage_id
    from .tickets_markdown import _parse_frontmatter, _sections, dequote
    from .tickets_store import NO_SINK_ERROR, _run_lock, _segment_error, _tickets_root
    from .tickets_context import run_snapshot
else:
    from tickets_adapters import AdapterError, adapter_spec, pack_path
    from tickets_format import ROOT_EXECUTOR, is_review_stage_id
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
    """Return the root's executor-result members, excluding review plumbing.

    Gate and ordinary checker stages are descendants in the ticket directory,
    but they are assurance work rather than independent result members.  A
    nested member remains a member of the issued root: the graph's width is
    the number of independently observable result tickets in its cut.
    """

    members = []
    for ticket_id in sorted(snapshot):
        if not ticket_id.startswith(root_id + "."):
            continue
        if is_review_stage_id(ticket_id):
            continue
        executor = _executor(snapshot[ticket_id])
        members.append(ticket_id)
    return members


_SPEC_FIELDS_HEADING = re.compile(r"(?m)^##\s+Spec fields\s*$")
_NEXT_CRAFT_SECTION = re.compile(r"(?m)^##\s+")
_FIELD_SEPARATOR = re.compile(r"\s*;\s*")
_EM_DASH = re.compile(r"\s+[—–-]\s+")
_WORDS = re.compile(r"[a-z0-9_]+")


def _required_spec_fields(pack: str) -> list[str]:
    try:
        craft = pack_path(pack).parent / "references" / "craft.md"
        text = craft.read_text(encoding="utf-8")
    except (AdapterError, OSError, UnicodeDecodeError) as error:
        raise GradeError(str(error)) from error
    match = _SPEC_FIELDS_HEADING.search(text)
    if not match:
        return []
    rest = text[match.end():]
    boundary = _NEXT_CRAFT_SECTION.search(rest)
    declared = " ".join(
        line.strip()
        for line in (rest[: boundary.start()] if boundary else rest).splitlines()
        if line.strip()
    )
    if not declared:
        return []
    fields = []
    for value in _FIELD_SEPARATOR.split(declared):
        value = dequote(value)
        if not value:
            continue
        # A pack may explain a field after an em dash.  The stable field name
        # is the portion before that explanation.
        value = dequote(_EM_DASH.split(value, maxsplit=1)[0])
        if value and value not in fields:
            fields.append(value)
    return fields


def _mentioned(field: str, text: str) -> bool:
    """Match a declared field by its meaningful words, not punctuation."""

    field_words = _WORDS.findall(field.casefold().replace("-", "_"))
    body_words = set(_WORDS.findall(text.casefold().replace("-", "_")))
    return bool(field_words) and all(word in body_words for word in field_words)


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
    root_executor = _executor(root_value)
    members = _member_ids(root_id, snapshot)
    if root_executor == ROOT_EXECUTOR:
        if dequote(root_data.get("independence")) == "checker":
            raise GradeError(f"decomposed root {root_id} must declare independence=gate")
        if len(members) == 1:
            raise GradeError(f"root {root_id} is over-decomposition: one executor result member")
        if not members:
            raise GradeError(f"root {root_id} has no executor result members")
        shape, width = "graph", len(members)
    else:
        if members:
            raise GradeError(f"root {root_id} is a direct root with executor-result members")
        shape, width = "single", 1
    pack = dequote(root_data.get("pack"))
    if not pack:
        raise GradeError(f"root {root_id} names no pack")
    try:
        deterministic_gate = bool(adapter_spec(pack).deterministic_gate)
    except AdapterError as error:
        raise GradeError(error.detail) from error
    sections = _sections(_ticket_text(root_value)) if _ticket_text(root_value) else {}
    semantic_text = "\n".join(
        sections.get(name, "") for name in ("Goal", "Context", "Details")
    )
    unmentioned = [
        field for field in _required_spec_fields(pack)
        if not _mentioned(field, semantic_text)
    ]
    return {
        "width": width,
        "shape": shape,
        "unmentioned_spec_fields": unmentioned,
        "deterministic_gate": deterministic_gate,
        "over_decomposed": False,
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
