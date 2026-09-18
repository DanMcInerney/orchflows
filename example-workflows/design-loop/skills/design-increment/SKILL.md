---
name: design-increment
description: Turn a goal, options and research into one implementable increment and an old/new evaluation plan.
disable-model-invocation: true
---

Use the [handoff contract](../../references/design-loop-contract.md). Inputs: request context, baseline, options, research evidence and any prior observations; equivalent caller material suffices.

For assignment `design-increment`, choose one coherent increment; explain the choice and rejected alternatives. Specify changed behavior, boundaries, implementation outline, risks and dependencies. The first cycle must target a minimum working PoC from the actual baseline.

Return an implementable design and evaluation plan fixed before implementation: acceptance criteria, baseline behavior to preserve, shared inputs/harness and conditions, expected old-state deficits, improvement measures, and required/optional checks. Mark blocking questions. If no change is justified, return that conclusion and evidence for analysis.
