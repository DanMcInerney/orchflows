---
name: skill-tournament
description: Apply the evolve campaign to one fixed skill identity against a benchmark sealed for it.
entry: named
---

Require: one fixed skill identity, the variant surface declaration,
and the campaign bounds.

Steps:
- benchmark — the `benchmaker` composition over the fixed skill
  identity: evidence, evaluation design, materialization,
  qualification, sealing — one immutable benchmark the campaign never
  changes.
- campaign — the `evolve` composition; frozen bindings: variant writer
  `orch-build`, variants differing only in the declared surface; each
  variant runs in isolation against the benchmark, its fixed evidence
  to `orch-verify`, every required failure excluded before
  `orch-panel`; blind judges cite the admitted evidence, one score
  card per eligible candidate; the frozen promotion rule returns one
  evolution result.

Edges: seq benchmark → campaign — the sealed benchmark identity is the
campaign's qualified-benchmark evidence.

Invariants — Never: change the benchmark inside the campaign; install
the winner — an evolution result does not activate; activation is a
separate authorized run; let a benchmaker run whose target is
BenchMaker itself call evolve — a separate evolve campaign consumes
the qualified benchmark, and any successor benchmark is independently
qualified before a later campaign.

Done check: the campaign's closing score card over the sealed
benchmark identity.

Return: status, result — the evolution result, verification — the
closing score card; then the benchmark identity and the variant set.
