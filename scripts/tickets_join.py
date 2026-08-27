"""Dispatch-v1 join-owned lifecycle transitions."""

from __future__ import annotations

from datetime import datetime, timezone

if __package__:
    from .tickets_attempts import (
        OUTCOME_RECORD_ID, PROTOCOL, _classification, _commit_record,
        _identity_failure,
    )
    from .tickets_format import (
        TERMINAL_STATES, TicketFormatError, _extract_flag, _section_body,
        _set_frontmatter_field, _write_section, canonical_json,
        parse_canonical_json,
    )
    from .tickets_markdown import SECTION_SENTINEL
    from .tickets_result import RESULT_ATTRIBUTION_PREFIX
    from .tickets_store import UTC_STAMP, _segment_error
    from .tickets_store import _terminal_identity_update, _write_identity
    from .tickets_project import TERMINAL_REMEDY, binding_refusal
    from .tickets_review import (
        REVIEW_FIELD, ReviewError, adjudicate, repair_outcome,
        state_from_text, verification_outcome,
    )
else:
    from tickets_attempts import (
        OUTCOME_RECORD_ID, PROTOCOL, _classification, _commit_record,
        _identity_failure,
    )
    from tickets_format import (
        TERMINAL_STATES, TicketFormatError, _extract_flag, _section_body,
        _set_frontmatter_field, _write_section, canonical_json,
        parse_canonical_json,
    )
    from tickets_markdown import SECTION_SENTINEL
    from tickets_result import RESULT_ATTRIBUTION_PREFIX
    from tickets_store import UTC_STAMP, _segment_error
    from tickets_store import _terminal_identity_update, _write_identity
    from tickets_project import TERMINAL_REMEDY, binding_refusal
    from tickets_review import (
        REVIEW_FIELD, ReviewError, adjudicate, repair_outcome,
        state_from_text, verification_outcome,
    )

JOIN_STATUSES = frozenset(TERMINAL_STATES) | {"suspended"}
OUTCOME_SECTIONS = ("Result", "Verification", "Feedback", "Risks", "Handoff")
DISPATCH_OUTCOME_USAGE = "dispatch-outcome <run> <id> --content <canonical-json>"
DISPATCH_JOIN_USAGE = (
    "dispatch-join <run> <id> --assignment-seal <seal> --dispatch-id <id> "
    "--outcome-record-id outcome --by <join-name> "
    "[--accepted <canonical-json-array>] [--artifact <fixed-identity>]"
)


def _critique_findings(attempt: dict, outcome_feedback: str) -> str:
    findings = []
    found = False
    for record in attempt.get("records", []):
        if record.get("kind") != "result":
            continue
        try:
            content = parse_canonical_json(record["content"])
        except (KeyError, TypeError, ValueError) as error:
            raise ReviewError(f"critique findings result is not canonical JSON: {error}") from error
        if not isinstance(content, dict) or content.get("section") != "Feedback":
            continue
        found = True
        try:
            values = parse_canonical_json(content.get("body"))
        except (TypeError, ValueError) as error:
            raise ReviewError(f"critique findings must be a canonical JSON array: {error}") from error
        if not isinstance(values, list):
            raise ReviewError("critique findings must be a canonical JSON array")
        findings.extend(values)
    return canonical_json(findings) if found else outcome_feedback


