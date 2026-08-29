"""The closed callable tier and review discriminators.

Ticket executors are deliberately a small, explicit vocabulary.  Pack data
selects craft and stages; it never adds a callable.  Scripts remain an
explicit ``script:`` escape hatch for mechanical state operations and are
validated by their path rather than this registry.
"""

from __future__ import annotations


# Keep this order stable: it is the user-facing registry artifact and is
# rendered in refusal messages and help/test projections.
CALLABLE_EXECUTORS = (
    "orch-execute",
    "orch-check",
    "orch-decompose",
    "orch-integrate",
    "orch-frontier",
    "orch-loop",
    "orch-spec",
)

EXECUTOR_REGISTRY = {
    "orch-execute": {"role": "worker", "consumer": "execute", "requires_pack": True},
    "orch-check": {"role": "planner", "consumer": "check", "requires_pack": True},
    "orch-decompose": {"role": "planner", "consumer": None},
    "orch-integrate": {"role": "none", "consumer": None},
    "orch-frontier": {"role": "none", "consumer": None},
    "orch-loop": {"role": "none", "consumer": None},
    "orch-spec": {"role": "planner", "consumer": None},
}

REVIEW_KINDS = ("critique", "repair", "verify")


def executor_registered(executor: str) -> bool:
    """Return whether ``executor`` is one of the seven callable verbs."""

    return str(executor or "").strip().strip("`").strip() in EXECUTOR_REGISTRY


def executor_refusal(executor: str) -> str:
    """Return one stable, actionable refusal for an unknown callable."""

    value = str(executor or "").strip().strip("`").strip() or "<missing>"
    names = ", ".join(CALLABLE_EXECUTORS)
    return f"executor-unregistered: '{value}' is not a registered callable; expected one of: {names}"


__all__ = (
    "CALLABLE_EXECUTORS",
    "EXECUTOR_REGISTRY",
    "REVIEW_KINDS",
    "executor_registered",
    "executor_refusal",
)
