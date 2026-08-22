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
from pathlib import Path

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


DRAFT_VALIDATE_USAGE = "draft-validate <run> <root-id> [--correction-bound N]"
SEAL_USAGE = "seal <run> <root-id> --cut-generation <identity>"
AMENDMENT_REQUEST_USAGE = "amendment-request <run> <id> --record <canonical-json>"


def _store_bindings():
    if __package__:
        from .tickets_store import NO_SINK_ERROR, _run_lock, _runs_root, _tickets_root, _write_text_atomically
    else:
        from tickets_store import NO_SINK_ERROR, _run_lock, _runs_root, _tickets_root, _write_text_atomically
    return NO_SINK_ERROR, _run_lock, _runs_root, _tickets_root, _write_text_atomically


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
    NO_SINK_ERROR, _, _, tickets_root, _ = _store_bindings()
    root = tickets_root()
    if root is None:
        raise GenerationError(NO_SINK_ERROR)
    run_dir = root / run
    values = {}
    for path in sorted(run_dir.glob("*.md")):
        values[path.stem] = path.read_text(encoding="utf-8")
    return run_dir, values


def _generation_dir(run: str) -> Path:
    NO_SINK_ERROR, _, runs_root, _, _ = _store_bindings()
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
    highest = 0
    for document in documents:
        prior = document["draft"]
        try:
            ordinal = generation_ordinal(prior.get("cut_generation"), "cut")
        except GenerationError:
            continue
        highest = max(highest, ordinal)
        if draft_snapshot(root_id, snapshot, ordinal) == prior:
            return prior
    return draft_snapshot(root_id, snapshot, highest + 1)


def _cmd_draft_validate(rest) -> dict:
    args = list(rest)
    bound_value = _extract(args, "--correction-bound")
    if len(args) != 2:
        return {"error": f"usage: {DRAFT_VALIDATE_USAGE}"}
    run, root_id = args
    try:
        bound = 1 if bound_value is None else int(bound_value)
        if bound <= 0:
            raise ValueError
    except ValueError:
        return {"error": "--correction-bound must be a finite positive integer"}
    _, run_lock, _, _, write_atomically = _store_bindings()
    try:
        with run_lock(run):
            _, snapshot = _snapshot(run)
            draft = _next_draft(run, root_id, snapshot)
            receipt = validate_draft(root_id, snapshot, draft)
            document = {"correction_bound": bound, "draft": draft, "receipt": receipt}
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
    _, run_lock, _, _, write_atomically = _store_bindings()
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
            sealed = seal_assignments(root_id, snapshot, draft, receipt)
            root_text = sealed[root_id]
            root_text = _set_frontmatter_field(root_text, "root_generation", draft["root_generation"])
            root_text = _set_frontmatter_field(root_text, "cut_generation", draft["cut_generation"])
            sealed[root_id] = root_text
            prior = dict(snapshot)
            try:
                for ticket_id, text in sealed.items():
                    if text != snapshot[ticket_id]:
                        write_atomically(run_dir / f"{ticket_id}.md", text)
                sealed_path = _state_path(run, cut_generation, "sealed")
                sealed_path.parent.mkdir(parents=True, exist_ok=True)
                write_atomically(sealed_path, canonical_json({"receipt": receipt, "state": "sealed"}) + "\n")
            except OSError:
                for ticket_id, text in prior.items():
                    write_atomically(run_dir / f"{ticket_id}.md", text)
                raise
    except (OSError, UnicodeDecodeError, ValueError, KeyError, GenerationError, json.JSONDecodeError) as error:
        return {"error": str(error)}
    return {"assignment_seal": {"cut_generation": cut_generation, "root_generation": draft["root_generation"], "state": "sealed", "path": str(sealed_path)}}


def _cmd_amendment_request(rest) -> dict:
    args = list(rest)
    encoded = _extract(args, "--record")
    if len(args) != 2 or encoded is None:
        return {"error": f"usage: {AMENDMENT_REQUEST_USAGE}"}
    run, ticket_id = args
    try:
        record = json.loads(encoded)
        if canonical_json(record) != encoded:
            raise GenerationError("amendment request JSON must be canonical")
    except (ValueError, json.JSONDecodeError, GenerationError) as error:
        return {"error": str(error)}
    _, run_lock, _, tickets_root, write_atomically = _store_bindings()
    root = tickets_root()
    if root is None:
        return {"error": _store_bindings()[0]}
    path = root / run / f"{ticket_id}.md"
    try:
        with run_lock(run):
            text = path.read_text(encoding="utf-8")
            if record.get("requester-ticket") != ticket_id:
                return {"error": "requester-ticket must equal the worker ticket being written"}
            updated = append_amendment_request(text, record)
            updated = _set_frontmatter_field(updated, "status", "suspended")
            write_atomically(path, updated)
    except (OSError, UnicodeDecodeError, GenerationError) as error:
        return {"error": str(error)}
    return {"amendment_request": {"id": record["request-id"], "run": run, "ticket": ticket_id, "status": "suspended"}}


__all__ = (
    "AMENDMENT_FIELDS", "GENERATION_RE", "GenerationError", "append_amendment_request",
    "assignment_digest", "assignment_payload", "canonical_json", "correction_decision",
    "draft_snapshot", "generation_identity", "generation_ordinal", "seal_assignments",
    "validate_draft", "v2_seal_findings", "_cmd_amendment_request",
    "_cmd_draft_validate", "_cmd_seal",
)
