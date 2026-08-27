"""Deterministic assignment generations and draft/seal mechanics."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
if __package__:
    from .tickets_format import (GATE_EXECUTORS, ROOT_EXECUTOR, _executor_of, _parse_frontmatter, _sections, _set_frontmatter_field, canonical_json)
    from .tickets_transitions import CLAIMED, stamp
else:
    from tickets_format import (GATE_EXECUTORS, ROOT_EXECUTOR, _executor_of, _parse_frontmatter, _sections, _set_frontmatter_field, canonical_json)
    from tickets_transitions import CLAIMED, stamp

GENERATION_RE = re.compile(r"^(root|cut):([A-Za-z0-9][A-Za-z0-9._-]*):(\d+):sha256:([0-9a-f]{64})$")
ASSIGNMENT_SYSTEM_FIELDS = (
    "bound", "independence", "isolation", "pack", "profile", "review_order",
    "sequence",
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
            "goal": sections.get("Goal", ""),
            "suggested_files": sections.get("Suggested files", ""),
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
    """Return the root's existing identity, or open its first generation."""

    inherited = str(_parse_frontmatter(snapshot[root_id]).get("root_generation") or "")
    if not inherited:
        return generation_identity("root", root_id, ordinal, payload)
    match = GENERATION_RE.fullmatch(inherited)
    if match is None or match.group(1) != "root" or match.group(2) != root_id:
        raise GenerationError("root ticket carries a malformed or foreign root generation")
    expected = generation_identity("root", root_id, int(match.group(3)), payload)
    if inherited != expected:
        raise GenerationError("root generation does not name the current root assignment")
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

def composite_gate_findings(root_id: str, snapshot: dict, member_ids=None) -> list:
    """Require the one exact gate around every decomposed multi-result graph."""

    if _executor_of(_parse_frontmatter(snapshot[root_id])) != ROOT_EXECUTOR:
        return []
    members = _cut_members(root_id, snapshot) if member_ids is None else sorted(str(value) for value in member_ids)
    units = sorted(ticket_id for ticket_id in members if ".gate." not in ticket_id)
    if len(units) < 2:
        return []
    prefix = f"{root_id}.gate.critique."
    repair_id = f"{root_id}.gate.repair"
    verify_id = f"{root_id}.gate.verify"
    critiques = sorted(ticket_id for ticket_id in members if ticket_id.startswith(prefix) and ticket_id != prefix)
    expected_gate_ids = set(critiques) | {repair_id, verify_id}
    actual_gate_ids = {ticket_id for ticket_id in members if ".gate." in ticket_id}
    findings = []
    if not critiques:
        findings.append({"code": "composite-gate-missing", "field": "members", "detail": "two or more executor members require at least one critique"})
    for ticket_id in sorted(expected_gate_ids - actual_gate_ids):
        findings.append({"code": "composite-gate-missing", "field": "members", "ticket": ticket_id})
    for ticket_id in sorted(actual_gate_ids - expected_gate_ids):
        findings.append({"code": "composite-gate-extra", "field": "members", "ticket": ticket_id})
    expected = {
        **{ticket_id: (GATE_EXECUTORS["critique"], units) for ticket_id in critiques},
        repair_id: (GATE_EXECUTORS["repair"], critiques),
        verify_id: (GATE_EXECUTORS["verify"], [repair_id]),
    }
    for ticket_id in sorted(expected_gate_ids & actual_gate_ids):
        data = _parse_frontmatter(snapshot[ticket_id])
        executor, dependencies = expected[ticket_id]
        if _executor_of(data) != executor:
            findings.append({"code": "composite-gate-executor", "field": "executor", "ticket": ticket_id, "detail": f"expected {executor}"})
        actual_dependencies = sorted(str(value) for value in (data.get("depends_on") or []))
        if actual_dependencies != sorted(dependencies):
            findings.append({"code": "composite-gate-dependencies", "field": "depends_on", "ticket": ticket_id, "detail": f"expected {sorted(dependencies)}"})
    return findings

def validate_draft(root_id: str, snapshot: dict, draft: dict, member_ids=None) -> dict:
    """Grade exactly one draft snapshot and return its validation receipt."""

    ordinal = generation_ordinal(draft.get("cut_generation"), "cut")
    expected = draft_snapshot(root_id, snapshot, ordinal, member_ids)
    if expected != draft:
        raise GenerationError("draft validation failed: supplied draft is not the exact snapshot grade")
    gate_findings = composite_gate_findings(root_id, snapshot, member_ids)
    if gate_findings:
        raise GenerationError("draft validation failed: composite gate topology: " + canonical_json(gate_findings))
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
        if root_match.group(2) != cut_match.group(2):
            findings.append({"code": "generation-pair-mismatch", "field": "cut_generation", "detail": "root and cut generations must name one root"})
    return findings

