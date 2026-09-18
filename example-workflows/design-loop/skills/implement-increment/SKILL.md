---
name: implement-increment
description: Implement one approved-scope design in an isolated candidate and return its exact reproducible state.
disable-model-invocation: true
---

Use the [handoff contract](../../references/design-loop-contract.md). Inputs: request context, identified immutable baseline, design/evaluation plan and isolated writable candidate derived from the baseline. A standalone caller establishes those states before implementation.

For assignment `implement-increment`, implement within scope in the candidate and report progress or blockers. Ordinary checks and fixes stay here; they neither replace independent comparison nor alter acceptance criteria.

Return changed paths, run/use instructions, limitations and actual check results. Freeze and identify the candidate; preserve the baseline. Mark partial implementation gaps.
