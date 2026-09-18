---
name: brainstorm-research
description: Generate project improvement options, then research their decision-relevant uncertainties for design.
disable-model-invocation: true
---

Use the [shared handoff contract](../../references/design-loop-contract.md). Inputs are the request context, baseline and any prior observations or decisions; first-use baseline may be an empty workspace. Coordinate the dependent stages in the caller.

Invoke [brainstorm-options](../brainstorm-options/SKILL.md), then [research-options](../research-options/SKILL.md) with those options and the unchanged request context. Return both handoffs together: candidate improvements, questions, evidence, ranking changes and unresolved gaps. Research informs design; this skill makes no adoption decision.
