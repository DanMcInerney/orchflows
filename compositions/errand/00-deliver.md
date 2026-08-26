---
id: 00-deliver
executor: {{executor}}
pack: orch-code-pack
depends_on: []
write_scope: [{{paths}}]
mutations: [change:{{paths}}]
isolation: {{isolation}}
bound: {{bound}}
---

<!-- tickets.py errand materializes {{mutations}} and {{oracle_provenance}}. -->

## Objective

{{simple_task}}

## Fixed inputs

- input: {"name":"simple-task","type":"literal","value":"{{simple_task}}"}
- input: {"name":"{{oracle_name}}","type":"literal","value":"{{oracle_command}}"}

## Completion test

- {{oracle_name}} passes for the delivered result | oracle: {{oracle_command}} | oracle_class: deterministic | provenance: pre-existing

## Return fields

status; result; verification; changed_artifacts; feedback; risks; Carry

## Result

## Verification

## Feedback

[]

## Risks

[]
