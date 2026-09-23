# Benchmark contract

Generated benchmarks meet these responsibilities through the selected harness's records or report gaps; no universal schema or runtime is required. Benchmarking guidance owns validity and interpretation, the [quality card](quality-card.md) owns admission and stages, and this contract owns data and execution.

## Package

A package runs without its author. Prefer JSON/JSONL records and a Markdown report, commonly:

```text
README.md            claim, commands, requirements, limits
card.json            quality card, comparison set, conditions, metrics, splits
tasks/<id>/          public instruction, interface, inputs, environment or initial state
evaluation/<id>/     verifier, reference solution, rubric, labeled outcomes, admission evidence
rejections.jsonl     every candidate's disposition and reason
adapters/            actual target invocation, if needed
run.py               runner or documented upstream entrypoint
runs/<run-id>/       attempts, artifacts, scores, summary
```

Where targets work in a directory or container, a task layout that an existing harness already runs lets the suite travel; Harbor's instruction, environment, solution and tests is one such layout. Provide preflight, smoke, quick, full and resume commands or host-driven steps. Preflight checks inputs, tools, access, output paths and adapter and verifier availability without billable target work, then shows planned tasks, repeats, concurrency, deadlines and estimated spend. Missing target or judge access may permit the checks that do not need it, never fabricated measurement.

| Profile | Purpose |
| --- | --- |
| Smoke | 1–3 tasks exercising adapter, inputs, verifier and evidence paths; no capability claim |
| Quick | A fixed stratified subset with one attempt each |
| Full | All declared tasks and predeclared repeats |

## Records

| Record | Required information |
| --- | --- |
| Benchmark | Identity; card; tasks, splits and groups; metrics, weights and mandatory constraints; verifier revision; profiles; dependencies and access |
| Public task | Stable ID; instruction; interface and inputs; allowed environment and tools; visible deliverable requirements |
| Evaluator task | Task ID; family; source group and provenance; split; difficulty rationale and time estimate; verifier and reference bindings; labeled outcomes |
| Admission | Task ID; each criterion's evidence, outcome and date; revisions; disposition and reason |
| Condition | Target content identity; the model that actually answered when observable, otherwise unknown; instructions; tool and network access; memory and reset policy; adapter and environment; budgets |
| Attempt | Task, condition, repetition and retry IDs; timings; execution status and reason; delivered artifacts or final state; transcript; observed usage and cost, unknowns explicit |
| Score | Verifier identity; grading status per metric; dimension outcomes with evidence and weights; outcome credit or its unavailable reason; separate full success and critical failures; indeterminate results |

## Identity and access

Bind results to the exact tasks, inputs, references, verifiers, adapters and runner by comparing bytes with a retained read-only copy, or a clean revision plus local changes; exclude runs and caches. Bind conditions separately. A resumed run rejects changed task, verifier, condition or repetition definitions and any missing, extra, foreign or inconsistent record. Re-scoring saved outputs records a new verifier result, not a fresh attempt. Redact credentials.

Stage only public task material in the solver's workspace. Never put evaluator answers, hidden checks or rubrics in a solver prompt. State which access boundaries are enforced and which are conventions.

## Adapters

An adapter runs the real candidate on one public task in an isolated workspace with its condition and remaining budget, and returns delivered artifacts or final state, transcript, execution status and observed usage. Verifiers run afterwards, outside the solver. CLI, API, interactive and native workflow adapters preserve native behavior; interactive adapters record simulator identity and state. Without automation, provide a host-driven route and the exact evidence to capture. A canned response exercises plumbing only. An adapter to an existing benchmark or harness preserves its execution and scoring meaning and demonstrates outcome parity before claiming integration; a small local fixture may borrow its boundary without claiming to reproduce it.

## Execution

- Bound concurrency, each attempt, the whole run, total launches including retries and repeats, and spend. Admit no work past a bound; label estimated spend limits honestly.
- Isolate writable state, outputs and ports per attempt; share only immutable fixtures. Reset memory between episodes unless carryover is the claim. Record concurrency and hardware with timings.
- Persist planned attempts and each launch before dispatch, and completed records as they finish. Preserve artifacts on failure. Resume completed work without relaunch. One owner per run directory.
- Retry only declared transient infrastructure errors within a small budget. Retries keep their own records and consume budgets. Wrong answers and agent budget exhaustion are never retried.
- On deadline or interruption, stop admitting work, cancel and reap owned processes, and record uncertain remote completion or billing. Exercise the failure paths a run depends on before trusting it; name untested paths and platforms.

## Status and aggregation

Keep execution status (completed, agent-budget-exhausted, infrastructure-error, canceled, interrupted or not-launched), grading status (scored, unscored or indeterminate) and task success separate. A completed wrong answer, malformed delivered work and established non-delivery are scored failures. Agent budget exhaustion fails when completion within budget is required. Infrastructure failure, broken setup, verifier crash and unavailable capture stay unscored with reasons. Recover grading from retained evidence without relaunching the target.

Report planned, launched, completed, scored, passed, failed, unscored and canceled counts, with exclusion identities and reasons. Launch counts include retries; quality counts use planned task and repetition units. Unknown cost stays unknown; show available components.

Average scored repeats within tasks before applying predeclared weights; expose missing repeats and each metric's scored denominator. Weighted outcome credit is `sum(weight[d] * credit[d])` with nonnegative weights summing to one and credits in [0, 1]. An unjudged required dimension leaves the aggregate unavailable; labeled lower and upper bounds may fill it with 0 and 1. Full success is a separate 0/1 judgment, and known critical failures defeat it. Report full-success rate, mean outcome credit and critical-failure counts separately, per family, never blended. For comparisons, retain per-task paired differences and ties and common-task coverage, and report setup, execution, grading and total wall time separately.

## Evidence handoff

Keep three labeled groups: harness checks, including stand-ins and injected failures; benchmark validation, including admission evidence, auditor outcomes saved before disclosure, labeled outcomes and the rejection log; and agent measurements, with conditions, attempts, artifacts, scores and usage. Keep review findings, the reviewed identity, repairs, new identities and affected checks. Unresolved required validation leaves the package draft.