DRAFT_VALIDATE_USAGE = "draft-validate <run> <root-id> [--correction-bound N]"
SEAL_USAGE = "seal <run> <root-id> --cut-generation <identity>"


def _store_bindings():
    if __package__:
        from .tickets_store import NO_SINK_ERROR, _run_lock, _runs_root, _segment_error, _tickets_root, _write_text_atomically
    else:
        from tickets_store import NO_SINK_ERROR, _run_lock, _runs_root, _segment_error, _tickets_root, _write_text_atomically
    return NO_SINK_ERROR, _run_lock, _runs_root, _segment_error, _tickets_root, _write_text_atomically


def _extract(args: list, flag: str):
    if flag not in args:
        return None
    index = args.index(flag)
    if index + 1 >= len(args):
        del args[index]
        return None
    value = args[index + 1]
    del args[index:index + 2]
    return value


def _snapshot(run: str):
    NO_SINK_ERROR, _, _, _, tickets_root, _ = _store_bindings()
    root = tickets_root()
    if root is None:
        raise GenerationError(NO_SINK_ERROR)
    run_dir = root / run
    values = {}
    for path in sorted(run_dir.glob("*.md")):
        values[path.stem] = path.read_text(encoding="utf-8")
    return run_dir, values


def _generation_dir(run: str) -> Path:
    NO_SINK_ERROR, _, runs_root, _, _, _ = _store_bindings()
    root = runs_root()
    if root is None:
        raise GenerationError(NO_SINK_ERROR)
    return root / run / "generations"


def _state_path(run: str, cut_generation: str, state: str) -> Path:
    match = GENERATION_RE.fullmatch(cut_generation)
    if match is None or match.group(1) != "cut":
        raise GenerationError("cut generation identity is malformed")
    return _generation_dir(run) / f"{match.group(4)}.{state}.json"


def _validated_documents(run: str) -> list:
    documents = []
    directory = _generation_dir(run)
    for path in sorted(directory.glob("*.validated.json")) if directory.is_dir() else []:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError):
            continue
        if isinstance(value, dict) and isinstance(value.get("draft"), dict):
            documents.append(value)
    return documents


def _next_draft(run: str, root_id: str, snapshot: dict) -> dict:
    documents = _validated_documents(run)
    ranked = []
    for document in documents:
        prior = document["draft"]
        try:
            identity = str(prior.get("cut_generation") or "")
            match = GENERATION_RE.fullmatch(identity)
            if match is not None and match.group(2) == root_id:
                ranked.append((generation_ordinal(identity, "cut"), prior))
        except GenerationError:
            continue
    if not ranked:
        return draft_snapshot(root_id, snapshot, 1)
    highest, latest = max(ranked, key=lambda item: item[0])
    candidate = draft_snapshot(root_id, snapshot, highest)
    return latest if candidate == latest else draft_snapshot(root_id, snapshot, highest + 1)


def _draft_findings(root_id: str, snapshot: dict) -> list:
    # A claimed root is an allowed grading vantage; a claimed member is not.
    positions = frozenset(stamp("draft-validate").draft_statuses)
    findings = []
    for ticket_id in [root_id, *_cut_members(root_id, snapshot)]:
        data = _parse_frontmatter(snapshot[ticket_id])
        status = str(data.get("status") or "")
        explicit = "root_generation" in data
        if not explicit:
            findings.append({"code": "generation-missing", "field": "root_generation", "ticket": ticket_id})
        if status not in (positions | {CLAIMED} if ticket_id == root_id else positions):
            findings.append({"code": "draft-status", "field": "status", "ticket": ticket_id})
    findings.extend(composite_gate_findings(root_id, snapshot))
    return findings


def _failure_path(run: str, root_id: str) -> Path:
    return _generation_dir(run) / f"{root_id}.failures.json"


def _record_failure(run: str, root_id: str, findings: list, bound: int, write_atomically) -> dict:
    path = _failure_path(run, root_id)
    history = []
    if path.is_file():
        value = json.loads(path.read_text(encoding="utf-8"))
        history = list(value.get("history") or []) if isinstance(value, dict) else []
    decision = correction_decision(findings, history, bound)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_atomically(path, canonical_json({"bound": bound, "history": decision.get("history") or history}) + "\n")
    return decision


