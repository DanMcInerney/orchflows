"""Closed persisted and wire identities for orchflows.dispatch.v1."""

from __future__ import annotations

from pathlib import Path

if __package__:
    from .tickets_shapes import (
        DISPATCH_ATTEMPT_FIELDS, DISPATCH_ATTEMPT_REQUIRED,
        DISPATCH_JOIN_CONTENT_FIELDS,
        DISPATCH_JOIN_SUCCESS_FIELDS, DISPATCH_JOIN_SUCCESS_REQUIRED,
        DISPATCH_LAUNCH_FIELDS, DISPATCH_LAUNCH_RECORD_FIELDS,
        DISPATCH_REPLACEMENT_DISPATCH_FIELDS, DISPATCH_RETIREMENT_DISPATCH_FIELDS,
        DISPATCH_RESULT_PROJECTION_FIELDS, DISPATCH_RESULT_RECORD_FIELDS,
        DISPATCH_RESULT_SUCCESS_FIELDS,
        DISPATCH_REPLACE_REQUEST_FIELDS, DISPATCH_RETIRE_REQUEST_FIELDS,
        DISPATCH_STORED_SUCCESS_FIELDS, DISPATCH_TRANSITION_SUCCESS_FIELDS,
        DISPATCH_STATE_VALUES, DISPATCH_ATTEMPT_VALUES,
        DISPATCH_JOIN_SUCCESS_VALUES,
        DISPATCH_OUTCOME_FIELDS,
        DISPATCH_RECORD_FIELDS, DISPATCH_RECORD_VALUES,
        EXECUTOR_RESULT_VALUES,
    )
    from .tickets_dispatch_identity import (
        IDENTITY_RE, LAUNCH_RECORD_ID, OUTCOME_RECORD_ID, PROTOCOL,
        RESERVED_RECORD_IDS, RESERVED_RECORD_PREFIXES,
        classification, identity_failure, record_id_is_reserved,
        record_id_namespace_ok,
    )
    from .tickets_format import (
        TERMINAL_STATES, _parse_iso, canonical_json,
        is_review_stage_id, parse_canonical_json,
    )
else:
    from tickets_shapes import (
        DISPATCH_ATTEMPT_FIELDS, DISPATCH_ATTEMPT_REQUIRED,
        DISPATCH_JOIN_CONTENT_FIELDS,
        DISPATCH_JOIN_SUCCESS_FIELDS, DISPATCH_JOIN_SUCCESS_REQUIRED,
        DISPATCH_LAUNCH_FIELDS, DISPATCH_LAUNCH_RECORD_FIELDS,
        DISPATCH_REPLACEMENT_DISPATCH_FIELDS, DISPATCH_RETIREMENT_DISPATCH_FIELDS,
        DISPATCH_RESULT_PROJECTION_FIELDS, DISPATCH_RESULT_RECORD_FIELDS,
        DISPATCH_RESULT_SUCCESS_FIELDS,
        DISPATCH_REPLACE_REQUEST_FIELDS, DISPATCH_RETIRE_REQUEST_FIELDS,
        DISPATCH_STORED_SUCCESS_FIELDS, DISPATCH_TRANSITION_SUCCESS_FIELDS,
        DISPATCH_STATE_VALUES, DISPATCH_ATTEMPT_VALUES,
        DISPATCH_JOIN_SUCCESS_VALUES,
        DISPATCH_OUTCOME_FIELDS,
        DISPATCH_RECORD_FIELDS, DISPATCH_RECORD_VALUES,
        EXECUTOR_RESULT_VALUES,
    )
    from tickets_dispatch_identity import (
        IDENTITY_RE, LAUNCH_RECORD_ID, OUTCOME_RECORD_ID, PROTOCOL,
        RESERVED_RECORD_IDS, RESERVED_RECORD_PREFIXES,
        classification, identity_failure, record_id_is_reserved,
        record_id_namespace_ok,
    )
    from tickets_format import (
        TERMINAL_STATES, _parse_iso, canonical_json,
        is_review_stage_id, parse_canonical_json,
    )

