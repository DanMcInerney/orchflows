---
id: 04-audit
executor: orch-check
pack: {{pack}}
depends_on: [03-qualify]
bound: <= 80 tool calls
independence: gate
isolation: required
profile: orch-planner
---

## Goal

An independent blocker report over the fixed package and qualification evidence
under the audit lens.

## Context

- input: {"name":"protocol-contract","type":"literal","value":"the protocol contract at example-workflows/references/benchmaker-protocol.md in the orchflows library"}
- input: {"name":"package","type":"literal","value":"{{package}}"}

## Details

- {{package}}

Exceptional constraints:

- Apply the pack's check craft and report every evidence-backed blocker.

## Report
