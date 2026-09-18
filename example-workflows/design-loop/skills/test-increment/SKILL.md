---
name: test-increment
description: Independently test exact baseline and candidate states against a supplied comparison plan without repairing either state.
disable-model-invocation: true
---

Use the [shared handoff contract](../../references/design-loop-contract.md). Inputs are request context, design/evaluation plan, immutable baseline and candidate identities, reproduction instructions and relevant implementation handoff.

Apply `shared:compare-candidates` with both actual states, intended outcome, the same evaluation plan, applicable common criteria and Review guidance, and isolated verification locations for side-effecting checks. Preserve scoped settings for `test-increment`. Require actual planned comparisons, raw evidence, old/new observations, candidate acceptance results, regressions, expected baseline feature deficits and missing or inapplicable checks. Candidates remain unchanged; a separate evaluation harness is permitted.

Return the evidence handoff with exact state/harness identities, conditions, reproduction procedures, results and limitations. A skipped or failed run is recorded as such; the reviewer does not decide adoption.
