---
id: 02-campaign
executor: orch-loop
pack: orch-code-pack
depends_on: [01-eligibility]
write_scope: [{{mutation_scope}}]
bound: {{bound}}
excluded_actions:
  - change evaluation after campaign open
  - rank an ineligible candidate
  - re-execute or substitute admitted evidence
  - expose protected evidence
  - call benchmaker
  - activate a selected candidate
  - add a closing wrapper
  - unfreezing a campaign constant — evaluation identity, mode, scoring, criteria, evidence adapter, runner, protected evidence policy, controller and planner revisions, mutation authority, search policy, promotion rule, margin and bound are fixed at open, and a changed constant starts a new campaign and reevaluates every retained candidate rather than continuing this one
  - closing on a promotion — promotion alone never completes the campaign; the done-check does
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

## Fixed inputs

- 01-eligibility's `## Result` — the admission verdicts and the frozen
  evaluation identity, mode and criteria, by identity.
- Body, one generation: generate N candidates through {{writer}} within
  {{mutation_scope}} ‖ score each one blind through orch-verify against
  the frozen scoring criteria — a scoring lane's inputs carry that
  candidate and nothing else, and what blindness is is
  [orch-verify](../../skills/kernel/orch-verify/SKILL.md)'s — then
  select by the frozen promotion rule and margin over the score cards;
  where the frozen search policy is a search-policy/v1 object,
  `search_plan.py advance` performs the selection. Slot, parent and
  spend mapping:
  [the generation protocol](../references/evolve-generation.md).
- A scoring lane scores and dispatches nothing: the children that apply
  a candidate are dispatched by this loop's own engine, one host depth
  below the orchestrator, per
  [the frontier's profiles](../../skills/engines/orch-frontier/references/profiles.md).
- Done-check: the frozen promotion rule and margin have been applied
  over the final incumbent's score card and rendered a verdict —
  promoted or kept — or {{bound}} is spent.
- Context packet: the worklog view `tickets.py worklog` renders —
  goal, iterations, failed approaches, queued scope — beside this
  campaign's own promotion/kill log and the score cards under
  {{mutation_scope}}; never a prior transcript.

## Completion test

- the frozen promotion rule and margin have been applied over the final incumbent's score card and rendered a verdict — promoted or kept — or the bound is spent | oracle: the promotion rule from 01-eligibility's Result, applied to the final score card | oracle_class: deterministic | provenance: pre-existing
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
