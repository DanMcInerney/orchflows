---
name: software-factory
description: Deliver software through bounded implementation, CI, specialist review, risk routing and an authorized observed rollout.
disable-model-invocation: true
---

Apply [library context](../../references/library-context.md) and [run contract](../../references/run-contract.md) in the caller. Inputs: outcome, workspace, optional output directory, release target, policy and bounds. Default endpoint: validated change and release handoff. A ship request enables the authorized release stage.

## Bounds

State positive integer `P`, default `3` candidate passes including initial implementation. Each pass makes a candidate through `orchflows:orch-work`, then, once checks pass, uses `orchflows:orch-review` once per applicable delivery lens, always correctness. Use separate reviewers for specialist coverage; the orchestrator chooses staffing/concurrency.

Failed work/review leaves that pass incomplete; another candidate attempt consumes a remaining pass. Recover interrupted work before retrying. Stop at requested endpoint, exhausted passes/constraints, caller stop or missing required capability/decision. Add no final review, nested repair loop, incident investigation or monitoring. Release requires request and eligibility.

## Delivery

1. **Context.** Inspect the project; save brief/checkpoint, relevant local/optional external context and starting state. Isolate candidates when edits could overlap. Define acceptance, checks and lenses before implementation. Missing release capabilities need not block useful implementation.
2. **Build/check.** Record pass consumption before work. Use `orchflows:orch-work` for implementation, docs, tests and release preparation; later passes receive all joined failures/findings. The builder runs selected checks and authorized candidate/PR publication/required CI, returning identity, patch, command/CI evidence and rollout plan. It reports failures for the next pass without adding review/deployment. Freeze the result.
3. **Review.** Failed checks feed the next remaining pass; unavailable checks block dependent work. After checks pass, dispatch fresh applicable reviewers with frozen candidate, actual domain context, acceptance, check evidence and guidance. Isolate test side effects with scratch/worktrees. Missing context limits review, never implies approval.
4. **Join/repair.** Gather every reviewer, deduplicate findings and resolve factual conflicts from evidence. Review newly exposed affected lenses before deciding. Unresolved actionable findings feed the next pass; revised candidates repeat required checks and all applicable reviews. Do not edit during review. Exhaustion returns open work without readiness claims.
5. **Risk.** Apply software-delivery guidance. Passing low-risk candidates satisfy the review gate automatically only under explicit project opt-in. Otherwise prepare human handoff: exact diff, checks, findings, risk and rollout/rollback plan. Reuse valid decisions/permissions for this state. Unknown/high risk needs human review; human decisions cannot bypass failed checks. Distinguish readiness for review versus release.
6. **Requested release.** Once review gate and release authority hold, use the release worker. If final approval is missing, complete authorized preparation and present the concrete release. Return under the run contract.

## Release worker

Use `orchflows:orch-work` with one accountable owner per external operation. Supply immutable validated artifact, approval/policy, target, plan, observability and authorized operations. Change no source or release scope. Verify published/merged inputs still match validation; changed inputs require a remaining candidate pass.

Before mutation, verify baseline signals, rollback and stopping criteria. Follow project staged/flag rollout; record operation IDs before advancing. Observe success/failure after each step for the planned window. Hold on missing telemetry and reconcile uncertain operations before retrying. Create a scoped dashboard only when needed and authorized.

On failure, stop advancement. Apply prepared rollback only if already authorized, then verify recovery; otherwise return evidence/proposal for decision. Time limits/missing signals mean incomplete observation, not health. Return release identity, exposure, observations, rollback and remaining watch window. [Investigate incidents](../investigate-incident/SKILL.md) only on request; subsequent [observation](../observe-production/SKILL.md) is separate.
