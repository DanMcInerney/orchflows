# Provenance — three-stage-pipeline benchmark package

Source trace (case evidence -> package component):

- evidence/pipeline-spec.md (gate law, join-identity law, stage-order
  law, transcript grammar) -> scoring/graph.json, scoring/policy.json,
  runner/check_transcript.py.
- evidence/interpreter.py (deterministic executor) -> consumed by
  runner/run.py as a supplied input; never copied into this package.

Case mappings: cases/cases.json rows stage-order, per-edge-gates,
frozen-joins, aggregate-nonempty each bind one spec law to the
transcript oracle.

Licensing: synthesis@41ee9ea2 claims 1,17,45 (G13); taxonomy HAZOP
late and reverse are seeded at the package's build-ordering and
design-evidence-join loci.
