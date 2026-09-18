---
name: implement-increment
description: Implement one approved-scope design in an isolated candidate and return its exact reproducible state.
disable-model-invocation: true
---

Use the [shared handoff contract](../../references/design-loop-contract.md). Inputs are request context, identified immutable baseline, design and evaluation plan, and an isolated writable candidate derived from that baseline. A caller invoking this leaf alone supplies or establishes those states before implementation.

For the named assignment `implement-increment`, implement the design within scope in the candidate workspace and report actual progress or blockers. Normal implementation checks and fixes stay within this assignment; they do not replace independent comparison testing or alter its acceptance criteria.

Return changed artifact paths, run/use instructions, known limitations and actual implementation check results. Freeze and identify the resulting candidate for the next handoff; the baseline stays unchanged. A partial implementation remains a candidate with explicit gaps.
