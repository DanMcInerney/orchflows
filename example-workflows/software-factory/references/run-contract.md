# Run contract

Accept workspace/repository, desired outcome or operational question, and optional output directory. Default to distinct `software-factory-runs/<run-id>/` in the caller workspace. Releases also require a target environment; infer established commands/policies before asking for missing inputs.

## Brief

Before dispatch, record project instructions and caller choices:

- Behavior, acceptance checks, constraints and affected surfaces.
- Baseline, candidate location and caller changes to preserve, including relevant untracked files. Exclude run evidence from source snapshots.
- Build/test commands, required CI and applicable baseline/candidate performance comparison. Label local-only projects; local checks cannot substitute for required remote CI.
- Review lenses/context: correctness always; data, infrastructure, cloud and security when affected. Explain omissions.
- Release scope, human-review requirements, explicit opt-in for unattended low-risk releases and existing publish/merge/deploy/rollback authority. Diagrams and risk labels grant no permission.
- Rollout artifact/command, flags/cohorts, baseline, success/failure signals, observation window, stages and rollback. Finish authorized preparation before requesting missing final approval.

Use plain Markdown and existing project tools, not a new configuration/CI system or irrelevant integrations.

## Checkpoint and evidence

The coordinator owns `checkpoint.md`. Save stage inputs and resumable work at handoff; before external mutation, record exact inputs/intended operation, then its outcome or interruption. Link code, commands, CI, reviews and telemetry rather than substituting status labels.

Record:

- Request/context, bounds, attempted passes and first unfinished stage.
- Baseline/current candidate identity: commits plus needed patch/untracked manifests, or equivalent reproducible snapshots.
- Delivered artifact identity/verification, including complete-patch reconstruction under software-delivery guidance.
- Each check/review's candidate, status, evidence and open findings. All reviewers inspect the same frozen state.
- Risk, policy and required human decision. Bind approval to reviewed state, target and operation; honor valid standing authorization.
- Release artifact/operation IDs, progress, observations, follow-up fingerprints and attempted external actions.
- Actual result: in progress, blocked, ready for review/release, released and observed, observation incomplete, rolled back or failed. Preparation is not deployment.

On resume, verify source, candidate, policy, authorization and external state before the first unfinished stage. Reuse only valid evidence. Source changes invalidate dependent checks/reviews/approvals and require a remaining pass or requested extension; resume never resets bounds. Reconcile uncertain publish/deploy/rollback outcomes before retrying; timeouts prove no absence of effects.

Before requested integration, compare the destination with the preserved baseline; never overwrite newer caller work. Changed bases/merge results need validation within the same bounds. Release only the validated artifact.

## Return

Return artifact/report, evidence, risk/release decision, actual external actions, consumed bounds, stop reason, gaps and checkpoint path. Continued observation needs requested host automation or another checkpoint-based invocation; this library adds no scheduler or promise of background execution.
