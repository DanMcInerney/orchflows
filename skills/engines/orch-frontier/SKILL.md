---
name: orch-frontier
description: Execute ticket runs by rolling frontier dispatch — every ready ticket in flight. Use for single tickets and dependency graphs.
role: none
---

Require: finite acyclic `tickets.py` run graph and root/caller bound.

Enter the pack workspace/evidence store, run `workspace.py start`, and retain
`workspace_path`, per
[workspace establishment](references/workspaces.md), before `dispatch-open`.
Choose unique
assigned name, dispatch id, and absolute lease. `tickets.py dispatch-open`
claims it; `tickets.py dispatch-packet` commits its
projection. Establish one
child under [delegation](../../../rules/delegation.md) §1–§2 and its
[role](../../../rules/roles.md) §4/[profile](references/profiles.md), and send
the response `.packet` through a file
or stdin; the child uses `dispatch-receive --file <path>` or `--file -`. Only
its durable accepted receipt, bound to its identity and authority,
applies the exact executor.

Each ticket takes one outside-independence path. An ordinary checker durably
makes one read-only `orch-critique` dispatch with fixed artifact,
Goal, Context, executor evidence, and one lens, then records the accepted set.
Accepted blockers move to a repair ticket, which invalidates
critique verdicts and is followed by fresh verification
([verification](../../../rules/verification.md) §7). Gate-deferred and already
checked tickets do not.

Transport silence replays the committed packet to the same recorded child. Abandon through join
or `dispatch-retire`; replace through `dispatch-replace`. Never extend leases
or infer abandonment.

For [topology](../../../rules/topology.md) §5 graphs, `GatePlan` fixes artifact,
root pack, workspace, isolation `none`, and lens order. Parallel critiques feed
`CritiqueAdjudication`; `RepairOutcome` binds the repair or empty-set proof;
fresh `Verification` evaluates it. Each stage names its predecessor digest.

`dispatch-open` and `dispatch-packet` require sealed admission matching
`root_generation`, `cut_generation`, and `assignment_seal`.
Refuse draft/validated-only, stale, missing, mismatched, or substituted
generations. Recompute the frontier after lifecycle transitions; only work
sealed by `tickets.py seal` proceeds.
Accept each return once through `orch-integrate`; `suspended` parks; others
grade isolation and integrate per pack; conflicts use its binding.
Commit unstreamed closing evidence as `outcome`; join consumes it only after
accepted receipt.
A lane runs its own chosen proof methods, nothing wider. After every return is
integrated and its required checker/gate is closed, run the standards
owner's required checks exactly once at the accepted terminal identity and
record its revision, not per merge batch. A red terminal suite blocks
completion.

Watch per [profiles](references/profiles.md); recompute on outcomes, tickets,
suspensions, or stale claims. `bound-check` parks overdue work without
post-bound motion as `suspended` through `dispatch-join`, Handoff naming bound and
`last_motion_at`; motion reports `over-bound`. Promote with `tickets.py ready`;
report `skipped` and terminal blockers. Suspended tickets retain claimant
Handoff observations after their attempts retire; dependents wait. Unsatisfied
exclusions exit with the remainder. Quiescent: read
`successors.md`. If a `planned` entry exists and the run is complete, return
the successor trigger and predecessor's accepted `## Result` identity to the
plan's materialization owner, who materializes and replaces the plan before
completion ([work-item](../../../contracts/work-item.md#roots-decomposition-and-integration)).
Otherwise exit; `limited` when bounds leave tickets open.

Never: batch ready tickets; hide blocked subtrees as successes; re-order the
graph to dodge failure.

Return: status; ticket result identities; verified terminal state; required
successor materialization; open remainder and blockers.
