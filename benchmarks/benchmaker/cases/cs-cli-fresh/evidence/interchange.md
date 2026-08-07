# csvmerge benchmark package — interchange formats

Normative formats for a produced benchmark package. A package is a
directory; every path below is relative to its root and uses forward
slashes.

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
canonical JSON: keys sorted, separators `("," , ":")` with no spaces,
`ensure_ascii` false, UTF-8 encoded.

## Runner report

The runner is invoked as `python <runner> <implementation-dir>` and
prints one JSON object on stdout. A passing implementation gets
`"pass": true` and exit status 0; any failure is `"pass": false` with
a nonzero exit. Worked example:

```json
{"pass": false, "cases": [{"id": "c1", "pass": false}]}
```

`pass` is the whole-suite boolean; `cases` holds one
`{"id": ..., "pass": ...}` object per runnable case.

## Case records

The runnable-cases component is a JSON object whose `cases` field is a
list of case records. In `argv`, the placeholders `{a}` and `{b}`
stand for the paths of the two input files whose contents the `a` and
`b` fields carry. A record either anchors one exhibited transcript by
its id or carries `"anchor": null`. Worked record, anchored to
transcript `t1`:

```json
{
  "id": "c2",
  "argv": ["{a}", "{b}"],
  "a": "1,alpha\n3,gamma\n5,epsilon\n",
  "b": "2,beta\n3,delta\n",
  "stdout": "1,alpha\n2,beta\n3,gamma\n5,epsilon\n",
  "exit": 0,
  "anchor": "t1"
}
```

An anchored record reproduces its transcript exactly: `argv` after
placeholder substitution, both input file contents, `stdout` and
`exit`. When no case can anchor any transcript, the case set records a
top-level `"anchor_impossibility": "<reason>"` string; the reason must
be substantive — "implementation artifact" is not acceptable.

## Qualification and provenance

The qualification component is a JSON object with `entries`, `gaps`
and `overall`. Each entry carries `criterion`, `verdict`, `oracle`,
`oracle_class`, `evidence`, `covers` and `required`. The `evidence`
value of an entry is an object whose `context` field names the context
that produced the verdict; for a required entry that context must be
one other than the building context, which the provenance component
records under `builder_context`. Worked entry:

```json
{
  "criterion": "discrimination",
  "verdict": "PASS",
  "oracle": "runner sweep over the fixed inner pool",
  "oracle_class": "deterministic",
  "evidence": {"context": "<qualifying-context-id>", "summary": "..."},
  "covers": ["runnable_cases sha256:<hex>"],
  "required": true
}
```

`overall` is an object carrying the aggregate verdict:

```json
{"verdict": "PASS"}
```

`gaps` is always present as a list, empty when nothing is unverified.
The provenance component is a JSON object; its `builder_context`
string names the context that built the package.