def _outcome_failure(run: str, ticket_id: str, content):
    required = {
        "assignment_seal", "by", "dispatch_id", "evidence", "id",
        "outcome_record_id", "protocol", "run", "status",
    }
    if not isinstance(content, dict) or set(content) != required:
        return _classification("outcome-invalid", "outcome envelope has unknown or missing fields")
    if content.get("protocol") != PROTOCOL or content.get("run") != run or content.get("id") != ticket_id:
        return _classification("outcome-invalid", "outcome envelope origin or protocol differs")
    if content.get("outcome_record_id") != OUTCOME_RECORD_ID:
        return _classification("outcome-invalid", "outcome envelope does not use the reserved identity")
    if content.get("status") not in JOIN_STATUSES:
        return _classification("outcome-invalid", "outcome status is not a join disposition")
    for kind, value in (("owner", content.get("by")), ("dispatch-id", content.get("dispatch_id"))):
        failure = _identity_failure(kind, value)
        if failure is not None:
            return _classification("outcome-invalid", failure["error"])
    evidence = content.get("evidence")
    if not isinstance(evidence, dict) or set(evidence) != set(OUTCOME_SECTIONS):
        return _classification("outcome-invalid", "outcome evidence must close the five executor sections")
    if any(not isinstance(evidence.get(section), str) for section in OUTCOME_SECTIONS):
        return _classification("outcome-invalid", "outcome evidence bodies must be strings")
    required_sections = ("Result", "Verification", "Feedback", "Risks")
    if any(not evidence[section].strip() for section in required_sections):
        return _classification("outcome-invalid", "terminal outcome evidence is incomplete")
    if content["status"] == "suspended" and not evidence["Handoff"].strip():
        return _classification("handoff-required", "suspension requires Handoff evidence")
    if content["status"] != "suspended" and evidence["Handoff"].strip():
        return _classification("outcome-invalid", "terminal outcome cannot carry a Handoff")
    for body in evidence.values():
        if any(line.startswith("## ") or line.startswith(RESULT_ATTRIBUTION_PREFIX) for line in body.splitlines()):
            return _classification("outcome-invalid", "outcome evidence contains a reserved heading or attribution")
    return None


def _cmd_dispatch_outcome(rest):
    args = list(rest)
    content_text = _extract_flag(args, "--content")
    if len(args) != 2 or content_text is None:
        return {"error": f"usage: {DISPATCH_OUTCOME_USAGE}"}
    run, ticket_id = args
    for kind, value in (("run id", run), ("ticket id", ticket_id)):
        invalid = _segment_error(kind, value)
        if invalid is not None:
            return invalid
    try:
        content = parse_canonical_json(content_text)
    except (TypeError, ValueError) as error:
        return _classification("outcome-invalid", f"outcome is not canonical JSON: {error}")
    if content_text != canonical_json(content):
        return _classification("outcome-invalid", "outcome is not canonical JSON")
    failure = _outcome_failure(run, ticket_id, content)
    if failure is not None:
        return failure

    def commit_outcome(text, _data, _attempt, _state):
        updated = text
        try:
            for section in OUTCOME_SECTIONS:
                body = content["evidence"][section]
                if not body:
                    continue
                prior = _section_body(updated, section)
                materialized = (
                    f"{RESULT_ATTRIBUTION_PREFIX}`{content['by']}`\n\n{body}"
                )
                if prior == materialized or f"\n\n{materialized}" in prior:
                    return text, None, _classification(
                        "outcome-invalid",
                        f"outcome {section} repeats evidence already materialized by this dispatch",
                    )
                updated = _write_section(
                    updated, section, materialized,
                    bool(prior and prior != SECTION_SENTINEL),
                )
        except TicketFormatError as error:
            return text, None, _classification("outcome-invalid", str(error))
        return updated, {"outcome": content}, None

    return _commit_record(
        run, ticket_id, content["dispatch_id"], OUTCOME_RECORD_ID, content,
        mutate=commit_outcome, expected_seal=content["assignment_seal"],
        expected_owner=content["by"], record_kind="outcome",
    )


