"""Closed persisted and wire identities for orchflows.dispatch.v1."""

from __future__ import annotations

from pathlib import Path
import re

if __package__:
    from .tickets_format import (
        EXECUTOR_SECTIONS, TERMINAL_STATES, _parse_iso, canonical_json,
        parse_canonical_json,
    )
else:
    from tickets_format import (
        EXECUTOR_SECTIONS, TERMINAL_STATES, _parse_iso, canonical_json,
        parse_canonical_json,
    )

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
OUTCOME_SECTIONS = frozenset({"Result", "Verification", "Feedback", "Risks", "Handoff"})
JOIN_STATUSES = frozenset(TERMINAL_STATES) | {"suspended"}


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


def _invalid(detail: str):
    return classification("dispatch-record-invalid", detail)


def _closed(value, keys) -> bool:
    return isinstance(value, dict) and set(value) == set(keys)


def _committed_success_failure(
    success, content, *, run, ticket_id, dispatch_id, record_id,
):
    if not _closed(success, {"committed_record"}):
        return _invalid(f"record '{record_id}' has a non-canonical stored success")
    committed = success["committed_record"]
    expected = {
        "protocol": PROTOCOL, "run": run, "id": ticket_id,
        "dispatch_id": dispatch_id, "record_id": record_id,
        "content": content,
    }
    if committed != expected:
        return _invalid(f"record '{record_id}' stored success differs from its content or origin")
    return None


def _outcome_failure(content, *, run, ticket_id, attempt):
    required = {
        "assignment_seal", "by", "dispatch_id", "evidence", "id",
        "outcome_record_id", "protocol", "run", "status",
    }
    if not _closed(content, required):
        return "outcome envelope has unknown or missing fields"
    expected = {
        "protocol": PROTOCOL, "run": run, "id": ticket_id,
        "dispatch_id": attempt["dispatch_id"],
        "assignment_seal": attempt["assignment_seal"],
        "by": attempt["owner"], "outcome_record_id": OUTCOME_RECORD_ID,
    }
    if any(content.get(key) != value for key, value in expected.items()):
        return "outcome envelope differs from its attempt or ticket origin"
    if content.get("status") not in JOIN_STATUSES:
        return "outcome status is not a join disposition"
    evidence = content.get("evidence")
    if not _closed(evidence, OUTCOME_SECTIONS):
        return "outcome evidence does not close the five executor sections"
    if any(not isinstance(evidence.get(section), str) for section in OUTCOME_SECTIONS):
        return "outcome evidence bodies are not strings"
    if any(not evidence[section].strip() for section in OUTCOME_SECTIONS - {"Handoff"}):
        return "outcome evidence is incomplete"
    if (content["status"] == "suspended") != bool(evidence["Handoff"].strip()):
        return "outcome Handoff does not match its disposition"
    return None


def _result_failure(record, content, *, run, ticket_id, attempt):
    record_id = record["record_id"]
    required = {"assignment_seal", "body", "mode", "operation", "section", "writer"}
    if not _closed(content, required):
        return _invalid(f"result record '{record_id}' content has an invalid shape")
    if (
        content.get("operation") != "result"
        or content.get("assignment_seal") != attempt["assignment_seal"]
        or content.get("writer") != attempt["owner"]
        or content.get("section") not in EXECUTOR_SECTIONS
        or content.get("mode") not in {"write", "append", "replace"}
        or not isinstance(content.get("body"), str)
    ):
        return _invalid(f"result record '{record_id}' content differs from its attempt")
    success = record["success"]
    if not _closed(success, {"result"}):
        return _invalid(f"result record '{record_id}' has a non-canonical stored success")
    result = success["result"]
    keys = {
        "protocol", "run", "id", "path", "section", "mode", "by",
        "assignment_seal", "dispatch_id", "record_id",
    }
    if not _closed(result, keys):
        return _invalid(f"result record '{record_id}' stored success has an invalid shape")
    expected = {
        "protocol": PROTOCOL, "run": run, "id": ticket_id,
        "section": content["section"], "by": content["writer"],
        "assignment_seal": content["assignment_seal"],
        "dispatch_id": attempt["dispatch_id"], "record_id": record_id,
    }
    if any(result.get(key) != value for key, value in expected.items()):
        return _invalid(f"result record '{record_id}' stored success differs from its content")
    if result.get("mode") not in ({content["mode"], "write"} if content["mode"] != "write" else {"write"}):
        return _invalid(f"result record '{record_id}' stored mode differs from its request")
    result_path = result.get("path")
    if not isinstance(result_path, str):
        return _invalid(f"result record '{record_id}' has no canonical ticket path")
    path = Path(result_path)
    if not path.is_absolute() or path.name != f"{ticket_id}.md" or path.parent.name != run:
        return _invalid(f"result record '{record_id}' ticket path differs from its origin")
    return None


