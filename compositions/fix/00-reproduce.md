---
id: 00-reproduce
executor: orch-investigate
depends_on: []
bound: <= 40 tool calls
independence: checker
isolation: none
---

## Goal

A deterministic reproduction of {{failure}} in {{workspace}}: one
command, runnable from a clean baseline, that fails on the observed
behaviour and on nothing else.

## Context

- input: {"name":"failure","type":"literal","value":"{{failure}}"}
- input: {"name":"workspace","type":"literal","value":"{{workspace}}"}

Exceptional constraints:

- changing any artifact in {{workspace}}
- naming a cause the reproduction has not toggled

## Result


## Verification


## Feedback

[]

## Risks

[]
