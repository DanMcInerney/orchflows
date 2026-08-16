---
name: skill-tournament
description: Apply the evolve campaign to one fixed skill identity against a benchmark built and qualified for it.
entry: named
placeholders: [skill, surface, policy, bound, sources, rigor, pack]
---

One skill improves against one benchmark that was built and qualified
for it before the first candidate existed, and that no candidate and no
generation may touch afterwards.

Two stubs, one edge: `00-benchmark` → `01-campaign`. Each instantiates
its nested template into a run of its own and drains it — the benchmaker
template builds and qualifies the benchmark, the evolve template spends
the campaign against it with `writer=orch-build` — so this template
binds those two and names only their placeholders. `01-campaign` is
terminal, so its completion test is this template's done check: the
final score card covers the one benchmark revision every candidate was
scored against.

Instantiate with all seven placeholders: `skill`, the fixed skill
identity being evolved; `surface`, its declared mutable surface, which
is `01-campaign`'s write scope and the candidates'; `policy`, the frozen
optimizer policy and candidate-accessible mappings; `bound`, the
campaign's budget, which the benchmark's own allocation is never drawn
from; and `sources`, `rigor` and `pack`, which the nested benchmaker
manifest declares and this template carries down to it. The run's bound is
`01-campaign`'s `bound`; `00-benchmark`'s is the benchmark's own
allocation beside it. Each stub is a ticket per
[contracts/work-item.md](../../contracts/work-item.md) missing only what
instantiation adds.
