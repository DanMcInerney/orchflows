---
name: test-increment
description: Independently test exact baseline and candidate states against a supplied comparison plan without repairing either state.
disable-model-invocation: true
---

Use the [shared handoff contract](../../references/design-loop-contract.md). Inputs are request context, design/evaluation plan, immutable baseline and candidate identities, reproduction instructions and relevant implementation handoff. Uses 1 fresh child who did not implement the candidate.

Invoke `shared:compare-candidates` in the caller for the named assignment `test-increment`, allocating exactly one reviewer from the parent's remaining allowance. Supply both actual states, the intended outcome, evaluation plan, resolved Review guidance and isolated verification locations when execution has side effects. Require execution of the planned comparison, raw evidence, old/new observations, candidate acceptance results, regressions, expected feature deficits and missing or inapplicable checks. A separate evaluation harness is permitted; the candidate and baseline remain unchanged. Preserve this assignment's scoped settings through the shared component. It launches the reviewer; do not launch another worker or reviewer around it.

Return the evidence handoff with exact state/harness identities, conditions, reproduction procedures, results and limitations. A skipped or failed run is recorded as such; the reviewer does not decide adoption.
