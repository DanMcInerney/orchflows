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

# PENDING is not respelled: ADMISSION_PENDING is tickets_admission's own
# declared "pending" literal, imported above, and this row only re-exports
# it under the lifecycle vocabulary's name.
PENDING, READY, CLAIMED, SUSPENDED = ADMISSION_PENDING, "ready", "claimed", "suspended"
STATUSES = tuple(sorted(VALID_STATUSES))
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
    Row("claim", (PENDING, READY), CLAIMED, ("admission", "status"), (), "claim it"),
    Row(set_status_command(PENDING), STATUSES, PENDING, ("status",), (), "release it to pending"),
    Row(set_status_command(SUSPENDED), STATUSES, SUSPENDED, ("status",), (), "suspend it"),
) + tuple(
    Row(set_status_command(state), STATUSES, state, ("status",), (), f"set status {state}")
    for state in TERMINAL_STATES
)
COMMANDS = tuple(sorted({row.command for row in _ROWS}))
STAMPS = {
    "stamp": Stamp(PENDING, ADMISSION_PENDING, (), (PENDING, READY)),
    "draft-validate": Stamp(PENDING, ADMISSION_PENDING, (), (PENDING, READY, SUSPENDED)),
}

# This is executable metadata beside the guards that own the transitions.
# Sources are expanded one-per-row for the rendered view. A same-state event
# still appears because it changes a required lifecycle record.
#
# `caller` as an actor means the command line, so such a row's event has
# to be a routed subcommand; `tools/render_lifecycle.py` refuses one that
# is not. An event folded inside another command names that command here
# instead, which is why `issue` and `stamp` say `tickets.py do|judge` and
# `ready` and `claim` say `tickets.py dispatch`.
_LIFECYCLE_SPECS = (
    LifecycleSpec("issue", ("unissued",), PENDING, "tickets.py do|judge", "sealed ticket source", "contracts/work-item.md", "rules/topology.md"),
    LifecycleSpec("stamp", ("unsealed draft",), PENDING, "tickets.py do|judge", "sealed root generation", "contracts/work-item.md", "rules/topology.md"),
    LifecycleSpec("ready", (PENDING,), READY, "tickets.py dispatch", "admission receipt", "contracts/work-item.md", "rules/topology.md"),
    LifecycleSpec("claim", (PENDING, READY, CLAIMED), CLAIMED, "tickets.py dispatch", "admission receipt; stale-claim proof when already claimed", "contracts/work-item.md", "rules/delegation.md"),
    LifecycleSpec("dispatch-open", ("ready / no dispatch state", "ready / ended attempts", "claimed / ended attempts", "suspended / ended attempts"), "claimed / live attempt", "caller", "assignment seal and admission receipt", "contracts/dispatch.md", "rules/delegation.md"),
    LifecycleSpec("dispatch-commit", ("claimed / live attempt",), "claimed / live attempt + generic record", "caller", "live dispatch attempt record", "contracts/dispatch.md", "rules/delegation.md"),
    LifecycleSpec("dispatch", ("ready / no dispatch state", "ready / ended attempts", "claimed / live attempt", "claimed / ended attempts", "suspended / ended attempts"), "claimed / launched", "caller", "assignment seal, admission receipt, and the established workspace", "contracts/dispatch.md", "rules/delegation.md"),
    LifecycleSpec("result", ("claimed / launched",), "claimed / launched + result record", "dispatched child", "committed launch record and the attempt's seal, dispatch id, and owner", "contracts/result.md", "rules/verification.md"),
    LifecycleSpec("dispatch-outcome", ("claimed / launched", "claimed / launched + result records"), "claimed / outcome committed", "dispatched child or relaying caller", "committed launch record and the attempt's seal, dispatch id, and owner", "contracts/dispatch.md", "rules/delegation.md"),
    LifecycleSpec("dispatch-retire", ("claimed / live attempt",), "claimed / retired attempt", "caller", "live dispatch attempt record", "contracts/dispatch.md", "rules/delegation.md"),
    LifecycleSpec("dispatch-replace", ("claimed / live or expired attempt",), "claimed / replaced attempt + new live attempt", "caller", "predecessor attempt and assignment seal; a declared supersession inside its lease", "contracts/dispatch.md", "rules/delegation.md"),
) + tuple(
    LifecycleSpec("dispatch-join", ("claimed / outcome committed",), f"{state} / retired attempt", "caller", "reserved outcome record", "contracts/dispatch.md", "rules/delegation.md")
    for state in (SUSPENDED,) + tuple(TERMINAL_STATES)
) + tuple(
    # Not a legacy path, though an earlier rendering called it one: these are
    # the only transitions a ticket that was never dispatched can take, and
    # `_set_status_under_run_lock` refuses once `dispatch_v1` records real
    # execution (`dispatch-join-required`). Marking an issued-but-undispatched
    # ticket blocked has no other route, so naming the majority of the table
    # "legacy" told every cold reader the opposite of the truth. The second
    # admissible shape is a lifecycle that never began -- one attempt, ended,
    # carrying nothing but its own lifecycle records -- which otherwise owns
    # a status it has no join and no retirement left to release.
    LifecycleSpec(
        set_status_command(state),
        STATUSES,
        state,
        "caller",
        "no dispatch-v1 record, or a lone attempt that never launched",
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
