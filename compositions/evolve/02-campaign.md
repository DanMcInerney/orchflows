---
id: 02-campaign
executor: orch-loop
pack: orch-code-pack
depends_on: [01-eligibility]
write_scope: [{{mutation_scope}}]
bound: {{bound}}
excluded_actions:
  - rank an ineligible candidate
  - re-execute or substitute admitted evidence
  - expose protected evidence
  - call benchmaker
  - activate a selected candidate
  - add a closing wrapper
  - unfreezing a campaign constant — evaluation identity, mode, scoring, criteria, evidence adapter, runner, protected evidence policy, controller and planner revisions, mutation authority, search policy, promotion rule, margin and bound are fixed at open, and a changed constant starts a new campaign and reevaluates every retained candidate rather than continuing this one
  - keeping a candidate that lacks PASS on every required admission criterion — kill it, since a score never compensates
  - taking an archive member as anything but an exploration parent
independence: checker
isolation: required
profile: orch-worker
---

## Objective

A final incumbent for {{target}} inside {{mutation_scope}}: generations
of candidates, each written and scored under the frozen evaluation,
until the frozen promotion rule and margin are met over the final
incumbent's score card or {{bound}} is spent.

Each generation consumes 01-eligibility's `## Result` and scores blind through
orch-verify; `search_plan.py advance` selects search-policy/v1 cases under the
generation protocol.

## Fixed inputs

- input: {"name":"writer","type":"literal","value":"{{writer}}"}
- input: {"name":"mutation-scope","type":"literal","value":"{{mutation_scope}}"}
- input: {"name":"bound","type":"literal","value":"{{bound}}"}
- input: {"name":"target","type":"literal","value":"{{target}}"}

## Completion test

- a candidate has been promoted: the frozen promotion rule and margin met over its score card against the incumbent's | oracle: the promotion rule from 01-eligibility's Result, applied to the score cards | oracle_class: deterministic | provenance: pre-existing
- every scored candidate's lane carried that candidate alone | oracle: the scoring lane inputs, read against the candidate set | oracle_class: deterministic | provenance: pre-existing
- every changed path lies inside {{mutation_scope}} | oracle: the workspace diff against the recorded baseline | oracle_class: deterministic | provenance: pre-existing

## Return fields

status; result — the final incumbent identity, generation count, and the
promotion/kill log; verification — the score cards and the plan and
projection identities they were taken under; then bounds spent and
cumulative changed artifacts, including accepted descendant changes and
the worklog path; feedback; risks

## Result

## Verification

## Feedback

[]

## Risks

[]
