---
name: skill-tournament
description: Apply the evolve campaign to one fixed skill identity against a benchmark built and qualified for it.
entry: named
placeholders: [skill, surface, policy, bound, sources, rigor, pack]
---

One skill improves against one benchmark that was built and qualified
for it before the first candidate existed, and that no candidate and no
generation may touch afterwards.

`00-benchmark` and `01-campaign` each instantiate their nested template
into a run of its own and drain it — the benchmaker template builds and
qualifies the benchmark, the evolve template spends the campaign against
it with `writer=orch-build` — so this template binds those two and names
only their placeholders.

Instantiate with all seven placeholders: `skill`, the fixed skill
identity being evolved; `surface`, its declared mutable surface, which
belongs to `01-campaign` and the candidates; `policy`, the frozen
search policy, promotion rule and margin; `bound`, the campaign's
budget, which the benchmark's own allocation is never drawn from; and
`sources`, `rigor` and `pack`, which the nested benchmaker manifest
declares and this template carries down to it.
