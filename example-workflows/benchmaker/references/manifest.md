# Benchmark manifest profiles

This is the data dictionary for the package-owned index. Mandatory benchmark
quality is in [benchmark-quality](../standards/benchmark-quality/STANDARD.md);
research quality is in [benchmark-evidence](../standards/benchmark-evidence/STANDARD.md).
The [calibration record](calibration-record.md) owns empirical event and summary
fields. These references define layouts, not additional qualification policy.

## Compatibility and identity

An absent `schema_version` or `schema_version: 1` denotes the legacy profile.
Its locators and two-configuration/control measurements retain their existing
interpretation; no empirical calibration or eligibility is inferred. The
existing fixture remains readable without rewriting its historical bytes.

New empirical manifests use `schema_version: 2` and
`profile: "empirical-calibration"`. V2 retains every component and provenance
field below, and adds the explicit configuration, coverage, policy, split,
lifecycle and external calibration-record fields. Unknown versions/profiles
are unsupported, not implicitly legacy or calibrated. Known control provenance
remains control provenance regardless of an `agent_attempt` label.

The benchmark identity is its git revision, supplied by the artifact carrier.
There is no `benchmark_identity`, `covered_set_digest`, or component-digest
version recipe. Record artifact hashes may establish integrity only.

## Shared fields

A locator is a workspace-resolved reference to an artifact or journal. Relative
file locators in the legacy fixture are one representation, not a universal
storage layout. External record locators bind their own result identity and
covered benchmark revision. The index may reserve a stable external journal
locator before freeze, without embedding later measurements in frozen bytes.

| Field | Data |
| --- | --- |
| `evaluation_design` | Design locator. |
| `runnable_cases` | Exact executable case-set locator. |
| `runner` | Executable interface locator. |
| `scoring` | Required-status, scoring and aggregation data locator. |
| `provenance` | Source trace, claim/case mappings and authored ancestry locator. |
| `reference_audit` | Record locator: auditor context, method and declared sample per case, fatal-flaw count, case ids and classes. |
| `attack_audit` | Record locator: dated checklist, context, per-class SUCCEEDED/FAILED/BLOCKED observations and unrepaired holes. |
| `measurement` | External measurement locator; legacy rung statuses retain legacy meaning; v2 points to a separate final record or explicit not-performed record. |
| `qualification` | Verdict-set locator, or draft-only one-entry marker `{"status":"construction-complete-qualification-pending"}`. |
| `expected_cost` | Units, per-execution limit and suite estimate. |
| `gaps` | Unresolved elements, `[]` when empty. |
| `protected_evidence` | Held-back file set, visibility, release policy and candidate-inaccessible-check identity or `null`. |
| `anchors` | Per-case external outcome anchor, or `none` with reason. |
| `builders` | Per-case builder contexts: model id, effort and host binding. |
| `qualifier` | Controls-qualifying context: model id, effort and host binding. |
| `attacker` | Attack context: model id, effort and host binding. |
| `resolution` | Smallest reportable difference: maximum of measured rerun spread and one case in declared units. |
| `retirement_trigger` | Declaration; observed firing belongs in external measurement. |
| `incomparability` | Identity boundaries including model, effort, host and scaffold. |

Qualification entries retain `verdict`, `oracle`, `oracle_class`, `evidence`,
`covers` and `required`. The pending marker describes an unqualified draft;
it carries no accepted validity or consumer eligibility. Qualification records
also locate builder/qualifier-disjoint reference audit evidence and bind the
fixed input revision. Optional unverified criteria remain distinguishable from
required unverified criteria.

## V2 additions

| Field | Data |
| --- | --- |
| `target_configuration` | Full fixed configuration object or immutable locator, using the configuration fields below. |
| `coverage` | Construct/failure mappings; strata, case ids, floors, case/stratum weights and explicit coverage gaps. |
| `calibration_policy` | Predeclared development/final sampling design, estimator weights/unit, trials, retry/exclusion policy, revision/sample budgets, inclusive band and uncertainty requirement. |
| `splits` | Development, confirmation and final ids, or independently seeded generation specification; access class distinguishes public/development confirmation from protected final. |
| `lifecycle` | Draft/frozen phase and freeze-policy evidence locator; frozen revision is carried externally to avoid a self-referential git hash. |
| `calibration_record` | External journal/result locator for all round summaries, revision ledger and separate final-record identity. |

`target_configuration` describes target artifact, model id/version, effort,
host/CLI version, scaffold/prompt identity, tools/network, delegation authority,
context policy, temperature/seed when exposed, time/token limits and grader
identity. Actual unavailable metadata is represented with its reason rather
than a guessed value. Requested/resolved observations live in each attempt.

Each case record contains `case_id`, `construct`, `failure_class`, `provenance`,
`stratum`, `execution_tier`, `expected_cost`, `visible_contract`,
`reference_solution`, `oracle_class`, `required_criteria`, `split`, and
`revision_ancestry`. Component files can carry these records; the manifest
indexes them rather than duplicating mutable copies.

Calibration policy has `case_ids`, `trials_per_case`, `split`, `round`, `band`
and `target_configuration` for the executable finite-suite profile. Its
predeclaration also fixes strata/case weights, independent unit, order/seed or
explicit unused reason, retry/exclusion policy, development/final sets,
revision cap (default two), sample budget and uncertainty rule. Advanced
sampling designs remain explicit unsupported executable profiles until a
corresponding implementation exists; they are not silently flattened.
