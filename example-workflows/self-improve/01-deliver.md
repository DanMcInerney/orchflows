---
id: 01-deliver
executor: orch-execute
pack: orch-code-pack
depends_on: [00-mine]
bound: <= 120 tool calls
independence: gate
isolation: required
---

## Goal

The top-ranked proposal from 00-mine's `## Report` landed in
{{workspace}} at its causal owner: the exact change the proposal names,
the owner's dependents still holding, the owner's required checks green
at the landed revision, and — as the delivery's last act — the covered
line appended through `tickets.py improvement --covered`, citing that
revision.

## Context

- input: {"name":"workspace","type":"literal","value":"{{workspace}}"}
- input: {"name":"target-repository","type":"literal","value":"{{workspace}}"}
- input: {"name":"improvement-law","type":"literal","value":"rules/improvement.md in the orchflows library, whose §4 states the qualification this delivery inherits"}
- input: {"identity":{"kind":"ticket-section","run":"{{run}}","section":"Result","ticket":"00-mine"},"name":"ranked-proposals","type":"identity"}

## Details

- {{workspace}}

Exceptional constraints:

- landing a proposal 00-mine did not rank first
- editing an owner outside the proposal's scope
- editing a friction entry or a prior covered line
- marking a criterion complete on the executor's own claim

## Report
