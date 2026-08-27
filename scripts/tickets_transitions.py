"""Lifecycle transition table for sealed tickets."""
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
