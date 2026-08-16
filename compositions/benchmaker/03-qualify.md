---
id: 03-qualify
executor: orch-decompose
pack: {{pack}}
depends_on: [02-materialize]
write_scope: [{{package}}]
bound: <= 80 tool calls
excluded_actions:
  - let builders qualify their own work
  - accept a builder's own cases or authored oracles as sufficient evidence
  - return a self-qualified verdict set, or the pending marker presented as finished, where the builder-disjoint context is unreachable
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

- 02-materialize's `## Result` — the assembled case set by identity, the
  fixed identity qualification runs against.
- 01-design's `## Result` — the required criteria, their oracles and
  `oracle_class`, and the gaps carried forward.
- [the protocol](../references/benchmaker-protocol.md)'s qualification
  mechanics — what each check means, what the seeded variants are, and
  what leaves a check UNVERIFIED.
- The known-good and known-bad seeds this qualifying context supplies;
  where no known-bad variant can exist, discrimination is UNVERIFIED
  with an explicit gap.

## Completion test

- every required check is recomputed from the resolved component bytes and captured outputs, never from a self-declared verdict | oracle: the qualification record against the package's locators | oracle_class: deterministic | provenance: pre-existing
- the benchmark passes every good seed and fails every bad one, at the declared trial count where the outcome is nondeterministic | oracle: the seeded runs | oracle_class: deterministic | provenance: authored-here
- a required deterministic failure blocks qualification, and a judged criterion neither compensates for one nor is recorded without its rerun variance | oracle: the verdict set read against contracts/verdict.md | oracle_class: deterministic | provenance: pre-existing

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
