"""Dispatch-v1 join-owned lifecycle transitions."""

from __future__ import annotations

from datetime import datetime, timezone
import sys

if __package__:
    from .tickets_attempts import (
        OUTCOME_RECORD_ID, PROTOCOL, _classification, _commit_record,
        _identity_failure,
    )
    from .tickets_shapes import DISPATCH_OUTCOME_VALUES
    from .tickets_format import (
        GATE_CRITIQUE_MARKER, CHECKER_STAGE_SUFFIX, TERMINAL_STATES,
        _extract_flag, _read_utf8, _set_frontmatter_field, canonical_json,
        is_critique_stage_id, is_review_stage_id, parse_canonical_json,
    )
    from .tickets_store import UTC_STAMP, _segment_error
    from .tickets_store import _terminal_identity_update, _write_identity
    from .tickets_worklog import _run_goal, _run_tickets
    from .tickets_project import TERMINAL_REMEDY, binding_refusal
    from .tickets_review import (
        REVIEW_FIELD, ReviewError, adjudicate, canonical_finding_array, repair_outcome,
        state_from_text, verification_outcome,
    )
else:
    from tickets_attempts import (
        OUTCOME_RECORD_ID, PROTOCOL, _classification, _commit_record,
        _identity_failure,
    )
    from tickets_shapes import DISPATCH_OUTCOME_VALUES
    from tickets_format import (
        GATE_CRITIQUE_MARKER, CHECKER_STAGE_SUFFIX, TERMINAL_STATES,
        _extract_flag, _read_utf8, _set_frontmatter_field, canonical_json,
        is_critique_stage_id, is_review_stage_id, parse_canonical_json,
    )
    from tickets_store import UTC_STAMP, _segment_error
    from tickets_store import _terminal_identity_update, _write_identity
    from tickets_worklog import _run_goal, _run_tickets
    from tickets_project import TERMINAL_REMEDY, binding_refusal
    from tickets_review import (
        REVIEW_FIELD, ReviewError, adjudicate, canonical_finding_array, repair_outcome,
        state_from_text, verification_outcome,
    )

JOIN_STATUSES = frozenset(DISPATCH_OUTCOME_VALUES["status"])
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


def _closes_the_run(run: str, ticket_id: str) -> bool:
    """Whether this ticket's terminal join is the run's own terminal moment.

    The run's goal ticket, read from `tickets_worklog._run_goal` -- the one
    owner `worklog` and `set-status` already read it from: the root of a cut
    run, and the single ticket of an ad-hoc, direct, or loop run. Any other
    member reaching a terminal status is one item finishing, and the run
    identity's terminal timing is written once and never rewritten, so
    stamping it there froze the whole run's elapsed time at whichever
    sibling happened to join first.
    """

    items, failure = _run_tickets(run)
    if failure is not None or not items:
        return False
    goal, _kind = _run_goal(items)
    return str(goal.get("id") or "") == ticket_id


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


def _cmd_dispatch_join(rest, *, _lock_held=False):
    """Commit or replay one outcome-fenced join and its lifecycle transition.

    ``_lock_held`` is the landing composition's, as above; the terminal
    timing write below then lands inside that same critical section rather
    than after its own lock has been released.
    """

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
    review_stage = is_critique_stage_id(ticket_id)
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
    if is_review_stage_id(ticket_id):
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
            if is_critique_stage_id(ticket_id):
                lens = (
                    "checker" if ticket_id.endswith(CHECKER_STAGE_SUFFIX)
                    else ticket_id.split(GATE_CRITIQUE_MARKER, 1)[1]
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
        _lock_held=_lock_held,
    )
    if "error" in result:
        return result
    status = result["join"]["status"]
    if status not in TERMINAL_STATES or not _closes_the_run(run, ticket_id):
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
