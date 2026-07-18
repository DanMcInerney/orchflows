# Spec contract

The frozen statement of one deliverable; the input to decomposition.
Two editors, never a third: `orch-spec` drafts and stamps it at
intake; `orch-decompose` repairs it in place when cutting surfaces a
defect. Every other reader treats it as frozen.

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
  instead of restating standards their owner already states.
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
missing fields. A defect it finds while cutting, it repairs in place
instead, recording the correction — never silently. Mixed-domain work
is two specs chained through a composition, never one spec.
