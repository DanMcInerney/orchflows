# Benchmark contract

These are responsibilities of each generated benchmark, not a universal schema or mandatory runtime. Use the selected harness's equivalent records when appropriate. Describe any unsupported responsibility as a gap. Benchmarking guidance owns validity and interpretation; this contract owns data and execution boundaries.

## Package and preflight

Prefer transparent JSON/JSONL records and a Markdown report. A standalone package commonly contains:

```text
README.md              purpose, commands, requirements, limits
benchmark.json         card, identity inputs, profiles, metrics, splits
cases.jsonl            evaluator inventory with public input references
inputs/                public prompts, assets, resettable fixtures
evaluation/            scorers, rubrics, reference evidence, controls
adapter.py             actual target invocation, if needed
run.py                 runner or documented upstream entrypoint
runs/<run-id>/          attempts, artifacts, summary
```

Provide reproducible preflight, controls, smoke, quick, full and resume commands (or explicit host-driven steps). Preflight checks inputs, required runtimes/tools/access, output paths and adapter/scorer availability without launching billable target work. Show planned cases/repetitions, concurrency, launch limit, deadlines and estimated spend before execution. Missing target or judge access may permit controls but never fabricated measurement.

The benchmark card records the intended decision and bounded claim, task population, complete system boundary, capability/family coverage, source and split policy, metric meanings and mandatory constraints, assumptions, budgets, dependencies/access, provenance, limitations and validation status. Reference solutions and expected controls belong to evaluator material.

## Records and identity

| Record | Required information |
| --- | --- |
| Benchmark | Version; card; cases/splits/groups; metrics, weights and required constraints; scorer version; profiles; dependency/access requirements |
| Public case | Stable ID; task; inputs/assets; allowed environment/tools; visible deliverable requirements |
| Evaluator case | Case ID; family; source/group identity; reference evidence; criterion/scorer bindings; controls and expected outcomes |
| Condition | Target revision/content identity; actual model/settings when observable, otherwise unknown; workflow/instructions; tool/network access; memory/reset policy; adapter and environment identity; budgets |
| Attempt | Case/condition/repetition/retry IDs; start/end and phase timings; execution status/reason; artifacts or final state; transcript path; observed usage/cost, with unknowns explicit |
| Score | Scorer identity; grading status/reason; criterion outcomes/evidence; task success where defined; indeterminate or uncertainty information |

Bind results to a digest of explicit immutable manifest inputs: cases, public assets, references, graders and relevant adapter/runner files. Exclude generated runs, caches and outputs. Retain the file inventory and hashes or a clean revision with local changes; Git is optional. Bind condition identity separately, including target instructions/settings, environment and budgets. Redact credential values from records. A resumed run must reject incompatible identities, including scorer or profile/repetition changes; re-scoring saved outputs produces an explicitly new scorer result, not a fresh agent attempt.

Only stage public case material into the solver's writable workspace. Pass no evaluator answers, controls or hidden rubric in the candidate prompt. Document actual filesystem/network access; this layout is not a security boundary.

## Adapter boundary

An async adapter may expose `run_case(public_case, context) -> result`. The context supplies an isolated workspace, public assets, condition, remaining execution budget and evidence destinations. The adapter returns delivered artifacts/state, transcript, execution status/reason and observable usage. Scoring reads evaluator material afterward and remains separate from the solver.

A CLI adapter builds an argument vector, invokes the real candidate and translates native output. An API adapter uses async calls or moves blocking clients off the scheduling path. Interactive adapters own an ordered episode and expose final state plus transcript, recording simulator identity/state. Native workflow adapters preserve the native composition. If automation is unavailable, provide a host-driven route and exact evidence to capture. A canned response exercises plumbing only.

## Profiles

| Profile | Selection and purpose |
| --- | --- |
| Smoke | 1–3 representative cases for adapter, inputs, grader and evidence paths; no capability claim |
| Quick | Fixed stratified subset, commonly 6–12 cases, one attempt each; aim for 2–5 minutes when faithful |
| Full | All declared evaluation cases and predeclared repeats; show duration/spend estimates before launch |

