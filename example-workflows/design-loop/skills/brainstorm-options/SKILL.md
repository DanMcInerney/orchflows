---
name: brainstorm-options
description: Propose a few scoped next increments from an endgoal, current state and prior observations.
disable-model-invocation: true
---

Use the [shared handoff contract](../../references/design-loop-contract.md). Inputs are request context, the identified baseline and any prior decisions, test results or analysis. For a standalone call, omitted history means this is the first increment.

Invoke core `orch-work` for the named assignment `brainstorm-options`, supplying those inputs and resolved Make guidance. Ask for 2–4 distinct options, each with the behavior it adds or improves, why it matters to the endgoal, scope, expected observable benefit, risks, and questions research should resolve. The first increment favors a minimal working PoC; later options respond to actual observations, including failed or retained work. Return a tentative preference with its assumptions; implementation is outside this assignment.
