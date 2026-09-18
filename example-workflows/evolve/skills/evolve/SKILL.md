---
name: evolve
description: Iteratively improve any artifact and its improvement harness, inventing evaluation when needed; supports bounded runs, tournaments and continuous resumable search.
disable-model-invocation: true
---

Apply [library context](../../references/library-context.md) and required [evaluation](references/evaluation.md) and [state](references/state.md) contracts. Accept artifacts, seeds or a creation brief; purpose and constraints; optional bounds, output location and scoped settings. Infer quality criteria; clarify gaps that prevent meaningful creation or assessment. Production follows core staffing rules and evaluation's context exclusions.

## Start or resume

Use the caller's directory or a distinct `evolve-runs/<run-id>/` in their workspace. Reconcile saved state and in-flight work before new work.

For a new run, preserve the original or create a seed from the brief. Design, calibrate and save evaluation before challengers. Evaluate seeds, choose the incumbent (current best), and save the harness: working instructions, tools and search policy.

Record bounds, scoped settings and per-experiment limits. Default to three rounds and one challenger per round. Explicit continuous requests remove the total round cap: continue until stopped, a supplied bound is reached or execution is blocked. A target stops work only if the caller says so; plateau is not completion.

## Repeat

1. **Start and choose.** Record each artifact/harness attempt under core's iteration bounds and the state contract before proposal or production. Read checkpoint/evidence; choose a hypothesis and predicted benefit. After three rounds since promotion with usable candidate/harness evidence but no promotion, change approach, investigate repeated failure or test a harness change. External failures neither advance nor reset this trigger; all attempts and resources still count.
2. **Make.** Save the plan and isolated candidate locations. Supply each challenger its parent snapshot, hypothesis, active harness, public evaluation and guidance. Give it one owner; exclude incumbent, evaluation and journal from production writes. A [harness experiment](references/harness.md) replaces the ordinary round.
3. **Compare.** Freeze candidates. Apply screening, matched evaluation versions, independent `orch-review` judgments and confirmation. Compare every proposed replacement with the incumbent. Missing evidence, failed requirements, ties or unconfirmed wins retain the incumbent. Record failures without invented scores.
4. **Record and continue.** Journal decision/evidence, then checkpoint winner, alternatives, lessons and remaining bounds. Check stopping conditions before another round. Repair uninformative, inconsistent or exploitable evaluation between rounds: preserve purpose/constraints, version it, and re-evaluate incumbent/contenders before promotion. Scores across versions are incomparable; easier evaluation is not progress. Evaluator repair spends resources but adds no artifact/harness round, repair loop or attempt reset.

## Return or yield

Persist at each decision and before interruption/context rollover. Return best artifact, improvements/evaluation version, active harness, evidence, observable resource use, actual stop reason and resume path. Separate measured, judge-preferred and untested claims. Missing execution/continuation capability requires a checkpoint and gap, not a background-execution claim. Reaching a finite bound completes the search without proving further improvement impossible.
