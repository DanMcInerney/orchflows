"""The closed callable tier and review discriminators.

Ticket executors are deliberately a small, explicit vocabulary.  Pack data
selects craft and stages; it never adds a callable.  Scripts remain an
explicit ``script:`` escape hatch for mechanical state operations and are
validated by their path rather than this registry.
"""

from __future__ import annotations

try:
    from scripts.tickets_markdown import dequote
except ImportError:
    from tickets_markdown import dequote


# Keep this order stable: it is the user-facing registry artifact and is
# rendered in refusal messages and help/test projections.
#
# `orch-slice` stays registered through this wave on the driver's own
# ruling (2026-08-31, wave-2 arbiter): admission refuses it the moment it
# retires, but the decomposed-root machinery ROOT_EXECUTOR discriminates
# (scripts/tickets_format.py, fenced from this ticket) is still live and
# consumes it across ~12 script modules -- retiring the verb without first
# deleting that machinery is a hole, not a tombstone. `orch-slice`'s
# registration dies together with the decomposed-root concept in W3a; that
# unit removes this entry, moves it into SUPERSEDED_EXECUTORS pointing at
# `_PLANNING_DO_REMEDY` below, and updates `orch-decompose`'s successor to
# match. Until then, treat this comment as the marker.
CALLABLE_EXECUTORS = (
    "orch-do",
    "orch-judge",
    "orch-slice",
)

# ``files_findings`` marks the verb whose product is a findings file rather
# than an artifact: it is what the launch prompt reads to ask for the second
# verbatim machine line, so the judging verb is named once here instead of
# in the prompt composer.
EXECUTOR_REGISTRY = {
    "orch-do": {"role": "worker", "requires_pack": True},
    "orch-judge": {"role": "planner", "requires_pack": True, "files_findings": True},
    "orch-slice": {"role": "planner"},
}

# `orch-outline` retired this wave toward this living remedy: a planning
# `do` -- goal a frozen root or a call plan -- reading the pack craft's
# Outline and Spec fields sections in `do`'s stead. Its own predecessor
# intake verb (`orch-spec`) points at the same remedy rather than at the
# retired name that once stood between them, so no refusal chains through
# a name that itself refuses. `orch-slice`'s own Slicing section stays
# `orch-slice`'s until W3a folds it in alongside the verb's retirement.
_PLANNING_DO_REMEDY = (
    "a planning `do` reading the pack craft's Outline and Spec fields "
    "sections"
)

# A superseded verb and the successor that replaced it, per
# ``rules/delegation.md`` 8: no dispatch may revive a superseded skill
# binding.  The refusal names the successor so a caller holding the old
# name has a mechanical remedy instead of a registry list to guess from.
# A successor that is itself a registered verb is offered as a binding;
# any other successor is a mechanism, named as the remedy it is.
SUPERSEDED_EXECUTORS = {
    "orch-execute": "orch-do",
    "orch-check": "orch-judge",
    "orch-outline": _PLANNING_DO_REMEDY,
    "orch-spec": _PLANNING_DO_REMEDY,
    "orch-decompose": "orch-slice",
    "orch-loop": "the ticket `loop` field, driven by tickets.py loop-arm | loop-evaluate | loop-advance",
    "orch-frontier": (
        "the driver loop is mechanical: `tickets.py dispatch` emits the launch, "
        "`tickets.py land` evaluates done, integrates, and prints the ready frontier"
    ),
    "orch-integrate": (
        "land evaluates the done predicate; a predicate-less ticket is accepted "
        "by the driver with `land --status`"
    ),
}

REVIEW_KINDS = ("critique", "repair")


def executor_registered(executor: str) -> bool:
    """Return whether ``executor`` is one of the registered callable verbs."""

    return dequote(executor) in EXECUTOR_REGISTRY


def executor_successor(executor: str):
    """Return the successor verb for a superseded name, else ``None``."""

    return SUPERSEDED_EXECUTORS.get(dequote(executor))


def executor_refusal(executor: str) -> str:
    """Return one stable, actionable refusal for an unknown callable."""

    value = dequote(executor) or "<missing>"
    successor = SUPERSEDED_EXECUTORS.get(value)
    if successor and successor in EXECUTOR_REGISTRY:
        return (
            f"executor-unregistered: '{value}' was superseded by '{successor}'; "
            f"bind '{successor}' instead"
        )
    if successor:
        return f"executor-unregistered: '{value}' was superseded by {successor}"
    names = ", ".join(CALLABLE_EXECUTORS)
    return f"executor-unregistered: '{value}' is not a registered callable; expected one of: {names}"


__all__ = (
    "CALLABLE_EXECUTORS",
    "EXECUTOR_REGISTRY",
    "SUPERSEDED_EXECUTORS",
    "REVIEW_KINDS",
    "executor_registered",
    "executor_successor",
    "executor_refusal",
)
