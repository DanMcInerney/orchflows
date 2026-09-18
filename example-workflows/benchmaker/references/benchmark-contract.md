# Benchmark contract

Generated benchmarks must satisfy these responsibilities through the selected harness's records or report gaps; no universal schema/runtime is required. Benchmarking guidance owns validity/interpretation; this contract owns data/execution boundaries.

## Package and preflight

Prefer JSON/JSONL records and a Markdown report, commonly:

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

Provide reproducible preflight, controls, smoke, quick, full and resume commands or host-driven steps. Preflight checks inputs, runtimes/tools/access, output paths and adapter/scorer availability without billable target work. Show planned cases/repetitions, concurrency, launch limit, deadlines and estimated spend before execution. Missing target or judge access may permit controls but never fabricated measurement.

The card records decision/claim, population, complete system boundary, capability/family coverage, source/split policy, metric meanings/constraints, assumptions, budgets, dependencies/access, provenance, limitations and validation status. Include the [quality profile](quality-profile.md)'s requested/achieved stage, track, gate evidence/gaps, work dossiers, coverage matrix and calibration plan/results. Reference solutions and expected controls belong to evaluator material.

## Records and identity

| Record | Required information |
| --- | --- |
| Benchmark | Version; card; cases/splits/groups; metrics, weights and required constraints; scorer version; profiles; dependency/access requirements |
| Public case | Stable ID; task; inputs/assets; allowed environment/tools; visible deliverable requirements |
| Evaluator case | Case ID; family; source/group identity; track/split; work dossier and feasibility evidence; criterion/scorer bindings; controls and expected outcomes |
| Condition | Target revision/content identity; actual model/settings when observable, otherwise unknown; workflow/instructions; tool/network access; memory/reset policy; adapter and environment identity; budgets |
| Attempt | Case/condition/repetition/retry IDs; start/end and phase timings; execution status/reason; artifacts or final state; transcript path; observed usage/cost, with unknowns explicit |
| Score | Scorer identity; grading status/reason per metric; anchored dimension outcomes/evidence and weights; aggregate outcome credit or explicit unavailable reason; separate full success and critical failures; indeterminate or uncertainty information |

Bind results to a digest of immutable manifest inputs: cases, public assets, references, graders and relevant adapter/runner files. Exclude runs/caches/outputs. Retain file inventory/hashes or a clean revision plus local changes; Git is optional. Bind condition identity separately, including target instructions/settings, environment and budgets. Redact credential values from records. A resumed run must reject incompatible identities, including scorer or profile/repetition changes; re-scoring saved outputs produces an explicitly new scorer result, not a fresh agent attempt.

On resume, import and summary reads, validate: fixed membership, case/repetition/retry IDs, benchmark and condition bindings, legal execution transitions, artifact hashes and score provenance. Reject missing, extra, foreign or inconsistent records even when filenames and top-level digests match.

Only stage public case material into the solver's writable workspace. Pass no evaluator answers, controls or hidden rubric in the candidate prompt. Document actual filesystem/network access; this layout is not a security boundary.

## Adapter boundary

An async adapter may expose `run_case(public_case, context) -> result`. The context supplies an isolated workspace, public assets, condition, remaining execution budget and evidence destinations. The adapter returns delivered artifacts/state, transcript, execution status/reason and observable usage. Scoring reads evaluator material afterward and remains separate from the solver.

CLI adapters invoke the real candidate through an argument vector and translate native output. An API adapter uses async calls or moves blocking clients off the scheduling path. Interactive adapters own an ordered episode and expose final state plus transcript, recording simulator identity/state. Native workflow adapters preserve the native composition. If automation is unavailable, provide a host-driven route and exact evidence to capture. A canned response exercises plumbing only.

## Profiles

| Profile | Selection and purpose |
| --- | --- |
| Smoke | 1–3 representative cases for adapter, inputs, grader and evidence paths; no capability claim |
| Quick | Fixed stratified subset, commonly 6–12 cases, one attempt each; aim for 2–5 minutes when faithful |
| Full | All declared evaluation cases and predeclared repeats; show duration/spend estimates before launch |

Adjust these budgets to the task; record manifest membership and freeze comparable runs. Disclose shared quick/full cases in small development suites. Do not shorten tasks so far that the trial loses fidelity.

## Scheduling and persistence

