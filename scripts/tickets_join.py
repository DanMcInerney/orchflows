"""Dispatch-v1 join-owned lifecycle transitions."""

from __future__ import annotations

from datetime import datetime, timezone

if __package__:
    from .tickets_attempts import (
        OUTCOME_RECORD_ID, PROTOCOL, _classification, _commit_record,
        _identity_failure,
    )
    from .tickets_shapes import DISPATCH_JOIN_SUCCESS_VALUES
    from .tickets_format import TERMINAL_STATES, _extract_flag, _set_frontmatter_field
    from .tickets_store import UTC_STAMP, _run_lock, _segment_error
    from .tickets_store import _terminal_identity_update, _write_identity
    from .tickets_worklog import _run_goal, _run_tickets
    from .tickets_project import TERMINAL_REMEDY, binding_refusal
else:
    from tickets_attempts import (
        OUTCOME_RECORD_ID, PROTOCOL, _classification, _commit_record,
        _identity_failure,
    )
    from tickets_shapes import DISPATCH_JOIN_SUCCESS_VALUES
    from tickets_format import TERMINAL_STATES, _extract_flag, _set_frontmatter_field
    from tickets_store import UTC_STAMP, _run_lock, _segment_error
    from tickets_store import _terminal_identity_update, _write_identity
    from tickets_worklog import _run_goal, _run_tickets
    from tickets_project import TERMINAL_REMEDY, binding_refusal

JOIN_STATUSES = frozenset(DISPATCH_JOIN_SUCCESS_VALUES["status"])
DISPATCH_JOIN_USAGE = (
    "dispatch-join <run> <id> --assignment-seal <seal> --dispatch-id <id> "
    "--outcome-record-id outcome --by <join-name> --status <disposition>"
)


def dispatch_join_identity_defects(outcome_record_id: str, dispatch_id: str, joined_by: str):
    """The argument-shape refusals a join can raise, before any tree read.

    One function for both callers: the standalone command validates its own
    parsed flags here, and `land`'s composition calls this before
    `workspace-integrate` merges anything, so a malformed `--dispatch-id` or
    `--by` refuses before the tree is mutated rather than after -- the
    landing defect this closes (a refused join left the candidate merged).
    """

    if outcome_record_id != OUTCOME_RECORD_ID:
        return _classification(
            "outcome-record-mismatch", "dispatch-join consumes only the reserved outcome record"
        )
    for kind, value in (("dispatch-id", dispatch_id), ("join-owner", joined_by)):
        failure = _identity_failure(kind, value)
        if failure is not None:
            return failure
    return None


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
    failure = dispatch_join_identity_defects(outcome_record_id, dispatch_id, joined_by)
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
        # The outcome's existence closes the attempt; it does not say what
        # the ticket became. `land` supplies the disposition its `done`
        # predicate read, and a ticket with no predicate gets the driver's
        # grade -- neither is the child's word for itself.
        status = disposition
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
        return updated, response, None

    def transaction():
        result = _commit_record(
            run, ticket_id, dispatch_id, join_record_id, content,
            mutate=join, expected_seal=assignment_seal, record_kind="join",
            # The join is the driver's act, not the worker's, and the
            # worker's own lease says nothing about when its caller gets
            # around to reading the outcome and joining it. `join` above
            # still refuses `outcome-record-mismatch` when no committed
            # outcome names this dispatch_id, so an attempt that ended
            # without ever filing one is refused exactly as before -- what
            # is dropped is only the requirement that the *join* itself
            # lands inside a lease the worker, not the driver, was bound by.
            require_live_lease=False,
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
