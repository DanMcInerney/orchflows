---
name: orch-work
description: Delegate a requested result to a fresh native child agent with relevant guidance.
disable-model-invocation: true
---

Reuse supplied guidance context or establish it per the [selection rule](../../docs/architecture.md#guidance-selection). Launch a fresh native child to make the requested result, applying the assignment's [model and effort](../../docs/architecture.md#model-and-effort) through native host controls. Give it the assignment, intended workspace and input state, resolved guidance paths and scoped caller choices; instruct it to read and apply the Make sections. Isolate per [hosts.md](../../docs/hosts.md) when edits could overlap.
