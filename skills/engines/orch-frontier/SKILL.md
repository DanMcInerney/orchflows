---
name: orch-frontier
description: Execute ticket runs by rolling frontier dispatch — every ready ticket in flight. Use for single tickets and dependency graphs.
role: none
---

Require: finite acyclic `tickets.py` run graph and root/caller bound.

Dispatch each ticket with complete `depends_on`. `tickets.py claim`; take its
packet (refusal is a cut defect); spawn a fresh child under
[delegation](../../../rules/delegation.md) §1–§2 and its
[role](../../../rules/roles.md) §4/[profile](references/profiles.md), applying
the executor. Each ticket takes one outside-independence path. An unchecked
`independence: checker` ticket gets one read-only `--executor orch-critique`
packet against its fixed artifact, Goal, Context, executor evidence, and lens;
gate-deferred and already checked tickets do not. Accepted blockers move to
one separate repair ticket, which invalidates critique verdicts and is
followed by fresh verification
([verification](../../../rules/verification.md) §7).

For a decomposed root with at least two executor results, regardless of
dependency order, the one mechanically graph-triggered gate gives each sealed
critique a fresh read-only context. Their accepted blockers feed at most one
repair ticket. Dispatch gate.verify once in another fresh child at final
identity; reuse no critique or repair context.

Readiness, claim, and packet require `root_generation`, `cut_generation`, and
`assignment_seal` resolving to one sealed snapshot and validation receipt.
Refuse draft/validated-only, stale, missing, mismatched, or substituted
generations. Recompute the frontier after lifecycle transitions; only work
newly sealed by `tickets.py seal` proceeds.
Accept each return once through `orch-integrate`; `suspended` parks; others
grade isolation and integrate per pack; conflicts use its binding.
A lane runs its own chosen proof methods, nothing wider. After every return is
integrated and its required checker or run gate is closed, run the standards
owner's required checks exactly once at the accepted terminal identity and
record its revision, not per merge batch. A red terminal suite blocks
completion.

Watch per [profiles](references/profiles.md); recompute on results, tickets,
suspensions, or stale claims. `bound-check` parks overdue work without
post-bound motion as `suspended` through join, Handoff naming bound and
`last_motion_at`; motion reports `over-bound`. Promote with `tickets.py ready`;
report `skipped` and terminal blockers. Parked claims stay live; dependents
wait; unsatisfied exclusions exit with the remainder. Quiescent: read
`successors.md`. If a `planned` entry exists and the run is complete, return
the successor trigger and predecessor's accepted `## Result` identity to the
plan's materialization owner, who materializes and replaces the plan before
completion ([work-item](../../../contracts/work-item.md#roots-decomposition-and-integration)).
Otherwise exit; `limited` when bounds leave tickets open.

Never: batch ready tickets; hide blocked subtrees as successes; re-order the
graph to dodge failure.

Return: status; ticket result identities; verified terminal state; required
successor materialization; open remainder and blockers.
