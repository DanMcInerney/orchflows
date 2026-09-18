---
name: test-increment
description: Independently test exact baseline and candidate states against a supplied comparison plan without repairing either state.
disable-model-invocation: true
---

Use the [handoff contract](../../references/design-loop-contract.md). Inputs: request context, design/evaluation plan, immutable baseline/candidate identities, reproduction instructions and implementation handoff.

Apply `shared:compare-candidates` with both states, intended outcome, evaluation plan, common criteria and Review guidance, and isolated locations for side-effecting checks. Preserve `test-increment` settings. Require planned comparisons, raw evidence, old/new observations, candidate acceptance results, regressions, expected baseline deficits and missing/inapplicable checks. Preserve candidates; a separate harness is permitted.

Return exact state/harness identities, conditions, reproduction procedures, results and limitations. Label skipped or failed runs. The reviewer does not decide adoption.
