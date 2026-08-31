"""Deterministic assignment generations and draft/seal mechanics.

The algebra alone: what a draft is, what validates one, and what a seal
writes. The two subcommands that run it against the state sink are
`tickets_seal`, which imports from here and is not imported back.
"""

from __future__ import annotations

import hashlib
import re
if __package__:
    from .tickets_admission import binding_findings
    from .tickets_format import (_executor_of, _parse_frontmatter, _sections, _set_frontmatter_field, canonical_json)
else:
    from tickets_admission import binding_findings
    from tickets_format import (_executor_of, _parse_frontmatter, _sections, _set_frontmatter_field, canonical_json)

GENERATION_RE = re.compile(r"^(root|cut):([A-Za-z0-9][A-Za-z0-9._-]*):(\d+):sha256:([0-9a-f]{64})$")
ASSIGNMENT_SYSTEM_FIELDS = (
    "bound", "done", "independence", "isolation", "pack",
    "pack_digest", "profile", "review_kind",
)


class GenerationError(ValueError):
    """A draft, seal, or typed request is not the exact value required."""
def _digest(value) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()

def assignment_payload(ticket_id: str, text: str) -> dict:
    """The semantic assignment and necessary system identity sealed before dispatch."""

    data = _parse_frontmatter(text)
    sections = _sections(text)
    return {
        "semantic": {
            "context": sections.get("Context", ""),
            "details": sections.get("Details", ""),
            "goal": sections.get("Goal", ""),
        },
        "dependencies": [str(value) for value in (data.get("depends_on") or [])],
        "executor": _executor_of(data),
        "system": {
            key: data.get(key) for key in ASSIGNMENT_SYSTEM_FIELDS if key in data
        },
        "ticket": ticket_id,
    }

def assignment_digest(ticket_id: str, text: str) -> str:
    return "sha256:" + _digest(assignment_payload(ticket_id, text))

def generation_identity(kind: str, root_id: str, ordinal: int, payload) -> str:
    if kind not in {"root", "cut"}:
        raise GenerationError("generation kind must be root or cut")
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal <= 0:
        raise GenerationError("generation ordinal must be a positive integer")
    return f"{kind}:{root_id}:{ordinal}:sha256:{_digest(payload)}"

def generation_ordinal(identity: str, kind: str | None = None) -> int:
    match = GENERATION_RE.fullmatch(str(identity or ""))
    if match is None or (kind is not None and match.group(1) != kind):
        raise GenerationError(f"invalid {kind or 'assignment'} generation identity")
    return int(match.group(3))

def _cut_members(root_id: str, snapshot: dict) -> list:
    """Return declared members, with stable child names as the pre-stamp cut."""

    declared = []
    for ticket_id, text in snapshot.items():
        if ticket_id == root_id:
            continue
        match = GENERATION_RE.fullmatch(str(_parse_frontmatter(text).get("root_generation") or ""))
        if match is not None and match.group(1) == "root" and match.group(2) == root_id:
            declared.append(ticket_id)
    if declared:
        return sorted(declared)
    prefix = root_id + "."
    return sorted(
        ticket_id for ticket_id in snapshot
        if ticket_id.startswith(prefix)
    )

def _root_payload(root_id: str, snapshot: dict) -> dict:
    try:
        root_text = snapshot[root_id]
    except KeyError as error:
        raise GenerationError(f"root ticket not found in exact snapshot: {root_id}") from error
    return {"assignment": assignment_payload(root_id, root_text)}

def _root_generation(root_id: str, snapshot: dict, ordinal: int, payload: dict) -> str:
    """Return the run's one root identity; later ordinals belong to cuts."""

    inherited = str(_parse_frontmatter(snapshot[root_id]).get("root_generation") or "")
    if not inherited:
        return generation_identity("root", root_id, 1, payload)
    match = GENERATION_RE.fullmatch(inherited)
    if match is None or match.group(1) != "root" or match.group(2) != root_id:
        raise GenerationError("root ticket carries a malformed or foreign root generation")
    if int(match.group(3)) != 1:
        raise GenerationError(
            "an in-run root amendment generation is unsupported; open a successor run "
            "whose root Context cites the accepted predecessor result identity"
        )
    expected = generation_identity("root", root_id, 1, payload)
    if inherited != expected:
        raise GenerationError(
            "a sealed semantic-root change requires a successor run whose root Context "
            "cites the accepted predecessor result identity"
        )
    return inherited

def _cut_payload(root_id: str, snapshot: dict, root_generation: str, member_ids=None) -> dict:
    members = _cut_members(root_id, snapshot) if member_ids is None else sorted(str(value) for value in member_ids)
    assignments = [
        {"digest": assignment_digest(ticket_id, snapshot[ticket_id]), "id": ticket_id}
        for ticket_id in members
    ]
    return {
        "assignments": assignments,
        "root_generation": root_generation,
    }

