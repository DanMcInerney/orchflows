---
id: 05-measure
executor: orch-check
pack: {{pack}}
depends_on: [04-audit]
bound: <= 40 tool calls
independence: checker
isolation: required
---

## Goal

The manifest recorded, and the measurement pass beside it: what the
candidates scored over the candidate-accessible scope at the declared
rungs, on [§Measurement pass](../references/benchmaker-protocol.md#measurement-pass)'s terms.

## Context

- input: {"name":"manifest-contract","type":"literal","value":"the manifest contract at example-workflows/references/benchmaker-manifest.md in the orchflows library"}
- input: {"name":"protocol-contract","type":"literal","value":"the protocol contract at example-workflows/references/benchmaker-protocol.md in the orchflows library"}
- input: {"name":"package","type":"literal","value":"{{package}}"}

## Details

- {{package}}

Exceptional constraints:

- rank candidates
- promote or activate anything

## Report
