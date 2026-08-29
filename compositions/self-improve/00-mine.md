---
id: 00-mine
executor: orch-loop
depends_on: []
bound: <= 60 tool calls
independence: checker
isolation: none
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

## Result


## Verification


## Feedback

[]

## Risks

[]
