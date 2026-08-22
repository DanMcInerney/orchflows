"""Stable ownership-region validation for same-artifact parallel work."""

from __future__ import annotations

import json

ALLOWED_SELECTOR_KINDS = frozenset({"symbol", "heading", "json-pointer", "adapter-equivalent"})
ADAPTER_SELECTOR_KINDS = {
    "git": frozenset({"symbol", "json-pointer"}),
    "document-tree": frozenset({"heading"}),
    "git-plus-render": frozenset({"symbol", "json-pointer"}),
    "evidence-store": frozenset({"adapter-equivalent"}),
}
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


def _adapter(data: dict) -> str:
    if __package__:
        from .tickets_format import adapter_id
    else:
        from tickets_format import adapter_id
    return adapter_id(data.get("pack"))


def region_findings(ticket_id: str, data: dict, adapter: str | None = None) -> list:
    records, findings = _regions(data)
    expected_adapter = adapter or _adapter(data)
    for position, record in enumerate(records, start=1):
        field = f"ownership_regions[{position}]"
        required = {"artifact", "merge_oracle", "owner", "selector"}
        if set(record) != required:
            findings.append(_finding("region-fields", field, f"record fields must be exactly {sorted(required)}"))
        artifact = record.get("artifact")
        selector = record.get("selector")
        if not isinstance(artifact, str) or not artifact.strip():
            findings.append(_finding("region-artifact-missing", field, f"{ticket_id} names no artifact"))
        if record.get("owner") != ticket_id:
            findings.append(_finding("region-owner-mismatch", field, f"owner must equal {ticket_id}"))
        if not isinstance(record.get("merge_oracle"), str) or not record.get("merge_oracle", "").strip():
            findings.append(_finding("merge-oracle-missing", field, "merge_oracle must be one non-empty identity"))
        if not isinstance(selector, dict):
            findings.append(_finding("region-selector-missing", field, f"{ticket_id} names no selector object"))
        else:
            kind = selector.get("kind")
            if kind not in ALLOWED_SELECTOR_KINDS:
                findings.append(_finding("region-selector-kind", field, f"selector kind {kind!r} is not stable; line selectors are prohibited"))
            if not isinstance(selector.get("value"), str) or not selector.get("value", "").strip():
                findings.append(_finding("region-selector-value", field, "selector value must be non-empty"))
            allowed = ADAPTER_SELECTOR_KINDS.get(expected_adapter, frozenset())
            if kind in ALLOWED_SELECTOR_KINDS and kind not in allowed:
                findings.append(_finding("region-selector-adapter", field, f"{expected_adapter} does not bind selector kind {kind}"))
    return sorted(findings, key=lambda item: (item["code"], item["field"], item["detail"]))


def _for_artifact(records, artifact: str) -> list:
    return [record for record in records if str(record.get("artifact") or "") == artifact]


def _adapter_proves(adapter: str, artifact: str, left: dict, right: dict, merge_oracle: str) -> bool:
    """Fail closed until the stamped adapter supplies its pinned resolver."""

    return False


def parallel_admission(left_id: str, left: dict, right_id: str, right: dict, artifact: str, prover=None) -> dict:
    """Prove stable non-overlap and a shared merge oracle for one artifact."""

    left_adapter, right_adapter = _adapter(left), _adapter(right)
    findings = region_findings(left_id, left, left_adapter) + region_findings(right_id, right, right_adapter)
    if left_adapter != right_adapter:
        findings.append(_finding("region-adapter-mismatch", "pack", "parallel owners use different stamped adapters"))
    left_regions, left_parse = _regions(left)
    right_regions, right_parse = _regions(right)
    findings.extend(left_parse + right_parse)
    left_at = _for_artifact(left_regions, artifact)
    right_at = _for_artifact(right_regions, artifact)
    if len(left_at) != 1 or len(right_at) != 1:
        findings.append(_finding("region-ownership-missing", "ownership_regions", f"{artifact} requires exactly one region from each parallel owner"))
    elif not findings:
        left_region, right_region = left_at[0], right_at[0]
        merge_oracle = left_region.get("merge_oracle")
        if merge_oracle != right_region.get("merge_oracle"):
            findings.append(_finding("merge-oracle-mismatch", "ownership_regions", "parallel owners cite different merge oracle identities"))
        else:
            proof = prover or _adapter_proves
            if not proof(left_adapter, artifact, left_region["selector"], right_region["selector"], merge_oracle):
                findings.append(_finding("region-proof-failed", "ownership_regions", "the stamped adapter did not prove stable non-overlap at the pinned identity"))
    unique = {(item["code"], item["field"], item["detail"]): item for item in findings}
    ordered = [unique[key] for key in sorted(unique)]
    return {"admitted": not ordered, "fallback": None if not ordered else FALLBACK, "findings": ordered}


__all__ = ("ADAPTER_SELECTOR_KINDS", "ALLOWED_SELECTOR_KINDS", "FALLBACK", "parallel_admission", "region_findings")
