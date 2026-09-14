---
name: test-increment
description: Independently test exact baseline and candidate states against a supplied comparison plan without repairing either state.
---

Use the [shared handoff contract](../../references/design-loop-contract.md). Inputs are request context, design/evaluation plan, immutable baseline and candidate identities, reproduction instructions and relevant implementation handoff. Uses 1 fresh child who did not implement the candidate.

Invoke core `orch-review` for the named assignment `test-increment`, supplying both actual states, the intended outcome, evaluation plan, resolved Review guidance and isolated verification locations when execution has side effects. Ask it to execute the required comparison, preserve raw evidence, and report old/new observations, candidate acceptance results, regressions, expected feature deficits and missing or inapplicable checks. It may build a separate evaluation harness needed by the plan; it must keep candidate and baseline unchanged and make no repairs.

Return the evidence handoff with exact state/harness identities, conditions, reproduction procedures, results and limitations. A skipped or failed run is recorded as such; the reviewer does not decide adoption.
