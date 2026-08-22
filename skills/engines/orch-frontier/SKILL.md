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
one outside-independence path. Only for unchecked `independence: checker`
with an `authored-here` oracle, dispatch `orch-critique` on the same claim via
the `--executor orch-critique` checker packet. For gate-deferred, already
checked, or pre-existing-only tickets, never emit it. Then, where its pass invalidates an entry whose oracle is judged, dispatch
that packet's `--executor orch-verify` form; else re-run the
invalidated deterministic oracles at the checked identity here, the
rest covered ([rules/verification.md](../../../rules/verification.md) §10).
For v2, the exact sealed generation is required for readiness, claim, and
packet emission: the ticket's `root_generation`, `cut_generation`, and
`assignment_seal` must all resolve to the same sealed run-state snapshot and
its validation receipt. Refuse a draft, merely validated, stale, missing, or
mismatched generation; never substitute the latest generation for the one the
packet names. Recompute the frontier after an accepted amendment disposition
so only a newly validated and sealed generation can proceed.
The absence of v2 fields means v1.
Its existing ready, claim, packet, receipt, and cohort semantics remain
unchanged.
A root cut reader is the exception: take it with three or more `<id>.NN` or
after a cutcheck advisory; units stay `pending` until `checked_by` and this
engine's `cutcheck.py` re-run — the re-verification — exits 0. Below that
threshold cutcheck accepts the cut alone.
Accept every return once through `orch-integrate`; `suspended` parks it, any
other grades isolation and integrates per the pack, conflicts through its
binding. After each merge batch run the
standards owner's required checks on the integrated tip, the run's notes
carrying the tip's revision: a lane runs its ticket's own oracles,
nothing wider, its green provisional until the tip's, and a red
tip blocks the next dispatch but its repair's.

Watch per [profiles](references/profiles.md); recompute on results, new
tickets, suspension, or stale claims. Promote via `tickets.py ready`, dispatch
at once, and report `skipped`; block a pending ticket behind any dependency's
other terminal status, naming it. Parked claims stay live and dependents wait;
an unsatisfied exclusion exits with the parked remainder. When no ticket is `ready` or
`pending` and no dispatch is live, read the run's durable `successors.md` when
present. If it carries a `planned` entry and this run completed, per
[work-item.md](../../../contracts/work-item.md#root-ticket), return the
successor trigger with the predecessor's accepted `## Result` identity to the
plan's materialization owner; it materializes the successor and replaces the
plan before the request is reported finished. Otherwise exit; `limited` when
the bound is spent with tickets open.

Never: hold a ready ticket back to batch it; hide a blocked
subtree in a summary of successes; re-order the graph to dodge a
failure.

Return: status; per-ticket results by identity; the graph's terminal
state as verification; successor trigger and materialized successor run when
`successors.md` requires one; the open remainder with what blocks it.
