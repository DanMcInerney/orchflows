"""Pure grading for one sealed ticket assignment."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

if __package__:
    from . import _bootstrap
    from .tickets_registry import EXECUTOR_REGISTRY, executor_refusal, executor_registered
    from .tickets_adapters import AdapterError, adapter_spec
    from .tickets_format import (
        RESULT_BEARING_STATES,
        SCRIPT_EXECUTOR_PREFIX, adapter_id, canonical_json, declared_parent,
        round_parent, _executor_of,
        _parse_frontmatter, _set_frontmatter_field,
    )
else:
    import _bootstrap
    from tickets_registry import EXECUTOR_REGISTRY, executor_refusal, executor_registered
    from tickets_adapters import AdapterError, adapter_spec
    from tickets_format import (
        RESULT_BEARING_STATES,
        SCRIPT_EXECUTOR_PREFIX, adapter_id, canonical_json, declared_parent,
        round_parent, _executor_of,
        _parse_frontmatter, _set_frontmatter_field,
    )

ADMISSION_PENDING = "pending"
# Re-exported, never respelled: `tickets_format` owns which terminal states
# carry a Result, and `tickets_readiness` answers the same question for the
# reader, so one spelling serves both.
_RECEIPT_RE = re.compile(r"^([a-z][a-z0-9-]*):sha256:([0-9a-f]{64})$")


def is_receipt(value) -> bool:
    return bool(_RECEIPT_RE.fullmatch(str(value or "").strip()))


def finding(code: str, field: str, detail: str) -> dict:
    return {"code": code, "field": field, "detail": detail}


def _ordered(findings) -> list:
    rows = {
        (str(item.get("code") or ""), str(item.get("field") or ""), str(item.get("detail") or ""))
        for item in findings
    }
    return [finding(*row) for row in sorted(rows)]


def adapter_resolution(data):
    """Resolve one ticket's declared adapter as data, never as a traceback.

    The adapter is declared by whichever resolved standard introduces the
    domain, so the ticket names it only through its stamped chain: this
    reads that chain and hands the rest of the module the one name every
    adapter-keyed derivation is taken off.
    """

    if __package__:
        from .tickets_pins import STANDARDS_FIELD, adapter_standard
    else:  # pragma: no cover - direct/installed flat script path
        from tickets_pins import STANDARDS_FIELD, adapter_standard
    if not data.get(STANDARDS_FIELD):
        return None, None
    stamped = adapter_standard(data)
    if not stamped:
        return None, None
    try:
        return adapter_id(stamped), None
    except AdapterError as error:
        return None, finding(error.code, STANDARDS_FIELD, error.detail)


def binding_findings(ticket_id: str, data: dict) -> list:
    """Grade script resolution and adapter-owned operational isolation."""
    if __package__:
        from .tickets_pins import STANDARDS_FIELD
    else:  # pragma: no cover - direct/installed flat script path
        from tickets_pins import STANDARDS_FIELD
    findings = []
    executor = _executor_of(data)
    stamped = bool(data.get(STANDARDS_FIELD))
    if (
        executor
        and not executor.startswith(SCRIPT_EXECUTOR_PREFIX)
        and not executor_registered(executor)
    ):
        findings.append(finding("executor-unregistered", "executor", executor_refusal(executor)))
    elif EXECUTOR_REGISTRY.get(executor, {}).get("requires_pack") and not stamped:
        findings.append(finding(
            "executor-pack-required", STANDARDS_FIELD,
            f"{executor} reads a resolved standard and requires one stamped",
        ))
    unbound = executor.startswith(SCRIPT_EXECUTOR_PREFIX)
    if executor.startswith(SCRIPT_EXECUTOR_PREFIX):
        target = executor[len(SCRIPT_EXECUTOR_PREFIX):].strip()
        if not (_bootstrap.ROOT / target).is_file():
            findings.append(finding(
                "script-executor-unresolved", "executor",
                f"executor names script '{target or '<missing>'}', which does not resolve in the tree",
            ))
    if stamped and not unbound:
        _adapter, adapter_failure = adapter_resolution(data)
        if adapter_failure is not None:
            findings.append(adapter_failure)
    findings.extend(stamped_item_findings(data))
    return findings


def stamped_item_findings(data: dict) -> list:
    """Re-derive every level of the stamped chain, and the applied skill."""

    if __package__:
        from .tickets_pins import pinned_findings
    else:  # pragma: no cover - direct/installed flat script path
        from tickets_pins import pinned_findings
    return pinned_findings(data, finding)


def landing_round_parent(ticket_id: str, siblings) -> str | None:
    """The sealed ticket whose landing machinery minted this id, or ``None``."""
    parent_id = round_parent(ticket_id)
    if parent_id is None or parent_id not in dict(siblings or {}):
        return None
    return parent_id


def post_seal_parent(ticket_id: str, data: dict, siblings) -> str | None:
    """The sealed ticket whose machinery minted this one after the cut, or None."""
    declared = declared_parent(data)
    if declared and declared in dict(siblings or {}):
        return declared
    return landing_round_parent(ticket_id, siblings)


def _canonical_json(value) -> bytes:
    return canonical_json(value).encode("utf-8")


def sealed_parent_target(ticket_id, text, data, siblings, digest, sealed_assignments=None):
    """The sealed ticket one lawful post-seal chain binds its admission through."""
    sealed_assignments = dict(sealed_assignments or {})
    visited = {ticket_id}
    current_id, current_text, current_data = ticket_id, text, data
    while True:
        parent_id = post_seal_parent(current_id, current_data, siblings)
        if parent_id is None or parent_id in visited:
            return None
        parent = _parse_frontmatter(siblings[parent_id])
        if any(
            str(current_data.get(field) or "") != str(parent.get(field) or "")
            for field in ("cut_generation", "root_generation")
        ):
            return None
        if str(current_data.get("assignment_seal") or "") != digest(current_id, current_text):
            return None
        if parent_id in sealed_assignments:
            return parent_id
        visited.add(parent_id)
        current_id, current_text, current_data = parent_id, siblings[parent_id], parent


def grade_admission(ticket_id: str, text: str, siblings: dict, context=None) -> dict:
    """Grade one exact sealed snapshot and return its portable receipt."""
    context = dict(context or {})
    siblings = dict(siblings or {})
    data = _parse_frontmatter(text)
    if __package__:
        from .tickets_generations import GENERATION_RE, assignment_digest, seal_findings
    else:
        module = __import__("tickets_generations")
        GENERATION_RE = module.GENERATION_RE
        assignment_digest = module.assignment_digest
        seal_findings = module.seal_findings
    findings = list(seal_findings(ticket_id, text))
    adapter, adapter_failure = adapter_resolution(data)
    if adapter_failure is not None:
        findings.append(adapter_failure)
    dependencies = [str(value) for value in (data.get("depends_on") or [])]
    for dependency in dependencies:
        if dependency not in siblings:
            findings.append(finding("dependency-dangling", "depends_on", dependency))
        else:
            status = str(_parse_frontmatter(siblings[dependency]).get("status") or "")
            if status not in RESULT_BEARING_STATES:
                findings.append(finding("dependency-incomplete", "depends_on", f"{dependency}:{status or '<missing>'}"))
    findings.extend(binding_findings(ticket_id, data))
    sealed_record = None
    runs_root = context.get("runs_root")
    run = str(data.get("run") or context.get("run") or "")
    cut_generation = str(data.get("cut_generation") or "")
    match = GENERATION_RE.fullmatch(cut_generation)
    if not runs_root or not run or match is None:
        findings.append(finding("seal-state-unavailable", "cut_generation", "admission requires the sealed run-state record"))
    else:
        directory = Path(runs_root) / run / "generations"
        try:
            sealed_record = json.loads((directory / f"{match.group(4)}.sealed.json").read_text(encoding="utf-8-sig"))
            validated = json.loads((directory / f"{match.group(4)}.validated.json").read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeDecodeError, ValueError):
            findings.append(finding("seal-state-missing", "cut_generation", "sealed and validated records must resolve"))
        else:
            root_match = GENERATION_RE.fullmatch(str(data.get("root_generation") or ""))
            expected = {
                "cut_generation": cut_generation,
                "root_generation": str(data.get("root_generation") or ""),
                "root_id": root_match.group(2) if root_match is not None else None,
                "state": "sealed",
            }
            if not isinstance(sealed_record, dict) or any(sealed_record.get(key) != value for key, value in expected.items()):
                findings.append(finding("seal-state-mismatch", "cut_generation", "sealed state names another generation"))
            draft = validated.get("draft") if isinstance(validated, dict) else None
            if not isinstance(draft, dict) or sealed_record.get("receipt") != validated.get("receipt") or draft.get("cut_generation") != cut_generation:
                findings.append(finding("validation-receipt-mismatch", "cut_generation", "sealed state does not bind the validation receipt"))
            sealed_assignments = sealed_record.get("assignment_seals") or {}
            sealed_parent = sealed_parent_target(
                ticket_id, text, data, siblings, assignment_digest,
                sealed_assignments,
            )
            if sealed_parent is not None:
                parent = _parse_frontmatter(siblings[sealed_parent])
                if sealed_assignments.get(sealed_parent) != parent.get("assignment_seal"):
                    findings.append(finding(
                        "sealed-parent-mismatch", "assignment_seal",
                        "sealed state does not bind the parent this child was minted under",
                    ))
            elif sealed_assignments.get(ticket_id) != data.get("assignment_seal"):
                findings.append(finding("sealed-assignment-mismatch", "assignment_seal", "sealed state does not bind this assignment"))
    ordered = _ordered(findings)
    receipt = ADMISSION_PENDING
    if not ordered:
        payload = {"assignment": assignment_digest(ticket_id, text), "sealed_state": sealed_record}
        receipt = f"{adapter or 'ticket'}:sha256:{hashlib.sha256(_canonical_json(payload)).hexdigest()}"
    return {
        "adapter": adapter, "findings": ordered, "receipt": receipt,
        "snapshot_ids": sorted({ticket_id, *dependencies}),
    }


def dependency_order_findings(ticket_id: str, data: dict) -> list:
    """Refuse an unsorted ``depends_on`` where it is still cheap to fix."""

    dependencies = [str(value) for value in (data.get("depends_on") or [])]
    if dependencies == sorted(dependencies):
        return []
    return [{
        "code": "depends-on-unsorted",
        "field": "depends_on",
        "ticket": ticket_id,
        "detail": "depends_on must be in ascending order: " + ", ".join(sorted(dependencies)),
    }]


def refresh_admissions(run, run_dir, snapshot: dict, write_atomically) -> list:
    """Re-issue the receipts one lawful mutation of this run invalidated."""

    if __package__:
        from .tickets_context import graded_admission
    else:  # pragma: no cover - direct/installed flat script path
        from tickets_context import graded_admission
    current = dict(snapshot)
    rewritten = []
    for ticket_id in sorted(current):
        stored = str(_parse_frontmatter(current[ticket_id]).get("admission") or "")
        if not stored or stored == ADMISSION_PENDING:
            continue
        grade = graded_admission(ticket_id, current[ticket_id], current, run)
        if grade["findings"] or grade["receipt"] == stored:
            continue
        text = _set_frontmatter_field(current[ticket_id], "admission", grade["receipt"])
        current[ticket_id] = text
        write_atomically(Path(run_dir) / f"{ticket_id}.md", text)
        rewritten.append(ticket_id)
    return rewritten


__all__ = (
    "ADMISSION_PENDING", "RESULT_BEARING_STATES", "adapter_id",
    "binding_findings", "dependency_order_findings", "finding",
    "grade_admission", "is_receipt",
    "landing_round_parent",
    "pinned_digest_finding", "post_seal_parent", "refresh_admissions",
    "sealed_parent_target", "stamped_item_findings",
)