def draft_snapshot(root_id: str, snapshot: dict, ordinal: int = 1, member_ids=None) -> dict:
    """Materialize one complete immutable draft from an exact ticket snapshot."""

    root_payload = _root_payload(root_id, snapshot)
    root_generation = _root_generation(root_id, snapshot, ordinal, root_payload)
    cut_payload = _cut_payload(root_id, snapshot, root_generation, member_ids)
    cut_generation = generation_identity("cut", root_id, ordinal, cut_payload)
    return {
        "assignments": cut_payload["assignments"],
        "cut_generation": cut_generation,
        "cut_payload": cut_payload,
        "root_generation": root_generation,
        "root_payload": root_payload,
    }

def validate_draft(root_id: str, snapshot: dict, draft: dict, member_ids=None) -> dict:
    """Grade exactly one draft snapshot and return its validation receipt."""

    ordinal = generation_ordinal(draft.get("cut_generation"), "cut")
    expected = draft_snapshot(root_id, snapshot, ordinal, member_ids)
    if expected != draft:
        raise GenerationError("draft validation failed: supplied draft is not the exact snapshot grade")
    members = [item["id"] for item in draft.get("assignments") or []]
    findings = []
    for ticket_id in [root_id, *members]:
        data = _parse_frontmatter(snapshot[ticket_id])
        findings.extend(binding_findings(ticket_id, data))
        current = str(data.get("assignment_seal") or "").strip()
        if current and current != assignment_digest(ticket_id, snapshot[ticket_id]):
            findings.append({
                "code": "assignment-seal-mismatch",
                "field": "assignment_seal",
                "ticket": ticket_id,
                "detail": "sealed digest does not match the current assignment",
            })
    if findings:
        raise GenerationError(
            "draft validation failed: assignment grade: " + canonical_json(findings)
        )
    return {
        "cut_generation": draft["cut_generation"],
        "draft_digest": "sha256:" + _digest(draft),
        "root_generation": draft["root_generation"],
        "state": "validated",
    }

def seal_assignments(root_id: str, snapshot: dict, draft: dict, receipt: dict, member_ids=None) -> dict:
    """Compare-and-swap seal only the exact draft named by ``receipt``."""

    members = [item["id"] for item in draft.get("assignments") or []]
    if member_ids is not None and sorted(str(value) for value in member_ids) != sorted(members):
        raise GenerationError("seal refused: explicit membership does not name this exact draft")
    validated = validate_draft(root_id, snapshot, draft, members)
    if receipt != validated or receipt.get("state") != "validated":
        raise GenerationError("seal refused: validation receipt does not name this exact draft")
    sealed = dict(snapshot)
    for ticket_id in [root_id, *members]:
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

def seal_findings(ticket_id: str, text: str) -> list:
    """Findings that guard worker eligibility at the assignment seal boundary."""

    data = _parse_frontmatter(text)
    expected = assignment_digest(ticket_id, text)
    seal = str(data.get("assignment_seal") or "").strip()
    findings = []
    if not seal:
        findings.append({"code": "assignment-unsealed", "field": "assignment_seal", "detail": "assignment has no validated seal"})
    elif seal != expected:
        findings.append({"code": "assignment-seal-mismatch", "field": "assignment_seal", "detail": "sealed digest does not match the current assignment"})
    parsed = {}
    for field, kind in (("root_generation", "root"), ("cut_generation", "cut")):
        try:
            value = str(data.get(field) or "")
            generation_ordinal(value, kind)
            parsed[field] = GENERATION_RE.fullmatch(value)
        except GenerationError:
            findings.append({"code": "generation-invalid", "field": field, "detail": f"missing or malformed {kind} generation"})
    if len(parsed) == 2:
        root_match, cut_match = parsed["root_generation"], parsed["cut_generation"]
        if int(root_match.group(3)) != 1:
            findings.append({
                "code": "root-generation-successor-required",
                "field": "root_generation",
                "detail": "an in-run root amendment generation is unsupported; open a successor run linked to the accepted predecessor result",
            })
        if root_match.group(2) != cut_match.group(2):
            findings.append({"code": "generation-pair-mismatch", "field": "cut_generation", "detail": "root and cut generations must name one root"})
    return findings

__all__ = (
    "GENERATION_RE", "GenerationError",
    "assignment_digest", "assignment_payload", "canonical_json",
    "correction_decision",
    "draft_snapshot", "generation_identity", "generation_ordinal",
    "seal_assignments", "validate_draft", "seal_findings",
)
