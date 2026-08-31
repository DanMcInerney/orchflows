---
id: 00-acquire
executor: orch-do
pack: orch-research-pack
depends_on: []
bound: <= 120 tool calls
independence: gate
profile: orch-worker
---

## Goal

One converged synthesis about {{target}} and its class, frozen with its
sources at one result identity, carrying every artifact the research
charter names.

## Context

- input: {"name":"target","type":"literal","value":"{{target}}"}
- input: {"name":"outcome","type":"literal","value":"{{outcome}}"}
- input: {"name":"sources","type":"literal","value":"{{sources}}"}
- input: {"name":"rigor","type":"literal","value":"{{rigor}}"}
- input: {"name":"package","type":"literal","value":"{{package}}"}
- input: {"name":"research-charter","type":"literal","value":"the research charter at example-workflows/references/benchmaker-research.md in the orchflows library"}

## Details

- {{package}}

Exceptional constraints:

- let unsupported semantics become invented target truth

## Report
