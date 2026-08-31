---
name: orch-frontier
description: Execute ticket runs by rolling frontier dispatch — every ready ticket in flight. Use for single tickets and dependency graphs.
role: none
---

Require: acyclic `tickets.py` run graph and caller bound.

Choose assigned-name/dispatch-id/lease; two commands per ticket:

Outbound: `tickets.py dispatch <run> <id> --by <name> --dispatch-id <id>
--lease-expires-at <absolute-iso> --host <host>`.
One transaction admits the ticket, establishes the workspace or evidence-store
([workspaces](references/workspaces.md)), opens the attempt, commits the
packet. Its result carries a
`launch`; invoke it verbatim with its exact fields
([profiles](references/profiles.md)). Hand the response `.packet` to the child
through `--packet-file <path>`; its first filed record is its acceptance.

`tickets.py land <run> <id> --assignment-seal <seal> --dispatch-id <id>
--outcome-record-id outcome --by <join-name> [--outcome-file <path|->]` imports
the outcome, joins it, retires the derived worktree, and reports the frontier
every joined outcome makes ready. Read that rather than deriving one.

Ordinary review creates `<id>.check`
with `checker-stage`, dispatches one distinct read-only `orch-check` dispatch,
lands its return, then anchors the joined stage with `check <run> <id> --stage
<id>.check`. `GatePlan` carries fixed artifact, Goal, Context, executor
evidence. Then:

- an accepted checked target invokes `gate <run> <id>` for one separate repair ticket and
  fresh verification without another critique;
- a clean checked target closes without repair; and
- a gate-deferred root invokes `gate <run> <root>` for its composite gate,
  never `checker-stage` ([verification](../../../rules/verification.md) §7).

Replay to the same recorded child; `dispatch-retire`/`dispatch-replace`;
never extend leases.

For [topology](../../../rules/topology.md) §5 graphs, `GatePlan` fixes artifact,
pack, workspace, isolation `none`, and lens order. Critiques run parallel;
[work-item](../../../contracts/work-item.md)'s review-chain stages follow in
order, each naming its predecessor digest.

Dispatch requires sealed admission matching
`root_generation`, `cut_generation`, and `assignment_seal`.
Refuse draft/validated-only, stale, missing, mismatched, or substituted
generations. Only work sealed by `tickets.py seal` is dispatched as it forms.
Accept each return once through `orch-integrate`; `suspended` parks; others
grade isolation and integrate per pack. `orch-integrate` owns actual candidate diffs;
its binding adjudicates overlap. Ordinary Git conflicts remain there for
resolution, outside frontier scheduling.
`orch-integrate` owns one shared-artifact finalization after all candidate
joins; it records fixed joined identity. When returns integrate
and checker/gate is closed, run the standards owner's required checks exactly once at the accepted terminal identity; record revision, not merge batch. Red suite blocks completion.

Watch per [profiles](references/profiles.md); recompute on outcomes, tickets,
suspensions, or transport silence. `bound-check` parks overdue motionless work
as `suspended` through `land`, Handoff naming bound
and `last_motion_at`; motion reports `over-bound`. Promote with `tickets.py ready`;
report `skipped` and blockers. Dependents wait; unsatisfied exclusions exit with
remainder.
Quiescent: read `successors.md`; when a `planned` entry exists and run is
complete, return its trigger and the predecessor's accepted `## Result`
identity to the materialization owner, who replaces it
([work-item](../../../contracts/work-item.md#roots-decomposition-and-integration)).
Otherwise exit; `limited` when bounds leave tickets open.

Never: batch ready tickets; hide blocked subtrees as successes; re-order the
graph to dodge failure.

Return: status; ticket result identities; verified terminal state; required
successor materialization; open remainder and blockers.
