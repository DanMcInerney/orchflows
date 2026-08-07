# dateparse benchmark package — interchange formats

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
results as JSON on stdout and exits 0. Scoring is invoked as
`python <scoring> <results-file>` with those results saved to a file;
it prints exactly `PASS` or `FAIL` on stdout.

## Case records and citations

Each record in the case set's `cases` list carries `id`, `topic`,
`argv` (a list of strings), `expect` and `cites` (a list of citation
strings). A citation is `<doc>.md#<line-id>` and resolves into the
exhibited line-id-addressed evidence: `doc-a.md#A04`, `doc-b.md#B04`,
`settlement.md#S02`. Worked record — a case for the settled point
cites the settlement artifact:

```json
{
  "id": "c4",
  "topic": "two-digit-year-pivot-strict",
  "argv": ["--strict", "85-03-14"],
  "expect": {"status": 0, "out": "2085-03-14"},
  "cites": ["settlement.md#S02"]
}
```

## Disagreement register

The package records the open disagreement in a register carried by
the provenance component, in either of two equivalent forms.

Embedded JSON — the provenance object's `disagreements` field:

```json
{
  "disagreements": {
    "open": [
      {"topic": "leap-second-acceptance", "citations": ["doc-a.md#A06", "doc-b.md#B06"]}
    ],
    "settled": [
      {"topic": "two-digit-year-pivot-strict", "citations": ["settlement.md#S02"]}
    ]
  }
}
```

Markdown file — the provenance object's `disagreements_file` field
names a package-relative markdown file with `## Open` and `## Settled`
sections whose entries are bullets, topic first, an em dash, then the
citations:

```markdown
## Open

- leap-second-acceptance — cites: doc-a.md#A06, doc-b.md#B06

## Settled

- two-digit-year-pivot-strict — cites: settlement.md#S02
```

In both forms an open entry cites into both disagreeing documents, and
a settled point appears only under Settled.
