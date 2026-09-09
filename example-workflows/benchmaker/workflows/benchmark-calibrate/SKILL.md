---
name: benchmark-calibrate
description: Calibrate one pinned target through bounded development trials, independent diagnosis and immutable final measurement.
disable-model-invocation: true
---

Require: fixed `draft`, revision-bound `qualification`, construction `standard`,
coverage/rigor, `target_configuration`, preregistered `calibration_policy`, native
execution mechanism, candidate access scope, builder identities, qualification
budget, git `workspace`, repository-relative `records`, durable external
`evidence_export` and total bounds. Missing inputs return UNVERIFIED
with partial artifacts and gaps.

    tickets.py frame-open <run> --goal-file <calibration-goal> --workflow benchmark-calibrate

Use [handoff layouts](../../references/calibration.md). Goals carry fixed inputs, records and budget.

## Development

Start trials only from VALID qualification. Otherwise select its
INVALID/UNVERIFIED evidence for Finalize; an evidenced repair may enter the
bounded revision branch below before attempts.

One maker records a complete native round in fresh repositories: transcripts, outputs, independent grades and summary. Export committed records; separate controls.

    tickets.py do <run> --parent <frame> --standard benchmark-quality --standard <standard> --workspace <workspace> --goal-file <attempts>

Diagnose landed attempts and qualification findings independently for uncertainty, discrimination, configuration and validity; never re-execute.

    tickets.py judge <run> --review-independent "named benchmark calibration diagnosis" --parent <frame> --standard benchmark-quality --standard <standard> --artifacts git:<draft-sha> git:<attempt-sha> --goal-file <diagnosis> --isolation required

Apply INVALID, then UNVERIFIED, then OUT_OF_BAND/CALIBRATED precedence. Preserve
numeric band observation. Missing evidence stops trials, then Finalize. For evidenced
validity defects or construct-preserving difficulty changes, spend at most two
development revisions, or the smaller declared cap; budget exhaustion selects
the unmet decision for Finalize. A score alone authorizes no revision. Fix validity defects before difficulty changes.

    tickets.py do <run> --parent <frame> --standard benchmark-quality --standard <standard> --workspace <workspace> --goal-file <revision>

Carry diagnostic findings, pre/post identities, affected cases, retained
strata/weights and spend into the ledger. Invoke benchmark-qualify on every
changed draft with its complete original inputs and new builder identities:

    tickets.py frame-open <run> --parent <frame> --goal-file <requalification> --workflow benchmark-qualify

Execute its body; only VALID resumes trials. Retain rounds; select by policy.

## Freeze and measure

Only accepted development calibration enters one freeze maker:

    tickets.py do <run> --parent <frame> --standard benchmark-quality --standard <standard> --workspace <workspace> --goal-file <freeze>

Requalify the frozen revision through benchmark-qualify before measurement.
Final measurement uses the attempts making call with read-only frozen inputs,
external outputs and verified access scope; otherwise record public confirmation
and protection UNVERIFIED. Preserve development decision separately from final
score/drift. Never: revise after final observations, change target configuration, or substitute controls for agents.

## Finalize

Every terminal branch, including failed revisions, qualification gaps and no-final
partials, enters one record-finalization maker after relevant returns are landed:

    tickets.py do <run> --parent <frame> --standard benchmark-quality --standard <standard> --workspace <workspace> --goal-file <finalize-records>

Supply actual qualification/diagnostic/measurement returns, selected decision,
all immutable round identities, ledger, bounds and export locator. It commits
the aggregate index, not-performed reasons and durable findings copies; it never
rewrites published summaries. Export that landed commit, then probe.

Return: `tickets.py frame-close <run> <frame> --done <calibration-check>` with
all round/qualification/diagnostic identities, revision ledger, decision, frozen
identity when eligible, one external final record (including not-performed
reason), spend and gaps. INVALID/UNVERIFIED/OUT_OF_BAND retain useful partials.
