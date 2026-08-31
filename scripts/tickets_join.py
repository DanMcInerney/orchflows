"""Dispatch-v1 join-owned lifecycle transitions."""

from __future__ import annotations

from datetime import datetime, timezone
import sys

if __package__:
    from .tickets_attempts import (
        OUTCOME_RECORD_ID, PROTOCOL, _classification, _commit_record,
        _identity_failure,
    )
    from .tickets_shapes import DISPATCH_JOIN_SUCCESS_VALUES
    from .tickets_format import (
        GATE_CRITIQUE_MARKER, CHECKER_STAGE_SUFFIX, TERMINAL_STATES,
        _extract_flag, _read_utf8, _set_frontmatter_field, canonical_json,
        is_critique_stage_id, is_review_stage_id,
    )
    from .tickets_store import UTC_STAMP, _run_lock, _segment_error
    from .tickets_store import _terminal_identity_update, _write_identity
    from .tickets_worklog import _run_goal, _run_tickets
    from .tickets_project import TERMINAL_REMEDY, binding_refusal
    from .tickets_review import (
        REVIEW_FIELD, ReviewError, adjudicate, canonical_finding_array, repair_outcome,
        state_from_text,
    )
else:
    from tickets_attempts import (
        OUTCOME_RECORD_ID, PROTOCOL, _classification, _commit_record,
        _identity_failure,
    )
    from tickets_shapes import DISPATCH_JOIN_SUCCESS_VALUES
    from tickets_format import (
        GATE_CRITIQUE_MARKER, CHECKER_STAGE_SUFFIX, TERMINAL_STATES,
        _extract_flag, _read_utf8, _set_frontmatter_field, canonical_json,
        is_critique_stage_id, is_review_stage_id,
    )
    from tickets_store import UTC_STAMP, _run_lock, _segment_error
    from tickets_store import _terminal_identity_update, _write_identity
    from tickets_worklog import _run_goal, _run_tickets
    from tickets_project import TERMINAL_REMEDY, binding_refusal
    from tickets_review import (
        REVIEW_FIELD, ReviewError, adjudicate, canonical_finding_array, repair_outcome,
        state_from_text,
    )

JOIN_STATUSES = frozenset(DISPATCH_JOIN_SUCCESS_VALUES["status"])
DISPATCH_JOIN_USAGE = (
    "dispatch-join <run> <id> --assignment-seal <seal> --dispatch-id <id> "
    "--outcome-record-id outcome --by <join-name> --status <disposition> "
    "[--findings-file <path|->] [--accepted-file <path|->] "
    "[--artifact <fixed-identity>]"
)


def _review_file(source: str, subject: str):
    """Read one review array from a file or standard input.

    Both review arrays cross this boundary the same way, as UTF-8 file data,
    so a shell argument cannot masquerade as a durable carrier. The complete
    findings used to be scraped out of the child's `Result` or `Feedback`
    prose; there is one free-text `Report` now and nothing machine-critical
    is read out of it, so the array a critique produces arrives here as the
    file it always was on disk, and lands in the `review_v1` adjudication
    that is its one durable home.
    """
    if source == "-":
        try:
            stream = getattr(sys.stdin, "buffer", sys.stdin)
            value = stream.read()
            if isinstance(value, bytes):
                value = value.decode("utf-8")
            return value, None
        except (OSError, UnicodeDecodeError, AttributeError) as error:
            return None, {"error": f"unreadable {subject}: {error}"}
    return _read_utf8(source, subject)


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
    """The tree this attempt was executed in, from that field's one owner.

    Read off the attempt, not off any record it carries: the establishment
    records the tree there, and a launch that restated it would be the second
    home this field no longer has. Imported at call time because the flat
    installed layout fixes no order between these two families.
    """

    try:
        if __package__:
            from . import workspace_record
        else:  # pragma: no cover - the flat installed layout
            import workspace_record
    except ImportError:  # pragma: no cover - a partial install
        return None
    return workspace_record.recorded_workspace(attempt)


def _cmd_dispatch_join(rest, *, _lock_held=False):
    """Commit or replay one outcome-fenced join and its lifecycle transition.

    Two writes, one critical section. The record commit and the run's
    terminal timing are one transaction wherever this is called from: the
    landing composition passes ``_lock_held`` and owns the lock, and the
    direct route takes the same lock here for the whole pair. It used to
    take it only inside ``_commit_record`` and stamp the identity after that
    lock had been released, which left the window every other mutating path
    was closed against -- and the identity is written once and never
    rewritten, so a loss in that window is permanent.
    """

    args = list(rest)
    assignment_seal = _extract_flag(args, "--assignment-seal")
    dispatch_id = _extract_flag(args, "--dispatch-id")
    outcome_record_id = _extract_flag(args, "--outcome-record-id")
    joined_by = _extract_flag(args, "--by")
    disposition = _extract_flag(args, "--status")
    findings_file = _extract_flag(args, "--findings-file")
    accepted_file = _extract_flag(args, "--accepted-file")
    artifact = _extract_flag(args, "--artifact")
    if len(args) != 2 or not all((
        assignment_seal, dispatch_id, outcome_record_id, joined_by, disposition,
    )):
        return {"error": f"usage: {DISPATCH_JOIN_USAGE}"}
    if disposition not in JOIN_STATUSES:
        return _classification(
            "join-invalid",
            "the join records the disposition and it must be one of "
            + ", ".join(sorted(JOIN_STATUSES)),
        )
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
    for flag, value in (("--findings-file", findings_file), ("--accepted-file", accepted_file)):
        if value is not None and not review_stage:
            return _classification(
                "review-invalid", f"{flag} applies only to critique joins"
            )
    findings = accepted = None
    for source, subject, target in (
        (findings_file, "critique findings file", "findings"),
        (accepted_file, "accepted blocker file", "accepted"),
    ):
        if source is None:
            continue
        body, failure = _review_file(source, subject)
        if failure is not None:
            return failure
        if target == "findings":
            findings = body
        else:
            accepted = body
    if review_stage:
        for flag, value in (("--findings-file", findings), ("--accepted-file", accepted)):
            if value is None:
                return _classification(
                    "review-invalid", f"critique join requires {flag} <path|->"
                )
        try:
            findings = canonical_finding_array(findings, "critique findings")
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
        # The outcome's existence closes the attempt; it does not say what
        # the ticket became. `land` supplies the disposition its `done`
        # predicate read, and a ticket with no predicate gets the driver's
        # grade -- neither is the child's word for itself.
        status = disposition
        try:
            review = state_from_text(text, allow_legacy=True)
            if is_critique_stage_id(ticket_id):
                lens = (
                    "checker" if ticket_id.endswith(CHECKER_STAGE_SUFFIX)
                    else ticket_id.split(GATE_CRITIQUE_MARKER, 1)[1]
                )
                review = adjudicate(
                    review, findings, accepted, outcome["by"], lens,
                )
            elif ticket_id.endswith(".gate.repair"):
                if accepted is not None:
                    raise ReviewError("repair join does not accept --accepted-file")
                review = repair_outcome(
                    review, artifact or "", outcome["evidence"],
                    joined_by, workspace=_attempt_workspace(attempt),
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

    def transaction():
        result = _commit_record(
            run, ticket_id, dispatch_id, join_record_id, content,
            mutate=join, expected_seal=assignment_seal, record_kind="join",
            _lock_held=True,
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

    if _lock_held:
        return transaction()
    try:
        with _run_lock(run):
            return transaction()
    except OSError as error:
        return {"error": f"unable to lock run '{run}' for the join: {error}"}
