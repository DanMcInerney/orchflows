# Quality profile and acceptance

Record the requested stage, achieved stage and unmet gates separately. Execution profiles (`smoke`, `quick`, `full`) select runs; they do not certify benchmark maturity. A full run of a prototype remains a prototype. This profile supplies planning defaults, not scientific minimum case counts.

## Stages

| Stage | Required evidence |
| --- | --- |
| Prototype | Bounded claim; source and coverage inventory; public tasks and feasible reference outcomes; runnable grading controls; explicit unresolved validation. Unverified feasibility leaves the affected cases draft. |
| Calibrated pilot | Prototype evidence plus validated substantial work, independent source groups appropriate to the claim, checked alternative and partial outcomes, independent public-input audit, frozen named baseline measurements, predeclared repetitions, failure analysis and uncertainty. Semantic metrics require held-out judge calibration and adjudication. |
| Evaluation suite | Pilot gates plus a justified sampling plan and size, frozen evaluation cases from source groups unseen during development, predeclared metrics/weights/conditions/exclusions, and completed evaluation with coverage and uncertainty. Required unresolved validity defects block this stage. |

An achieved stage requires its evidence; retain finer statuses for task validity, grading, execution and access protection. Partial completion of a requested stage is a useful deliverable with an explicit gap, not permission to relabel it as achieved. Unprotected local access cannot establish protected evaluation.

## Substantial work

Use substantial user work as the default evaluation unit. An explicit smoke, compact or machinery request can use smaller fixtures, labeled as such. For a broad substantial-work request, plan roughly 40–60 independently sourced development cases and a later 150–300-case evaluation suite, adjusting to population, expense and available evidence. Explain a smaller scope and narrow its claim. Plan and execute affordable stages; never silently replace a requested suite with a handful of examples or launch the whole plan without a bounded execution budget.

For each case retain a short work dossier:

- Source request/artifact/issue or practitioner account, provenance and transformations; mark synthetic reconstructions and unvalidated realism.
- User objective and usable deliverables; interacting constraints, evidence or state dependencies that make the work substantive.
- Representative inputs, information-discovery requirements, allowed tools/authority and realistic resources.
- Feasible reference execution, expert check or appropriate feasibility proof; alternatives and practitioner validation when available, with missing validation explicit.

Build a coverage matrix before expanding cases: family, source group, track, split, difficulty factors and validation evidence. Report case count, unique source-group count and independent work families separately. Renamed variants and grader assertions are not new families or independent work. File/action counts and estimated human effort describe work; none alone is an acceptance threshold.

## Tracks and calibration

Keep a representative-work track when estimating practical performance. A challenge track samples harder valid work and supports a different claim. For a requested challenge track, default to a **30–50% full-task success objective for a named strong baseline on development cases**, unless the caller specifies another range. This is this profile's calibration objective, not a required mean partial score, universal quality rule or guarantee for unseen cases.

Before launches, freeze the baseline's observable model/settings, framework/instructions, tools/permissions, environment, realistic resource budget and repetitions. Unknown settings limit reproducibility. Predeclare a repeated subset; repeats estimate variation, not source diversity. Include a materially different comparator where feasible or record its absence and narrower comparison claim.

Inspect failures and partial outputs before interpreting difficulty: distinguish capability failures from task defects, unfair grading, infrastructure failure and unknown observation. If development tasks are too easy, sample more demanding source work. Do not tune individual cases to defeat a model, insert hidden constraints or shrink resources artificially. Record development selection and exclusions.

Freeze unseen groups before final measurement. Publish out-of-band results; do not reshape that evaluation after observing answers. Later harder suites receive a new version while prior results remain intact. Difficulty remains unmeasured without real baseline execution; a requested challenge claim remains provisional without valid calibration evidence.

## Acceptance evidence

The card links each gate to retained evidence or a named gap. Deliver a coverage matrix, per-case dossiers, scoring definitions/controls, baseline and repetition plan, observed failure taxonomy, and stage decision. A plan is not observed evidence. Follow [benchmarking guidance](../guidance/benchmarking.md) for scoring validity and [benchmark contract](benchmark-contract.md) for records and aggregation.

For semantic metrics, keep rubric-development examples separate from a held-out grading sample containing correct alternatives, useful partial work, misleading near misses and incorrect/empty outputs. Save blinded judgments, independent labels, disagreements and adjudications before claiming calibration. Author labels alone leave the metric provisional. Exposed grading examples are no longer held out for subsequent tuning.