ATTEMPT_STATES = frozenset(DISPATCH_ATTEMPT_VALUES["state"])
ATTEMPT_KEYS = frozenset(DISPATCH_ATTEMPT_FIELDS)
ATTEMPT_REQUIRED_KEYS = frozenset(DISPATCH_ATTEMPT_REQUIRED)
RECORD_KEYS = frozenset(DISPATCH_RECORD_FIELDS)
RECORD_KINDS = frozenset(DISPATCH_RECORD_VALUES["kind"])
RESULT_OPERATION = EXECUTOR_RESULT_VALUES["operation"][0]
JOIN_STATUSES = frozenset(DISPATCH_JOIN_SUCCESS_VALUES["status"])


def _invalid(detail: str):
    return classification("dispatch-record-invalid", detail)


def _closed(value, keys) -> bool:
    return isinstance(value, dict) and set(value) == set(keys)


def _committed_success_failure(
    success, *, run, ticket_id, dispatch_id, record_id,
):
    if not _closed(success, set(DISPATCH_STORED_SUCCESS_FIELDS)):
        return _invalid(f"record '{record_id}' has a non-canonical stored success")
    committed = success["committed_record"]
    expected = {
        "protocol": PROTOCOL, "run": run, "id": ticket_id,
        "dispatch_id": dispatch_id, "record_id": record_id,
    }
    if committed != expected:
        return _invalid(f"record '{record_id}' stored success differs from its origin")
    return None


def _outcome_failure(content, *, run, ticket_id, attempt):
    required = set(DISPATCH_OUTCOME_FIELDS)
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
    evidence = content.get("evidence")
    if not isinstance(evidence, str) or not evidence.strip():
        return "outcome evidence is not a non-empty closing note"
    return None


