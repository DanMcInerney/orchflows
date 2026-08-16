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
  - restate or call evolve's verification, panel, search, or selection internals
  - letting a benchmaker run targeting benchmaker call evolve
independence: checker
isolation: required
profile: orch-worker
---

## Objective

One qualified benchmark revision for {{skill}}, fixed at the git
revision its manifest names, that the campaign behind it never changes.

## Fixed inputs

- Instantiate compositions/benchmaker into a nested run of its own —
  this ticket's own `run` field plus `.00-benchmark`, never the outer
  run — naming every placeholder that manifest declares:
  target={{skill}}, outcome={{skill}}'s declared observable outcome,
  sources={{sources}}, rigor={{rigor}},
  bound=this stub's own bound below, pack={{pack}},
  package=the benchmark write scope this stub holds. Drain that ticket
  set here.
- This stub's bound is the benchmark's own allocation, partitioned
  before the work and never drawn from the campaign's, which is why the
  nested run's caller bound is this one and not {{bound}}.
- The qualified result is recorded in the package's manifest, whose
  field set and component resolution the manifest reference owns; the
  benchmark's version is the git revision it sits at.

## Completion test

- the nested run met benchmaker's done check, which [its terminal stub](../benchmaker/05-measure.md) states | oracle: the manifest read against the package's component set | oracle_class: deterministic | provenance: pre-existing
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
