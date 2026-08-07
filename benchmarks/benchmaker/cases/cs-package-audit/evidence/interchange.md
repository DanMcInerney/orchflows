# Sealed-package interchange contract

The shapes the caller's audit relies on when it recomputes over the
returned tree. A return that departs from any shape below is rejected.

## Returned tree

The sealed benchmark lives in a `package/` subtree at the
implementation root:

    <impl-root>/package/manifest.json
    <impl-root>/package/...        (components at their locators)

Exactly one JSON artifact anywhere in the returned tree carries a
`benchmark_identity` key: the manifest.

## Manifest

`package/manifest.json` carries these ten fields:

    benchmark_identity, evaluation_design, runnable_cases, runner,
    scoring, provenance, qualification, expected_cost, gaps,
    protected_evidence

`gaps` is an explicit list (`[]` allowed). `benchmark_identity`
recomputes from the canonical payload: the manifest object minus
`benchmark_identity`, serialized as JSON with sorted keys, compact
separators `(",", ":")` and `ensure_ascii=False`, digested as UTF-8
and recorded as `sha256:<hex>`.

Each of the six components — `evaluation_design`, `runnable_cases`,
`runner`, `scoring`, `provenance`, `qualification` — is a reference
object of exactly this form:

    {"sha256": "sha256:<64-hex>", "locator": "<path relative to package/>"}

The locator resolves to a single file; the `sha256` value is the
prefixed digest of that file's bytes.

## Qualification record

The qualification component is a JSON object:

- `context`: the qualifying context id (a string, e.g.
  `"qx-conv-21"`), distinct from the `builder_context` the provenance
  component records.
- `entries`: non-empty list of entry objects, each carrying all of
  `criterion`, `verdict`, `oracle`, `oracle_class`, `evidence`,
  `covers`, `required`. Verdicts are `PASS`, `FAIL` or `UNVERIFIED`; a
  `PASS` entry's `evidence` is non-empty; `overall` `"PASS"` cannot
  coexist with a required `FAIL`. The recorded `criterion` values
  include all seven axis literals:

      failability, coverage, discrimination, reproducibility,
      redundancy, provenance, execution-cost

  Every entry's `evidence` string embeds the qualifying context id,
  attributing the verdict to that context, for example:

      "evidence": "recomputed in qualifying context qx-conv-21: ..."

- `seed_sweep`: the seed-discipline record:

      {
        "seeds": [
          {"name": "good-...", "role": "good", ...},
          {"name": "bad-...", "role": "bad", "inert": false,
           "behavior_change_proof": "<observed output delta>", ...},
          {"name": "bad-...", "role": "bad", "inert": true,
           "behavior_change_proof": "<observed output delta>", ...}
        ],
        "excluded": [
          {"name": "var-...", "equivalence_proof": "<why it cannot discriminate>"}
        ]
      }

  Every counted bad seed carries a non-empty
  `behavior_change_proof`; at least one bad seed is `"inert": true`;
  every excluded variant carries a non-empty `equivalence_proof`. A
  bad seed recorded `"shown_equivalent": true` must also appear in
  the manifest's `gaps` by name, with the `discrimination` entry's
  verdict `UNVERIFIED`.

- `spend`: `{"expected": "<non-empty>", "actual": "<non-empty>"}` —
  both the budgeted and the actually incurred qualification spend.

## Case provenance

Each record in the runnable cases component's `cases` list is an
object whose `provenance` string parses as one of exactly two forms —
synthesis-claim tracing or an evidence-identity citation:

    synthesis@<hex, 6+ digits> claims <n>[, <n>...]
    evidence@sha256:<hex, 8+ digits> [<free text>]

No other provenance form is accepted; in particular, a case never
cites the package's own answer key.

## Runner and scoring

The runner component is a Python file invoked as

    python <runner-file> <impl-dir>

It exits 0 and prints one JSON object on stdout mapping each case id
to its result record: `{"pc-1": {"ok": true}, ...}` — a case passes
only when its record is an object with `"ok": true`. The scoring
component is a JSON file naming the required case ids:

    {"required": ["pc-1", "pc-2"], ...}
