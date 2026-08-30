"""Dispatch-v1 join-owned lifecycle transitions."""

from __future__ import annotations

from datetime import datetime, timezone
import sys

if __package__:
    from .tickets_attempts import (
        OUTCOME_RECORD_ID, PROTOCOL, _classification, _commit_record,
        _identity_failure, accepted_receipt_failure,
    )
    from .tickets_shapes import (
        DISPATCH_OUTCOME_EVIDENCE_FIELDS, DISPATCH_OUTCOME_REQUIRED,
        DISPATCH_OUTCOME_VALUES,
    )
    from .tickets_format import (
        TERMINAL_STATES, TicketFormatError, _extract_flag, _section_body,
        _read_utf8, _set_frontmatter_field, _write_section, canonical_json,
        parse_canonical_json,
    )
    from .tickets_markdown import SECTION_SENTINEL
    from .tickets_result import RESULT_ATTRIBUTION_PREFIX
    from .tickets_store import UTC_STAMP, _segment_error
    from .tickets_store import _terminal_identity_update, _write_identity
    from .tickets_project import TERMINAL_REMEDY, binding_refusal
    from .tickets_outcome import (
        DISPATCH_OUTCOME_USAGE, _outcome_attempt,
        _outcome_attempt_match, _outcome_content, _prior_result_body,
    )
    from .tickets_review import (
        REVIEW_FIELD, ReviewError, adjudicate, canonical_finding_array, repair_outcome,
        state_from_text, verification_outcome,
    )
else:
    from tickets_attempts import (
        OUTCOME_RECORD_ID, PROTOCOL, _classification, _commit_record,
        _identity_failure, accepted_receipt_failure,
    )
    from tickets_shapes import (
        DISPATCH_OUTCOME_EVIDENCE_FIELDS, DISPATCH_OUTCOME_REQUIRED,
        DISPATCH_OUTCOME_VALUES,
    )
    from tickets_format import (
        TERMINAL_STATES, TicketFormatError, _extract_flag, _section_body,
        _read_utf8, _set_frontmatter_field, _write_section, canonical_json,
        parse_canonical_json,
    )
    from tickets_markdown import SECTION_SENTINEL
    from tickets_result import RESULT_ATTRIBUTION_PREFIX
    from tickets_store import UTC_STAMP, _segment_error
    from tickets_store import _terminal_identity_update, _write_identity
    from tickets_project import TERMINAL_REMEDY, binding_refusal
    from tickets_outcome import (
        DISPATCH_OUTCOME_USAGE, _outcome_attempt,
        _outcome_attempt_match, _outcome_content, _prior_result_body,
    )
    from tickets_review import (
        REVIEW_FIELD, ReviewError, adjudicate, canonical_finding_array, repair_outcome,
        state_from_text, verification_outcome,
    )

JOIN_STATUSES = frozenset(DISPATCH_OUTCOME_VALUES["status"])
OUTCOME_SECTIONS = tuple(DISPATCH_OUTCOME_EVIDENCE_FIELDS)
DISPATCH_JOIN_USAGE = (
    "dispatch-join <run> <id> --assignment-seal <seal> --dispatch-id <id> "
    "--outcome-record-id outcome --by <join-name> "
    "[--accepted-file <path|->] [--artifact <fixed-identity>]"
)


def _finding_array(body, subject: str):
    if not isinstance(body, str) or not body.strip():
        return None
    # Result/Feedback may carry surrounding prose in historical records.  A
    # JSON-looking body, however, is claiming to be the typed findings
    # carrier and must be a JSON array; do not silently ignore malformed or
    # object-shaped carriers when another record happens to contain `[]`.
    if body.lstrip()[0] not in "[{\"-0123456789tfn":
        return None
    try:
        value = parse_canonical_json(body)
    except (TypeError, ValueError) as error:
        raise ReviewError(f"{subject} is not a valid JSON array: {error}") from error
    if not isinstance(value, list):
        raise ReviewError(f"{subject} is not a valid JSON array")
    return value


