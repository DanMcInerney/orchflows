---
id: 02-checkpoint
executor: orch-spec
depends_on: [00-record, 01-evidence]
bound: <= 60 tool calls
independence: checker
isolation: none
profile: orch-planner
---

## Goal

Exactly one product checkpoint disposition — `advance`, `revise`,
`experiment`, `user-decision-required`, or `stop` — bound to its governing
requirement, fixed program-record revision, and evidence identity. The result
names its invalidation and revalidation boundary and either one verbatim
user-only question, a matched experiment, or a lawful pack-separated
successor plan with ordered artifact kinds, packs, run/root identities,
dependencies, and status.

## Context

- input: {"name":"workspace","type":"literal","value":"{{workspace}}"}
- input: {"name":"program-record","type":"literal","value":"the accepted 00-record Result identity in this composition instance"}
- input: {"name":"empirical-evidence","type":"literal","value":"the accepted 01-evidence Result identity in this composition instance"}
- checkpoint-contract: `../references/browser-game-checkpoint.schema.json`

Exceptional constraints:

- infer `advance` from task completion
- emit a disposition that does not validate against the checkpoint contract
- answer a `kind: user-only` question, paraphrase it for the root, or block unrelated empirical work on it
- open or dispatch a successor whose kind, pack, accepted predecessor identity, dependency, or root identity is unresolved
- hide research, prose, code, or rendered outcomes behind another artifact kind's identity

## Result


## Verification


## Feedback

[]

## Risks

[]
