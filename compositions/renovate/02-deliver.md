---
id: 02-deliver
executor: orch-frontier
pack: {{pack}}
depends_on: [01-triage]
bound: {{brief_bound}} per ready-for-agent brief
independence: gate
isolation: required
profile: orch-worker
---

## Goal

Every ready-for-agent brief delivered into {{workspace}} with its own
final verification, and every ready-for-human brief returned to the
maintainer unanswered. One root ticket over every brief, not one per
brief: this cut yields a unit per brief, so the gate runs once over the
whole delivery.

## Context

- input: {"name":"pack","type":"literal","value":"{{pack}}"}
- input: {"name":"workspace","type":"literal","value":"{{workspace}}"}
- input: {"name":"brief-bound","type":"literal","value":"{{brief_bound}}"}

## Details

- {{workspace}}

Exceptional constraints:

- deliver a brief 01-triage did not disposition ready-for-agent
- answer a ready-for-human brief on the maintainer's behalf

## Report