def _critique_findings(attempt: dict, outcome_evidence: dict) -> str:
    findings = []
    found = False
    for record in attempt.get("records", []):
        if record.get("kind") != "result":
            continue
        try:
            content = parse_canonical_json(record["content"])
        except (KeyError, TypeError, ValueError) as error:
            raise ReviewError(f"critique findings result is not canonical JSON: {error}") from error
        if not isinstance(content, dict) or content.get("section") not in {
            "Result", "Feedback",
        }:
            continue
        values = _finding_array(
            content.get("body"), f"critique {content.get('section')} result"
        )
        if values is not None:
            found = True
            findings.extend(values)
    if isinstance(outcome_evidence, dict):
        for section in ("Result", "Feedback"):
            values = _finding_array(
                outcome_evidence.get(section), f"critique outcome {section}"
            )
            if values is not None:
                found = True
                findings.extend(values)
    if not found:
        raise ReviewError(
            "critique findings must be a JSON array in Result or Feedback"
        )
    # One authoritative finding is one finding however many of the
    # protocol's own carriers it rode: an executor that streams it in a
    # result record and repeats it in the reserved outcome's copy of that
    # section recorded the same fact twice, not two findings.  Collapsing
    # byte-identical values here leaves the id-uniqueness grade below to
    # convict what it is for -- two distinct records claiming one id.
    seen, authoritative = set(), []
    for value in findings:
        identity = canonical_json(value)
        if identity in seen:
            continue
        seen.add(identity)
        authoritative.append(value)
    # Validate the flattened carrier before caller-supplied acceptance is
    # considered.  This keeps malformed or duplicate executor findings out of
    # the immutable adjudication boundary even when they arrived in several
    # streamed Result/Feedback records.
    return canonical_finding_array(canonical_json(authoritative), "critique findings")


def _accepted_file(source: str):
    """Read the protocol-owned accepted blocker subset from a file/stdin.

    Review findings are executor evidence.  The only caller-facing review
    input is the accepted subset, and it crosses this boundary as UTF-8 file
    data so a shell argument cannot masquerade as a durable carrier.
    """
    if source == "-":
        try:
            stream = getattr(sys.stdin, "buffer", sys.stdin)
            value = stream.read()
            if isinstance(value, bytes):
                value = value.decode("utf-8")
            return value, None
        except (OSError, UnicodeDecodeError, AttributeError) as error:
            return None, {"error": f"unreadable accepted blocker file: {error}"}
    return _read_utf8(source, "accepted blocker file")


def _attempt_workspace(attempt: dict) -> str | None:
    record = next((
        item for item in attempt.get("records", [])
        if item.get("kind") == "packet" and item.get("record_id") == "dispatch-packet"
    ), None)
    if record is None:
        return None
    try:
        content = parse_canonical_json(record["content"])
    except (KeyError, TypeError, ValueError):
        return None
    packet = content.get("packet") if isinstance(content, dict) else None
    return packet.get("workspace") if isinstance(packet, dict) else None


def _outcome_failure(run: str, ticket_id: str, content):
    required = set(DISPATCH_OUTCOME_REQUIRED)
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
    if ".gate.critique." in ticket_id or ticket_id.endswith(".check"):
        # Critique Result and Feedback are generated finding carriers, not
        # arbitrary prose.  Keep the import lazy because tickets_review
        # consumes this module while joining a review stage.
        if __package__:
            from .tickets_review import ReviewError, canonical_finding_array
        else:
            from tickets_review import ReviewError, canonical_finding_array
        for section in ("Result", "Feedback"):
            try:
                canonical_finding_array(evidence[section], f"critique outcome {section}")
            except ReviewError as error:
                return _classification("outcome-invalid", str(error))
    for body in evidence.values():
        if any(line.startswith("## ") or line.startswith(RESULT_ATTRIBUTION_PREFIX) for line in body.splitlines()):
            return _classification("outcome-invalid", "outcome evidence contains a reserved heading or attribution")
    return None


