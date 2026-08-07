# Evaluation design — three-stage pipeline

evidence-source: cases/cases.json
evidence-source: case-evidence:interpreter.py

Boundary: the observable outcome is the run transcript the supplied
interpreter emits for a pipeline description; the package scores
transcripts against the spec's three laws plus the aggregate gate.
Out of scope: interpreter internals, payload semantics, wall-clock
timing.

Flow direction: this design consumes only the case evidence named
above. The materialized cases downstream of it are its output, never
its evidence.
