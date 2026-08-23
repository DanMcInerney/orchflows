---
name: orch-frontier
description: Execute a ticket dependency graph by rolling frontier dispatch — every ready ticket in flight. Use whenever items have dependency edges.
role: none
---

Require: one finite acyclic run ticket graph issued through `tickets.py`,
plus its bound from the root ticket or caller.

Dispatch every ticket whose `depends_on` are `complete`, one lane each.
Claim through `tickets.py claim`; take its packet (refusal is a cut defect);
spawn one fresh child under [delegation](../../../rules/delegation.md) §1–§2,
role per [roles](../../../rules/roles.md) §4, host depth per
[profiles](references/profiles.md), applying its executor. Each ticket takes
one outside-independence path: only for unchecked `independence: checker`
with an `authored-here` oracle, dispatch the same claim's `--executor
orch-critique` checker packet, and never for gate-deferred, already checked,
or pre-existing-only tickets. Then, where its pass invalidates a
judged oracle, dispatch that packet's `--executor orch-verify` form; otherwise
re-run invalidated deterministic oracles at the checked identity here
([verification](../../../rules/verification.md) §10).

For v2, readiness, claim, and packet require that `root_generation`,
`cut_generation`, and `assignment_seal` resolve to one sealed run-state
snapshot and validation receipt. Refuse draft, merely
validated, stale, missing, or mismatched generations; never substitute the
latest. After an accepted amendment disposition, recompute the frontier:
only a newly validated, sealed generation proceeds. The absence of v2 fields
means v1.
A root cut reader is the exception: take it with three or more `<id>.NN` or
after a cutcheck advisory; units stay `pending` until `checked_by` and this
engine's `cutcheck.py` re-run, the re-verification, exits 0. Below that
threshold cutcheck accepts the cut alone.
Accept every return once through `orch-integrate`; `suspended` parks it, any
other grades isolation and integrates per the pack, conflicts through its
binding. After each merge batch run the
standards owner's required checks on the integrated tip, the run's notes
carrying the tip's revision. A lane runs its ticket's own oracles, nothing
wider; its green provisional until the tip's, and a red tip blocks the next
dispatch but its repair's.

Watch per [profiles](references/profiles.md); recompute on results, tickets,
suspension, or stale claims. Re-checks run `bound-check`: overdue
without motion since the bound parks `suspended` through the join-side status
path, Handoff naming bound, `last_motion_at`; overdue with motion reports
`over-bound`. Promote via `tickets.py ready`, dispatch at once,
report `skipped`; name terminal dependencies blocking pending tickets.
Parked claims remain live, dependents wait, unsatisfied exclusions exit
with the remainder. At quiescence read durable `successors.md`. With a
`planned` entry and the run complete, return the successor trigger plus the
predecessor's accepted `## Result` identity to the plan's materialization
owner, who materializes it and replaces the plan before completion
is reported
([work-item](../../../contracts/work-item.md#root-ticket)). Otherwise exit;
`limited` when the bound leaves tickets open.

Never: hold a ready ticket back to batch it; hide a blocked
subtree in a summary of successes; re-order the graph to dodge a
failure.

Return: status; per-ticket results by identity; the graph's terminal
state as verification; successor trigger and materialized run when
`successors.md` requires one; the open remainder with what blocks it.
