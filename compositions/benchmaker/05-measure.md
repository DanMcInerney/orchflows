---
id: 05-measure
executor: orch-verify
depends_on: [04-audit]
write_scope: [{{package}}]
bound: <= 40 tool calls
excluded_actions:
  - rank candidates
  - promote or activate anything
independence: checker
isolation: none
---

## Objective

The manifest recorded, and the measurement pass beside it: what the
candidates scored over the candidate-accessible scope at the declared
rungs, on [§Measurement pass](../references/benchmaker-protocol.md#measurement-pass)'s terms.

## Fixed inputs

- input: {"name":"manifest-contract","type":"literal","value":"the manifest contract at compositions/references/benchmaker-manifest.md in the orchflows library"}
- input: {"name":"protocol-contract","type":"literal","value":"the protocol contract at compositions/references/benchmaker-protocol.md in the orchflows library"}
- input: {"name":"package","type":"literal","value":"{{package}}"}

## Completion test

- the manifest's qualification verdict set covers every component but its own — covered PASS on every required criterion, its `covers` naming the post-repair identities, gaps explicit (`[]` when none) | oracle: the manifest read against its own field set and the verdict set | oracle_class: deterministic | provenance: pre-existing
- the measurement record is filed in this ticket's `## Result` carrying every field §Measurement pass's record names | oracle: the record against §Measurement pass | oracle_class: deterministic | provenance: authored-here
- every criterion the dispatched authority made unreachable is recorded as §Measurement pass requires | oracle: the declared authority beside the gap list | oracle_class: deterministic | provenance: pre-existing

## Return fields

status; result — the benchmark's revision; verification — the
qualification; then gaps (`[]` when none), bounds spent, and changed
artifacts

## Result

## Verification

## Feedback

[]

## Risks

[]
