---
id: 00-acquire
executor: orch-decompose
pack: orch-research-pack
depends_on: []
write_scope: [{{package}}]
bound: <= 120 tool calls
excluded_actions:
  - let unsupported semantics become invented target truth
independence: gate
isolation: required
profile: orch-worker
---

## Objective

One converged synthesis about {{target}} and its class, frozen with its
sources at one result identity, carrying every artifact the research
charter names.

## Fixed inputs

- input: {"name":"target","type":"literal","value":"{{target}}"}
- input: {"name":"outcome","type":"literal","value":"{{outcome}}"}
- input: {"name":"sources","type":"literal","value":"{{sources}}"}
- input: {"name":"rigor","type":"literal","value":"{{rigor}}"}
- input: {"name":"package","type":"literal","value":"{{package}}"}
- input: {"name":"research-charter","type":"literal","value":"the research charter at compositions/references/benchmaker-research.md in the orchflows library"}
## Completion test

- the terminal synthesis fixes construct definition, claim register, failure atlas, prior-art register, disagreement register, gaps and sourcing mode at one result identity | oracle: the charter's artifact list against the frozen synthesis | oracle_class: deterministic | provenance: pre-existing
- every claim maps to a case specification or a recorded gap | oracle: the claim register | oracle_class: deterministic | provenance: pre-existing

## Return fields

status; result — the frozen synthesis identity and its source
identities; verification; feedback; risks — gaps explicit; a
non-complete delivery returns partial evidence, never a closed-over gap

## Result

## Verification

## Feedback

[]

## Risks

[]