- Bound independent episodes with configurable concurrency. Keep turns/dependencies within an episode ordered. Use async subprocess/provider APIs; keep blocking and CPU-heavy work off the event loop. Avoid process-global cwd/environment changes.
- Isolate writable state, outputs and required ports per attempt; share only immutable fixtures. Reset memory between episodes unless carryover is the stated capability. Limit providers, judges and costly resources separately; serialize only contested resources. Record concurrency and hardware for timing comparisons.
- Bound each attempt, the overall run, total launches (including retries/repeats), and spend. Reserve capacity for in-flight work before admission. Label estimated spend limits honestly when exact provider spend cannot be enforced; enforce observable call/token/time limits as well. Do not admit more work after a bound is reached.
- Persist planned attempts and each launch before dispatch; write completed records as they finish through one writer or atomic per-attempt files. Preserve artifacts and logs on failure. Resume matching completed work without relaunch. Record interrupted attempts; reconcile uncertain remote completion before relaunching anything that could still be running or billed. Prevent overlapping owners of one run directory.
- Retry only enumerated transient infrastructure errors within a small declared retry budget. Every retry has a distinct ID, links to its original attempt and consumes launch/time/cost budget. Wrong answers and declared agent time/budget exhaustion are not transient retries. Independent stochastic repetitions have separate IDs and fixed counts.
- On deadline or interruption, stop admission, cancel outstanding work, and terminate/reap owned subprocess trees using the platform's process-group/job mechanisms. Test cleanup on the supported platform. Local cancellation cannot establish remote completion or stopped billing; record that uncertainty. Unsupported cleanup leaves that adapter/platform provisional.

## Boundary checks

Within pilot bounds, exercise actual adapter/runner boundaries: changed plan membership and attempt/score identities, stale artifacts, invalid delivered output or known nondelivery, and applicable failed-dispatch, intermediate-preservation and overall-deadline transitions. Check budget enforcement under supported invocation modes. Include valid records and outcomes so rejecting everything cannot pass. Use stand-ins only at the actual execution boundary; retain unsupported properties as gaps rather than testing a substitute runner.

Exercise score eligibility against execution and delivery evidence on import, resume and summary: ordinary infrastructure failures or unknown capture stay unscored, task-budget exhaustion defeats full success, and established nondelivery earns no progress. Change a stored success or credit while retaining its identity fields and artifact hashes; reject unsupported score content using bound authoritative judgments and deterministic recomputation where applicable. Matching provenance fields alone do not validate a score.

Include null or wrongly shaped nested target output, missing grading and a scorer interruption after delivery. Verify the status rules below: malformed delivered work is a task failure; unavailable capture or a scorer fault remains visibly unscored. Recover grading from retained evidence without relaunching the target, preserving prior failures and scorer identities.

## Status and aggregation

Keep execution status (completed, agent-budget-exhausted, infrastructure-error, canceled, interrupted or not-launched), grading status (scored, unscored/error or indeterminate), and task success separate. A completed wrong answer is a scored failure. Agent budget exhaustion is a scored failure when completion within that budget is required. Infrastructure failure, broken setup, grader crash and missing evidence are unscored with reasons. A robustness task can grade failure handling only when that requirement was predeclared.

A delivered artifact or state that violates required structure is a scored task failure. Established non-delivery of a required answer by a completed target also fails; unavailable capture that leaves the outcome unknown stays unscored. Separate target-output validation from scorer errors so invalid answers are not excluded from the scored denominator.

Report planned, launched, completed, scored, passed, failed, unscored and canceled counts, plus interrupted/not-launched identities. State units: launch counts include retries; quality counts use planned case/repetition units after retry resolution. Preserve unsuccessful retry records and total their resources instead of counting retries as extra quality observations. Report coverage and exclusion identities/reasons alongside quality. Unknown cost stays unknown; show available components separately.

Average scored repetitions within cases before applying predeclared case/family weights; expose missing repeats/cases and the scored denominator. Report per-family results and an appropriate primary metric. Optional best/worst bounds across missing observations must respect bounded metric ranges and declared weights, not impute invented observed scores. Suppress an unqualified ranking if missingness or coverage differences could reverse it.

For weighted outcome credit, use `sum(weight[d] * credit[d])` with nonnegative finite weights summing to one and anchored finite credits in [0, 1]. Validate definitions and reject invalid scorer records. If a required dimension is unjudged, retain observed dimensions but leave the aggregate unavailable; optional lower/upper bounds may fill unknown credits with 0/1 and must be labeled as bounds. Inapplicability and any case-specific weights must be defined before results, not renormalized after missing judgments.

Full success is a separate 0/1 judgment under predeclared requirements, or unknown when evidence cannot establish it. Known critical failures defeat full success even if some dimensions are unknown. Report full-success rate, mean outcome credit, critical-failure counts/rates and each metric's scored denominator separately, including per-family coverage. Do not blend these into one acceptance score. Record a reason when a benchmark uses binary-only scoring.

For comparisons retain per-case deltas/ties and common-case coverage. Report cold setup, candidate execution, grading, total wall time and throughput separately. Save raw evidence alongside a human-readable summary with commands, conditions, limits and untested paths.

## Evidence handoff

Keep three labeled groups: harness checks (including stand-ins and injected failures), benchmark validation (controls, independent public-input audit and solvability evidence), and fresh agent measurements (conditions, executions, artifacts, scores, usage). Record the pilot worker's public answers before reference disclosure and its subsequent discrepancies. Keep review findings, the candidate identity reviewed, repair changes, new identities and affected verification. A repaired development case does not become fresh held-out evidence.

Deliver runnable controls/package with blocked execution and required capabilities explicit. Unresolved required validation remains draft/partial; one passing pilot establishes no general readiness.
