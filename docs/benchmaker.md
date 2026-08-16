# BenchMaker

The `benchmaker` template builds one qualified
[benchmark](vocabulary.md#verification) for an opaque target with an
observable outcome. Its
[template](../compositions/benchmaker/template.md) owns the chain, its
six stubs and what instantiation fills; its
[protocol](../compositions/references/benchmaker-protocol.md)
owns the construction craft no stub, rule or contract states; its
[research charter](../compositions/references/benchmaker-research.md)
owns acquisition's lane cut and synthesis shape; its
[manifest](../compositions/references/benchmaker-manifest.md) owns the
field set. [Benchmark design](benchmark-design.md) carries the field
evidence a builder needs — findings, not law.

## Dataflow

Fixed evidence flows into a frozen
[evaluation design](vocabulary.md#verification), then exact materialization
and independent qualification, then three audit and measurement stages —
reference audit, attack pass, measurement — into one recorded manifest.

Qualification gates validity. The audit and measurement stages ask the three
questions it does not: is the expectation right, is the probe passable without
the work, and does the target find this hard. What each stage may do about its
answer is
[the protocol](../compositions/references/benchmaker-protocol.md#audit-and-measurement)'s,
and what each stub may not do is that stub's own `excluded_actions` —
[01-design](../compositions/benchmaker/01-design.md),
[02-materialize](../compositions/benchmaker/02-materialize.md) and
[05-measure](../compositions/benchmaker/05-measure.md).

Benchmark execution produces fixed evidence. `orch-verify` decides required
eligibility before it may score that same evidence against a scale; a
[score card](vocabulary.md#verification) never re-executes or substitutes the
evidence it cites. Required failure never enters ranking. The `evolve`
composition consumes the qualified benchmark at one revision and returns an
[evolution result](vocabulary.md#verification) without calling BenchMaker or
revising that benchmark.

## Self-benchmarking

Self-benchmarking is manual, acyclic, and between campaigns. One BenchMaker run
may target a fixed BenchMaker identity and return a benchmark. A separately
invoked Evolve campaign may consume it. A later benchmark revision must be
built and independently qualified before a later Evolve campaign; neither
workflow activates it automatically.
