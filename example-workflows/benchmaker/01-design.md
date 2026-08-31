---
id: 01-design
executor: orch-do
pack: {{pack}}
depends_on: [00-acquire]
bound: <= 60 tool calls
independence: checker
isolation: none
profile: orch-worker
---

## Goal

One evaluation for {{target}}, frozen at one package-owned identity:
case specifications with their execution tiers and anchors, measurable
criteria and evidence classifications, scoring and aggregation,
intended coverage, and expected execution cost.

## Context

- input: {"name":"target","type":"literal","value":"{{target}}"}
- input: {"name":"outcome","type":"literal","value":"{{outcome}}"}
- input: {"name":"sources","type":"literal","value":"{{sources}}"}
- input: {"name":"protocol-contract","type":"literal","value":"the protocol contract at example-workflows/references/benchmaker-protocol.md in the orchflows library"}
- input: {"name":"package","type":"literal","value":"{{package}}"}

## Details

- {{package}}

Exceptional constraints:

- move the declared coverage floor with the target's execution cost
- buy speed from the coverage floor, the oracle, or the horizon the outcome needs

## Report
