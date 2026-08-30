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
    "orch-decompose",
    "orch-integrate",
    "orch-frontier",
    "orch-loop",
    "orch-outline",
)

EXECUTOR_REGISTRY = {
    "orch-execute": {"role": "worker", "consumer": "execute", "requires_pack": True},
    "orch-check": {"role": "planner", "consumer": "check", "requires_pack": True},
    "orch-decompose": {"role": "planner", "consumer": None},
    "orch-integrate": {"role": "none", "consumer": None},
    "orch-frontier": {"role": "none", "consumer": None},
    "orch-loop": {"role": "none", "consumer": None},
    "orch-outline": {"role": "planner", "consumer": "outline"},
}

# A superseded verb and the successor that replaced it, per
# ``rules/delegation.md`` 8: no dispatch may revive a superseded skill
# binding.  The refusal names the successor so a caller holding the old
# name has a mechanical remedy instead of a registry list to guess from.
SUPERSEDED_EXECUTORS = {
    "orch-spec": "orch-outline",
}

REVIEW_KINDS = ("critique", "repair", "verify")


def executor_registered(executor: str) -> bool:
    """Return whether ``executor`` is one of the seven callable verbs."""

    return dequote(executor) in EXECUTOR_REGISTRY


def executor_successor(executor: str):
    """Return the successor verb for a superseded name, else ``None``."""

    return SUPERSEDED_EXECUTORS.get(dequote(executor))


def executor_refusal(executor: str) -> str:
    """Return one stable, actionable refusal for an unknown callable."""

    value = dequote(executor) or "<missing>"
    successor = SUPERSEDED_EXECUTORS.get(value)
    if successor:
        return (
            f"executor-unregistered: '{value}' was superseded by '{successor}'; "
            f"bind '{successor}' instead"
        )
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