def _result_failure(record, content, *, run, ticket_id, attempt):
    record_id = record["record_id"]
    required = set(DISPATCH_RESULT_RECORD_FIELDS)
    if not _closed(content, required):
        return _invalid(f"result record '{record_id}' content has an invalid shape")
    if (
        content.get("operation") != RESULT_OPERATION
        or content.get("assignment_seal") != attempt["assignment_seal"]
        or content.get("writer") != attempt["owner"]
        or not isinstance(content.get("body"), str)
    ):
        return _invalid(f"result record '{record_id}' content differs from its attempt")
    success = record["success"]
    if not _closed(success, set(DISPATCH_RESULT_SUCCESS_FIELDS)):
        return _invalid(f"result record '{record_id}' has a non-canonical stored success")
    result = success["result"]
    keys = set(DISPATCH_RESULT_PROJECTION_FIELDS)
    if not _closed(result, keys):
        return _invalid(f"result record '{record_id}' stored success has an invalid shape")
    expected = {
        "protocol": PROTOCOL, "run": run, "id": ticket_id,
        "by": content["writer"],
        "assignment_seal": content["assignment_seal"],
        "dispatch_id": attempt["dispatch_id"], "record_id": record_id,
    }
    if any(result.get(key) != value for key, value in expected.items()):
        return _invalid(f"result record '{record_id}' stored success differs from its content")
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
            record["success"], run=run, ticket_id=ticket_id,
            dispatch_id=attempt["dispatch_id"], record_id=record_id,
        )
    if kind == "launch":
        if not _closed(content, set(DISPATCH_LAUNCH_RECORD_FIELDS)) or not isinstance(content["launch"], dict):
            return _invalid("committed launch content has an invalid shape")
        # The launch object closes `contracts/dispatch.md`'s declared shape and
        # carries no identity of its own: it is the invocation, and what binds
        # it to this attempt is the stored success below, the same anchor every
        # other record is held to. A launch that restated the seal and the
        # dispatch id would be a second home for both.
        if not _closed(content["launch"], set(DISPATCH_LAUNCH_FIELDS)):
            return _invalid("committed launch has unknown or missing fields")
        return _committed_success_failure(
            record["success"], run=run, ticket_id=ticket_id,
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
            if not _closed(content, set(DISPATCH_RETIRE_REQUEST_FIELDS)) or content != expected:
                return _invalid(f"lifecycle record '{record_id}' has invalid retirement content")
            success = record["success"]
            dispatch = success.get("dispatch") if _closed(success, set(DISPATCH_TRANSITION_SUCCESS_FIELDS)) else None
            if not _closed(dispatch, set(DISPATCH_RETIREMENT_DISPATCH_FIELDS)):
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
            if not _closed(content, set(DISPATCH_REPLACE_REQUEST_FIELDS)) or (
                content.get("assignment_seal") != attempt["assignment_seal"]
                or content.get("replaces") != attempt["dispatch_id"]
            ):
                return _invalid(f"lifecycle record '{record_id}' has invalid replacement content")
            success = record["success"]
            dispatch = success.get("dispatch") if _closed(success, set(DISPATCH_TRANSITION_SUCCESS_FIELDS)) else None
            if not _closed(dispatch, set(DISPATCH_REPLACEMENT_DISPATCH_FIELDS)):
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
        if not isinstance(content, dict):
            return _invalid(f"join record '{record_id}' has invalid content")
        review_stage = is_review_stage_id(ticket_id)
        expected = {
            "assignment_seal": attempt["assignment_seal"],
            "dispatch_id": attempt["dispatch_id"],
            "joined_by": content.get("joined_by"),
            "operation": "join", "outcome_record_id": OUTCOME_RECORD_ID,
        }
        if review_stage:
            review = content.get("review")
            if not _closed(review, {"accepted", "artifact"}) or any(
                value is not None and not isinstance(value, str)
                for value in review.values()
            ):
                return _invalid(f"join record '{record_id}' has invalid review content")
            expected["review"] = review
        if content != expected or identity_failure("join-owner", content.get("joined_by")) is not None:
            return _invalid(f"join record '{record_id}' has invalid content")
        outcome = next((
            item for item in attempt["records"]
            if item.get("record_id") == OUTCOME_RECORD_ID and item.get("kind") == "outcome"
        ), None)
        success = record["success"]
        joined = success.get("join") if _closed(success, {"join"}) else None
        joined_keys = set(DISPATCH_JOIN_SUCCESS_REQUIRED)
        if review_stage:
            joined_keys.add("review_identity")
        if outcome is None or not _closed(joined, joined_keys):
            return _invalid(f"join record '{record_id}' has invalid stored success")
        if review_stage and identity_failure(
            "review-identity", joined.get("review_identity"),
        ) is not None:
            return _invalid(f"join record '{record_id}' has invalid review identity")
        # The disposition is the join's own. The outcome is still required
        # to exist -- its existence is what closed the attempt -- but it no
        # longer carries a status for this to check itself against, so the
        # grade is that the joining authority recorded a lawful one.
        if joined.get("status") not in JOIN_STATUSES:
            return _invalid(f"join record '{record_id}' records an invalid disposition")
        expected_join = {
            "protocol": PROTOCOL, "run": run, "id": ticket_id,
            "assignment_seal": attempt["assignment_seal"],
            "dispatch_id": attempt["dispatch_id"],
            "outcome_record_id": OUTCOME_RECORD_ID, "by": content["joined_by"],
            "status": joined["status"],
            "joined_at": attempt.get("retired_at"),
        }
        if review_stage:
            expected_join["review_identity"] = joined["review_identity"]
        if joined != expected_join or attempt.get("retirement") != success:
            return _invalid(f"join record '{record_id}' differs from its outcome or retirement")
        return None
    return _invalid(f"record '{record_id}' has an unsupported kind")


def validate_state(state: dict, *, run=None, ticket_id=None):
    if __package__:
        from .tickets_dispatch_validate import validate_state as validate
    else:
        from tickets_dispatch_validate import validate_state as validate
    return validate(state, run=run, ticket_id=ticket_id)


def stored_state(data: dict):
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
    if failure is not None:
        return None, failure
    return parsed, None


def state(data: dict):
    parsed, failure = stored_state(data)
    if failure is not None or parsed is None:
        return parsed, failure
    ticket_id = str(data.get("id") or "").strip()
    review_text = str(data.get("review_v1") or "").strip()
    review_stage = is_review_stage_id(ticket_id)
    if review_text and review_stage:
        try:
            if __package__:
                from .tickets_review import review_records
            else:
                from tickets_review import review_records
            review = review_records(review_text, allow_legacy=True)
        except (ImportError, ValueError) as error:
            return None, classification(
                "dispatch-record-invalid", f"review_v1 is invalid: {error}",
            )
        joins = [
            record
            for attempt in parsed["attempts"]
            for record in attempt["records"]
            if record.get("kind") == "join"
        ]
        if joins:
            if len(joins) != 1:
                return None, classification(
                    "dispatch-record-invalid",
                    "review stage has more than one protocol-owned join",
                )
            joined = joins[0].get("success", {}).get("join", {})
            if not review or joined.get("review_identity") != review[-1]["identity"]:
                return None, classification(
                    "dispatch-record-invalid",
                    "review_v1 tip is not anchored to its protocol-owned join",
                )
            if review[-1]["kind"] == "CritiqueAdjudication":
                attempt = next(
                    item for item in parsed["attempts"] if joins[0] in item["records"]
                )
                if review[-1].get("adjudicated_by") != attempt.get("owner"):
                    return None, classification(
                        "dispatch-record-invalid",
                        "critique adjudication authority differs from the accepted receiver",
                    )
    return parsed, None


def status_ownership_returned(data: dict) -> bool:
    """Whether this ticket's dispatch lifecycle ever took its status.

    A ticket wedged on 2026-08-31 asked the question: its one attempt was
    opened and self-retired before any launch, and after that nothing
    could move it. `set-status` refused `dispatch-join-required`,
    `dispatch-retire` refused `stale-attempt` on the ended attempt, and no
    join could exist because there was no outcome for one to consume. The
    lifecycle owns a status it never started executing.

    The door is exactly as wide as that: one attempt, ended, carrying
    nothing but its own lifecycle records. A launch record, a result, an
    outcome or a join is real execution evidence, and a ticket holding any
    of them keeps its status with the join that has to read them --
    including a second attempt, whose existence says something was retried
    rather than never begun.
    """

    parsed, failure = stored_state(data)
    if failure is not None or not isinstance(parsed, dict):
        return False
    attempts = parsed.get("attempts") or []
    if len(attempts) != 1 or attempts[0].get("state") == "live":
        return False
    return all(
        record.get("kind") == "lifecycle"
        for record in attempts[0].get("records") or []
    )


def attempt_window(data: dict):
    """Return the current attempt's immutable clock from validated state.

    It reads the clock `state` has just validated, so it belongs beside that
    reader rather than beside the operations that consume the window.
    """

    validated, failure = state(data)
    if failure is not None or validated is None:
        return None, failure
    attempts = validated["attempts"]
    if not attempts:
        return None, classification(
            "dispatch-record-invalid", "dispatch_v1 has no execution attempt"
        )
    attempt = next(
        (item for item in reversed(attempts) if item.get("state") == "live"),
        attempts[-1],
    )
    opened = _parse_iso(attempt.get("opened_at"))
    expires = _parse_iso(attempt.get("lease_expires_at"))
    if opened is None or expires is None:
        return None, classification(
            "dispatch-record-invalid", "dispatch attempt has no absolute lease window"
        )
    return {
        "attempt": attempt,
        "opened_at": opened,
        "lease_expires_at": expires,
    }, None
