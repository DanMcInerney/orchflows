"""Closed persisted and wire identities for orchflows.dispatch.v1."""

from __future__ import annotations

import re

if __package__:
    from .tickets_format import _parse_iso, parse_canonical_json
else:
    from tickets_format import _parse_iso, parse_canonical_json

PROTOCOL = "orchflows.dispatch.v1"
OUTCOME_RECORD_ID = "outcome"
PACKET_RECORD_ID = "dispatch-packet"
RESERVED_RECORD_IDS = frozenset({OUTCOME_RECORD_ID, PACKET_RECORD_ID})
RESERVED_RECORD_PREFIXES = ("join:", "lifecycle:")
IDENTITY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
ATTEMPT_STATES = frozenset({"live", "expired", "retired", "replaced"})
ATTEMPT_KEYS = frozenset({
    "assignment_seal", "dispatch_id", "lease_expires_at", "opened_at",
    "outcome_record_id", "owner", "records", "state", "expired_at",
    "retired_at", "retirement", "replaced_at", "replaced_by",
    "replacement", "replaces",
})
RECORD_KEYS = frozenset({"committed_at", "content", "kind", "record_id", "success"})
RECORD_KINDS = frozenset({"generic", "join", "lifecycle", "outcome", "packet", "result"})


def classification(code: str, detail: str) -> dict:
    return {"error": detail, "code": code, "protocol": PROTOCOL}


def identity_failure(kind: str, value, *, allow_path: bool = False):
    if not isinstance(value, str) or not value:
        return classification(f"{kind}-invalid", f"{kind} must be a non-empty string")
    if any(ord(mark) < 32 or mark == "`" for mark in value):
        return classification(f"{kind}-invalid", f"{kind} contains a control character or backtick")
    if not allow_path and IDENTITY_RE.fullmatch(value) is None:
        return classification(f"{kind}-invalid", f"{kind} is not a canonical protocol identity")
    return None


def record_id_is_reserved(record_id: str) -> bool:
    return record_id in RESERVED_RECORD_IDS or record_id.startswith(RESERVED_RECORD_PREFIXES)


