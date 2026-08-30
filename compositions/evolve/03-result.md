---
id: 03-result
executor: orch-check
pack: orch-code-pack
depends_on: [02-campaign]
bound: <= 30 tool calls
independence: checker
isolation: required
---

## Goal

The campaign's verdict over {{target}}: one final score card naming the
final incumbent and the admitted result/evidence behind it.

## Context

- input: {"name":"none","type":"literal","value":null}
- input: {"name":"target","type":"literal","value":"{{target}}"}
- input: {"name":"incumbent","type":"literal","value":"{{incumbent}}"}

Exceptional constraints:

- closing on a score card that cites no admitted evidence
- expose protected evidence
- add a closing wrapper

## Result


## Verification


## Feedback

[]

## Risks

[]
