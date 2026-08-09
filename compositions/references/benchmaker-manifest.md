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
- `qualification` — identity and locator of the verdict set. At
  construction, before independent qualification has rendered
  anything, this component may instead be the one-entry pending
  marker `{"status": "construction-complete-qualification-pending"}`;
  a manifest carrying it names an unqualified benchmark no campaign
  or consumer may cite, and qualification replaces the marker only by
  minting a successor identity. The marker is schema-legal and never
  task-complete: it satisfies no objective that asks for a qualified
  package. Behavior when qualification is unreachable is
  [the protocol](benchmaker-protocol.md)'s.
- `expected_cost` — declared units, per-execution limit, and suite estimate.
- `gaps` — explicit unresolved elements; `[]` when none.
- `protected_evidence` — fixed evidence identity, visibility, release policy,
  and candidate-inaccessible-check identity or `null`.

These carry what [the protocol](benchmaker-protocol.md)'s pre-seal stages
establish. Each is true at seal and none is re-derivable afterwards, so
each is fixed here rather than recomputed by a consumer:

- `anchors` — per case, the reference outside the package that the expected
  outcome is bound to, or `none` with its reason. A declared `none` is
  legal; silence is not.
- `builders` — per case, the builder context's model id, effort, and host
  binding. Recording it is what lets a successor compute a builder-family
  effect the run itself cannot.
- `reference_audit` — the auditing context identity, the method per case
  (solve-from-prompt or re-read), the declared sample, a defect **count**,
  and each defect's class. Never a rate.
- `attack_audit` — the dated checklist identity, the outcome per class, and
  every hole left unrepaired at seal named with the attack that works.
- `seal_measurement` — the recorded measurement pass: candidate identities,
  measured scope, per-case status, the count of distinct failure signatures,
  and the margin.
- `resolution` — the smallest reportable difference,
  `max(measured rerun spread, one case)`.
- `retirement_trigger` — the declaration only. Its firing is recorded in the
  measurement record outside the package, never here.
- `incomparability` — the identity boundary scores do not cross, covering
  model id, effort level, host binding, and scaffold.

Every component reference carries a `sha256:` digest of its exact
canonical bytes and a workspace-resolved locator; consumers and qualification
resolve the locator and verify that digest before use. The reference fixture
uses relative-file locators, but the schema prescribes no storage layout. Each
qualification entry carries `verdict`, `oracle`, `oracle_class`, `evidence`,
and `covers` per the verdict contract, plus whether the criterion is required.

A component identity is recomputable from the bytes it names, and the
recipe is one rule nested: a file component's identity is the SHA-256 of
its bytes; a directory component's is the SHA-256 of its component lock —
one `<sha256>  <posix-path>` line per contained file, path relative to
the component root, sorted by path, LF-terminated. An identity no tool
can reproduce from the tree proves only that the JSON agrees with
itself, so the package ships the recompute as a runnable check. Evidence
held off-tree by policy is exempt and named as exempt.

Canonicalize the manifest after removing only `benchmark_identity`: UTF-8 JSON,
keys sorted recursively, no insignificant whitespace, and non-ASCII characters
unescaped. The SHA-256 of those bytes is `benchmark_identity`; this
non-self-referential digest covers every other field and, through each
verified component digest, the referenced bytes.
Changing any covered byte mints a successor benchmark identity; a builder or
consumer never edits the manifest in place. Candidate execution emits a
separate result identity and cannot change a manifest field.
