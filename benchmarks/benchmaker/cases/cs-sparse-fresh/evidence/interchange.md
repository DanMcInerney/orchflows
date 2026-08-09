# QML-lite linter benchmark package — interchange formats

Normative formats for a produced benchmark package. A package is a
directory; paths are relative to its root, forward slashes.

## Manifest

`manifest.json` is a JSON object with exactly these ten fields:

    evaluation_design, runnable_cases, runner, scoring, provenance,
    qualification, expected_cost, gaps, protected_evidence, anchors

`anchors` binds each case to the reference outside the package its
expected outcome is measured against, or declares `none` with its
reason. A case left silent is invalid; a declared `none` is not.

These are recorded once qualification closes and are not re-derivable
afterwards, which is why the manifest carries them. Other
post-qualification fields may be present and are not read here.

The six component fields — `evaluation_design`, `runnable_cases`,
`runner`, `scoring`, `provenance`, `qualification` — are component
references naming the component's package-relative path:

```json
{"locator": "cases/cases.json"}
```

`gaps` is an explicit list.

## Runner and scoring interface

The runner is invoked as `python <runner> <impl-dir>`; it prints the
results as JSON on stdout and exits 0. Scoring is invoked as
`python <scoring> <results-file>` with those results saved to a file;
it prints exactly `PASS` or `FAIL` on stdout.

## Case records and licensed behavior slugs

Each record in the case set's `cases` list names the documented
behavior it exercises under `rule` and the documenting spec line under
`cites`, in the form `spec.md#<line-id>`. The licensed slugs and their
documenting lines:

| `rule` slug      | documenting line |
|------------------|------------------|
| `key-syntax`     | `spec.md#L03`    |
| `value-type`     | `spec.md#L05`    |
| `comment`        | `spec.md#L07`    |
| `section-header` | `spec.md#L09`    |

Worked record:

```json
{"id": "k1", "rule": "key-syntax", "cites": "spec.md#L03", "input": "alpha = 1\n", "expect_findings": []}
```

No case asserts semantics outside this table, and each case cites
exactly the line documenting its rule.

## Gap register

The manifest `gaps` list is non-empty: it names the undocumented
constructs left uncased (the examples the spec marks undocumented).
Gap entries reference undocumented material only — a gap entry never
contains any of the documenting line ids `L03`, `L05`, `L07` or `L09`.

## Qualification component

A JSON object with `overall` (the aggregate verdict string, `"PASS"`
or `"FAIL"`), `entries` and `gaps`. Each entry carries `criterion`,
`verdict`, `oracle`, `oracle_class`, `evidence` (a non-empty string
for a PASS), `covers` (non-empty list) and `required`. `gaps` is
always present as a list.
