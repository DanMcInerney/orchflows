---
name: orch-frontier
description: Execute ticket runs by rolling frontier dispatch — every ready ticket in flight. Use for single tickets and dependency graphs.
role: none
---

Require: finite acyclic `tickets.py` run graph and root/caller bound.

Establish/enter the pack workspace, run `workspace.py start`, retain
`workspace_path`, per [workspace establishment](references/workspaces.md),
before `dispatch-open`. Choose unique
assigned name, dispatch id, and absolute lease. `tickets.py dispatch-open`
claims it; `tickets.py dispatch-packet` commits its
projection. Establish exactly one
child under [delegation](../../../rules/delegation.md) §1–§2 and its
[role](../../../rules/roles.md) §4/[profile](references/profiles.md), and send
the stored packet. The child runs `tickets.py dispatch-receive` against its
packet-bound identity and authority; only an accepted receipt applies the exact
executor. Each ticket takes one outside-independence path. A checker result gets
one `orch-critique` dispatch against its artifact, Goal, Context, evidence, and
lens, carrying the `GatePlan` `review_v1` ledger; gate-deferred and already
checked tickets do not. Accepted blockers move to
one separate repair ticket, which invalidates critique verdicts and is
followed by fresh verification
([verification](../../../rules/verification.md) §7).

Silence replays the committed packet to the same child. Abandon through join
or `dispatch-retire`; replace through `dispatch-replace`. Never extend leases
or infer abandonment.

For [topology](../../../rules/topology.md) §5 graphs, give each critique fresh
read-only context, then one repair and a fresh final-identity verify child.

`dispatch-open` and `dispatch-packet` require one sealed admission matching
`root_generation`, `cut_generation`, and `assignment_seal`.
Refuse draft/validated-only, stale, missing, mismatched, or substituted
generations. Recompute the frontier after lifecycle transitions; only work
newly sealed by `tickets.py seal` proceeds.
Accept each return once through `orch-integrate`; `suspended` parks; others
grade isolation and integrate per pack; conflicts use its binding.
At close, reference commits `outcome`; offline inline returns that envelope for
caller relay. No section record closes the attempt; join consumes only
`outcome`.
A lane runs its own chosen proof methods, nothing wider. After every return is
integrated and its required checker or run gate is closed, run the standards
owner's required checks exactly once at the accepted terminal identity and
record its revision, not per merge batch. A red terminal suite blocks
completion.

Watch per [profiles](references/profiles.md); recompute on outcomes, tickets,
suspensions, or stale claims. `bound-check` parks overdue work without
post-bound motion as `suspended` through `dispatch-join`, Handoff naming bound and
`last_motion_at`; motion reports `over-bound`. Promote with `tickets.py ready`;
report `skipped` and terminal blockers. Parked tickets retain claimant Handoff
observations but have retired attempts; dependents wait;
unsatisfied exclusions exit with the remainder. Quiescent: read
`successors.md`. If a `planned` entry exists and the run is complete, return
the successor trigger and predecessor's accepted `## Result` identity to the
plan's materialization owner, who materializes and replaces the plan before
completion ([work-item](../../../contracts/work-item.md#roots-decomposition-and-integration)).
Otherwise exit; `limited` when bounds leave tickets open.

Never: batch ready tickets; hide blocked subtrees as successes; re-order the
graph to dodge failure.

Return: status; ticket result identities; verified terminal state; required
successor materialization; open remainder and blockers.
