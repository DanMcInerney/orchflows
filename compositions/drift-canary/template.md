---
name: drift-canary
description: Detect behavior drift when a model, effort, or host binding changes — before it surfaces as production friction.
entry: named
placeholders: [canary_set]
---

When a model, effort level, or host binding changes, the frozen canary
items run again and their results are read against the golden ones. A
divergence is a signal, not a failure: a better model may beat the
golden result, so the canary records the delta and a human decides.

Two stubs, one chain: `00-run` → `01-diff`. `01-diff` is terminal, so
its completion test is this template's done check — every canary item
ran, and every divergence is logged as friction under category
`surprising-output`, which is what feeds `orch-self-improve` the
earliest signal that a skill's wording lands differently on the new
model.

Instantiate with `canary_set`, the frozen fixture directory. There is no
scheduler: a profiles.md change or an announced model update is a person
naming this template, which is why its entry is `named`. Each canary
item is already a ticket, so `00-run` instantiates nothing — it issues
the set it is handed into the run's own ticket directory and drains it
there. The run's bound is the sum of the two stubs' own bounds, each
fixed in its own frontmatter. Each stub is a ticket per
[contracts/work-item.md](../../contracts/work-item.md) missing only what
instantiation adds.
