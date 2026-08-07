# Package interchange contract

The manifest and qualification shapes every consumer of a benchmark
suite for this target relies on. A suite that departs from any shape
below is rejected. The limiter surface, case op vocabulary and scoring
invocation are in `interface.md`.

## Manifest

`manifest.json` sits at the package root and carries exactly these ten
fields — no extras, none missing:

    benchmark_identity, evaluation_design, runnable_cases, runner,
    scoring, provenance, qualification, expected_cost, gaps,
    protected_evidence

`gaps` is an explicit list (`[]` allowed). `benchmark_identity` is a
`sha256:`-prefixed hex string recomputable from the canonical payload:
the manifest object minus `benchmark_identity`, serialized as JSON
with sorted keys, compact separators `(",", ":")` and
`ensure_ascii=False`, digested as UTF-8.

Each of the six components — `evaluation_design`, `runnable_cases`,
`runner`, `scoring`, `provenance`, `qualification` — is a reference
object of exactly this form:

    {"identity": "sha256:<64-hex>", "locator": "<posix-relative-path>"}

The locator is a forward-slash path that resolves to a single file
inside the package; the identity is the `sha256:`-prefixed digest of
that file's bytes.

## Qualification record

The qualification component is a JSON object whose `entries` is a
non-empty list of entry objects, each carrying all of `verdict`,
`oracle`, `oracle_class`, `evidence`, `covers`, `required`. A `PASS`
entry's `evidence` is non-empty. The record's `overall` is a verdict
string; `"PASS"` cannot coexist with an entry that is both
`"verdict": "FAIL"` and `"required": true`.
