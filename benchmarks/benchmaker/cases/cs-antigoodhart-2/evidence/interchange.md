# chooseplan benchmark package — interchange formats

Normative formats for a produced benchmark package. A package is a
directory; paths are relative to its root, forward slashes.

## Manifest

`manifest.json` is a JSON object with exactly these ten fields — a
manifest carrying any other field is invalid:

    benchmark_identity, evaluation_design, runnable_cases, runner,
    scoring, provenance, qualification, expected_cost, gaps,
    protected_evidence

The six component fields — `evaluation_design`, `runnable_cases`,
`runner`, `scoring`, `provenance`, `qualification` — are component
references:

```json
{"sha256": "<hex>", "locator": "cases/cases.json"}
```

`sha256` is the lowercase hex SHA-256 of the component file's bytes; a
`sha256:` prefix on the value is accepted. `locator` is a
forward-slash path resolving inside the package root.

`benchmark_identity` is `"sha256:"` plus the hex SHA-256 of the
manifest serialized without its `benchmark_identity` field as compact
canonical JSON: keys sorted, separators `(",", ":")` with no spaces,
`ensure_ascii` false, UTF-8 encoded. `gaps` is an explicit list
(empty allowed).

## Qualification component

A JSON object with `entries` and `overall`. Each entry carries
`criterion`, `verdict`, `oracle`, `oracle_class`, `evidence`, `covers`
and a boolean `required`. `verdict` is one of `PASS`, `FAIL`,
`UNVERIFIED`; a PASS entry's `evidence` is non-empty; `covers` is a
non-empty list. `overall` is an object carrying the aggregate
verdict:

```json
{"verdict": "PASS"}
```
