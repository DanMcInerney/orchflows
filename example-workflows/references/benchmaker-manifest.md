# Benchmark manifest

The manifest is the package-owned index of one benchmark. It carries
these fields:

- `evaluation_design` — locator of the frozen evaluation design.
- `runnable_cases` — locator of the exact executable case set.
- `runner` — locator of the executable interface.
- `scoring` — locator of required-status, scoring, and aggregation
  data.
- `provenance` — locator of the source trace and case mappings.
- `reference_audit` — locator of the reference audit record: the auditing
  context identity, the method per case (solve-from-prompt or re-read), the
  declared sample, a defect **count**, and each defect's class. Never a rate.
- `attack_audit` — locator of the attack pass record: the dated checklist
  identity, the outcome per class, and every hole left unrepaired named with
  the attack that works.
- `measurement` — locator of the recorded measurement pass: candidate
  identities, measured scope, per-case status, the count of distinct failure
  signatures, and the margin.
- `qualification` — locator of the verdict set. At
  construction, before independent qualification has rendered
  anything, this component may instead be the one-entry pending
  marker `{"status": "construction-complete-qualification-pending"}`;
  a manifest carrying it names an unqualified benchmark no campaign
  or consumer may cite, and qualification replaces the marker. The
  marker is schema-legal and never task-complete: it satisfies no
  objective that asks for a qualified package.
- `expected_cost` — declared units, per-execution limit, and suite estimate.
- `gaps` — explicit unresolved elements; `[]` when none.
- `protected_evidence` — the held-back file set, visibility, release policy,
  and candidate-inaccessible-check identity or `null`.

None of the following is re-derivable afterwards, so each is fixed here
rather than recomputed by a consumer:

- `anchors` — per case, the reference outside the package that the expected
  outcome is bound to, or `none` with its reason. A declared `none` is
  legal; silence is not.
- `builders` — per case, the builder context's model id, effort, and host
  binding. Recording it is what lets a successor compute a builder-family
  effect the run itself cannot.
- `qualifier` — the qualifying context's model id, effort, and host binding.
- `attacker` — the attack pass context's model id, effort, and host binding.
- `resolution` — the smallest reportable difference,
  `max(measured rerun spread, one case)`.
- `retirement_trigger` — the declaration only. Its firing is recorded in the
  measurement record outside the package, never here.
- `incomparability` — the identity boundary scores do not cross, covering
  model id, effort level, host binding, and scaffold.

Every component reference carries a workspace-resolved locator; consumers
and qualification resolve it before use. The reference fixture uses
relative-file locators, but the schema prescribes no storage layout. Each
qualification entry carries `verdict`, `oracle`, `oracle_class`, `evidence`,
and `covers` per the verdict contract, plus whether the criterion is required.

Candidate execution emits a separate result identity and cannot change a
manifest field.
