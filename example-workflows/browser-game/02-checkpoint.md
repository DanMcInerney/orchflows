---
id: 02-checkpoint
executor: orch-do
depends_on: [00-record, 01-evidence]
bound: <= 60 tool calls
independence: checker
isolation: none
profile: orch-planner
---

<!-- BGW-TRACE[implementation:checkpoint-disposition|PJ-05] -->
<!-- BGW-TRACE[implementation:kind-separation|AUTH-05,PJ-18,PJ-19,PJ-28] -->
<!-- BGW-TRACE[implementation:evidence-identity|PJ-08,PJ-24] -->

## Goal

Exactly one product checkpoint disposition — `advance`, `revise`,
`experiment`, `user-decision-required`, or `stop` — bound to its governing
requirement, fixed program-record revision, and evidence identity. The result
names its invalidation and revalidation boundary and either one verbatim
user-only question, a matched experiment, or a lawful pack-separated
successor plan whose ordered entries each preserve an artifact identity,
artifact kind, matching pack, proposed run/root identities, dependencies,
and `planned` or `opened` status.

## Context

- input: {"name":"workspace","type":"literal","value":"{{workspace}}"}
- input: {"name":"program-record","type":"literal","value":"the accepted 00-record Result identity in this workflow instance"}
- input: {"name":"empirical-evidence","type":"literal","value":"the accepted 01-evidence Result identity in this workflow instance"}
- checkpoint-contract: `../references/browser-game-checkpoint.schema.json`
- input: {"name":"successor-plan-contract","type":"literal","value":"the definition at example-workflows/references/browser-game-program-record.schema.json#/$defs/successorPlanRevision in the orchflows library"}
- input: {"name":"instance-validator","type":"literal","value":"browser_game_validate.py; run it against the bound program record and emitted checkpoint before filing Result"}

Exceptional constraints:

- infer `advance` from task completion
- emit a disposition that does not validate against the checkpoint contract
- answer a `kind: user-only` question, paraphrase it for the root, or block unrelated empirical work on it
- open or dispatch a successor whose kind, pack, accepted predecessor identity, dependency, or root identity is unresolved
- hide research, prose, code, or rendered outcomes behind another artifact kind's identity
- file a checkpoint or successor projection that the instance validator rejects

## Report
