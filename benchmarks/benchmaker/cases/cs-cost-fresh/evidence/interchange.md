# Package interchange contract

The manifest and qualification shapes every consumer of a benchmark
suite for this target relies on. A suite that departs from any shape
below is rejected. Budget, corpus-pin and scoring-invocation shapes
are in `spec.md`.

## Manifest

`manifest.json` sits at the package root and carries exactly these ten
fields:

    evaluation_design, runnable_cases, runner, scoring, provenance,
    qualification, expected_cost, gaps, protected_evidence, measurement

`measurement` records `candidates`, `scope`, `per_case_status` drawn
from `both-pass`/`split`/`both-fail`/`inversion`,
`distinct_failure_signatures` and `margin_cases`.

These are recorded once qualification closes and are not re-derivable
afterwards, which is why the manifest carries them. Other
post-qualification fields may be present and are not read here.

`gaps` is an explicit list (`[]` allowed).

Each of the six components — `evaluation_design`, `runnable_cases`,
`runner`, `scoring`, `provenance`, `qualification` — is a reference
object of exactly this form:

    {"locator": "<posix-relative-path>"}

The locator is a forward-slash path that resolves to a single file
inside the package.

## Qualification record

The qualification component is a JSON object whose `entries` is a
non-empty list of entry objects, each carrying all of `verdict`,
`oracle`, `oracle_class`, `evidence`, `covers`, `required`. A `PASS`
entry's `evidence` is non-empty. The record's `overall` is a verdict
string; `"PASS"` cannot coexist with an entry that is both
`"verdict": "FAIL"` and `"required": true`.
