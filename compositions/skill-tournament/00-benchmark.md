---
id: 00-benchmark
executor: orch-frontier
pack: orch-code-pack
depends_on: []
write_scope: [benchmarks/{{skill}}/]
bound: <= 200 tool calls
excluded_actions:
  - mutating {{skill}} — the benchmark is built for it, never by changing it
  - generating, scoring or comparing a candidate; this stub builds and qualifies, and nothing else
independence: checker
isolation: required
profile: orch-worker
---

## Objective

One qualified benchmark revision for {{skill}}, fixed at the git
revision its manifest names, that the campaign behind it never changes.

## Fixed inputs

- Instantiate compositions/benchmaker into this run with
  target={{skill}}, its declared observable outcome, and the benchmark
  write scope this stub holds; drain that ticket set here.
- This stub's bound is the benchmark's own allocation, partitioned
  before the work and never drawn from the campaign's.
- The qualified result is recorded in the package's manifest, whose
  field set and component resolution the manifest reference owns; the
  benchmark's version is the git revision it sits at.

## Completion test

- the manifest's qualification verdict set covers every component but its own — covered PASS on every required criterion, gaps explicit (`[]` when none) | oracle: the manifest read against the package's component set | oracle_class: deterministic | provenance: pre-existing
- the benchmark revision is named by identity and the package is clean at it | oracle: git status over the benchmark package at the revision the manifest names | oracle_class: deterministic | provenance: pre-existing

## Return fields

status; result — the qualified benchmark revision by identity;
verification — the manifest's qualification; feedback; risks

## Result

## Verification

## Feedback

[]

## Risks

[]