These are adjustable starting budgets. Record actual membership in the manifest and keep comparable runs fixed. A smaller development suite may use the same cases in quick/full with that limitation stated. Do not compress an intrinsically long task into a misleading short trial.

## Scheduling and persistence

- Bound independent episodes with configurable concurrency. Keep turns/dependencies within an episode ordered. Use async subprocess/provider APIs; keep blocking and CPU-heavy work off the event loop. Avoid process-global cwd/environment changes.
- Give attempts separate writable state, outputs and ports as needed. Share immutable fixtures only. Reset memory between episodes unless carryover is the stated capability. Limit providers, judges and costly resources separately; serialize only contested resources. Record concurrency and hardware for timing comparisons.
- Bound each attempt, the overall run, total launches (including retries/repeats), and spend. Reserve capacity for in-flight work before admission. Label estimated spend limits honestly when exact provider spend cannot be enforced; enforce observable call/token/time limits as well. Do not admit more work after a bound is reached.
- Persist planned attempts and each launch before dispatch; write completed records as they finish through one writer or atomic per-attempt files. Preserve artifacts and logs on failure. Resume matching completed work without relaunch. Record interrupted attempts; reconcile uncertain remote completion before relaunching anything that could still be running or billed. Prevent overlapping owners of one run directory.
- Retry only enumerated transient infrastructure errors within a small declared retry budget. Every retry has a distinct ID, links to its original attempt and consumes launch/time/cost budget. Wrong answers and declared agent time/budget exhaustion are not transient retries. Independent stochastic repetitions have separate IDs and fixed counts.
- On deadline or interruption, stop admission, cancel outstanding work, and terminate/reap owned subprocess trees using the platform's process-group/job mechanisms. Test cleanup on the supported platform. Local cancellation cannot establish remote completion or stopped billing; record that uncertainty. Unsupported cleanup leaves that adapter/platform provisional.

## Status and aggregation

Keep execution status (completed, agent-budget-exhausted, infrastructure-error, canceled, interrupted or not-launched), grading status (scored, unscored/error or indeterminate), and task success separate. A completed wrong answer is a scored failure. Agent budget exhaustion is a scored failure when completion within that budget is required. Infrastructure failure, broken setup, grader crash and missing evidence are unscored with reasons. A robustness task can grade failure handling only when that requirement was predeclared.

Report planned, launched, completed, scored, passed, failed, unscored and canceled counts, plus interrupted/not-launched identities. State units: launch counts include retries; quality counts use planned case/repetition units after retry resolution. Preserve unsuccessful retry records and total their resources instead of counting retries as extra quality observations. Report coverage and exclusion identities/reasons alongside quality. Unknown cost stays unknown; show available components separately.

Average scored repetitions within cases before applying predeclared case/family weights; expose missing repeats/cases and the scored denominator. Report per-family results and an appropriate primary metric. Optional best/worst bounds across missing observations must respect bounded metric ranges and declared weights, not impute invented observed scores. Suppress an unqualified ranking if missingness or coverage differences could reverse it.

For comparisons retain per-case deltas/ties and common-case coverage. Report cold setup, candidate execution, grading, total wall time and throughput separately. Save raw evidence alongside a human-readable summary with commands, conditions, limits and untested paths.

## Evidence handoff

Keep three labeled groups: harness checks (including stand-ins and injected failures), benchmark validation (controls, independent public-input audit and solvability evidence), and fresh agent measurements (conditions, executions, artifacts, scores, usage). Record the pilot worker's public answers before reference disclosure and its subsequent discrepancies. Keep review findings, the candidate identity reviewed, repair changes, new identities and affected verification. A repaired development case does not become fresh held-out evidence.

Deliver a runnable package even if only controls are currently runnable, with the blocked execution step and required capability explicit. Classify required unresolved validation as draft/partial. Do not claim general readiness from one passing pilot.