def _record_failure(record, content, *, run, ticket_id, attempt):
    record_id = record["record_id"]
    kind = record["kind"]
    if kind == "generic":
        return _committed_success_failure(
            record["success"], content, run=run, ticket_id=ticket_id,
            dispatch_id=attempt["dispatch_id"], record_id=record_id,
        )
    if kind == "packet":
        if not _closed(content, {"packet"}) or not isinstance(content["packet"], dict):
            return _invalid("committed packet content has an invalid shape")
        packet = content["packet"]
        if (
            packet.get("protocol") != PROTOCOL
            or packet.get("dispatch_id") != attempt["dispatch_id"]
            or packet.get("assignment_seal") != attempt["assignment_seal"]
            or packet.get("assigned_name") != attempt["owner"]
            or packet.get("durability") != "ticket"
            or packet.get("source") != {"run": run, "id": ticket_id}
        ):
            return _invalid("committed packet differs from its ticket attempt")
        return _committed_success_failure(
            record["success"], content, run=run, ticket_id=ticket_id,
            dispatch_id=attempt["dispatch_id"], record_id=record_id,
        )
    if kind == "result":
        return _result_failure(record, content, run=run, ticket_id=ticket_id, attempt=attempt)
    if kind == "outcome":
        failure = _outcome_failure(content, run=run, ticket_id=ticket_id, attempt=attempt)
        if failure is not None:
            return _invalid(f"outcome record is invalid: {failure}")
        if record["success"] != {"outcome": content}:
            return _invalid("outcome stored success differs from its envelope")
        return None
    if kind == "lifecycle":
        operation = content.get("operation") if isinstance(content, dict) else None
        if operation == "retire":
            expected = {
                "assignment_seal": attempt["assignment_seal"],
                "dispatch_id": attempt["dispatch_id"], "operation": "retire",
            }
            if content != expected:
                return _invalid(f"lifecycle record '{record_id}' has invalid retirement content")
            success = record["success"]
            dispatch = success.get("dispatch") if _closed(success, {"dispatch"}) else None
            if not _closed(dispatch, {
                "protocol", "outcome", "run", "id", "dispatch_id",
                "record_id", "retired_at", "state",
            }):
                return _invalid(f"lifecycle record '{record_id}' has invalid retirement success")
            expected_fields = {
                "protocol": PROTOCOL, "outcome": "retired", "run": run,
                "id": ticket_id, "dispatch_id": attempt["dispatch_id"],
                "record_id": record_id, "state": "retired",
                "retired_at": attempt.get("retired_at"),
            }
            if dispatch != expected_fields or attempt.get("retirement") != success:
                return _invalid(f"lifecycle record '{record_id}' differs from the retired attempt")
            return None
        if operation == "replace":
            expected_keys = {
                "assignment_seal", "dispatch_id", "lease_expires_at",
                "operation", "owner", "replaces",
            }
            if not _closed(content, expected_keys) or (
                content.get("assignment_seal") != attempt["assignment_seal"]
                or content.get("replaces") != attempt["dispatch_id"]
            ):
                return _invalid(f"lifecycle record '{record_id}' has invalid replacement content")
            success = record["success"]
            dispatch = success.get("dispatch") if _closed(success, {"dispatch"}) else None
            if not _closed(dispatch, {
                "protocol", "outcome", "run", "id", "dispatch_id",
                "record_id", "replaces", "assignment_seal", "lease_expires_at",
                "opened_at", "state",
            }):
                return _invalid(f"lifecycle record '{record_id}' has invalid replacement success")
            expected_fields = {
                "protocol": PROTOCOL, "outcome": "replaced", "run": run,
                "id": ticket_id, "dispatch_id": content["dispatch_id"],
                "record_id": record_id, "replaces": attempt["dispatch_id"],
                "assignment_seal": content["assignment_seal"],
                "lease_expires_at": content["lease_expires_at"],
                "opened_at": attempt.get("replaced_at"), "state": "live",
            }
            if dispatch != expected_fields or attempt.get("replacement") != success:
                return _invalid(f"lifecycle record '{record_id}' differs from the replaced attempt")
            return None
        return _invalid(f"lifecycle record '{record_id}' has an unknown operation")
    if kind == "join":
        expected = {
            "assignment_seal": attempt["assignment_seal"],
            "dispatch_id": attempt["dispatch_id"],
            "joined_by": content.get("joined_by") if isinstance(content, dict) else None,
            "operation": "join", "outcome_record_id": OUTCOME_RECORD_ID,
        }
        if content != expected or identity_failure("join-owner", content.get("joined_by")) is not None:
            return _invalid(f"join record '{record_id}' has invalid content")
        outcome = next((
            item for item in attempt["records"]
            if item.get("record_id") == OUTCOME_RECORD_ID and item.get("kind") == "outcome"
        ), None)
        success = record["success"]
        joined = success.get("join") if _closed(success, {"join"}) else None
        if outcome is None or not _closed(joined, {
            "protocol", "run", "id", "assignment_seal", "dispatch_id",
            "outcome_record_id", "by", "status", "joined_at",
        }):
            return _invalid(f"join record '{record_id}' has invalid stored success")
        expected_join = {
            "protocol": PROTOCOL, "run": run, "id": ticket_id,
            "assignment_seal": attempt["assignment_seal"],
            "dispatch_id": attempt["dispatch_id"],
            "outcome_record_id": OUTCOME_RECORD_ID, "by": content["joined_by"],
            "status": parse_canonical_json(outcome["content"])["status"],
            "joined_at": attempt.get("retired_at"),
        }
        if joined != expected_join or attempt.get("retirement") != success:
            return _invalid(f"join record '{record_id}' differs from its outcome or retirement")
        return None
    return _invalid(f"record '{record_id}' has an unsupported kind")


