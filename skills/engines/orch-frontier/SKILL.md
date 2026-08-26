---
name: orch-frontier
description: Execute a ticket dependency graph by rolling frontier dispatch — every ready ticket in flight. Use whenever items have dependency edges.
role: none
---

Require: finite acyclic `tickets.py` run graph and root/caller bound.

Dispatch each ticket with complete `depends_on`. `tickets.py claim`; take its
packet (refusal is a cut defect); spawn a fresh child under
[delegation](../../../rules/delegation.md) §1–§2 and its
[role](../../../rules/roles.md) §4/[profile](references/profiles.md), applying
the executor. Each ticket takes one outside-independence path. Only unchecked
`independence: checker` tickets with an `authored-here` oracle get the claim's
`--executor orch-critique` packet. Exclude gate-deferred, checked, and
pre-existing-only tickets. If that pass invalidates a judged oracle, dispatch
`--executor orch-verify`; otherwise re-run invalidated deterministic oracles
at the checked identity
([verification](../../../rules/verification.md) §10).

A sealed ordered-bundle gate critique gets one fresh reviewer and sequence
packet without evaluator redispatch. Dispatch gate.verify once in another
fresh child at final identity; reuse neither.

V2 readiness, claim, and packet require `root_generation`,
`cut_generation`, and `assignment_seal` to resolve to one sealed snapshot and
validation receipt. Refuse draft, merely validated, stale, missing, mismatched,
or substituted generations. After accepting a `tickets.py amendment-request`
disposition, recompute; only work newly sealed by `tickets.py seal` proceeds. The absence of v2
fields means v1. A root cut reader is the exception: take it with three or
more `<id>.NN` or after a cutcheck advisory;
units stay `pending` until `checked_by` and this engine's `cutcheck.py`
re-verification exits 0. Below that threshold cutcheck accepts the cut alone.
Accept each return once through `orch-integrate`; `suspended` parks; others
grade isolation and integrate per pack; conflicts use its binding.
An errand run authored through `tickets.py errand` runs the ticket's scoped
oracles and its one lawful checker, nothing wider. Once every return integrates
and derived closure is closed, run the standards owner's required checks
exactly once at the accepted terminal identity and record its revision.
For every non-errand run, keep the existing policy: After each merge batch run
the standards owner's required checks on the integrated tip; run notes record
its revision. A lane runs only its ticket's oracles; green is provisional until
the tip's, and red blocks the next dispatch but its repair's.

Watch per [profiles](references/profiles.md); recompute on results, tickets,
suspensions, or stale claims. `bound-check` parks overdue work without
post-bound motion as `suspended` through join, Handoff naming bound and
`last_motion_at`; motion reports `over-bound`. Promote with `tickets.py ready`;
report `skipped` and terminal blockers. Parked claims stay live; dependents
wait; unsatisfied exclusions exit with the remainder. At quiescence read
`successors.md`. If a `planned` entry exists and the run is complete, return
the trigger and predecessor's accepted `## Result` identity to its
materialization owner, who materializes and replaces the plan before
completion ([work-item](../../../contracts/work-item.md#root-ticket)).
Otherwise exit; `limited` when bounds leave tickets open.

Never: batch ready tickets; hide blocked subtrees as successes; re-order the
graph to dodge failure.

Return: status; ticket result identities; verified terminal state; required
successor materialization; open remainder and blockers.
