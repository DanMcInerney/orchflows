# Skill tournament (non-normative example)

Apply Evolve to one fixed skill identity. Before the campaign,
`orch-benchmaker` runs its canonical evidence, evaluation-design,
materialization, qualification, and sealing pipeline to return one immutable
benchmark. The campaign never changes that benchmark.

`orch-build` writes variants that differ only in the declared surface. Run
each variant in isolation against the benchmark, submit its fixed evidence to
`orch-verify`, and exclude every required failure before `orch-panel`. Blind
judges cite that same admitted evidence in one score card per eligible
candidate; Evolve applies its frozen promotion rule and returns an evolution
result. The evolution result does not install its winner; activation is a
separate authorized run.

BenchMaker itself can be the fixed target identity. That BenchMaker run does
not call Evolve. A separate Evolve campaign may consume the qualified
benchmark, and any successor benchmark must be independently qualified before
a later campaign.
