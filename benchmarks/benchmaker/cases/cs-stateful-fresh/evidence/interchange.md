# migrate benchmark package — interchange formats

Normative formats for a produced benchmark package. A package is a
directory; paths are relative to its root, forward slashes.

## Manifest

`manifest.json` sits at the package root and is a JSON object carrying
these ten fields:

    benchmark_identity, evaluation_design, runnable_cases, runner,
    scoring, provenance, qualification, expected_cost, gaps,
    protected_evidence

The six component fields — `evaluation_design`, `runnable_cases`,
`runner`, `scoring`, `provenance`, `qualification` — are component
references of this exact shape:

```json
{"identity": "sha256:<hex>", "locator": "cases/cases.json"}
```

`identity` is the lowercase hex SHA-256 of the component file's bytes,
prefixed `sha256:`. `locator` is the component's package-relative
path.

`benchmark_identity` is `"sha256:"` plus the hex SHA-256 of the
manifest serialized without its `benchmark_identity` field as compact
canonical JSON: keys sorted, separators `(",", ":")` with no spaces,
`ensure_ascii` false, UTF-8 encoded.

## Runner report

The runner is invoked as `python <runner> <implementation-dir>` and
prints one JSON object on stdout. A passing implementation gets
`"pass": true` and exit status 0; any failure is `"pass": false` with
a nonzero exit. Each case record carries the two-run transcript: a
`runs` list with one entry per execution, each recording the state
directory that execution ran against — both runs of a case use the
same state directory, so the second run meets the state the first run
itself produced. Worked example:

```json
{"pass": true, "cases": [{"id": "c1", "pass": true, "runs": [{"state_dir": "s1"}, {"state_dir": "s1"}]}]}
```

## Qualification component

A JSON object with `entries`, `gaps` and `overall`. Each entry carries
`criterion`, `verdict`, `oracle`, `oracle_class`, `evidence`, `covers`
and `required`; `overall` is an object carrying the aggregate verdict:

```json
{"verdict": "PASS"}
```

`gaps` is always present as a list.
