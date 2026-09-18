---
name: evolve
description: Iteratively improve any artifact and its improvement harness, inventing evaluation when needed; supports bounded runs, tournaments and continuous resumable search.
disable-model-invocation: true
---

Apply [library context](../../references/library-context.md) and the required [evaluation](references/evaluation.md) and [state](references/state.md) contracts. Inputs are artifacts, multiple seeds or a creation brief, the caller's purpose and constraints, and optional bounds, output location and scoped settings. Infer missing quality criteria; clarify only gaps that prevent meaningful creation or assessment. Ordinary production follows core staffing rules and evaluation's context exclusions.

## Start or resume

Use the caller's run directory or a distinct `evolve-runs/<run-id>/` in their workspace. On resume, reconcile state and in-flight work before starting anything new.

For a new run, preserve the original; if only a brief exists, make a seed. Design, calibrate and save evaluation before challengers. Evaluate the seeds and select the initial incumbent (current best). Save the working harness: instructions, tools and search policy actually used.

Record bounds, scoped settings and per-experiment limits. Default to three rounds and one challenger per round. An explicit continuous request has no total round cap: continue until stopped, a supplied bound is reached or execution is blocked. A target stops work only if the caller makes it a stop condition; a plateau is not completion.

## Repeat

1. **Start and choose.** Begin each artifact or harness round with the durable **round-start** event defined in state, before proposal or production work. Read the checkpoint and relevant evidence; select a concrete hypothesis and predicted benefit. After three rounds since the last promotion that provide usable candidate or harness evidence but no promotion, change the approach, investigate the repeated failure or test a harness change. Failures outside the candidate or harness neither advance nor reset this trigger; all attempts and spent resources still count against caller bounds.
2. **Make.** Save the plan and isolated candidate locations. Produce each challenger from its parent snapshot, hypothesis, active harness, public evaluation and applicable guidance. Give each candidate one owner; keep incumbent, evaluation and journal outside production write scope. For a harness round, apply the required [harness experiment](references/harness.md) instead; it replaces an ordinary round.
3. **Compare.** Freeze candidates. Apply evaluation, including screening, matched versions, independent `orch-review` judgments and required confirmation. Compare every proposed replacement with the incumbent. Missing evidence, failed requirements, ties and unconfirmed wins retain the incumbent. Save actual failures without inventing scores.
4. **Record and continue.** Journal the decision and evidence, then checkpoint the verified winner, retained alternatives, lessons and remaining bounds. Check stop conditions before starting another round. If evaluation is uninformative, inconsistent or exploitable, repair it between rounds: preserve purpose and constraints, version it and re-evaluate the incumbent and contenders before any promotion. Never compare scores across versions or count an easier evaluator as progress. Evaluation repair is separate from harness promotion; it consumes resources but adds no artifact/harness round and grants no repair loop or reset of attempts.

## Return or yield

Persist state at each decision and before interruption or context rollover. Return the best artifact, improvements and their evaluation version, active harness, evidence, observable resource use, actual stop reason and resume path. Distinguish measured, judge-preferred and untested claims. If execution or continuation is unavailable, report the checkpoint and gap without claiming background execution. A finite run reaching its bound completes the search; it does not prove no further improvement is possible.
