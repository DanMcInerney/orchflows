# Benchmark manifest

The manifest is the package-owned immutable index of one benchmark. It carries
these fields:

- `benchmark_identity` — `sha256:` plus the digest of the canonical manifest
  payload defined below.
- `evaluation_design` — identity and locator of the frozen evaluation design.
- `runnable_cases` — identity and locator of the exact executable case set.
- `runner` — identity and locator of the executable interface.
- `scoring` — identity and locator of required-status, scoring, and aggregation
  data.
- `provenance` — identity and locator of the source trace and case mappings.
- `qualification` — identity and locator of the verdict set.
- `expected_cost` — declared units, per-execution limit, and suite estimate.
- `gaps` — explicit unresolved elements; `[]` when none.
- `protected_evidence` — fixed evidence identity, visibility, release policy,
  and candidate-inaccessible-check identity or `null`.

Every component reference carries a `sha256:` digest of its exact
canonical bytes and a workspace-resolved locator; consumers and qualification
resolve the locator and verify that digest before use. The reference fixture
uses relative-file locators, but the schema prescribes no storage layout. Each
qualification entry carries `verdict`, `oracle`, `oracle_class`, `evidence`,
and `covers` per the verdict contract, plus whether the criterion is required.

Canonicalize the manifest after removing only `benchmark_identity`: UTF-8 JSON,
keys sorted recursively, no insignificant whitespace, and non-ASCII characters
unescaped. The SHA-256 of those bytes is `benchmark_identity`; this
non-self-referential digest covers every other field and, through each
verified component digest, the referenced bytes.
Changing any covered byte mints a successor benchmark identity; a builder or
consumer never edits the manifest in place. Candidate execution emits a
separate result identity and cannot change a manifest field.
