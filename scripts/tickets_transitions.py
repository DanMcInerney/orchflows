"""Executable lifecycle transition declarations for sealed tickets.

The mutation code consumes the compact rows below.  The documentation
renderer consumes their expanded form, so the public lifecycle view cannot
acquire a second, hand-maintained state machine.
"""
from __future__ import annotations

from collections import namedtuple

if __package__:
    from .tickets_admission import ADMISSION_PENDING
    from .tickets_format import TERMINAL_STATES, VALID_STATUSES
else:
    from tickets_admission import ADMISSION_PENDING
    from tickets_format import TERMINAL_STATES, VALID_STATUSES

PENDING, READY, CLAIMED, SUSPENDED, COMPLETE = "pending", "ready", "claimed", "suspended", "complete"
STATUSES = tuple(sorted(VALID_STATUSES))
LEASE_FIELDS = ("claimed_by", "claimed_at")
CHECKABLE_STATUSES = frozenset({CLAIMED, SUSPENDED})
ADMISSION_OWNED_TARGETS = (READY, CLAIMED)
Row = namedtuple("Row", ("command", "sources", "target", "sets", "blanks", "remedy"))
Stamp = namedtuple("Stamp", ("status", "admission", "blanks", "draft_statuses"))
LifecycleSpec = namedtuple(
    "LifecycleSpec",
    ("event", "sources", "target", "actor", "required_record", "contract", "rule"),
)
LifecycleRow = namedtuple(
    "LifecycleRow",
    (
        "predecessor",
        "event",
        "actor",
        "required_record",
        "result",
        "contract",
        "rule",
        "anchor",
    ),
)


def set_status_command(target: str) -> str:
    return f"set-status {target}"


_ROWS = (
    Row("claim", (PENDING, READY), CLAIMED, ("admission", "status") + LEASE_FIELDS, (), "claim it"),
    Row("check", tuple(sorted(CHECKABLE_STATUSES)), None, ("checked_by",), (), "check it"),
    Row("join-noop-repair", (READY,), COMPLETE, ("status",) + LEASE_FIELDS, (), "complete the clean repair at its join"),
    Row(set_status_command(PENDING), STATUSES, PENDING, ("status",), LEASE_FIELDS, "release it to pending"),
    Row(set_status_command(SUSPENDED), STATUSES, SUSPENDED, ("status",), (), "suspend it"),
) + tuple(
    Row(set_status_command(state), STATUSES, state, ("status",), (), f"set status {state}")
    for state in TERMINAL_STATES
)
COMMANDS = tuple(sorted({row.command for row in _ROWS}))
STAMPS = {
    "stamp": Stamp(PENDING, ADMISSION_PENDING, LEASE_FIELDS, (PENDING, READY)),
    "draft-validate": Stamp(PENDING, ADMISSION_PENDING, LEASE_FIELDS, (PENDING, READY, SUSPENDED)),
}

