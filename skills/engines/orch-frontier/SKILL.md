---
name: orch-frontier
description: Execute ticket runs by rolling frontier dispatch — every ready ticket in flight. Use for single tickets and dependency graphs.
role: none
---

Require: acyclic `tickets.py` run graph and caller bound.

Choose assigned-name/dispatch-id/lease; invoke `tickets.py dispatch` per
ticket. The facade atomically readies, establishes pack workspace/evidence-store, opens
attempt, and projects its packet; it retains `workspace_path` and returns
packet or refusal. Establish the same recorded child under
[delegation](../../../rules/delegation.md) §1–§2 and its
[role](../../../rules/roles.md) §4/[profile](references/profiles.md); send
response `.packet` via file/stdin; the child uses
`dispatch-receive --file <path>` or `--file -`. Only its durable accepted
receipt bound to identity and authority applies the exact executor.

Ordinary review creates `<id>.check`
with `checker-stage`, dispatches one distinct read-only `orch-check` dispatch through
packet, receipt, outcome, and join, then runs `check <run> <id> --stage
<id>.check`. `GatePlan` carries fixed artifact, Goal, Context, executor evidence,
Result, and Verification. Then:

- an accepted checked target invokes `gate <run> <id>` for one separate repair ticket and
  fresh verification without another critique;
- a clean checked target closes without repair; and
- a gate-deferred root invokes `gate <run> <root>` for its composite gate,
  never `checker-stage` ([verification](../../../rules/verification.md) §7).

Replay; `dispatch-retire`/`dispatch-replace`; never extend leases.

For [topology](../../../rules/topology.md) §5 graphs, `GatePlan` fixes artifact,
pack, workspace, isolation `none`, and lens order. Parallel critiques feed
`CritiqueAdjudication`; `RepairOutcome` binds the repair or empty-set proof;
fresh `Verification` evaluates it.
Each stage names its predecessor digest.

`dispatch-open` and `dispatch-packet` require sealed admission matching
`root_generation`, `cut_generation`, and `assignment_seal`.
Refuse draft/validated-only, stale, missing, mismatched, or substituted
generations. Recompute the frontier after lifecycle transitions and every
joined outcome; only work sealed by `tickets.py seal` is dispatched as it forms.
Accept each return once through `orch-integrate`; `suspended` parks; others
grade isolation and integrate per pack. `orch-integrate` owns actual candidate diffs;
its binding adjudicates overlap. Ordinary Git conflicts remain there for
resolution, outside frontier scheduling.
Commit unstreamed closing evidence as `outcome`; join consumes it only after
accepted receipt. `orch-integrate` owns one shared-artifact finalization after all candidate
joins; it records fixed joined identity. When returns integrate
and checker/gate is closed, run the standards owner's required checks exactly once at the accepted terminal identity; record revision, not per
merge batch. Red suite blocks completion.

Watch per [profiles](references/profiles.md); recompute on outcomes, tickets,
suspensions, or transport silence. `bound-check` parks overdue work without
post-bound motion as `suspended` through `dispatch-join`, Handoff naming bound
and `last_motion_at`; motion reports `over-bound`. Promote with `tickets.py ready`;
report `skipped` and blockers. Suspended tickets retain claimant Handoff after
attempts retire; dependents wait. Unsatisfied exclusions exit with remainder.
Quiescent: read `successors.md`; when a `planned` entry exists and run is
complete, return its trigger and the predecessor's accepted `## Result`
identity to the materialization owner, who replaces it
([work-item](../../../contracts/work-item.md#roots-decomposition-and-integration)).
Otherwise exit; `limited` when bounds leave tickets open.

Never: batch ready tickets; hide blocked subtrees as successes; re-order the
graph to dodge failure.

Return: status; ticket result identities; verified terminal state; required
successor materialization; open remainder and blockers.