def validate_state(state: dict):
    if set(state) != {"attempts", "protocol"}:
        return classification("dispatch-record-invalid", "dispatch_v1 has unknown or missing top-level fields")
    attempts = state.get("attempts")
    if not isinstance(attempts, list) or not attempts:
        return classification("dispatch-record-invalid", "dispatch_v1 attempts must be a non-empty list")
    dispatch_ids = set()
    live = 0
    for ordinal, attempt in enumerate(attempts):
        if not isinstance(attempt, dict) or not set(attempt).issubset(ATTEMPT_KEYS):
            return classification("dispatch-record-invalid", f"attempt {ordinal} has an invalid shape")
        required = {
            "assignment_seal", "dispatch_id", "lease_expires_at", "opened_at",
            "outcome_record_id", "owner", "records", "state",
        }
        if not required.issubset(attempt):
            return classification("dispatch-record-invalid", f"attempt {ordinal} is incomplete")
        for kind, value in (
            ("assignment-seal", attempt.get("assignment_seal")),
            ("dispatch-id", attempt.get("dispatch_id")),
            ("owner", attempt.get("owner")),
            ("outcome-record-id", attempt.get("outcome_record_id")),
        ):
            failure = identity_failure(kind, value)
            if failure is not None:
                return classification("dispatch-record-invalid", failure["error"])
        if attempt["outcome_record_id"] != OUTCOME_RECORD_ID:
            return classification("dispatch-record-invalid", f"attempt {ordinal} has a non-canonical outcome record id")
        dispatch_id = attempt["dispatch_id"]
        if dispatch_id in dispatch_ids:
            return classification("dispatch-record-invalid", f"duplicate dispatch_id '{dispatch_id}'")
        dispatch_ids.add(dispatch_id)
        if attempt.get("state") not in ATTEMPT_STATES:
            return classification("dispatch-record-invalid", f"attempt {ordinal} has an unknown state")
        state_name = attempt["state"]
        transition_fields = {
            "live": set(),
            "expired": {"expired_at"},
            "retired": {"retired_at", "retirement"},
            "replaced": {"replaced_at", "replaced_by", "replacement"},
        }
        present = set(attempt) - required - {"replaces"}
        if present != transition_fields[state_name]:
            return classification("dispatch-record-invalid", f"attempt {ordinal} transition fields do not match state '{state_name}'")
        for time_field in ("expired_at", "retired_at", "replaced_at"):
            if time_field in attempt and _parse_iso(attempt[time_field]) is None:
                return classification("dispatch-record-invalid", f"attempt {ordinal} has an invalid {time_field}")
        if "replaced_by" in attempt and identity_failure("dispatch-id", attempt["replaced_by"]) is not None:
            return classification("dispatch-record-invalid", f"attempt {ordinal} has an invalid replacement identity")
        if "replaces" in attempt and identity_failure("dispatch-id", attempt["replaces"]) is not None:
            return classification("dispatch-record-invalid", f"attempt {ordinal} has an invalid predecessor identity")
        live += attempt.get("state") == "live"
        opened = _parse_iso(attempt.get("opened_at"))
        expires = _parse_iso(attempt.get("lease_expires_at"))
        if opened is None or expires is None or expires <= opened:
            return classification("dispatch-record-invalid", f"attempt {ordinal} has an invalid absolute lease window")
        records = attempt.get("records")
        if not isinstance(records, list):
            return classification("dispatch-record-invalid", f"attempt {ordinal} records is not a list")
        record_ids = set()
        for record_ordinal, record in enumerate(records):
            if not isinstance(record, dict) or set(record) != RECORD_KEYS:
                return classification("dispatch-record-invalid", f"attempt {ordinal} record {record_ordinal} has an invalid shape")
            record_id = record.get("record_id")
            failure = identity_failure("record-id", record_id)
            if failure is not None or record_id in record_ids:
                detail = failure["error"] if failure is not None else f"duplicate record_id '{record_id}'"
                return classification("dispatch-record-invalid", detail)
            record_ids.add(record_id)
            if record.get("kind") not in RECORD_KINDS:
                return classification("dispatch-record-invalid", f"record '{record_id}' has an unknown kind")
            kind = record["kind"]
            namespace_ok = {
                "packet": record_id == PACKET_RECORD_ID,
                "outcome": record_id == OUTCOME_RECORD_ID,
                "join": record_id.startswith("join:"),
                "lifecycle": record_id.startswith("lifecycle:"),
                "generic": not record_id_is_reserved(record_id),
                "result": not record_id_is_reserved(record_id),
            }
            if not namespace_ok[kind]:
                return classification("dispatch-record-invalid", f"record '{record_id}' does not belong to kind '{kind}'")
            if not isinstance(record.get("content"), str) or not isinstance(record.get("success"), dict):
                return classification("dispatch-record-invalid", f"record '{record_id}' has invalid content or success")
            try:
                parse_canonical_json(record["content"])
            except (TypeError, ValueError):
                return classification("dispatch-record-invalid", f"record '{record_id}' content is not canonical JSON")
            if _parse_iso(record.get("committed_at")) is None:
                return classification("dispatch-record-invalid", f"record '{record_id}' has no absolute commit time")
    if live > 1:
        return classification("dispatch-record-invalid", "dispatch_v1 has more than one live attempt")
    return None


def state(data: dict):
    encoded = str(data.get("dispatch_v1") or "").strip()
    if not encoded:
        return None, None
    try:
        parsed = parse_canonical_json(encoded)
    except (TypeError, ValueError) as error:
        return None, classification("dispatch-record-invalid", f"dispatch_v1 is not canonical JSON: {error}")
    if not isinstance(parsed, dict) or parsed.get("protocol") != PROTOCOL:
        return None, classification("dispatch-record-invalid", f"dispatch_v1 does not name {PROTOCOL}")
    failure = validate_state(parsed)
    return (None, failure) if failure is not None else (parsed, None)
