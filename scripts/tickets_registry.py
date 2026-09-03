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
# `orch-slice` retired in W4a together with `tickets.py instantiate`, its
# only minter of decomposed roots: with nothing left to mint one, the
# decomposed-root discriminator ROOT_EXECUTOR (scripts/tickets_format.py)
# is gone too, and the two minting commands are the whole callable tier.
CALLABLE_EXECUTORS = (
    "orch-do",
    "orch-judge",
)

# ``files_findings`` marks the verb whose product is a findings file rather
# than an artifact: it is what the launch prompt reads to ask for the second
# verbatim machine line, so the judging verb is named once here instead of
# in the prompt composer.
EXECUTOR_REGISTRY = {
    "orch-do": {"role": "worker", "requires_pack": True},
    "orch-judge": {"role": "planner", "requires_pack": True, "files_findings": True},
}

# `orch-outline` and `orch-slice` both retired toward this living remedy: a
# planning `do` -- goal a frozen root or a cut -- making toward the pack
# craft's `## Lens` entry for that kind in `do`'s stead. Their own
# predecessor intake verbs (`orch-spec`, `orch-decompose`) point at the same
# remedy rather than at a retired name that itself refuses, so no refusal
# chains through a name with no binding left to offer.
_PLANNING_DO_REMEDY = (
    "a planning `do` making a `root` or `cut` toward the pack craft's "
    "`## Lens` entry for that kind"
)

# A superseded verb and the successor that replaced it, per
# ``rules/delegation.md`` 8: no dispatch may revive a superseded skill
# binding.  The refusal names the successor so a caller holding the old
# name has a mechanical remedy instead of a registry list to guess from.
# A successor that is itself a registered verb is offered as a binding;
# any other successor is a mechanism, named as the remedy it is.
#
# Each entry's trailing comment dates its retirement: the commit (short
# hash) that first added the name to this dict, from ``git log --follow``
# over this file -- real history, not a guess.  None of the current
# entries predate this registry: this file's own creation commit
# (a68eeabe, 2026-08-29) held no ``SUPERSEDED_EXECUTORS`` dict at all, so
# every name below was retired after the registry already existed to
# record it; a future entry whose retirement predates the registry says
# so here instead of dating a commit that only re-recorded it.
SUPERSEDED_EXECUTORS = {
    "orch-execute": "orch-do",  # retired-on 2026-08-31 (34341e5d)
    "orch-check": "orch-judge",  # retired-on 2026-08-31 (34341e5d)
    "orch-outline": _PLANNING_DO_REMEDY,  # retired-on 2026-08-31 (34341e5d)
    "orch-spec": _PLANNING_DO_REMEDY,  # retired-on 2026-08-30 (fa7c2fa1)
    "orch-slice": _PLANNING_DO_REMEDY,  # retired-on 2026-08-31 (338c1678)
    "orch-decompose": _PLANNING_DO_REMEDY,  # retired-on 2026-08-31 (15bea6aa)
    "orch-loop": (  # retired-on 2026-08-30 (30651e8f)
        "a prose loop in the calling workflow over repeated `do` callables, with "
        "the ticket `done` predicate evaluated by tickets.py land"
    ),
    "orch-frontier": (  # retired-on 2026-08-31 (17f04765)
        "the driver loop is mechanical: `tickets.py dispatch` emits the launch, "
        "`tickets.py land` evaluates done, integrates, and prints the ready frontier"
    ),
    "orch-integrate": (  # retired-on 2026-08-31 (17f04765)
        "land evaluates the done predicate; a predicate-less ticket is accepted "
        "by the driver with `land --status`"
    ),
}


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
    "executor_registered",
    "executor_successor",
    "executor_refusal",
)
