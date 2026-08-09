# Package interchange contract

The interface every consumer of a benchmark package for this target
relies on. A package that departs from any shape below is rejected.

## Manifest

`manifest.json` sits at the package root and carries exactly these ten
fields:

    evaluation_design, runnable_cases, runner, scoring, provenance,
    qualification, expected_cost, gaps, protected_evidence, resolution

`resolution` records `one_case`, `measured_rerun_spread` (a number, or
null beside a `note`) and a `smallest_reportable_difference` whose
leading figure is max(spread, one case).

These are recorded once qualification closes and are not re-derivable
afterwards, which is why the manifest carries them. Other
post-qualification fields may be present and are not read here.

Each of the six components — `evaluation_design`, `runnable_cases`,
`runner`, `scoring`, `provenance`, `qualification` — is a reference
object of exactly this form:

    {"locator": "<posix-relative-path>"}

Locators are forward-slash paths relative to the package root and must
resolve inside it, to a file or to a directory.

## Layout

Whatever the locators say, consumers resolve these fixed paths inside
the package:

    cases/cases.json
    runner/run.py
    scoring/policy.json
    scoring/aggregate.py
    provenance/notes.md          (or provenance/evaluation-design.md)
    qualification/qualification.json

When the `qualification` locator is a directory, the record inside it
is named `qualification.json`.

## Qualification record

`qualification.json` is a JSON object with:

- `entries`: non-empty list of entry objects, each carrying all of
  `criterion`, `verdict`, `oracle`, `oracle_class`, `evidence`,
  `covers`, `required`. `verdict` is one of `PASS`, `FAIL`,
  `UNVERIFIED`; `oracle_class` is one of `deterministic`, `judged`,
  `evidence`; `required` is a boolean. A `PASS` entry's `evidence` is a
  non-empty string.
- `gaps`: an explicit list (`[]` allowed).
- `overall`: a string, one of `PASS`, `FAIL`, `UNVERIFIED`. `PASS`
  cannot coexist with a required `FAIL` entry.

## Scoring policy

`scoring/policy.json` declares the trial law with these keys:

    {"trial_count": 3, "aggregation": "all-trials"}

`trial_count` is an integer, at least 3; `aggregation` is the literal
string `all-trials`. Additional descriptive keys are permitted.

## Runner and aggregation command lines

The runner is invoked as

    python runner/run.py <impl-dir> --out <results.json> [--cases <cases.json>]

and exits 0 after writing the results file (an implementation failing
its trials is still a successful run). Aggregation is invoked as

    python scoring/aggregate.py <results.json> --policy scoring/policy.json

and its exit code is the verdict: 0 when every case passes under the
policy, nonzero otherwise.

## Results record

The runner writes a JSON object of this shape:

    {"cases": [{"id": "anchored-trace", "trials": ["PASS", "PASS", "PASS"]}]}

Each case record carries the case `id` and a `trials` list of exactly
`trial_count` entries, each the string `PASS` or `FAIL`.

## Anchored case

The case set binds the exhibited run (evidence/trace.md) with a case
record of this shape — `anchor` is the literal path string, `stream`,
`seed` and `k` repeat the exhibited run, and `expected` is a list of
per-trial samples whose first element is the exhibited sample:

    {
      "id": "anchored-trace",
      "anchor": "evidence/trace.md",
      "stream": ["item-00", "item-01", "item-02", "item-03", "item-04",
                 "item-05", "item-06", "item-07", "item-08", "item-09"],
      "seed": 14,
      "k": 3,
      "expected": [["item-03", "item-01", "item-02"], ...]
    }

Unanchored cases record `"expected": null`. If anchoring the exhibited
run is impossible, `provenance/notes.md` or
`provenance/evaluation-design.md` records one line

    anchor-impossibility: <substantive reason>

where the reason is non-empty and is not merely "implementation
artifact".
