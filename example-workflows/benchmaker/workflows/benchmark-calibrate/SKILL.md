---
name: benchmark-calibrate
description: Calibrate one pinned target through bounded development trials, independent diagnosis and immutable final measurement.
disable-model-invocation: true
---

Require: fixed `draft`, revision-bound `qualification`, construction `standard`,
coverage/rigor, `target_configuration`, preregistered `calibration_policy`, native
execution mechanism, candidate access scope, builder identities, qualification
budget, git evidence workspace and total bounds. Missing inputs return UNVERIFIED
with partial artifacts and gaps.

    tickets.py frame-open <run> --goal-file <calibration-goal> --workflow benchmark-calibrate

Use [handoff layouts](../../references/calibration.md). Every making/judging goal
carries the fixed inputs, relevant records and budget. All artifact calls stamp
package-private benchmark-quality beside the construction standard. Keep the
exact target configuration unchanged throughout.

## Development

Start only from VALID qualification covering this draft. Otherwise return its
INVALID/UNVERIFIED decision and evidence; an evidenced repair may enter the
bounded revision branch below before attempts.

One ordinary making ticket owns the complete declared round in an external
evidence workspace. Run actual native attempts as experiment subjects, using
fresh candidate repositories; collect transcripts, outputs, independent grader
observations and summary. Controls remain separately classified.

    tickets.py do <run> --parent <frame> --standard benchmark-quality --standard <standard> --workspace <evidence-workspace> --goal-file <attempts>

Give a fresh diagnostic judge the fixed draft and landed attempt commit plus
qualification findings. Inspect per-case uncertainty, empirical discrimination,
configuration and validity; never silently re-execute attempts.

    tickets.py judge <run> --parent <frame> --standard benchmark-quality --standard <standard> --artifacts git:<draft-sha> git:<attempt-sha> --goal-file <diagnosis> --isolation required

Apply INVALID, then UNVERIFIED, then OUT_OF_BAND/CALIBRATED precedence. Preserve
numeric band observation. Missing evidence stops dependent work. For evidenced
validity defects or construct-preserving difficulty changes, spend at most two
development revisions, or the smaller declared cap; budget exhaustion returns
the unmet decision. A score alone authorizes no revision. Fix validity defects before difficulty changes.

    tickets.py do <run> --parent <frame> --standard benchmark-quality --standard <standard> --workspace <workspace> --goal-file <revision>

Carry diagnostic findings, pre/post identities, affected cases, retained
strata/weights and spend into the ledger. Invoke benchmark-qualify on every
changed draft with its complete original inputs and new builder identities:

    tickets.py frame-open <run> --parent <frame> --goal-file <requalification> --workflow benchmark-qualify

Execute its body; only VALID resumes a complete preregistered round. Retain all
rounds; select by declared policy.

## Freeze and measure

Only accepted development calibration enters one freeze maker:

    tickets.py do <run> --parent <frame> --standard benchmark-quality --standard <standard> --workspace <workspace> --goal-file <freeze>

Requalify the frozen revision through benchmark-qualify before measurement.
Final measurement uses the attempts making call with read-only frozen inputs,
external outputs and verified access scope; otherwise record public confirmation
and protection UNVERIFIED. Preserve development decision separately from final
score/drift. Never: revise after final observations, change target configuration, or substitute controls for agents.

Return: `tickets.py frame-close <run> <frame> --done <calibration-check>` with
all round/qualification/diagnostic identities, revision ledger, decision, frozen
identity when eligible, one external final record (including not-performed
reason), spend and gaps. INVALID/UNVERIFIED/OUT_OF_BAND retain useful partials.
