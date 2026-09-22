---
name: brainstorm-research
description: Generate project improvement options, then research their decision-relevant uncertainties for design.
disable-model-invocation: true
---

Use the [handoff contract](../../references/design-loop-contract.md). Inputs: request context, baseline and any prior observations or decisions. An empty initial workspace is valid.

Apply [brainstorm-options](../brainstorm-options/SKILL.md), then [research-options](../research-options/SKILL.md) to its options and applicable context. Return both handoffs: proposed improvements, questions, evidence, ranking changes and gaps. Make no adoption decision.
