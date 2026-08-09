# Package interchange contract

The shapes the caller's audit relies on when it reads the returned
tree. A return that departs from any shape below is rejected.

## Returned tree

The benchmark lives in a `package/` subtree at the implementation
root:

    <impl-root>/package/manifest.json
    <impl-root>/package/...        (components at their locators)

Exactly one manifest ships anywhere in the returned tree.

## Manifest

`package/manifest.json` carries these eleven fields:

    evaluation_design, runnable_cases, runner, scoring, provenance,
    qualification, expected_cost, gaps, protected_evidence,
    builders, reference_audit

`builders` records each case's builder context by `model_id`, `effort`
and `host_binding`. A value left null is legal only beside a `note`
saying why it was not recorded.
`reference_audit` records `auditor_context`, `method` per case,
`declared_sample`, a `defect_count` and one entry in `defect_classes`
per defect. A rate is not a count and is invalid.

These are recorded once qualification closes and are not re-derivable
afterwards, which is why the manifest carries them. Other
post-qualification fields may be present and are not read here.

`gaps` is an explicit list (`[]` allowed).

Each of the six components — `evaluation_design`, `runnable_cases`,
`runner`, `scoring`, `provenance`, `qualification` — is a reference
object of exactly this form:

    {"locator": "<path relative to package/>"}

The locator resolves to a single file.

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