def _cmd_dispatch_outcome(rest):
    args = list(rest)
    if len(args) < 2:
        return {"error": f"usage: {DISPATCH_OUTCOME_USAGE}"}
    run, ticket_id = args[:2]
    remaining = args[2:]
    for kind, value in (("run id", run), ("ticket id", ticket_id)):
        invalid = _segment_error(kind, value)
        if invalid is not None:
            return invalid
    carrier, failure = _outcome_content(remaining)
    if failure is not None:
        return failure

    inferred, failure = _outcome_attempt(run, ticket_id)
    if failure is not None:
        return failure
    _path, _text, _data, _state, attempt = inferred
    # A caller without an accepted receipt may not write an execution record
    # at all, so it is told that before its evidence is graded: resolving
    # closing files first answers a receipt-less caller with a complaint
    # about content it was never entitled to commit.
    failure = accepted_receipt_failure(attempt)
    if failure is not None:
        return failure
    if isinstance(carrier, dict) and "_files" in carrier:
        evidence = {}
        for section in OUTCOME_SECTIONS:
            source = carrier["_files"].get(section)
            if source is not None:
                body, read_failure = _read_utf8(source, f"{section} evidence file")
                if read_failure is not None:
                    return read_failure
            elif section in {"Result", "Verification"}:
                body = _prior_result_body(attempt, section)
                if body is None:
                    return _classification(
                        "outcome-invalid",
                        f"outcome requires {section} evidence through --{section.lower()}-file or a prior result record",
                    )
            elif section in {"Feedback", "Risks"}:
                body = "[]"
            else:
                body = ""
            if body is None:
                body = ""
            evidence[section] = body
        content = {
            "protocol": PROTOCOL,
            "run": run,
            "id": ticket_id,
            "assignment_seal": attempt["assignment_seal"],
            "dispatch_id": attempt["dispatch_id"],
            "outcome_record_id": OUTCOME_RECORD_ID,
            "by": attempt["owner"],
            "status": carrier["status"],
            "evidence": evidence,
        }
    else:
        content = carrier
    failure = _outcome_attempt_match(content, run, ticket_id, attempt)
    if failure is not None:
        return failure
    if content.get("protocol") != PROTOCOL or content.get("run") != run or content.get("id") != ticket_id:
        return _classification("outcome-invalid", "outcome envelope origin or protocol differs")
    if not isinstance(content, dict):
        return _classification("outcome-invalid", "outcome envelope must be an object")
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
    accepted_file = _extract_flag(args, "--accepted-file")
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
    review_stage = ".gate.critique." in ticket_id or ticket_id.endswith(".check")
    if accepted_file is not None and not review_stage:
        return _classification(
            "review-invalid", "--accepted-file applies only to critique joins"
        )
    accepted = None
    if accepted_file is not None:
        accepted, failure = _accepted_file(accepted_file)
        if failure is not None:
            return failure
    if review_stage:
        if accepted is None:
            return _classification(
                "review-invalid", "critique join requires --accepted-file <path|->"
            )
        try:
            accepted = canonical_finding_array(accepted, "critique accepted")
        except ReviewError as error:
            return _classification("review-invalid", str(error))

    join_record_id = f"join:{outcome_record_id}"
    content = {
        "assignment_seal": assignment_seal,
        "dispatch_id": dispatch_id,
        "joined_by": joined_by,
        "operation": "join",
        "outcome_record_id": outcome_record_id,
    }
    if ".gate." in ticket_id or ticket_id.endswith(".check"):
        content["review"] = {"accepted": accepted, "artifact": artifact}

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
            review = state_from_text(text, allow_legacy=True)
            if ".gate.critique." in ticket_id or ticket_id.endswith(".check"):
                lens = (
                    "checker" if ticket_id.endswith(".check")
                    else ticket_id.split(".gate.critique.", 1)[1]
                )
                review = adjudicate(
                    review, _critique_findings(
                        attempt, outcome["evidence"],
                    ), accepted,
                    outcome["by"], lens,
                )
            elif ticket_id.endswith(".gate.repair"):
                if accepted is not None:
                    raise ReviewError("repair join does not accept --accepted-file")
                review = repair_outcome(
                    review, artifact or "", outcome["evidence"]["Result"],
                    joined_by, workspace=_attempt_workspace(attempt),
                )
            elif ticket_id.endswith(".gate.verify"):
                if accepted is not None:
                    raise ReviewError("verification join does not accept --accepted-file")
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
        if review is not None:
            response["join"]["review_identity"] = review["records"][-1]["identity"]
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
