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

Instantiate with `canary_set`, the frozen fixture directory. There is no
scheduler: a profiles.md change or an announced model update is a person
naming this template, which is why its entry is `named`.
