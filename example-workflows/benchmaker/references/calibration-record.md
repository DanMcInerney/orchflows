# External calibration record

This data dictionary owns empirical attempt and summary field meanings.
[Manifest](manifest.md) owns the package index and configuration description;
[benchmark-quality](../standards/benchmark-quality/STANDARD.md) owns all required
validity, calibration and protection criteria. Records live outside the frozen
benchmark package, bind its git revision, and have separate result identities.

## Attempt

An attempt is one actual isolated execution, not a control score or aggregate.
Its `(benchmark_revision, split, round, case_id, trial)` tuple is unique. Trial
is a stable attempt index, including excluded infrastructure events; an allowed
retry remains a separately attributable event with its predecessor/reason.
Locators are absolute under the durable external export; its bytes are committed
in a separate record subtree of the same integration repository.

| Field | Shape and meaning |
| --- | --- |
| `case_id` | Stable case id. |
| `split` | Declared development, confirmation or final split. |
| `round` | Declared sampling-round identity. |
| `trial` | Trial index within that case/round. |
| `case_binding` | Resolved committed manifest/case/split, prompt, input inventory, checks and required oracle; receipt input snapshots bind what the native subject received. |
| `retry_of` | Null for declared primary samples; otherwise an earlier excluded infrastructure trial index in the same case/round, replaced at most once. |
| `target_configuration` | Full object or immutable locator to the fixed configuration. |
| `benchmark_revision` | Full git revision of measured benchmark bytes. |
| `candidate_kind` | `agent_attempt` or `control`; provenance determines classification, never the label alone. |
| `requested_command` | Native argv array, with no shell interpolation. |
| `resolved_command` | Observed native argv array. |
| `requested_configuration` | Requested configuration object. |
| `resolved_configuration` | Observed configuration object; unavailable fields carry reasons, including an `unavailable_reason` object when resolution failed. |
| `prompt_locator` | Actual candidate-visible input artifact. |
| `raw_transcript_locator` | Complete native stdout/event transcript artifact. |
| `result_artifact_locator` | Actual candidate output artifact, or explicit unavailable reason. |
| `launch_receipt_locator` | Observed subprocess command, configuration, exit and timing receipt. |
| `grader_observation_locator` | Separate deterministic grader or anchored oracle observation. |
| `classification` | `completed`, `candidate_failure`, `task_timeout`, `startup_timeout`, `permission_failure`, `launch_failure` or `environment_failure`. |
| `evaluator_classification` | `completed`, `environment_failure` or `unsupported`; never overwrites the native `classification`. |
| `exit_code` | Observed process exit, or unavailable reason where no process started. |
| `elapsed_seconds` | Observed nonnegative wall time. |
| `token_usage` | Native-reported usage or explicit unavailable reason. |
| `oracle_outcome` | Observed outcome status; unavailable oracle evidence remains explicit. |
| `failure_class` | Named observed failure class, or explicit none/unavailable reason. |
| `valid_for_estimate` | Boolean inclusion under the fixed policy. |
| `exclusion_reason` | Reason for exclusion, otherwise explicit none. |

A launcher/environment/permission failure is distinct from a candidate failing
its task after a usable environment exists. A completed native process may
produce missing or wrong source: that is candidate failure, with the transcript
and failed grader/extraction observation preserved. `task_timeout` after an
established native turn is a counted failure;
`startup_timeout` is excluded infrastructure. The predeclared execution
boundary/policy identifies this distinction; infrastructure exclusions never
become target failures by omission. An explicit resolved-configuration
unavailable reason produces UNVERIFIED;
omitting the configuration is a malformed record. Raw token counts, model
versions and prices are observations, not synthetic estimates.

Control records use their real provenance and cannot contribute to agent
pass@1. Legacy known-good/bad scripts remain controls even when wrapped in a
native-looking receipt. A record schema label alone is no native-execution
proof; transcript, receipt, output and independent oracle linkage are the
observable evidence.

## Summary

