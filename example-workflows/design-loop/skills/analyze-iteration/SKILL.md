---
name: analyze-iteration
description: Analyze one project increment's design and comparison evidence, recommend adopt or retain, and inform the next brainstorm.
disable-model-invocation: true
---

Use the [shared handoff contract](../../references/design-loop-contract.md). Inputs are request context, baseline and any candidate identities, cycle design, research, implementation and test evidence, and prior observations. Explicitly partial evidence is valid input. Uses 1 fresh child.

Invoke core `orch-work` for the named assignment `analyze-iteration` with the inputs and resolved Make guidance. Ask it to explain what changed against the baseline, whether required criteria and endgoal progress are supported, what failed or remains uncertain, and why. Apply the contract's adoption criteria and recommend adopt or retain, linking the exact candidate and evidence.

Return the recommendation, confidence limits, retained lessons, and a compact next-brainstorm handoff of observed problems, useful opportunities and unanswered questions. Analysis changes no project state and performs no repairs or additional review. The caller checks and records the adoption decision.
