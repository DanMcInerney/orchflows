# Provenance — reservoir-sampler benchmark package

Source trace (case evidence -> package component):

- evidence/spec.md (sampling law, RNG seeding law, multi-trial law)
  -> runner/refmodel.py, scoring/policy.json.
- evidence/trace.md (the one exhibited concrete run)
  -> cases/cases.json case `anchored-trace`, whose pinned trial-0
  expectation is the exhibited sample.
- evidence/holdback-policy.md (held-back stream class, digest-only
  declaration) -> manifest `protected_evidence`; members are never
  exhibited here.

Case mappings: `anchored-trace` anchors the exhibited trace;
`mid-stream` and `long-stream` exercise replacement density and the
reservoir boundary under the reference model at three declared trials
each.

Licensing: synthesis@41ee9ea2 claims 40,49 — exhibited artifacts are
licensed oracle material; nondeterministic outcomes carry a declared
trial count with all-trials aggregation.
