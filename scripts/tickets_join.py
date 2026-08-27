"""Dispatch-v1 join-owned lifecycle transitions."""

from __future__ import annotations

from datetime import datetime, timezone

if __package__:
    from .tickets_attempts import PROTOCOL, _classification, _commit_record
    from .tickets_format import (
        TERMINAL_STATES, _extract_flag, _set_frontmatter_field,
    )
    from .tickets_store import UTC_STAMP, _segment_error
    from .tickets_store import _terminal_identity_update, _write_identity
    from .tickets_project import TERMINAL_REMEDY, binding_refusal
else:
    from tickets_attempts import PROTOCOL, _classification, _commit_record
    from tickets_format import TERMINAL_STATES, _extract_flag, _set_frontmatter_field
    from tickets_store import UTC_STAMP, _segment_error
    from tickets_store import _terminal_identity_update, _write_identity
    from tickets_project import TERMINAL_REMEDY, binding_refusal

JOIN_STATUSES = frozenset(TERMINAL_STATES) | {"suspended"}
DISPATCH_JOIN_USAGE = (
    "dispatch-join <run> <id> --assignment-seal <seal> --dispatch-id <id> "
    "--result-record-id <id> --by <join-name> --status <status>"
)


def _cmd_dispatch_join(rest):
    args = list(rest)
    assignment_seal = _extract_flag(args, "--assignment-seal")
    dispatch_id = _extract_flag(args, "--dispatch-id")
    result_record_id = _extract_flag(args, "--result-record-id")
    joined_by = _extract_flag(args, "--by")
    status = _extract_flag(args, "--status")
    if len(args) != 2 or not all((
        assignment_seal, dispatch_id, result_record_id, joined_by, status,
    )):
        return {"error": f"usage: {DISPATCH_JOIN_USAGE}"}
    run, ticket_id = args
    for kind, value in (("run id", run), ("ticket id", ticket_id)):
        invalid = _segment_error(kind, value)
        if invalid is not None:
            return invalid
    if status not in JOIN_STATUSES:
        return _classification(
            "join-status-invalid",
            f"dispatch-join status must be one of {sorted(JOIN_STATUSES)}",
        )
    if status in TERMINAL_STATES:
        held = binding_refusal(run, TERMINAL_REMEDY)
        if held is not None:
            return {"error": held}
    if any(
        mark in value
        for value in (assignment_seal, dispatch_id, result_record_id, joined_by)
        for mark in ("`", "\r", "\n")
    ):
        return _classification(
            "join-identity-invalid", "join identity contains backticks or line breaks"
        )

    join_record_id = f"join:{result_record_id}"
    content = {
        "assignment_seal": assignment_seal,
        "dispatch_id": dispatch_id,
        "joined_by": joined_by,
        "operation": "join",
        "result_record_id": result_record_id,
        "status": status,
    }

    def join(text, _data, attempt, _state):
        result_record = next(
            (
                item for item in attempt.get("records", [])
                if item.get("record_id") == result_record_id
            ),
            None,
        )
        result_success = (
            result_record.get("success") if isinstance(result_record, dict) else None
        )
        if not isinstance(result_success, dict) or not isinstance(
            result_success.get("result"), dict
        ):
            return text, None, _classification(
                "result-record-mismatch",
                f"record_id '{result_record_id}' is not a committed executor result",
            )
        result_identity = result_success["result"]
        if result_identity.get("dispatch_id") != dispatch_id:
            return text, None, _classification(
                "result-record-mismatch", "committed result belongs to another dispatch"
            )
        if status == "suspended" and result_identity.get("section") != "Handoff":
            return text, None, _classification(
                "handoff-required",
                "suspension requires a committed Handoff result record",
            )
        joined_at = datetime.now(timezone.utc).strftime(UTC_STAMP)
        response = {"join": {
            "protocol": PROTOCOL,
            "run": run,
            "id": ticket_id,
            "assignment_seal": assignment_seal,
            "dispatch_id": dispatch_id,
            "result_record_id": result_record_id,
            "by": joined_by,
            "status": status,
            "joined_at": joined_at,
        }}
        attempt["state"] = "retired"
        attempt["retired_at"] = joined_at
        attempt["retirement"] = response
        updated = _set_frontmatter_field(text, "status", status)
        return updated, response, None

    result = _commit_record(
        run, ticket_id, dispatch_id, join_record_id, content,
        mutate=join, expected_seal=assignment_seal,
    )
    if "error" in result or status not in TERMINAL_STATES:
        return result
    identity_dir, identity, refusal = _terminal_identity_update(
        run, ticket_id, status, datetime.now(timezone.utc)
    )
    if refusal is not None:
        return refusal
    if identity is not None:
        try:
            identity_dir.mkdir(parents=True, exist_ok=True)
            _write_identity(identity_dir, identity)
        except OSError as error:
            return {"error": f"join committed and terminal timing remains pending: {error}"}
    return result
