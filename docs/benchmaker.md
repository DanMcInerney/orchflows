# BenchMaker

The `benchmaker` composition builds one qualified, immutable
[benchmark](vocabulary.md#verification) for an opaque target with an
observable outcome. Its
[composition](../compositions/benchmaker.md) owns invocation; its
[protocol](../compositions/references/benchmaker-protocol.md)
owns construction and qualification; its
[research charter](../compositions/references/benchmaker-research.md)
owns acquisition's lane cut and synthesis shape; its
[manifest](../compositions/references/benchmaker-manifest.md) owns
identity.

## Immutable dataflow

Fixed evidence flows into a frozen
[evaluation design](vocabulary.md#verification), then exact materialization
and independent qualification seal one benchmark identity. Changing any
covered component creates a successor benchmark; BenchMaker never mutates the
target, generates candidates, promotes, or activates anything.

Benchmark execution produces fixed evidence. `orch-verify` decides required
eligibility before `orch-judge` may create a
[score card](vocabulary.md#verification) citing that same evidence; Judge
never re-executes or substitutes it. Required failure never enters ranking.
The `evolve` composition consumes the qualified benchmark by identity and
returns an [evolution result](vocabulary.md#verification) without calling
BenchMaker or revising that benchmark.

## Self-benchmarking

Self-benchmarking is manual, acyclic, and between campaigns. One BenchMaker run
may target a fixed BenchMaker identity and return a benchmark. A separately
invoked Evolve campaign may consume it. A successor benchmark must be built and
independently qualified before a later Evolve campaign; neither workflow
activates it automatically.

## Migration

Replace `orch-bench` calls with `orch-eval-design`, and any `orch-benchmaker`
invocation with the named `benchmaker` composition. No alias remains.
