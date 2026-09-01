"""Shared ticket-origin and admission guards for dispatch-v1 mutations."""

from __future__ import annotations

if __package__:
    from .tickets_admission import ADMISSION_PENDING
    from .tickets_context import graded_admission, run_snapshot
    from .tickets_dispatch_schema import classification
    from .tickets_format import _parse_iso
else:
    from tickets_admission import ADMISSION_PENDING
    from tickets_context import graded_admission, run_snapshot
    from tickets_dispatch_schema import classification
    from tickets_format import _parse_iso


def origin_failure(data: dict, run: str, ticket_id: str):
    recorded = (
        str(data.get("run") or "").strip(),
        str(data.get("id") or "").strip(),
    )
    if recorded == (run, ticket_id):
        return None
    return classification(
        "origin-mismatch",
        f"ticket origin is {recorded[0] or '<missing>'}/{recorded[1] or '<missing>'}, not {run}/{ticket_id}",
    )


def admission_failure(path, text: str, data: dict, run: str, ticket_id: str):
    snapshot, failures = run_snapshot(path.parent)
    if failures:
        return failures[0][1]
    grade = graded_admission(ticket_id, text, snapshot, run)
    if grade["findings"]:
        return classification(
            "admission-mismatch", "ticket no longer has a valid sealed admission"
        )
    stored = str(data.get("admission") or "")
    if stored == grade["receipt"]:
        return None
    # A never-promoted ticket is the common half of this refusal and the only
    # half with a mechanical remedy: it holds the pending placeholder because
    # nothing has admitted it yet, and promotion is `dispatch`'s own first
    # step now that `ready` is no longer a door of its own. This is the door a
    # claim on a pending ticket actually reaches -- the status check further
    # down never sees it -- so the remedy is named here.
    if stored == ADMISSION_PENDING:
        return classification(
            "admission-mismatch",
            "ticket has never been admitted: its receipt is still the pending "
            f"placeholder. `tickets.py dispatch {run} {ticket_id}` promotes "
            "and launches it under one lock",
        )
    return classification(
        "admission-mismatch", "ticket's stored admission receipt is not current"
    )


def live_attempt_failure(attempts, now):
    live = [attempt for attempt in attempts if attempt.get("state") == "live"]
    if not live:
        return None
    expiry = _parse_iso(live[-1].get("lease_expires_at"))
    if expiry is None or now >= expiry:
        return classification(
            "lease-expired",
            f"expired dispatch_id '{live[-1].get('dispatch_id')}' must be retired or replaced before a successor opens",
        )
    return classification(
        "live-attempt",
        f"ticket already has live dispatch_id '{live[-1].get('dispatch_id')}'",
    )


def undeclared_supersession_failure(attempt, now, *, declared: bool):
    """Refuse replacing work that is still inside the lease it was opened
    under, unless the caller says that is what it means to do.

    A caller cannot observe a child think.  Quiet is not evidence that the
    child stopped -- the bound the attempt was opened under is the only
    evidence this protocol has -- so superseding still-authorized work is a
    declaration the caller makes, never one the transition infers from
    silence.  Past the lease the attempt is stale and crosses freely.
    """

    if declared:
        return None
    expiry = _parse_iso(attempt.get("lease_expires_at"))
    if expiry is None or now >= expiry:
        return None
    return classification(
        "supersession-undeclared",
        f"dispatch_id '{attempt.get('dispatch_id')}' holds a lease until "
        f"{attempt.get('lease_expires_at')}; declare --supersede-live to "
        "replace work that is still within its bound",
    )


__all__ = (
    "admission_failure", "live_attempt_failure", "origin_failure",
    "undeclared_supersession_failure",
)
