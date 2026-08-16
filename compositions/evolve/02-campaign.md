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
  - call Benchmaker
  - activate a selected candidate
  - add a closing wrapper
  - unfreezing a campaign constant — evaluation identity, mode, scoring, criteria, evidence adapter, runner, protected evidence policy, mutation authority, search policy, promotion rule, margin and bound are fixed at open, and a changed constant starts a new campaign rather than continuing this one
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
  candidate and nothing else, which is what blindness is — then select
  through `python search_plan.py advance`. Slot, parent and spend
  mapping: [the generation protocol](../references/evolve-generation.md).
- Done-check: the frozen promotion rule and margin met over the final
  incumbent's score card.
- Context packet: the worklog `tickets.py worklog` renders — accepted
  plan and projection identities, spend and launch state — never a prior
  transcript.

## Completion test

- the frozen promotion rule and margin are met over the final incumbent's score card | oracle: the promotion rule from 01-eligibility's Result, applied to the final score card | oracle_class: deterministic | provenance: pre-existing
- every scored candidate's lane carried that candidate alone | oracle: the scoring lane inputs, read against the candidate set | oracle_class: deterministic | provenance: pre-existing
- every changed path lies inside {{mutation_scope}} | oracle: the workspace diff against the recorded baseline | oracle_class: deterministic | provenance: pre-existing

## Return fields

status; result — the final incumbent identity, generation count, and the
promotion/kill log; verification — the score cards and the plan and
projection identities they were taken under; feedback; risks

## Result

## Verification

## Feedback

[]

## Risks

[]