# This is executable metadata beside the guards that own the transitions.
# Sources are expanded one-per-row for the rendered view. A same-state event
# still appears because it changes a required lifecycle record.
_LIFECYCLE_SPECS = (
    LifecycleSpec("issue", ("unissued",), PENDING, "caller", "sealed ticket source", "contracts/work-item.md", "rules/topology.md"),
    LifecycleSpec("stamp", ("unsealed draft",), PENDING, "caller", "sealed root generation", "contracts/work-item.md", "rules/topology.md"),
    LifecycleSpec("ready", (PENDING,), READY, "caller", "admission receipt", "contracts/work-item.md", "rules/topology.md"),
    LifecycleSpec("claim", (PENDING, READY, CLAIMED), CLAIMED, "caller", "admission receipt; stale-claim proof when already claimed", "contracts/work-item.md", "rules/delegation.md"),
    LifecycleSpec("dispatch-open", (READY, CLAIMED, SUSPENDED), CLAIMED, "caller", "assignment seal and admission receipt", "contracts/dispatch.md", "rules/delegation.md"),
    LifecycleSpec("dispatch-commit", (CLAIMED,), CLAIMED, "caller or accepted receiver", "live dispatch attempt record", "contracts/dispatch.md", "rules/delegation.md"),
    LifecycleSpec("dispatch-packet", (CLAIMED,), CLAIMED, "caller", "live dispatch attempt record", "contracts/dispatch.md", "rules/delegation.md"),
    LifecycleSpec("dispatch-receive", (CLAIMED,), CLAIMED, "established worker or planner", "committed dispatch-packet record", "contracts/dispatch.md", "rules/roles.md"),
    LifecycleSpec("result", (CLAIMED,), CLAIMED, "accepted receiver", "accepted dispatch-receipt record", "contracts/result.md", "rules/verification.md"),
    LifecycleSpec("dispatch-outcome", (CLAIMED,), CLAIMED, "accepted receiver", "accepted dispatch-receipt record", "contracts/dispatch.md", "rules/delegation.md"),
    LifecycleSpec("dispatch-retire", (CLAIMED,), CLAIMED, "caller", "live dispatch attempt record", "contracts/dispatch.md", "rules/delegation.md"),
    LifecycleSpec("dispatch-replace", (CLAIMED,), CLAIMED, "caller", "live predecessor attempt and assignment seal", "contracts/dispatch.md", "rules/delegation.md"),
) + tuple(
    LifecycleSpec("dispatch-join", (CLAIMED,), state, "caller", "reserved outcome record", "contracts/dispatch.md", "rules/delegation.md")
    for state in TERMINAL_STATES
) + (
    LifecycleSpec("check", (COMPLETE,), COMPLETE, "caller", "completed critique adjudication", "contracts/verdict.md", "rules/verification.md"),
    LifecycleSpec("join-noop-repair", (READY,), COMPLETE, "caller", "completed critique dependencies and empty Result", "contracts/verdict.md", "rules/verification.md"),
) + tuple(
    LifecycleSpec(
        set_status_command(state),
        STATUSES,
        state,
        "caller",
        "no dispatch-v1 record (legacy path)",
        "contracts/worklog.md" if state in TERMINAL_STATES else "contracts/work-item.md",
        "rules/loops.md" if state in TERMINAL_STATES else "rules/topology.md",
    )
    for state in (PENDING, SUSPENDED) + tuple(sorted(TERMINAL_STATES))
)


def _anchor(value: str) -> str:
    return "lifecycle-" + "-".join(
        part for part in "".join(
            character.lower() if character.isalnum() else " " for character in value
        ).split() if part
    )


def lifecycle_rows() -> tuple:
    """Return the complete, deterministic one-row-per-predecessor view."""
    rows = []
    for spec in _LIFECYCLE_SPECS:
        for source in spec.sources:
            identity = f"{spec.event}-{source}-to-{spec.target}"
            rows.append(LifecycleRow(
                predecessor=source,
                event=spec.event,
                actor=spec.actor,
                required_record=spec.required_record,
                result=spec.target,
                contract=spec.contract,
                rule=spec.rule,
                anchor=_anchor(identity),
            ))
    return tuple(rows)


def pending_admission() -> str:
    return STAMPS["stamp"].admission


def stamp(command: str = "stamp"):
    return STAMPS.get(command)


def transition(status: str, command: str):
    return next((row for row in _ROWS if row.command == command and status in row.sources), None)


def allows(status: str, command: str) -> bool:
    return transition(status, command) is not None


def sets(status: str, command: str) -> tuple:
    row = transition(status, command)
    return () if row is None else row.sets


def blanks(status: str, command: str) -> tuple:
    row = transition(status, command)
    return () if row is None else row.blanks


def set_status_blanks(target: str) -> tuple:
    return blanks(CLAIMED, set_status_command(target))


def remedies(status: str) -> tuple:
    return tuple(row.remedy for row in _ROWS if status in row.sources)


def refusal(subject: str, command: str, status: str, note: str = None, **_ignored) -> str:
    row = transition(status, command)
    remedy = f" Remedy: {row.remedy}." if row is not None else ""
    suffix = f" {note}" if note else ""
    return f"{subject}.{remedy}{suffix}"
