"""Structural validation for persisted orchflows.dispatch.v1 attempts."""

from __future__ import annotations

if __package__:
    from .tickets_dispatch_schema import (
        ATTEMPT_KEYS, ATTEMPT_REQUIRED_KEYS, ATTEMPT_STATES, OUTCOME_RECORD_ID,
        RECORD_KEYS, RECORD_KINDS, _invalid, _record_failure, classification,
        identity_failure, record_id_namespace_ok,
    )
    from .tickets_shapes import DISPATCH_STATE_REQUIRED
    from .tickets_format import _parse_iso, canonical_json, parse_canonical_json
else:
    from tickets_dispatch_schema import (
        ATTEMPT_KEYS, ATTEMPT_REQUIRED_KEYS, ATTEMPT_STATES, OUTCOME_RECORD_ID,
        RECORD_KEYS, RECORD_KINDS, _invalid, _record_failure, classification,
        identity_failure, record_id_namespace_ok,
    )
    from tickets_shapes import DISPATCH_STATE_REQUIRED
    from tickets_format import _parse_iso, canonical_json, parse_canonical_json


def validate_state(state: dict, *, run=None, ticket_id=None):
    if set(state) != set(DISPATCH_STATE_REQUIRED):
        return classification("dispatch-record-invalid", "dispatch_v1 has unknown or missing top-level fields")
    attempts = state.get("attempts")
    if not isinstance(attempts, list) or not attempts:
        return classification("dispatch-record-invalid", "dispatch_v1 attempts must be a non-empty list")
    dispatch_ids = set()
    live = 0
    for ordinal, attempt in enumerate(attempts):
        if not isinstance(attempt, dict) or not set(attempt).issubset(ATTEMPT_KEYS):
            return classification("dispatch-record-invalid", f"attempt {ordinal} has an invalid shape")
        required = ATTEMPT_REQUIRED_KEYS
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
            "retired": {"retired_at", "retirement"},
            "replaced": {"replaced_at", "replaced_by", "replacement"},
        }
        # `workspace_path` rides with the attempt in every state, so it is
        # excluded from the transition-field comparison exactly as `replaces`
        # is: it says which tree the item was executed in, not where in the
        # lifecycle the attempt stands.
        present = set(attempt) - required - {"replaces", "workspace_path"}
        if present != transition_fields[state_name]:
            return classification("dispatch-record-invalid", f"attempt {ordinal} transition fields do not match state '{state_name}'")
        for time_field in ("retired_at", "replaced_at"):
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
        causal_kinds = []
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
            if kind in {"packet", "result", "outcome", "join"}:
                causal_kinds.append(kind)
            if record_id_namespace_ok(kind, record_id) is False:
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
        causal_rank = {"packet": 0, "result": 1, "outcome": 2, "join": 3}
        if causal_kinds != sorted(causal_kinds, key=causal_rank.__getitem__):
            return classification(
                "dispatch-record-invalid",
                f"attempt {ordinal} execution records are not in causal order",
            )
        execution_present = any(
            kind in {"result", "outcome", "join"} for kind in causal_kinds
        )
        # The child's first filed record is its acceptance, so nothing here
        # asks for a separate one -- but a child that filed anything was
        # launched, and a launch is what the committed packet is.
        if execution_present and causal_kinds[:1] != ["packet"]:
            return classification(
                "dispatch-record-invalid",
                "one committed packet must precede execution records",
            )
        if "join" in causal_kinds and "outcome" not in causal_kinds:
            return classification(
                "dispatch-record-invalid",
                "dispatch join must follow the reserved outcome",
            )
    if live > 1:
        return classification("dispatch-record-invalid", "dispatch_v1 has more than one live attempt")
    attempts_by_id = {attempt["dispatch_id"]: attempt for attempt in attempts}
    for ordinal, attempt in enumerate(attempts):
        transition_records = [
            record for record in attempt["records"]
            if record["kind"] in {"join", "lifecycle"}
        ]
        if attempt["state"] == "retired":
            matching = [
                record for record in transition_records
                if record["success"] == attempt.get("retirement")
                and (
                    record["kind"] == "join"
                    or parse_canonical_json(record["content"]).get("operation") == "retire"
                )
            ]
            if len(matching) != 1:
                return _invalid(f"attempt {ordinal} retirement has no exact lifecycle record")
        if attempt["state"] == "replaced":
            matching = [
                record for record in transition_records
                if record["kind"] == "lifecycle"
                and record["success"] == attempt.get("replacement")
                and parse_canonical_json(record["content"]).get("operation") == "replace"
            ]
            if len(matching) != 1:
                return _invalid(f"attempt {ordinal} replacement has no exact lifecycle record")
        predecessor_id = attempt.get("replaces")
        if predecessor_id is None:
            continue
        predecessor = attempts_by_id.get(predecessor_id)
        if predecessor is None or attempts.index(predecessor) >= ordinal:
            return _invalid(f"attempt {ordinal} has an orphan or forward replacement edge")
        if predecessor.get("state") != "replaced" or predecessor.get("replaced_by") != attempt["dispatch_id"]:
            return _invalid(f"attempt {ordinal} replacement edge is not bidirectional")
        replacement = predecessor.get("replacement", {}).get("dispatch", {})
        predecessor_record = next((
            record for record in predecessor["records"]
            if record["kind"] == "lifecycle"
            and record["success"] == predecessor.get("replacement")
        ), None)
        replacement_content = (
            parse_canonical_json(predecessor_record["content"])
            if predecessor_record is not None else {}
        )
        if (
            replacement.get("dispatch_id") != attempt["dispatch_id"]
            or replacement.get("replaces") != predecessor_id
            or replacement.get("opened_at") != attempt["opened_at"]
            or replacement.get("lease_expires_at") != attempt["lease_expires_at"]
            or replacement.get("assignment_seal") != attempt["assignment_seal"]
            or replacement_content.get("owner") != attempt["owner"]
            or replacement_content.get("dispatch_id") != attempt["dispatch_id"]
            or replacement_content.get("lease_expires_at") != attempt["lease_expires_at"]
        ):
            return _invalid(f"attempt {ordinal} differs from its predecessor replacement record")
    for ordinal, attempt in enumerate(attempts):
        if attempt.get("state") == "replaced" and attempt.get("replaced_by") not in attempts_by_id:
            return _invalid(f"attempt {ordinal} replacement successor does not exist")
    return None
