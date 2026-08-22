"""Deterministic v2 assignment generations and draft/seal mechanics.

The pure functions in this module deliberately exclude ticket lifecycle and
executor-owned output from generation identities.  Callers may therefore
compare-and-swap a validated assignment without making ordinary status or
result writes self-invalidating.
"""

from __future__ import annotations

import hashlib
import json
import re

if __package__:
    from .tickets_format import (
        _executor_of, _parse_frontmatter, _scope_entries, _sections,
        _set_frontmatter_field, _write_section, canonical_json,
    )
else:
    from tickets_format import (
        _executor_of, _parse_frontmatter, _scope_entries, _sections,
        _set_frontmatter_field, _write_section, canonical_json,
    )


GENERATION_RE = re.compile(r"^v2:(root|cut):([A-Za-z0-9][A-Za-z0-9._-]*):(\d+):sha256:([0-9a-f]{64})$")
AMENDMENT_FIELDS = (
    "bound-state", "change-kind", "cut-generation", "evidence-identities",
    "parent-ticket", "reason", "request-id", "requester-ticket",
    "root-generation", "target-fields",
)
ASSIGNMENT_AUTHORITY_FIELDS = (
    "write_scope", "mutations", "excluded_actions", "isolation", "pack",
    "independence", "bound", "ownership_regions", "merge_oracles",
)


class GenerationError(ValueError):
    """A draft, seal, or typed request is not the exact value required."""


def _digest(value) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _field_value(data, key):
    value = data.get(key)
    if key in {"write_scope", "mutations", "excluded_actions"}:
        return _scope_entries(value)
    return value


def assignment_payload(ticket_id: str, text: str) -> dict:
    """The six caller-owned assignment facets sealed before dispatch."""

    data = _parse_frontmatter(text)
    sections = _sections(text)
    return {
        "acceptance": sections.get("Completion test", ""),
        "authority": {
            key: _field_value(data, key)
            for key in ASSIGNMENT_AUTHORITY_FIELDS if key in data
        },
        "dependencies": [str(value) for value in (data.get("depends_on") or [])],
        "executor": _executor_of(data),
        "inputs": sections.get("Fixed inputs", ""),
        "objective": sections.get("Objective", ""),
        "ticket": ticket_id,
    }


def assignment_digest(ticket_id: str, text: str) -> str:
    return "sha256:" + _digest(assignment_payload(ticket_id, text))


def generation_identity(kind: str, root_id: str, ordinal: int, payload) -> str:
    if kind not in {"root", "cut"}:
        raise GenerationError("generation kind must be root or cut")
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal <= 0:
        raise GenerationError("generation ordinal must be a positive integer")
    return f"v2:{kind}:{root_id}:{ordinal}:sha256:{_digest(payload)}"


def generation_ordinal(identity: str, kind: str | None = None) -> int:
    match = GENERATION_RE.fullmatch(str(identity or ""))
    if match is None or (kind is not None and match.group(1) != kind):
        raise GenerationError(f"invalid {kind or 'v2'} generation identity")
    return int(match.group(3))


def _cut_members(root_id: str, snapshot: dict) -> list:
    prefix = root_id + "."
    return sorted(
        ticket_id for ticket_id in snapshot
        if ticket_id.startswith(prefix) and ".gate." not in ticket_id
    )


def _root_payload(root_id: str, snapshot: dict) -> dict:
    try:
        root_text = snapshot[root_id]
    except KeyError as error:
        raise GenerationError(f"root ticket not found in exact snapshot: {root_id}") from error
    return {"assignment": assignment_payload(root_id, root_text), "version": 2}


def _cut_payload(root_id: str, snapshot: dict, root_generation: str) -> dict:
    members = _cut_members(root_id, snapshot)
    assignments = [
        {"digest": assignment_digest(ticket_id, snapshot[ticket_id]), "id": ticket_id}
        for ticket_id in members
    ]
    declarations = []
    merge_oracles = []
    for ticket_id in members:
        data = _parse_frontmatter(snapshot[ticket_id])
        if data.get("ownership_regions"):
            declarations.append({"id": ticket_id, "value": data["ownership_regions"]})
        if data.get("merge_oracles"):
            merge_oracles.append({"id": ticket_id, "value": data["merge_oracles"]})
    root_data = _parse_frontmatter(snapshot[root_id])
    coverage = root_data.get("coverage_map") or []
    return {
        "assignments": assignments,
        "coverage_map_digest": "sha256:" + _digest(coverage),
        "merge_oracles": merge_oracles,
        "ownership_regions": declarations,
        "root_generation": root_generation,
        "version": 2,
    }


def draft_snapshot(root_id: str, snapshot: dict, ordinal: int = 1) -> dict:
    """Materialize one complete immutable draft from an exact ticket snapshot."""

    root_payload = _root_payload(root_id, snapshot)
    root_generation = generation_identity("root", root_id, ordinal, root_payload)
    cut_payload = _cut_payload(root_id, snapshot, root_generation)
    cut_generation = generation_identity("cut", root_id, ordinal, cut_payload)
    return {
        "assignments": cut_payload["assignments"],
        "cut_generation": cut_generation,
        "cut_payload": cut_payload,
        "root_generation": root_generation,
        "root_payload": root_payload,
    }