Each summary identifies `benchmark_revision`, fixed `target_configuration`,
`split`, `round`, its policy and the complete attempt record locators. The
finite-suite executable policy uses equal case weights; explicitly different
weights/designs remain separate supported implementations or declared gaps.

| Field | Meaning |
| --- | --- |
| `validity` | Lossless revision-bound VALID, INVALID or UNVERIFIED qualification. |
| `estimator` | pass@1 definition and computation, never best-of-k. |
| `weights` | Actual case/stratum weights. |
| `independent_unit` | Sampling unit and fixed-case repeat interpretation. |
| `per_case` | `attempted`, `valid`, `passed`, `failed`, `invalid`, `unverified`, `controls`, `failure_classes`, `estimate`, `interval`, `interval_assumption`. |
| `distinct_cases` | Count of distinct cases, separate from repetitions. |
| `total_attempts` | Total attempted events, with valid/excluded totals separately represented. |
| `estimate` | Finite-suite pass@1 or explicit unavailable reason. |
| `interval` | Bounds, method and assumptions, or `null`; per-case intervals are conditional on their case. |
| `interval_unavailable_reason` | Reason no aggregate interval is reported, otherwise explicit none. |
| `band_observation` | `IN_BAND`, `OUT_OF_BAND` or `UNVERIFIED` numeric observation, independent of eligibility. |
| `decision` | `INVALID`, `UNVERIFIED`, `OUT_OF_BAND` or `CALIBRATED`, with required criterion evidence/gaps. |
| `criterion_gaps` | Missing evidence by criterion, distinguishing required and optional. |


The numeric band observation survives higher-priority validity or evidence
problems. A finite-suite IN_BAND observation can coexist with UNVERIFIED
calibration when the declared uncertainty or isolation requirement is unmet.
The record distinguishes conditional per-case uncertainty from population
inference; repetition count is never substituted for distinct-case sample size.
Optional configuration comparisons use separate records and paired case
observations, not a replacement calibration target.

## Final measurement and admission observations

A final record identifies the frozen revision, configuration, cases/sampling
policy, permitted candidate scope, evidence-access observations, actual
attempts, recomputed summary and date. Its `evaluation_scope` distinguishes
`protected_final` from `public_confirmation` or `development`; protection
status includes the actual access mechanism and adversarial probe observation.
Before/after measured-byte identity observations demonstrate unchanged frozen
content. Final failure and drift remain external observations.

Workflow admission and calibrated benchmark eligibility are separate probe
observations. A useful INVALID/UNVERIFIED/OUT_OF_BAND partial artifact can have
valid workflow admission evidence while remaining ineligible for calibration
consumers. An unavailable native tool or zero actual attempts is an explicit
live-admission gap, not evidence that the workflow executed. Admission receipts
locate source package commit, runtime run/frame/ticket identities, standard
pins, landed artifacts, independent findings, outside probe exits, launch and
case/trial totals, spend and unexecuted branches.

The first `trials_per_case` attempt indices are primary slots. Every later
attempt names `retry_of`, whose event must be excluded for native or grader
infrastructure. A predecessor can be replaced only once; valid slots never
exceed the declared sample, and all replacements share the round's allocated
`infrastructure_retry_budget`. The admission envelope also declares the global
retry allocation across every round. No extra valid sampling is a partial estimate.

Configuration policy lists `required_configuration_fields` and
`optional_configuration_fields` as dotted paths. Fields default to required;
nested unavailable markers remain gaps even when requested and resolved JSON
are equal. Optional unavailable seed/temperature metadata stays in
`optional_gaps`. Required instruction, scaffold, delegation and capability
observations cannot be satisfied by copied placeholders.

`revision_ledger`, `frozen_revision`, `final_record`, diagnostic
`development_evidence` and `terminal_gaps` belong to the final aggregate index,
not per-round summaries. Each round's `snapshot_kind` is
`immutable-round-observation`. It is compared with its own fixed policy,
qualification and criterion gaps, never future metadata.

An unsupported evaluator capability is an excluded UNVERIFIED oracle observation,
not an infrastructure event eligible for a retry and not a genuine candidate FAIL.
The fixed source profile and its limitation are declared before execution.
