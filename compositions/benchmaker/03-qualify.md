---
id: 03-qualify
executor: orch-decompose
pack: {{pack}}
depends_on: [02-materialize]
write_scope: [{{package}}]
bound: <= 80 tool calls
excluded_actions:
  - return a self-qualified verdict set where the builder-disjoint context is unreachable
independence: gate
isolation: required
profile: orch-worker
---

## Objective

The assembled benchmark qualified at a fixed identity in a delivery
disjoint from every builder: oracle failability, coverage,
discrimination, reproducibility, redundancy, provenance and execution
cost each checked independently, with a verdict per required criterion.

## Fixed inputs

- input: {"identity":{"kind":"artifact","locator":"project:compositions/references/benchmaker-protocol.md","sha256":"cbe548149efd0ce3184e5f805a91173bd85a6c8a354f8d6e083a1781e4331f8d"},"name":"protocol-contract","type":"identity"}
- input: {"name":"package","type":"literal","value":"{{package}}"}
- input: {"name":"pack","type":"literal","value":"{{pack}}"}

## Completion test

- every required check is recomputed on the protocol's §Qualification terms, never from a self-declared verdict | oracle: the qualification record against the package's locators | oracle_class: deterministic | provenance: pre-existing
- the seeded discrimination check holds as §Qualification states it | oracle: the seeded runs | oracle_class: deterministic | provenance: authored-here
- the verdict set honours §Qualification on required deterministic failure and on judged criteria | oracle: the verdict set read against contracts/verdict.md and §Qualification | oracle_class: deterministic | provenance: pre-existing

## Return fields

status; result — the qualification verdict set by criterion with its
evidence, the qualifying context's model id, effort and host binding,
expected cost and actual qualification spend; verification; feedback;
risks — gaps explicit

## Result

## Verification

## Feedback

[]

## Risks

[]
