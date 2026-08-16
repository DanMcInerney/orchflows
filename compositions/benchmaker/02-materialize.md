---
id: 02-materialize
executor: orch-decompose
pack: {{pack}}
depends_on: [01-design]
write_scope: [{{package}}]
bound: <= 120 tool calls
excluded_actions:
  - mutate the target
  - generate a candidate
  - select, add, remove, rank, rewrite or substitute a case
  - let a candidate or search context read, choose, rewrite, retire or receive item-level feedback from protected evidence
independence: gate
isolation: required
profile: orch-worker
---

## Objective

Every case specification the frozen design names, materialized exactly
into {{package}}: runnable cases, runner, scoring data and provenance,
each at a preserved identity.

## Fixed inputs

- 01-design's `## Result`, in full: whatever orch-eval-design's Return
  filed there.
- {{pack}} — the run's stamp.
- {{package}} — the target repository: where the materialized case set
  is written. Builders' write scopes are disjoint.
- [the manifest](../references/benchmaker-manifest.md) — the field set
  this stage writes with the pending `qualification` marker.
- The standards owner, by pointer: the workspace's own owner file —
  AGENTS.md or its equivalent.
- Acceptance as runnable checks: the workspace's required checks as
  that owner names them, beside this stub's own completion test.

## Completion test

- every case the design names exists and runs, and no case exists that the design does not name | oracle: the case set against the frozen design | oracle_class: deterministic | provenance: pre-existing
- each case, runner, scoring and provenance identity is preserved from the design | oracle: the identities recorded in the package | oracle_class: deterministic | provenance: pre-existing
- protected evidence is fixed by identity with its visibility and release policy | oracle: the package's protected-evidence record | oracle_class: deterministic | provenance: pre-existing

## Return fields

status; result — the assembled case set by identity, the builder
contexts' model id, effort and host binding per case, and changed
artifacts; verification; feedback; risks

## Result

## Verification

## Feedback

[]

## Risks

[]
