# Spec contract

The frozen statement of one deliverable; the input to decomposition.
`orch-spec` is the spec's only editor: it drafts and stamps the spec
at intake. Every other reader, `orch-decompose` included while
cutting, treats it as frozen.

- `run` — the owning run id, carried verbatim into every work item and
  dispatch the run decomposes.
- `objective` — one outcome stated as an observable end state, never
  activities.
- `non_goals` — the adjacent scope deliberately deferred.
- `acceptance` — enumerated criteria, each checkable alone by a named
  external oracle with its oracle_class, covering failure behavior as
  well as success. A criterion no oracle can check is a spec defect, not
  the decomposer's slack.
- `binding_constraints` — the invariants, prohibitions, budgets, and
  source policy every work item inherits verbatim.
- `evidence` — the frozen input set, by identity.
- `affected_surfaces` — the concrete artifacts touched, from which
  disjoint write scopes are cut.
- `exemplars` — by pointer, naming an existing artifact to imitate
  instead of restating standards their owner already states, plus each
  property the imitation must carry, named at the identity that fixes it
  or pinned by a check a divergent copy trips. A pointer alone
  transmits shape, not convention.
- `routing` — the stamp: `pattern` ∈ {deliver, loop(<body>), evolve,
  fix, decision, snapshot} and `pack` (exactly one per
  run). A loop stamp names as `<body>` the skill one iteration
  dispatches and names the acceptance criterion that is its
  done-check — any oracle_class per the class policy in
  [verdict.md](verdict.md); a count of iterations
  (`iterations_run == N`) is a deterministic done-check.
- `bound` — the run's effort budget, from which item bounds are cut;
  and `plan_gate`: true when execution must pause for approval after
  decomposition.
- The stamped pack's `required_spec_fields`, verbatim as fields.
- `risks`, `assumptions`.

Decomposition rejects a spec missing a required field by naming the
missing fields. A defect or an uncoverable criterion it finds while
cutting returns a decision gap naming exactly those criteria — never
edited into the spec; the covered remainder is still cut and still
executed. Mixed-domain work is two specs chained through a
composition, never one spec.
