# Evolve (non-normative example)

Start from a frozen evolve spec carrying an incumbent identity, its covered
evidence and score card, and one qualified benchmark identity. The benchmark's
evaluation design, runner, scoring, and protected-evidence policy remain fixed.
The campaign's promotion rule, mutation authority, and bound also remain fixed.

Before ranking, send the incumbent's fixed evidence to `orch-verify`. Only
required PASS permits its Judge-owned score card to direct variation. Each
`orch-loop` generation dispatches bounded variants through `orch-delegate`;
each return crosses
`orch-integrate`, runs against the same benchmark, and crosses `orch-verify`.
Required failure removes a candidate before `orch-panel`; judged score cannot
compensate.

The panel receives only verified survivors, each bound to the exact evidence
identity Verify admitted, plus fixed scoring criteria. Judge lanes cite that
evidence without re-execution or substitution. Promote only under the frozen
margin and promotion rule. A fresh closing `orch-judge` pass over the same
admitted evidence decides the judged done-check; the campaign returns one
evolution result.

A changed benchmark starts a new campaign and every retained candidate runs
again. Ambiguity or non-discrimination blocks the current campaign with
feedback for a separate BenchMaker run; Evolve never calls BenchMaker or
revises the benchmark it consumes.

Self-benchmarking uses the same acyclic boundary: BenchMaker may first target a
fixed BenchMaker identity, then a separately invoked Evolve campaign consumes
the qualified benchmark. A successor benchmark is independently qualified
before a later campaign and is never activated automatically.
