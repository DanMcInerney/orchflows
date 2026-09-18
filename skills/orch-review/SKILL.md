---
name: orch-review
description: Delegate independent review of identified work to a fresh native child who did not make it, without repairs.
disable-model-invocation: true
---

The top-level orchestrator applies the [execution rules](../../docs/architecture.md#execution) and reuses or resolves [guidance](../../docs/architecture.md#guidance-selection). Launch a fresh native child who made none of the work, with the assignment's [model and effort](../../docs/architecture.md#model-and-effort). Supply the intended outcome, stable candidate, guidance paths and scoped caller choices. Instruct it to apply Review guidance without repairs, launching agents or assigning work to agents, and return findings, gaps and further-work requests to the orchestrator. [Isolate](../../docs/hosts.md#isolation) verification side effects.
