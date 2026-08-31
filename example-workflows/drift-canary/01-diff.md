---
id: 01-diff
executor: orch-do
pack: orch-content-pack
loop: true
done: {"form":"check","value":"Every canary item carries a verdict against its golden result, and every divergence carries one friction entry in the improvement evidence sink."}
depends_on: [00-run]
bound: <= 40 tool calls
independence: checker
---

## Goal

One verdict per canary item against its golden result, and one friction
entry per divergence, so the delta between the new binding and the
frozen one is recorded in the improvement evidence sink.

## Context

- input: {"identity":{"kind":"ticket-section","run":"{{run}}","section":"Result","ticket":"00-run"},"name":"canary-results","type":"identity"}
- input: {"name":"canary-set","type":"literal","value":"{{canary_set}}"}

Exceptional constraints:

- edit a golden result inside a canary run
- treat divergence as failure

## Report
