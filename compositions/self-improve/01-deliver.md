---
id: 01-deliver
executor: orch-decompose
pack: orch-code-pack
depends_on: [00-mine]
write_scope: [{{workspace}}]
bound: <= 120 tool calls
excluded_actions:
  - landing a proposal 00-mine did not rank first
  - editing an owner outside the proposal's scope
  - editing a friction entry or a prior covered line
  - marking a criterion complete on the executor's own claim
independence: gate
isolation: required
profile: orch-planner
---

## Objective

The top-ranked proposal from 00-mine's `## Result` landed in
{{workspace}} at its causal owner: the exact change the proposal names,
the owner's dependents still holding, the owner's required checks green
at the landed revision, and — as the delivery's last act — the covered
line appended through `tickets.py improvement --covered`, citing that
revision.

## Fixed inputs

- 00-mine's `## Result` — the top-ranked proposal by path; the proposal
  file is the run's frozen statement: its causal owner, scope, exact
  change, evidence entries and blame class, by identity.
- {{workspace}} — the repository holding the owner, at its current
  revision; its required checks as its own standards owner names them.
- rules/improvement.md §5–§6 — replay before acceptance; coverage as the
  last act.

## Completion test

- the proposal's exact change is present at the owner and nowhere outside its scope | oracle: the workspace diff against the recorded baseline | oracle_class: deterministic | provenance: pre-existing
- the owner's required checks PASS at the landed revision | oracle: the workspace's own check commands, run at that revision | oracle_class: deterministic | provenance: pre-existing
- the covered line is present in the sink's `improvement/covered.jsonl`, naming the proposal and the landed revision | oracle: `improvement/covered.jsonl` | oracle_class: deterministic | provenance: pre-existing

## Return fields

status; result — the landed revision, the changed artifacts by identity,
the covered line verbatim; verification; feedback; risks

## Result

## Verification

## Feedback

[]

## Risks

[]
