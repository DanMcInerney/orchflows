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
CALLABLE_EXECUTORS = (
    "orch-execute",
    "orch-check",
    "orch-slice",
    "orch-outline",
)

EXECUTOR_REGISTRY = {
    "orch-execute": {"role": "worker", "requires_pack": True},
    "orch-check": {"role": "planner", "requires_pack": True},
    "orch-slice": {"role": "planner"},
    "orch-outline": {"role": "planner"},
}

# A superseded verb and the successor that replaced it, per
# ``rules/delegation.md`` 8: no dispatch may revive a superseded skill
# binding.  The refusal names the successor so a caller holding the old
# name has a mechanical remedy instead of a registry list to guess from.
# A successor that is itself a registered verb is offered as a binding;
# any other successor is a mechanism, named as the remedy it is.
SUPERSEDED_EXECUTORS = {
    "orch-spec": "orch-outline",
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
    """Return whether ``executor`` is one of the four callable verbs."""

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
