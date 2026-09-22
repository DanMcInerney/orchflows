---
name: orch-work
description: Delegate a requested result to a fresh native child agent with relevant guidance. Use when a workflow names it or the user selects it; ordinary requests use orch-dynamic-workflow. Top-level coordinators only.
disable-model-invocation: false
---

The coordinator applies [execution](../../docs/architecture.md#execution) and resolves [guidance](../../docs/architecture.md#guidance-selection) and scoped [model/effort](../../docs/architecture.md#model-and-effort). Launch a fresh native maker honoring those settings, with the intended result, acceptance criteria, relevant inputs, workspace/output location, guidance paths, bounds and allowed effects. The maker applies common criteria and Make instructions, works without launching or tasking agents, and returns the result, evidence, gaps and further-work requests. [Isolate](../../docs/hosts.md#isolation) overlapping edits.
