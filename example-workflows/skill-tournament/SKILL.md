---
name: skill-tournament
description: Apply the evolve campaign to one fixed skill identity against a benchmark built and qualified for it.
disable-model-invocation: true
---

Require: `skill`, the fixed skill identity being evolved; `surface`, its
declared mutable surface, which belongs to the campaign and its candidates;
`policy`, the frozen search policy, promotion rule and margin; `bound`, the
campaign's budget, which the benchmark's own allocation is never drawn from;
and `sources`, `rigor` and `pack`, which this workflow carries down into the
nested benchmark.

One skill improves against one benchmark that was built and qualified for it
before the first candidate existed, and that no candidate and no generation
may touch afterwards. Both halves are workflows, not calls: each opens its
own frame under this one, and the ticket tree is the call tree.

    tickets.py frame-open <run> --goal-file <tournament-goal> --bound <bound> --workflow skill-tournament


**Build the benchmark.** Invoke `benchmaker` with `target=skill`, the
skill's declared observable outcome as `outcome`, `sources`, `rigor`, `pack`
and this workflow's benchmark location as `package`, opening its frame under
this one:

    tickets.py frame-open <run> --parent <frame> --goal-file <benchmark-goal>

Its qualified result is recorded in the package manifest at the one Git
revision that versions the benchmark, and that revision stays fixed for the
whole campaign.

**Spend the campaign.** Invoke `evolve` under this frame the same way, with
`target=skill`, the skill's current fixed result/evidence as `incumbent`,
the benchmark's qualified revision plus `policy` as `evaluation`,
`writer=orch-do`, `mutation_scope=surface`, and `bound`. Its final score
card names the final incumbent and the one benchmark revision every
candidate was scored against.

Never: mutate `skill` — the benchmark is built for it, never by changing it;
generate, score or compare a candidate here, since both halves own that;
change the benchmark or the policy inside the campaign; restate or call
evolve's verification, search or selection internals; let a benchmaker frame
targeting benchmaker invoke evolve; or activate a selected result — that
requires a separate authorized integration.

Return: `tickets.py frame-close <run> <frame> --done <check>` over the
campaign's final score card and the fixed benchmark revision it cites.
