---
name: orch-frontier
description: Execute a ticket dependency graph by rolling frontier dispatch — every ready ticket in flight. Use whenever items have dependency edges.
role: none
---

Require: a finite acyclic `tickets.py` run graph and its root/caller bound.

Dispatch each ticket whose `depends_on` are `complete`, one lane. Claim
through `tickets.py claim`; take its packet (refusal is a cut defect); spawn
one fresh child under [delegation](../../../rules/delegation.md) §1–§2, role per
[roles](../../../rules/roles.md) §4 and host depth per
[profiles](references/profiles.md), applying its executor. Each ticket takes
one outside-independence path. Only unchecked `independence: checker` tickets
with an `authored-here` oracle get the same claim's `--executor orch-critique`
checker packet, and never for gate-deferred, already checked, or
pre-existing-only tickets. Then, where its pass invalidates a judged oracle,
dispatch its `--executor orch-verify` form;
otherwise re-run invalidated deterministic oracles at the checked identity
([verification](../../../rules/verification.md) §10).

A sealed ordered-bundle gate critique gets one fresh reviewer child and its
sequence packet without evaluator redispatch. Dispatch gate.verify once in
another fresh child over the final identity; reuse neither across tickets.

V2 readiness, claim, and packet require `root_generation`,
`cut_generation`, and `assignment_seal` to resolve to one sealed snapshot and
validation receipt. Refuse draft, merely validated, stale, missing,
mismatched, or latest-substituted generations. After an accepted `tickets.py
amendment-request` disposition, recompute the frontier; only what `tickets.py
seal` newly sealed proceeds. The absence of v2 fields means v1.
A root cut reader is the exception: take it with three or more `<id>.NN` or after a
cutcheck advisory; units stay `pending` until `checked_by` and this engine's
`cutcheck.py` re-verification exits 0. Below that threshold cutcheck accepts
the cut alone.
Accept every return once through `orch-integrate`; `suspended` parks, any other
grades isolation and integrates per its pack, conflicts through its binding.
An errand run authored through `tickets.py errand` runs the ticket's scoped
oracles and its one lawful checker, nothing wider. Once every return is
integrated and derived closure is closed, run the standards owner's required
checks exactly once at the accepted terminal identity and record its revision.
For every non-errand run, keep the existing policy: After each merge batch run
the standards owner's required checks on the integrated tip, the run's notes
carrying the tip's revision. A lane runs its ticket's own oracles, nothing
wider; its green is provisional until the tip's, and a red tip blocks the next
dispatch but its repair's.

Watch per [profiles](references/profiles.md); recompute on results, tickets,
suspensions, stale claims. Re-check through `bound-check`: overdue without
post-bound motion parks `suspended` through join, Handoff naming bound and
`last_motion_at`; motion reports `over-bound`. Promote via `tickets.py ready`
and dispatch; report `skipped` and terminal blockers. Parked claims stay live;
dependents wait; unsatisfied
exclusions exit with the remainder. At quiescence read `successors.md`. If a
`planned` entry exists and the run is complete, return the successor trigger
and predecessor's accepted `## Result` identity to the plan's materialization
owner, who materializes and replaces the plan before completion
([work-item](../../../contracts/work-item.md#root-ticket)). Otherwise exit;
`limited` when the bound leaves tickets open.

Never: hold a ready ticket to batch it; hide a blocked
subtree in a summary of successes; re-order the graph to dodge a
failure.

Return: status; per-ticket results by identity; the graph's terminal
state as verification; successor trigger and materialized run when
`successors.md` requires one; the open remainder with what blocks it.
