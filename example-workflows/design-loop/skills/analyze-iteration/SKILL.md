---
name: analyze-iteration
description: Analyze an increment's evidence, recommend adopt or retain, and inform the next brainstorm.
disable-model-invocation: true
---

Use the [handoff contract](../../references/design-loop-contract.md). Inputs: request context, baseline and any candidate identities, design, research, implementation/test evidence and prior observations. Explicitly partial evidence is valid.

For assignment `analyze-iteration`, explain changes, supported criteria and goal progress, failures and uncertainties. Apply the adoption criteria; recommend adopt or retain with exact candidate and evidence links.

Return the recommendation, confidence limits, lessons and next-brainstorm problems, opportunities and questions. Change no project state; perform no repairs or additional review. The coordinator checks and records adoption.
