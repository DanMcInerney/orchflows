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
the executor. Each ticket takes one outside-independence path. In a
single-ticket run, pre-existing-only acceptance ends with its falsifiable
oracles; only an unchecked `independence: checker` ticket with an
`authored-here` oracle gets the claim's `--executor orch-critique` checker
packet, never for gate-deferred or already checked tickets. Where a
checker invalidates a judged oracle, dispatch `--executor orch-verify`;
otherwise re-run invalidated deterministic oracles at the checked identity
([verification](../../../rules/verification.md) §10).

A sealed ordered-bundle gate critique gets one fresh closer and one sequence
packet for orch-critique then orch-repair, without evaluator redispatch.
Dispatch gate.verify once in another fresh child at final identity; reuse
neither context.

V2 readiness/claim/packet require `root_generation`, `cut_generation`, and
`assignment_seal` resolving to one sealed snapshot and validation receipt.
Refuse draft/validated-only, stale, missing, mismatched, or substituted
generations. An accepted `tickets.py amendment-request` disposition recomputes
the frontier; only work newly sealed by `tickets.py seal` proceeds. The absence
of v2 fields means v1. A root cut reader is the exception: take it with three
or more `<id>.NN` or after a cutcheck advisory;
units stay `pending` until `checked_by` and this engine's `cutcheck.py`
re-verification exits 0. Below that threshold cutcheck accepts the cut alone.
Accept each return once through `orch-integrate`; `suspended` parks; others
grade isolation and integrate per pack; conflicts use its binding.
A lane runs its ticket's own oracles, nothing wider. After every return is
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
completion ([work-item](../../../contracts/work-item.md#root-ticket)).
Otherwise exit; `limited` when bounds leave tickets open.

Never: batch ready tickets; hide blocked subtrees as successes; re-order the
graph to dodge failure.

Return: status; ticket result identities; verified terminal state; required
successor materialization; open remainder and blockers.
