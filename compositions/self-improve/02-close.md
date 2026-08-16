---
id: 02-close
executor: orch-verify
pack: orch-code-pack
depends_on: [01-deliver]
write_scope: []
bound: <= 30 tool calls
excluded_actions:
  - accepting the delivery's own verification as the verdict
  - editing any artifact in {{workspace}} or in the state sink
independence: checker
isolation: none
profile: orch-worker
---

## Objective

Verdicts over the landed proposal: the owner's checks at the landed
revision, the coverage record, and the evidence's replay — so the same
entries cannot requalify and a regressed owner is seen here, not in the
next cycle's friction.

## Fixed inputs

- 01-deliver's `## Result` — the landed revision, the changed artifacts,
  the covered line and the replay run, by identity.
- 00-mine's `## Result` — the proposal by path, with its evidence
  entries.
- {{workspace}} at the landed revision; its required checks as its own
  standards owner names them.
- rules/improvement.md §5 — the replay condition.

## Completion test

- the owner's required checks PASS at the landed revision, rerun here | oracle: the workspace's own check commands at that revision | oracle_class: deterministic | provenance: pre-existing
- the covered line is present in `improvement/covered.jsonl`, naming the proposal and the landed revision | oracle: `improvement/covered.jsonl` | oracle_class: deterministic | provenance: pre-existing
- the replay run 01-deliver's Result names is terminal `complete`, or the proposal states why replay does not apply | oracle: that run's terminal ticket status, or the proposal's stated non-applicability | oracle_class: deterministic | provenance: pre-existing

## Return fields

status; result — the verdict per criterion with evidence cited by
identity, and the replay run by identity where one ran; verification;
feedback; risks

## Result

## Verification

## Feedback

[]

## Risks

[]