def _cmd_dispatch_join(rest):
    args = list(rest)
    assignment_seal = _extract_flag(args, "--assignment-seal")
    dispatch_id = _extract_flag(args, "--dispatch-id")
    outcome_record_id = _extract_flag(args, "--outcome-record-id")
    joined_by = _extract_flag(args, "--by")
    accepted = _extract_flag(args, "--accepted")
    artifact = _extract_flag(args, "--artifact")
    if len(args) != 2 or not all((
        assignment_seal, dispatch_id, outcome_record_id, joined_by,
    )):
        return {"error": f"usage: {DISPATCH_JOIN_USAGE}"}
    run, ticket_id = args
    for kind, value in (("run id", run), ("ticket id", ticket_id)):
        invalid = _segment_error(kind, value)
        if invalid is not None:
            return invalid
    if outcome_record_id != OUTCOME_RECORD_ID:
        return _classification("outcome-record-mismatch", "dispatch-join consumes only the reserved outcome record")
    for kind, value in (("dispatch-id", dispatch_id), ("join-owner", joined_by)):
        failure = _identity_failure(kind, value)
        if failure is not None:
            return failure

    join_record_id = f"join:{outcome_record_id}"
    content = {
        "assignment_seal": assignment_seal,
        "dispatch_id": dispatch_id,
        "joined_by": joined_by,
        "operation": "join",
        "outcome_record_id": outcome_record_id,
    }

    def join(text, _data, attempt, _state):
        outcome_record = next(
            (
                item for item in attempt.get("records", [])
                if item.get("record_id") == outcome_record_id
                and item.get("kind") == "outcome"
            ),
            None,
        )
        outcome_success = (
            outcome_record.get("success") if isinstance(outcome_record, dict) else None
        )
        if not isinstance(outcome_success, dict) or not isinstance(
            outcome_success.get("outcome"), dict
        ):
            return text, None, _classification(
                "outcome-record-mismatch",
                f"record_id '{outcome_record_id}' is not the committed executor outcome",
            )
        outcome = outcome_success["outcome"]
        if outcome.get("dispatch_id") != dispatch_id:
            return text, None, _classification(
                "outcome-record-mismatch", "committed outcome belongs to another dispatch"
            )
        status = outcome["status"]
        try:
            review = state_from_text(text)
            if ".gate.critique." in ticket_id:
                lens = ticket_id.split(".gate.critique.", 1)[1]
                review = adjudicate(
                    review, _critique_findings(
                        attempt, outcome["evidence"]["Feedback"],
                    ), accepted,
                    joined_by, lens,
                )
            elif ticket_id.endswith(".gate.repair"):
                if accepted is not None:
                    raise ReviewError("repair join does not accept --accepted")
                review = repair_outcome(
                    review, artifact or "", outcome["evidence"]["Result"],
                    joined_by,
                )
            elif ticket_id.endswith(".gate.verify"):
                if accepted is not None:
                    raise ReviewError("verification join does not accept --accepted")
                review = verification_outcome(
                    review, artifact, outcome["evidence"]["Verification"],
                    joined_by,
                )
            elif accepted is not None or artifact is not None:
                raise ReviewError("review flags apply only to gate-stage joins")
        except ReviewError as error:
            return text, None, _classification("review-invalid", str(error))
        if status in TERMINAL_STATES:
            held = binding_refusal(run, TERMINAL_REMEDY)
            if held is not None:
                return text, None, {"error": held}
        joined_at = datetime.now(timezone.utc).strftime(UTC_STAMP)
        response = {"join": {
            "protocol": PROTOCOL,
            "run": run,
            "id": ticket_id,
            "assignment_seal": assignment_seal,
            "dispatch_id": dispatch_id,
            "outcome_record_id": outcome_record_id,
            "by": joined_by,
            "status": status,
            "joined_at": joined_at,
        }}
        attempt["state"] = "retired"
        attempt["retired_at"] = joined_at
        attempt["retirement"] = response
        updated = _set_frontmatter_field(text, "status", status)
        if review is not None:
            updated = _set_frontmatter_field(
                updated, REVIEW_FIELD, canonical_json(review)
            )
        return updated, response, None

    result = _commit_record(
        run, ticket_id, dispatch_id, join_record_id, content,
        mutate=join, expected_seal=assignment_seal, record_kind="join",
    )
    if "error" in result:
        return result
    status = result["join"]["status"]
    if status not in TERMINAL_STATES:
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
