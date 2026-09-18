---
name: orch-work
description: Delegate a requested result to a fresh native child agent with relevant guidance.
disable-model-invocation: true
---

The coordinator applies [execution](../../docs/architecture.md#execution) and resolves the assignment's [guidance](../../docs/architecture.md#guidance-selection). Launch a fresh native maker with the scoped [model and effort](../../docs/architecture.md#model-and-effort). Supply the intended result and acceptance criteria, relevant inputs, workspace/output location, guidance paths, bounds and allowed effects. The maker applies common criteria and Make instructions, performs the assignment without launching or tasking agents, and returns the result, evidence, gaps and further-work requests. [Isolate](../../docs/hosts.md#isolation) overlapping edits.
