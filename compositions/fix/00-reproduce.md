---
id: 00-reproduce
executor: orch-investigate
depends_on: []
write_scope: []
bound: <= 40 tool calls
excluded_actions:
  - changing any artifact in {{workspace}}
  - naming a cause the reproduction has not toggled
independence: checker
isolation: none
---

## Objective

A deterministic reproduction of {{failure}} in {{workspace}}: one
command, runnable from a clean baseline, that fails on the observed
behaviour and on nothing else.

## Fixed inputs

- input: {"name":"failure","type":"literal","value":"{{failure}}"}
- input: {"name":"workspace","type":"literal","value":"{{workspace}}"}

## Completion test

- the reproduction command FAILs at HEAD and its failure identity names {{failure}}'s observed behaviour | oracle: the reproduction command | oracle_class: deterministic | provenance: authored-here
- the same command run at HEAD twice gives the same failure identity | oracle: the reproduction command | oracle_class: deterministic | provenance: authored-here

## Return fields

status; result — the reproduction command verbatim, the revision it was
run at, and the failure identity it produces; verification; feedback;
risks

## Result

## Verification

## Feedback

[]

## Risks

[]
