"""Pure grading for one sealed ticket assignment."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

if __package__:
    from .tickets_adapters import AdapterError, adapter_spec
    from .tickets_format import (
        GATE_EXECUTORS,
        SCRIPT_EXECUTOR_PREFIX, adapter_id, canonical_json,
        _executor_of, _parse_frontmatter,
    )
else:
    from tickets_adapters import AdapterError, adapter_spec
    from tickets_format import (
        GATE_EXECUTORS,
        SCRIPT_EXECUTOR_PREFIX, adapter_id, canonical_json,
        _executor_of, _parse_frontmatter,
    )

ADMISSION_PENDING = "pending"
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


def adapter_resolution(pack):
    """Resolve one declared pack adapter as data, never as a traceback."""

    if not str(pack or "").strip():
        return None, None
    try:
        return adapter_id(pack), None
    except AdapterError as error:
        return None, finding(error.code, "pack", error.detail)


def binding_findings(ticket_id: str, data: dict) -> list:
    """Grade script resolution and adapter-owned operational isolation."""
    findings = []
    executor = _executor_of(data)
    pack = str(data.get("pack") or "").strip()
    if executor.startswith(SCRIPT_EXECUTOR_PREFIX):
        target = executor[len(SCRIPT_EXECUTOR_PREFIX):].strip()
        if not (Path(__file__).resolve().parents[1] / target).is_file():
            findings.append(finding(
                "script-executor-unresolved", "executor",
                f"executor names script '{target or '<missing>'}', which does not resolve in the tree",
            ))
    if pack:
        adapter, adapter_failure = adapter_resolution(pack)
        if adapter_failure is not None:
            findings.append(adapter_failure)
        elif adapter and adapter_spec(pack).establishes_isolation and str(data.get("isolation") or "none").strip() != "required":
            findings.append(finding(
                "vcs-isolation-required", "isolation",
                "the selected adapter requires an isolated candidate workspace",
            ))
    return findings


def _canonical_json(value) -> bytes:
    return canonical_json(value).encode("utf-8")


def _ordinary_review_target(ticket_id: str, data: dict, dependencies, siblings):
    if ticket_id.endswith(".check") and dependencies == [
        ticket_id[:-len(".check")]
    ]:
        return dependencies[0], None
    target_id = None
    kind = None
    if ticket_id.endswith(".gate.repair"):
        target_id = ticket_id[:-len(".gate.repair")]
        kind = "repair"
    elif ticket_id.endswith(".gate.verify"):
        target_id = ticket_id[:-len(".gate.verify")]
        kind = "verify"
    else:
        return None
    target_text = siblings.get(target_id)
    checker_text = siblings.get(f"{target_id}.check")
    if target_text is None or checker_text is None:
        return None
    target = _parse_frontmatter(target_text)
    checker = _parse_frontmatter(checker_text)
    if (
        str(target.get("independence") or "checker") != "checker"
        or not str(target.get("checked_by") or "").strip()
        or str(target.get("review_stage") or "") != f"{target_id}.check"
        or str(checker.get("status") or "") != "complete"
        or _executor_of(checker) != GATE_EXECUTORS["critique"]
        or list(checker.get("depends_on") or []) != [target_id]
    ):
        return None
    run = str(target.get("run") or data.get("run") or "")
    if __package__:
        from .tickets_ordinary_review import ordinary_stage_text
    else:
        from tickets_ordinary_review import ordinary_stage_text
    return target_id, ordinary_stage_text(run, target_id, target, kind)


def grade_admission(ticket_id: str, text: str, siblings: dict, context=None) -> dict:
    """Grade one exact sealed snapshot and return its portable receipt."""
    context = dict(context or {})
    data = _parse_frontmatter(text)
    if __package__:
        from .tickets_generations import GENERATION_RE, assignment_digest, seal_findings
    else:
        module = __import__("tickets_generations")
        GENERATION_RE = module.GENERATION_RE
        assignment_digest = module.assignment_digest
        seal_findings = module.seal_findings
    findings = list(seal_findings(ticket_id, text))
    adapter, adapter_failure = adapter_resolution(data.get("pack"))
    if adapter_failure is not None:
        findings.append(adapter_failure)
    dependencies = [str(value) for value in (data.get("depends_on") or [])]
    for dependency in dependencies:
        if dependency not in siblings:
            findings.append(finding("dependency-dangling", "depends_on", dependency))
        else:
            status = str(_parse_frontmatter(siblings[dependency]).get("status") or "")
            if status != "complete":
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
            sealed_record = json.loads((directory / f"{match.group(4)}.sealed.json").read_text(encoding="utf-8"))
            validated = json.loads((directory / f"{match.group(4)}.validated.json").read_text(encoding="utf-8"))
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
            review_target = _ordinary_review_target(
                ticket_id, data, dependencies, siblings,
            )
            if review_target is not None:
                target_id, expected_stage = review_target
                target_text = siblings.get(target_id)
                target = _parse_frontmatter(target_text) if target_text is not None else {}
                if sealed_assignments.get(target_id) != target.get("assignment_seal"):
                    findings.append(finding(
                        "sealed-checker-target-mismatch"
                        if ticket_id.endswith(".check")
                        else "sealed-review-target-mismatch",
                        "assignment_seal",
                        "sealed state does not bind the checker target"
                        if ticket_id.endswith(".check")
                        else "sealed state does not bind the ordinary review target",
                    ))
                if expected_stage is not None:
                    if __package__:
                        from .tickets_ordinary_review import ordinary_stage_matches
                    else:
                        from tickets_ordinary_review import ordinary_stage_matches
                if expected_stage is not None and not ordinary_stage_matches(
                    ticket_id, text, expected_stage,
                ):
                    findings.append(finding(
                        "ordinary-review-stage-mismatch", "assignment_seal",
                        "ordinary repair or verification assignment differs from "
                        "the canonical checked-target continuation",
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


__all__ = (
    "ADMISSION_PENDING", "adapter_id",
    "binding_findings", "finding",
    "grade_admission", "is_receipt",
)