def _cmd_draft_validate(rest) -> dict:
    args = list(rest)
    bound_value = _extract(args, "--correction-bound")
    if len(args) != 2:
        return {"error": f"usage: {DRAFT_VALIDATE_USAGE}"}
    run, root_id = args
    _, _, _, segment_error, _, _ = _store_bindings()
    for kind, value in (("run id", run), ("ticket id", root_id)):
        refusal = segment_error(kind, value)
        if refusal is not None: return refusal
    try:
        bound = 1 if bound_value is None else int(bound_value)
        if bound <= 0:
            raise ValueError
    except ValueError:
        return {"error": "--correction-bound must be a finite positive integer"}
    _, run_lock, _, _, _, write_atomically = _store_bindings()
    try:
        with run_lock(run):
            _, snapshot = _snapshot(run)
            if root_id not in snapshot:
                return {"error": f"root ticket not found in exact snapshot: {root_id}"}
            findings = _draft_findings(root_id, snapshot)
            if findings:
                decision = _record_failure(run, root_id, findings, bound, write_atomically)
                return {"error": "draft validation failed", "findings": findings, "correction": decision}
            draft = _next_draft(run, root_id, snapshot)
            receipt = validate_draft(root_id, snapshot, draft)
            document = {"draft": draft, "receipt": receipt}
            path = _state_path(run, draft["cut_generation"], "validated")
            path.parent.mkdir(parents=True, exist_ok=True)
            encoded = canonical_json(document) + "\n"
            if path.exists() and path.read_text(encoding="utf-8") != encoded:
                return {"error": "content-addressed validation receipt collision"}
            if not path.exists():
                write_atomically(path, encoded)
    except (OSError, UnicodeDecodeError, GenerationError) as error:
        return {"error": str(error)}
    return {"draft_validation": {**receipt, "path": str(path)}}


def _cmd_seal(rest) -> dict:
    args = list(rest)
    cut_generation = _extract(args, "--cut-generation")
    if len(args) != 2 or cut_generation is None:
        return {"error": f"usage: {SEAL_USAGE}"}
    run, root_id = args
    _, run_lock, _, segment_error, _, write_atomically = _store_bindings()
    for kind, value in (("run id", run), ("ticket id", root_id)):
        refusal = segment_error(kind, value)
        if refusal is not None: return refusal
    try:
        with run_lock(run):
            run_dir, snapshot = _snapshot(run)
            validated_path = _state_path(run, cut_generation, "validated")
            if not validated_path.is_file():
                return {"error": "seal refused: no validation receipt for requested cut generation"}
            document = json.loads(validated_path.read_text(encoding="utf-8"))
            draft, receipt = document["draft"], document["receipt"]
            if draft.get("cut_generation") != cut_generation:
                return {"error": "seal refused: validation receipt names another cut generation"}
            findings = _draft_findings(root_id, snapshot)
            if findings:
                return {"error": "seal refused: snapshot is not a mutable assignment draft", "findings": findings}
            sealed = seal_assignments(root_id, snapshot, draft, receipt)
            prior = dict(snapshot)
            try:
                for ticket_id, text in sealed.items():
                    if text != snapshot[ticket_id]:
                        write_atomically(run_dir / f"{ticket_id}.md", text)
                sealed_path = _state_path(run, cut_generation, "sealed")
                sealed_path.parent.mkdir(parents=True, exist_ok=True)
                member_ids = [item["id"] for item in draft.get("assignments") or []]
                seals = {
                    ticket_id: _parse_frontmatter(sealed[ticket_id]).get("assignment_seal")
                    for ticket_id in [root_id, *member_ids]
                }
                record = {"assignment_seals": seals, "cut_generation": draft["cut_generation"], "receipt": receipt, "root_generation": draft["root_generation"], "root_id": root_id, "state": "sealed"}
                write_atomically(sealed_path, canonical_json(record) + "\n")
            except OSError:
                for ticket_id, text in prior.items():
                    write_atomically(run_dir / f"{ticket_id}.md", text)
                raise
    except (OSError, UnicodeDecodeError, ValueError, KeyError, GenerationError, json.JSONDecodeError) as error:
        return {"error": str(error)}
    return {"assignment_seal": {"cut_generation": cut_generation, "root_generation": draft["root_generation"], "state": "sealed", "path": str(sealed_path)}}


GENERATION_SUBCOMMANDS = {
    "draft-validate": (DRAFT_VALIDATE_USAGE, "Grade one exact assignment snapshot and persist its content-addressed validation receipt.", _cmd_draft_validate),
    "seal": (SEAL_USAGE, "Compare-and-swap seal only the exact validated cut generation, making its units eligible for admission.", _cmd_seal),
}


__all__ = (
    "GENERATION_RE", "GenerationError",
    "assignment_digest", "assignment_payload", "canonical_json", "composite_gate_findings", "correction_decision",
    "draft_snapshot", "generation_identity", "generation_ordinal", "seal_assignments",
    "validate_draft", "seal_findings",
    "_cmd_draft_validate", "_cmd_seal",
)
