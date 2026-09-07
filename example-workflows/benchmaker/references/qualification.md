# Qualification record

This layout indexes the fixed evidence returned by the private qualification
workflow. Mandatory quality belongs to
[benchmark-quality](../standards/benchmark-quality/STANDARD.md); shared criterion
fields belong to [manifest](manifest.md). It is consumed initially by benchmaker
and again by calibration after development revisions. It is not a new artifact
adapter or a second benchmark identity.

## Inputs and carriers

`draft` is the caller's exact `artifact: git:<full-commit>` identity, passed to
each judge through `--artifacts git:<full-commit>`. Component locators resolve
against that revision. Goal/Details carry coverage, rigor, construction standard,
budget allocations, access policy, builder identities and audit sample; Context
carries provenance and prior findings where relevant. Findings are relayed as
`findings: <path>`, with their immutable review-ticket identities, never cast as
`git:` artifacts. There is no synthetic commit for a judge's findings file.

The workflow frame closes over the returned record and evidence locators. The
caller preserves that return in its journal; an external measurement collector
may serialize it beside empirical records without editing the qualified draft.
A later manifest update creates a different revision and cannot inherit this
record's verdict by omission.

## Returned fields

| Field | Representation |
| --- | --- |
| `benchmark_revision` | Exact full input draft commit. |
| `validity` | VALID, INVALID or UNVERIFIED, with evidence-backed reasons. |
| `qualification` | Entries with `verdict`, `oracle`, `oracle_class`, `evidence`, `covers`, `required`, as defined in manifest. |
| `controls_review` | Run/frame/ticket, findings locator, standard pins, qualifier context and per-case command/evidence locators. |
| `reference_audit` | Run/frame/ticket, findings locator, standard pins, auditor context, predeclared sample, prompt-first artifact locators, comparisons and fatal-flaw counts/case ids/classes. |
| `attack_audit` | Run/frame/ticket, findings locator, standard pins, attacker context, date, permitted scope, access-mechanism observations, checklist results and unrepaired holes. |
| `independence` | Builder contexts plus qualifier, reference auditor and attacker context identities, model/effort/host observations and disjointness evidence or unavailable reason. |
| `spend` | Declared allocations and actual elapsed/cost observations; unavailable values have reasons. |
| `gaps` | Criterion, required/optional flag, affected case/scope and reason; empty is `[]`. |

Each nested review repeats the covered revision. Mixed-revision evidence is a
gap, never an implicitly updated qualification. Reference correctness and control
separation are separate evidence fields, even when both concern the same case.
Attack status uses SUCCEEDED/FAILED/BLOCKED per tested class; it is not itself a
validity status. A working contamination attack is interpreted under the pinned
standard for the claimed evaluation scope. Public development confirmation can
retain its actual scope while protected-final evidence remains UNVERIFIED.

## Consumer projection

The admission envelope's existing `qualification.instrument_valid` is true only
for VALID; INVALID and UNVERIFIED both project to false. Preserve the typed
`validity` and required criterion gaps beside that boolean so missing evidence
is not relabeled as demonstrated invalidity by a collector. Its per-case `audits`
rows (`case_id`, `benchmark_revision`, `builder`, `auditor`, `reference_outcome`,
`inert_outcome`, `near_miss_outcome`, `evidence_locator`) index control observations;
that compact projection does not replace the separate reference and attack
records or prove all independence relationships. Calibration consumes the full
record and gates eligibility on required evidence, not this boolean alone.

## Semantic review examples

These examples describe review seams, not proof that workflow prose executed:

- Shared builder/reference-auditor identity leaves independence UNVERIFIED even
  with passing controls and an apparently correct key.
- Good/inert/near-miss separation without a prompt-first comparison leaves
  reference correctness UNVERIFIED.
- One required UNVERIFIED entry prevents VALID; an optional gap remains visible
  without automatically rejecting otherwise complete required evidence.
- Findings over a different draft cannot qualify the current input; changed
  cases or shared graders return to making and fresh qualification.
- A blocked attack without enforced read exclusion supplies no protected-final
  acceptance, even if the candidate workspace lacks answer files.
