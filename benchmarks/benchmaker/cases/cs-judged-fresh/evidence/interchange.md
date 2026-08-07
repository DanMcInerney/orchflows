# Minutes-condenser benchmark package — interchange formats

Normative formats for a produced benchmark package. A package is a
directory; paths are relative to its root, forward slashes.

## Manifest

`manifest.json` is a JSON object with exactly these ten fields — no
more, no fewer:

    benchmark_identity, evaluation_design, runnable_cases, runner,
    scoring, provenance, qualification, expected_cost, gaps,
    protected_evidence

The six component fields — `evaluation_design`, `runnable_cases`,
`runner`, `scoring`, `provenance`, `qualification` — are component
references whose digest is the bare lowercase hex SHA-256 of the
component file's bytes (no prefix):

```json
{"sha256": "<hex>", "locator": "cases/cases.json"}
```

`benchmark_identity` is `"sha256:"` plus the hex SHA-256 of the
manifest serialized without its `benchmark_identity` field as compact
canonical JSON: keys sorted, separators `(",", ":")` with no spaces,
`ensure_ascii` false, UTF-8 encoded. `gaps` is an explicit list.

## Runner and scoring interface

The runner is invoked as `python <runner> <impl-dir>`; it prints the
results records to stdout as JSON and exits 0. Scoring is invoked as
`python <scoring> <results-file>` with the results saved to a file; it
prints exactly `PASS` or `FAIL` on stdout and exits 0.

Results records are a JSON list, one record per criterion, in exactly
this shape — deterministic and judged records:

```json
[
  {"id": "cite-resolve", "class": "deterministic", "required": true, "verdict": "PASS"},
  {"id": "judged-coverage", "class": "judged", "secondary": true, "required": false, "score": 2}
]
```

Deterministic records carry a `verdict` of `PASS` or `FAIL`; judged
records carry a numeric `score` on the criterion's declared scale and
never a gating verdict.

## Case-set component

The runnable-cases component is a JSON object with a `deterministic`
array and a `judged` array. Worked fragment:

```json
{
  "deterministic": [
    {"id": "cite-resolve", "required": true}
  ],
  "judged": [
    {
      "id": "judged-coverage",
      "criterion": "decision coverage quality",
      "secondary": true,
      "scale": [0, 1, 2],
      "anchors": [
        {"level": 2, "cite": "m2-04", "note": "a level-2 rendering carries this decision"},
        {"level": 0, "cite": "m4-05", "note": "a level-0 rendering omits this rejection"}
      ]
    }
  ]
}
```

Every judged criterion is `"secondary": true`, declares its `scale`,
and carries at least two `anchors` spanning at least two scale levels;
each anchor's `cite` is a source line id (`m<meeting>-<line>`, e.g.
`m2-04`) resolving into the exhibited sources.

## Qualification component

A JSON object with `overall`, `entries`, `gaps` and `judge_variance`.
`overall` is the aggregate verdict string, `"PASS"` or `"FAIL"`.
Each entry carries `criterion`, `verdict`, `oracle`, `oracle_class`,
`evidence` (a non-empty string for a PASS), `covers` (non-empty list)
and `required`. `gaps` is always present as a list.

`judge_variance` is a list with one record per judged criterion,
recorded before the package seals:

```json
{
  "criterion": "judged-coverage",
  "reruns": 3,
  "scores": [2, 2, 1],
  "spread": 1,
  "recorded_at": "2026-08-07T05:10:00Z",
  "covers": "runnable_cases@sha256:<hex>"
}
```

`reruns` is an integer of at least 3 and `scores` lists exactly one
score per rerun.

## Provenance component

A JSON object whose `sealed_at` field is an ISO-8601 UTC timestamp
(string-comparable); every `judge_variance.recorded_at` precedes it.
