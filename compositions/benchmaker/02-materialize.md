---
id: 02-materialize
executor: orch-decompose
pack: {{pack}}
depends_on: [01-design]
bound: <= 120 tool calls
independence: gate
isolation: required
profile: orch-worker
---

## Goal

Every case specification the frozen design names, materialized exactly
into {{package}}: runnable cases, runner, scoring data and provenance,
each at a preserved identity.

## Context

- input: {"name":"pack","type":"literal","value":"{{pack}}"}
- input: {"name":"package","type":"literal","value":"{{package}}"}
- input: {"name":"manifest-contract","type":"literal","value":"the manifest contract at compositions/references/benchmaker-manifest.md in the orchflows library"}

## Suggested files

- {{package}}

Exceptional constraints:

- mutate the target
- generate a candidate
- select, add, remove, rank, rewrite or substitute a case
- let a candidate or search context read, choose, rewrite, retire or receive item-level feedback from protected evidence

## Result


## Verification


## Feedback

[]

## Risks

[]