def validate_state(state: dict, *, run=None, ticket_id=None):
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
                content = parse_canonical_json(record["content"])
            except (TypeError, ValueError):
                return classification("dispatch-record-invalid", f"record '{record_id}' content is not canonical JSON")
            if record["content"] != canonical_json(content):
                return classification("dispatch-record-invalid", f"record '{record_id}' content is not canonical JSON")
            if _parse_iso(record.get("committed_at")) is None:
                return classification("dispatch-record-invalid", f"record '{record_id}' has no absolute commit time")
            if run is not None and ticket_id is not None:
                failure = _record_failure(
                    record, content, run=run, ticket_id=ticket_id, attempt=attempt,
                )
                if failure is not None:
                    return failure
    if live > 1:
        return classification("dispatch-record-invalid", "dispatch_v1 has more than one live attempt")
    attempts_by_id = {attempt["dispatch_id"]: attempt for attempt in attempts}
    for ordinal, attempt in enumerate(attempts):
        predecessor_id = attempt.get("replaces")
        if predecessor_id is None:
            continue
        predecessor = attempts_by_id.get(predecessor_id)
        if predecessor is None or attempts.index(predecessor) >= ordinal:
            return _invalid(f"attempt {ordinal} has an orphan or forward replacement edge")
        if predecessor.get("state") != "replaced" or predecessor.get("replaced_by") != attempt["dispatch_id"]:
            return _invalid(f"attempt {ordinal} replacement edge is not bidirectional")
        replacement = predecessor.get("replacement", {}).get("dispatch", {})
        if (
            replacement.get("dispatch_id") != attempt["dispatch_id"]
            or replacement.get("replaces") != predecessor_id
            or replacement.get("opened_at") != attempt["opened_at"]
            or replacement.get("lease_expires_at") != attempt["lease_expires_at"]
            or replacement.get("assignment_seal") != attempt["assignment_seal"]
        ):
            return _invalid(f"attempt {ordinal} differs from its predecessor replacement record")
    for ordinal, attempt in enumerate(attempts):
        if attempt.get("state") == "replaced" and attempt.get("replaced_by") not in attempts_by_id:
            return _invalid(f"attempt {ordinal} replacement successor does not exist")
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
    if encoded != canonical_json(parsed):
        return None, classification("dispatch-record-invalid", "dispatch_v1 is not canonical JSON")
    run = str(data.get("run") or "").strip()
    ticket_id = str(data.get("id") or "").strip()
    failure = validate_state(parsed, run=run, ticket_id=ticket_id)
    return (None, failure) if failure is not None else (parsed, None)
