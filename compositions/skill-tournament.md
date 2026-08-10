---
name: skill-tournament
description: Apply the evolve campaign to one fixed skill identity against a benchmark built and qualified for it.
entry: named
---

Require: one fixed skill identity, declared mutable surface, frozen optimizer
policy and candidate-accessible mappings, and campaign bounds.

Steps:
- benchmark — the `benchmaker` composition builds and qualifies one benchmark
  revision the campaign never changes for the fixed skill identity.
- campaign — the `evolve` composition receives that revision, the frozen policy
  and bounds, variant writer binding orch-build, and variants limited to the
  declared surface.

Edges: seq benchmark → campaign — the qualified benchmark revision is the
campaign's qualified-benchmark evidence.

Invariants — Never: change the benchmark or policy inside the campaign; restate
or call Evolve's verification, panel, search, or selection internals; install a
winner; let a Benchmaker run targeting Benchmaker call Evolve. A selected
evolution result requires a separate authorized integration before activation.

Done check: the campaign's final score card covers the one benchmark revision
every candidate was scored against.

Return: status, result — the evolution result, verification — the final score
card; then the benchmark revision, variant set, and cumulative changed artifacts.
