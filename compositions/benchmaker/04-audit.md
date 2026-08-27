---
id: 04-audit
executor: orch-critique
depends_on: [03-qualify]
bound: <= 80 tool calls
independence: gate
isolation: required
profile: orch-planner
---

## Goal

An `orch-critique` report over the fixed package and qualification evidence
under the audit lens.

## Context

- input: {"name":"protocol-contract","type":"literal","value":"the protocol contract at compositions/references/benchmaker-protocol.md in the orchflows library"}
- input: {"name":"package","type":"literal","value":"{{package}}"}

## Suggested files

- {{package}}

Exceptional constraints:

- Apply the evaluator contract in `skills/kernel/orch-critique/SKILL.md`.

## Result


## Verification


## Feedback

[]

## Risks

[]
