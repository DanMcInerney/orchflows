---
name: software-factory
description: Deliver a software outcome through bounded implementation, CI and specialist review loops, risk routing and an authorized observed rollout.
disable-model-invocation: true
---

Apply [library context](../../references/library-context.md) and the [run contract](../../references/run-contract.md). Inputs are the desired software outcome, workspace and optional output directory, release target, project policy and bounds. The coordinator runs in the caller. Default the requested endpoint to a validated change and release handoff; a caller request to ship also enables the authorized release stage.

## Bounds

Default to `P=3` candidate passes, including the initial implementation; require a positive integer and state it. Each pass produces a candidate through `orch-work` and, after checks pass, uses `orch-review` once per applicable software-delivery lens, including correctness. Separate reviewers preserve specialist coverage. The orchestrator chooses maker staffing and concurrency.

Release follows only when requested and eligible. No extra final review, nested repair loop, incident investigation or monitoring is implicit. Failed implementation or review leaves the pass incomplete; a new candidate attempt consumes a remaining pass. Recover interrupted work before retrying it. Stop when the requested endpoint is achieved, passes or caller constraints are exhausted, the caller stops, or a required capability or decision is missing.

## Deliver

1. **Establish context.** Inspect the project and save the brief/checkpoint. Gather relevant repository and optional external context. Preserve the starting state and give the builder an isolated candidate when edits could overlap. Define acceptance, checks and review lenses before implementation. Required release capabilities may be recorded as gaps while useful implementation proceeds.
2. **Build and check.** Consume a pass and use `orch-work` for implementation, project documentation, applicable tests and release preparation. On later passes include all joined failures/findings. The builder runs the selected checks and, where authorized, publishes the candidate/PR and obtains required CI results. It returns candidate identity, patch, command/CI evidence and rollout plan. A builder reports remaining failures for the next pass instead of adding independent review or deployment. Freeze the returned state.
3. **Review.** If required checks fail, route actionable failures into the next remaining pass. If checks cannot run, report the gap and stop dependent work. Once they pass, dispatch the applicable fresh reviewers against the frozen candidate and actual domain context. Give each reviewer its lens, acceptance criteria, check evidence and resolved guidance. Prevent shared test side effects with separate scratch/worktrees. Missing domain context limits the review; it is never silently treated as approval.
4. **Join and repair.** Wait for all reviewers, deduplicate findings and resolve factual conflicts from evidence. Revisit lens coverage if the implementation exposed another affected surface; cover that lens before deciding. Feed unresolved actionable findings to the next builder pass. Re-run required checks and all applicable reviews for a revised candidate. Do not modify the candidate while reviewers inspect it. Exhaustion returns the candidate and open findings without calling it ready.
5. **Route risk.** Apply software-delivery guidance to the joined evidence. A passing low-risk candidate may satisfy the review gate automatically only under explicit project opt-in. Otherwise prepare a human-review handoff with the exact diff, checks, findings, risk and rollout/rollback plan. Reuse a valid human decision already supplied for this state. Do not ask again for permissions already granted. Unknown/high risk takes the human path; a human decision cannot bypass failed required checks. If delivery stops at a handoff, report readiness for review or release accurately.
6. **Release when requested.** Once the review gate and release authority are satisfied, use the release worker below. If final approval is missing, first finish all authorized preparation and present the concrete release for that decision. Return using the run contract.

## Release worker

Assign release through `orch-work`, with one accountable owner for each external operation. Supply the immutable validated artifact, approval/policy evidence, target, rollout plan, observability access and authorized operations. Release work must not change source or broaden the release. Check that the published/merged artifact still matches validated inputs; changed inputs return to a remaining candidate pass before release.

Before mutation, verify the baseline signals, rollback path and rollout stopping criteria. Use the project's staged release or feature-flag process. Record external operation identifiers before advancing. Compare success/failure signals after each step for the planned observation window; hold on missing telemetry and reconcile uncertain operations rather than repeat them. Create a scoped dashboard only if needed and within existing authorization.

On a failure signal, stop advancing. Execute the prepared rollback only if already authorized, then verify recovery; otherwise return the evidence and proposed rollback for the required decision. A time limit or missing signal produces an incomplete observation, not a healthy-release claim. Return the release identity, actual exposure, observations, any rollback and remaining watch window. An outage can be handed to [investigate-incident](../investigate-incident/SKILL.md) on an explicit request; subsequent production feedback uses [observe-production](../observe-production/SKILL.md).
