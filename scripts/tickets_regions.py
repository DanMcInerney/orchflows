"""Stable ownership-region validation for same-artifact parallel work."""

from __future__ import annotations

import json

ALLOWED_SELECTOR_KINDS = frozenset({"symbol", "heading", "json-pointer", "adapter-equivalent"})
FALLBACK = "dependency-order-or-sole-owner"


def _finding(code: str, field: str, detail: str) -> dict:
    return {"code": code, "field": field, "detail": detail}


def _records(value, field: str):
    """Decode records from adapters or ticket frontmatter JSON entries."""

    if value is None or value == "":
        return ([], [])
    raw = value if isinstance(value, list) else [value]
    records, findings = [], []
    for position, item in enumerate(raw, start=1):
        if isinstance(item, dict):
            records.append(item)
            continue
        try:
            parsed = json.loads(str(item))
        except (TypeError, ValueError, json.JSONDecodeError):
            findings.append(_finding(f"{field}-invalid", field, f"record {position} is not JSON object data"))
            continue
        if not isinstance(parsed, dict):
            findings.append(_finding(f"{field}-invalid", field, f"record {position} is not an object"))
            continue
        records.append(parsed)
    return records, findings


def _regions(data: dict):
    return _records(data.get("ownership_regions"), "ownership-regions")


def _merge_oracles(data: dict):
    return _records(data.get("merge_oracles"), "merge-oracles")


def region_findings(ticket_id: str, data: dict) -> list:
    records, findings = _regions(data)
    for position, record in enumerate(records, start=1):
        field = f"ownership_regions[{position}]"
        artifact = record.get("artifact")
        selector = record.get("selector")
        proof = record.get("proof")
        if not isinstance(artifact, str) or not artifact.strip():
            findings.append(_finding("region-artifact-missing", field, f"{ticket_id} names no artifact"))
        if not isinstance(selector, dict):
            findings.append(_finding("region-selector-missing", field, f"{ticket_id} names no selector object"))
        else:
            kind = selector.get("kind")
            if kind not in ALLOWED_SELECTOR_KINDS:
                findings.append(_finding("region-selector-kind", field, f"selector kind {kind!r} is not stable; line selectors are prohibited"))
            if not isinstance(selector.get("value"), str) or not selector.get("value", "").strip():
                findings.append(_finding("region-selector-value", field, "selector value must be non-empty"))
        if not isinstance(proof, dict):
            findings.append(_finding("region-proof-missing", field, "a pinned adapter non-overlap proof is required"))
        else:
            required = ("adapter", "identity", "non-overlap")
            if any(not isinstance(proof.get(key), str) or not proof.get(key, "").strip() for key in required):
                findings.append(_finding("region-proof-invalid", field, f"proof requires non-empty {list(required)}"))
    return sorted(findings, key=lambda item: (item["code"], item["field"], item["detail"]))


def _for_artifact(records, artifact: str) -> list:
    return [record for record in records if str(record.get("artifact") or "") == artifact]


def parallel_admission(left_id: str, left: dict, right_id: str, right: dict, artifact: str) -> dict:
    """Prove stable non-overlap and a shared merge oracle for one artifact."""

    findings = region_findings(left_id, left) + region_findings(right_id, right)
    left_regions, left_parse = _regions(left)
    right_regions, right_parse = _regions(right)
    findings.extend(left_parse + right_parse)
    left_at = _for_artifact(left_regions, artifact)
    right_at = _for_artifact(right_regions, artifact)
    if len(left_at) != 1 or len(right_at) != 1:
        findings.append(_finding("region-ownership-missing", "ownership_regions", f"{artifact} requires exactly one region from each parallel owner"))
    elif not findings:
        left_region, right_region = left_at[0], right_at[0]
        if left_region.get("proof") != right_region.get("proof"):
            findings.append(_finding("region-proof-mismatch", "ownership_regions", "string inequality is not proof; both selectors must cite one adapter-certified non-overlap set"))
        elif left_region.get("selector") == right_region.get("selector"):
            findings.append(_finding("region-overlap", "ownership_regions", f"{left_id} and {right_id} claim the same stable selector"))
    left_oracles, left_oracle_findings = _merge_oracles(left)
    right_oracles, right_oracle_findings = _merge_oracles(right)
    findings.extend(left_oracle_findings + right_oracle_findings)
    left_merge = _for_artifact(left_oracles, artifact)
    right_merge = _for_artifact(right_oracles, artifact)
    if len(left_merge) != 1 or len(right_merge) != 1:
        findings.append(_finding("merge-oracle-missing", "merge_oracles", f"{artifact} requires one merge oracle from each parallel owner"))
    else:
        for owner, record in ((left_id, left_merge[0]), (right_id, right_merge[0])):
            if not all(isinstance(record.get(key), str) and record.get(key, "").strip() for key in ("identity", "oracle")):
                findings.append(_finding("merge-oracle-invalid", "merge_oracles", f"{owner} merge oracle requires identity and oracle"))
        if left_merge[0].get("identity") != right_merge[0].get("identity"):
            findings.append(_finding("merge-oracle-mismatch", "merge_oracles", "parallel owners cite different merge oracle identities"))
    unique = {(item["code"], item["field"], item["detail"]): item for item in findings}
    ordered = [unique[key] for key in sorted(unique)]
    return {"admitted": not ordered, "fallback": None if not ordered else FALLBACK, "findings": ordered}


__all__ = ("ALLOWED_SELECTOR_KINDS", "FALLBACK", "parallel_admission", "region_findings")
