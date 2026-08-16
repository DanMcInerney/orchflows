---
id: 00-mine
executor: orch-self-improve
pack: orch-code-pack
depends_on: []
write_scope: []
bound: <= 60 tool calls
excluded_actions:
  - everything the orch-self-improve skill body's Never clause forbids
independence: checker
isolation: none
profile: orch-planner
---

## Objective

Ranked improvement proposals for {{window}}, each written to the state
sink's `improvement/` through `tickets.py improvement --proposal` with
one causal owner, its scope, the exact change, and every evidence entry
verbatim — and the top-ranked proposal named as this run's delivery
target, or the finding that nothing qualified.

## Fixed inputs

- {{window}} — this run's value for the window orch-self-improve's
  Require defines.
- The state sink's `friction/`, `runs/`, `tickets/` and
  `improvement/covered.jsonl`, at their root per
  rules/visibility.md §6, read as data.
- rules/improvement.md §3–§6 — scope, qualification, replay, coverage.

## Completion test

- every proposal names exactly one causal owner as a repository-relative path and cites its evidence entries verbatim | oracle: each proposal file under the sink's `improvement/` | oracle_class: deterministic | provenance: pre-existing
- no proposal rests on an entry at or before a covered cluster's watermark | oracle: the proposals' evidence against `improvement/covered.jsonl` | oracle_class: deterministic | provenance: pre-existing
- the ranking follows evidence strength — green replay, checked contradiction or probe, then recurrence | oracle: each proposal's qualification basis against rules/improvement.md §4 | oracle_class: judged | provenance: pre-existing

## Return fields

status; result — everything orch-self-improve's Return names, and the
top-ranked proposal by path; verification; feedback; risks

## Result

## Verification

## Feedback

[]

## Risks

[]
