# changelog benchmark package — interchange formats

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
a nonzero exit. Worked example:

```json
{"pass": false, "cases": [{"id": "mc1-entry-sequence", "pass": false}]}
```

`pass` is the whole-suite boolean; `cases` holds one
`{"id": ..., "pass": ...}` object per runnable case. Each runnable
case record names its domain under a `domain` key (`"code"` or
`"doc"`).

## Qualification component

A JSON object with `entries`, `gaps` and `overall`. Each entry carries
`criterion`, `verdict`, `oracle`, `oracle_class`, `evidence`, `covers`
and `required`; `overall` is an object carrying the aggregate verdict:

```json
{"verdict": "PASS"}
```

`gaps` is always present as a list.

## Provenance chain

The provenance component is a JSON object whose `chain` field records
the two chained single-pack constructions, joined by a frozen evidence
identity: each link names its `pack`, its frozen `output_identity`,
and — from the second link on — the `consumes_identity` it was built
from, equal to the upstream link's `output_identity`. Identities are
`sha256:`-prefixed 64-hex strings. Worked fragment:

```json
{
  "chain": [
    {"pack": "orch-code-pack", "output_identity": "sha256:<hex-1>"},
    {"pack": "orch-content-pack", "consumes_identity": "sha256:<hex-1>", "output_identity": "sha256:<hex-2>"}
  ]
}
```

The chain has at least two links and the links name two distinct
packs.
