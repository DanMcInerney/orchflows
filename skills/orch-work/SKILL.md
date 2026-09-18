---
name: orch-work
description: Delegate a requested result to a fresh native child agent with relevant guidance.
disable-model-invocation: true
---

The top-level orchestrator applies the [execution rules](../../docs/architecture.md#execution) and reuses or resolves [guidance](../../docs/architecture.md#guidance-selection). Launch a fresh native child with the assignment's [model and effort](../../docs/architecture.md#model-and-effort). Supply its assignment, workspace, input state, guidance paths and scoped caller choices. Instruct it to apply Make guidance, do the work without launching or assigning work to agents, and return results and further-work requests to the orchestrator. [Isolate](../../docs/hosts.md#isolation) overlapping edits.
