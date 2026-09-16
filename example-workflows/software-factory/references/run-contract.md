# Run contract

Each entrypoint accepts a repository/workspace, an outcome or operational question, and an optional output directory. Default outputs to a distinct `software-factory-runs/<run-id>/` in the caller workspace. A release request also needs its target environment; infer established project commands and policies before asking for missing inputs.

## Project context

Before dispatch, save a short brief using existing project instructions and caller choices:

- Desired behavior, acceptance checks, constraints and affected surfaces.
- Source baseline, working changes to preserve, and candidate location. Include relevant untracked files. Keep run evidence outside the source snapshot.
- Build/test commands, required CI checks and any baseline-versus-candidate performance comparison. Mark local-only projects explicitly; local checks do not substitute for required remote CI.
- Applicable review lenses and their actual source context: correctness always; data, infrastructure, cloud and security when affected. Record why a lens is omitted.
- Release scope, existing human-review requirements, any explicit opt-in policy for unattended low-risk releases, and the caller's existing authorization for publishing, merge, deployment and rollback. Do not infer permission from the source diagram or from a risk label.
- For rollout: artifact identity, deployment command, feature flags/cohorts, success and failure signals, baseline, observation window, rollout steps and rollback procedure. Prepare these before asking for any missing final approval.

This is a handoff, not a new configuration format. Use plain Markdown and references to the project's existing tools. Do not create another CI system or require integrations irrelevant to the task.

## Evidence and checkpoint

The coordinator owns `checkpoint.md`. Before each child or external mutation, record its stage, exact inputs, allocated call and intended operation. Afterward, save its result or interruption. Link the actual code, command results, CI runs, reviewer reports and telemetry; do not replace evidence with a green label.

Record at least:

- Request, resolved context, bounds, consumed calls/passes and first unfinished stage.
- Baseline and current candidate identities; use commits plus a patch/untracked-file manifest when needed, or an equivalent reproducible content snapshot.
- Delivered artifact identity and verification evidence, including the reconstruction result when returning a complete patch, as defined in software-delivery guidance.
- For each check/review: candidate identity, status, evidence and unresolved findings. Every reviewer sees the same frozen state.
- Risk rationale, applicable policy and human decision where required. Bind release approval to the reviewed state, target and operation; honor the scope of valid standing authorization.
- Release artifact and operation identifier, rollout progress, observations, follow-up fingerprints and any external action already attempted.
- Current result: in progress, blocked, ready for review/release, released and observed, observation incomplete, rolled back, or failed. A prepared release is not a deployed change.

On resume, verify source, candidate, policy, authorization and external operation state before continuing the first unfinished stage. Reuse evidence only while its inputs remain valid. A source change invalidates dependent checks, reviews and approvals; use a remaining candidate pass or report that an extension is needed. Resuming never resets bounds. An interrupted call still counts. Reconcile an uncertain publish/deploy/rollback result before retrying; a timeout does not prove the action did not happen.

Do not overwrite newer caller work when returning changes. Verify the integration target against the preserved starting state, then apply the candidate if integration was requested. Integrating into a changed base requires new validation within the same bounds. External release uses only the validated artifact; a changed merge result must be checked again.

## Return

Return the changed artifact or operational report, evidence links, risk and release decision, actual external actions, consumed bounds, stop reason, remaining gaps and checkpoint path. Do not claim background monitoring after the host stops. Longer observation requires an explicitly requested host automation or another invocation using the checkpoint; the library adds no scheduler.