def validate_draft(root_id: str, snapshot: dict, draft: dict) -> dict:
    """Grade exactly one draft snapshot and return its validation receipt."""

    ordinal = generation_ordinal(draft.get("cut_generation"), "cut")
    expected = draft_snapshot(root_id, snapshot, ordinal)
    if expected != draft:
        raise GenerationError("draft validation failed: supplied draft is not the exact snapshot grade")
    return {
        "cut_generation": draft["cut_generation"],
        "draft_digest": "sha256:" + _digest(draft),
        "root_generation": draft["root_generation"],
        "state": "validated",
    }


def seal_assignments(root_id: str, snapshot: dict, draft: dict, receipt: dict) -> dict:
    """Compare-and-swap seal only the exact draft named by ``receipt``."""

    validated = validate_draft(root_id, snapshot, draft)
    if receipt != validated or receipt.get("state") != "validated":
        raise GenerationError("seal refused: validation receipt does not name this exact draft")
    sealed = dict(snapshot)
    for ticket_id in _cut_members(root_id, snapshot):
        text = snapshot[ticket_id]
        text = _set_frontmatter_field(text, "root_generation", draft["root_generation"])
        text = _set_frontmatter_field(text, "cut_generation", draft["cut_generation"])
        text = _set_frontmatter_field(text, "assignment_seal", assignment_digest(ticket_id, text))
        sealed[ticket_id] = text
    return sealed


def _failure_identity(findings) -> str:
    normalized = sorted(
        canonical_json({
            "code": str(item.get("code") or ""),
            "field": str(item.get("field") or ""),
        })
        for item in findings
    )
    return "sha256:" + _digest(normalized)


def correction_decision(findings, history, bound: int = 1) -> dict:
    """Spend one bounded correction generation, or suspend deterministically."""

    if isinstance(bound, bool) or not isinstance(bound, int) or bound <= 0:
        raise GenerationError("correction bound must be a finite positive integer")
    prior = list(history or [])
    identity = _failure_identity(findings)
    if identity in prior:
        return {"disposition": "suspend", "reason": "recurring-validation-failure", "failure_identity": identity, "history": prior}
    if len(prior) >= bound:
        return {"disposition": "suspend", "reason": "correction-bound-exhausted", "failure_identity": identity, "history": prior}
    updated = prior + [identity]
    return {"disposition": "new-generation", "failure_identity": identity, "history": updated, "next_ordinal": len(updated) + 1}


def _validate_amendment(record: dict) -> None:
    if not isinstance(record, dict) or tuple(record) != AMENDMENT_FIELDS:
        raise GenerationError(f"amendment request fields must be exactly {list(AMENDMENT_FIELDS)} in canonical order")
    for key in ("bound-state", "change-kind", "parent-ticket", "reason", "request-id", "requester-ticket"):
        if not isinstance(record[key], str) or not record[key].strip():
            raise GenerationError(f"amendment request {key} must be a non-empty string")
    generation_ordinal(record["root-generation"], "root")
    generation_ordinal(record["cut-generation"], "cut")
    for key in ("target-fields", "evidence-identities"):
        if not isinstance(record[key], list) or not record[key] or not all(isinstance(value, str) and value.strip() for value in record[key]):
            raise GenerationError(f"amendment request {key} must be a non-empty string list")
    if record["parent-ticket"] == record["requester-ticket"]:
        raise GenerationError("amendment requester must not be its own parent")


def append_amendment_request(worker_text: str, record: dict) -> str:
    """Append the one worker-owned typed request allowed per dispatch."""

    _validate_amendment(record)
    handoff = _sections(worker_text).get("Handoff", "")
    if any(line.strip().startswith("- amendment-request:") for line in handoff.splitlines()):
        raise GenerationError("one amendment request is already recorded for this dispatch")
    line = "- amendment-request: " + canonical_json(record)
    return _write_section(worker_text, "Handoff", line, append=True)


def v2_seal_findings(ticket_id: str, text: str) -> list:
    """Findings that guard worker eligibility at the v2 seal boundary."""

    data = _parse_frontmatter(text)
    expected = assignment_digest(ticket_id, text)
    seal = str(data.get("assignment_seal") or "").strip()
    findings = []
    if not seal:
        findings.append({"code": "assignment-unsealed", "field": "assignment_seal", "detail": "v2 assignment has no validated seal"})
    elif seal != expected:
        findings.append({"code": "assignment-seal-mismatch", "field": "assignment_seal", "detail": "sealed digest does not match the current assignment"})
    for field, kind in (("root_generation", "root"), ("cut_generation", "cut")):
        try:
            generation_ordinal(str(data.get(field) or ""), kind)
        except GenerationError:
            findings.append({"code": "generation-invalid", "field": field, "detail": f"missing or malformed v2 {kind} generation"})
    return findings


__all__ = (
    "AMENDMENT_FIELDS", "GENERATION_RE", "GenerationError", "append_amendment_request",
    "assignment_digest", "assignment_payload", "canonical_json", "correction_decision",
    "draft_snapshot", "generation_identity", "generation_ordinal", "seal_assignments",
    "validate_draft", "v2_seal_findings",
)
