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
- [the protocol](../references/benchmaker-protocol.md#qualification) —
  what each check means, what the seeded variants are, what the
  qualifying context supplies, and what leaves a check UNVERIFIED.
- {{package}} — the target repository the qualified assembly sits in.
- The standards owner, by pointer: the workspace's own owner file —
  AGENTS.md or its equivalent.
- Acceptance as runnable checks: the workspace's required checks as
  that owner names them, beside this stub's own completion test.

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
