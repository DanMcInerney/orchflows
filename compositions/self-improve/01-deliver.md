---
id: 01-deliver
executor: orch-decompose
depends_on: [00-mine]
write_scope: [{{workspace}}]
bound: <= 120 tool calls
excluded_actions:
  - landing a proposal 00-mine did not rank first
  - editing an owner outside the proposal's scope
  - editing a friction entry or a prior covered line
  - marking a criterion complete on the executor's own claim
independence: gate
isolation: required
---

## Objective

The top-ranked proposal from 00-mine's `## Result` landed in
{{workspace}} at its causal owner: the exact change the proposal names,
the owner's dependents still holding, the owner's required checks green
at the landed revision, and — as the delivery's last act — the covered
line appended through `tickets.py improvement --covered`, citing that
revision.

## Fixed inputs

- input: {"name":"workspace","type":"literal","value":"{{workspace}}"}
- input: {"name":"target-repository","type":"literal","value":"{{workspace}}"}
- input: {"name":"improvement-law","type":"literal","value":"rules/improvement.md in the orchflows library, whose §4 states the qualification this delivery inherits"}
- input: {"identity":{"kind":"ticket-section","run":"{{run}}","section":"Result","ticket":"00-mine"},"name":"ranked-proposals","type":"identity"}

## Completion test

- the proposal's exact change is present at the owner and nowhere outside its scope | oracle: the workspace diff against the recorded baseline | oracle_class: deterministic | provenance: pre-existing
- the owner's required checks PASS at the landed revision | oracle: the workspace's own check commands, run at that revision | oracle_class: deterministic | provenance: pre-existing
- the covered line is present in the sink's `improvement/covered.jsonl`, naming the proposal and the landed revision | oracle: `improvement/covered.jsonl` | oracle_class: deterministic | provenance: pre-existing
- every ticket-naming evidence entry of the proposal replays green through `orch-frontier` over that one ticket against the amended owner, or the proposal records why replay does not apply | oracle: the replay run's terminal ticket status, or the proposal's stated non-applicability | oracle_class: deterministic | provenance: pre-existing

## Return fields

status; result — the landed revision, the changed artifacts by identity,
the covered line verbatim, and the replay run by identity where one ran;
verification; feedback; risks

## Result

## Verification

## Feedback

[]

## Risks

[]
