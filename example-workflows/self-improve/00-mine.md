---
id: 00-mine
executor: orch-execute
pack: orch-content-pack
loop: true
done: {"form":"check","value":"Ranked qualifying proposals are written to the state sink's improvement/ and the top-ranked proposal, or the finding that nothing qualified, is named in Result."}
depends_on: []
bound: <= 60 tool calls
independence: checker
profile: orch-planner
---

## Goal

Ranked improvement proposals for {{window}}, each written to the state
sink's `improvement/` through `tickets.py improvement --proposal` with
one causal owner, its scope, the exact change, and every evidence entry
verbatim — and the top-ranked proposal named as this run's delivery
target, or the finding that nothing qualified.

## Context

- input: {"name":"window","type":"literal","value":"{{window}}"}
- input: {"name":"improvement-law","type":"literal","value":"rules/improvement.md in the orchflows library, whose §4 states the qualification and ranking this run applies"}

Exceptional constraints:

- editing any artifact of the mined workspace
- editing a friction entry or a prior covered line
- ranking a proposal on evidence a covered watermark already answers

## Report
