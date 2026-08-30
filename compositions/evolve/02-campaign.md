---
id: 02-campaign
executor: orch-execute
pack: orch-code-pack
loop: {"done":{"form":"check","value":"The frozen promotion rule and margin are met over the final incumbent's score card, per the campaign's frozen evaluation."}}
depends_on: [01-eligibility]
bound: {{bound}}
independence: checker
profile: orch-worker
---

## Goal

A final incumbent for {{target}} inside {{mutation_scope}}: generations
of candidates, each written and scored under the frozen evaluation,
until the frozen promotion rule and margin are met over the final
incumbent's score card or {{bound}} is spent.

Each generation consumes 01-eligibility's `## Result` and scores blind through
orch-check; `search_plan.py advance` selects search-policy/v1 cases under the
generation protocol.

## Context

- input: {"name":"writer","type":"literal","value":"{{writer}}"}
- input: {"name":"mutation-scope","type":"literal","value":"{{mutation_scope}}"}
- input: {"name":"bound","type":"literal","value":"{{bound}}"}
- input: {"name":"target","type":"literal","value":"{{target}}"}

## Suggested files

- {{mutation_scope}}

Exceptional constraints:

- rank an ineligible candidate
- re-execute or substitute admitted evidence
- expose protected evidence
- call benchmaker
- activate a selected candidate
- add a closing wrapper
- unfreezing a campaign constant — evaluation identity, mode, scoring, criteria, evidence adapter, runner, protected evidence policy, controller and planner revisions, mutation authority, search policy, promotion rule, margin and bound are fixed at open, and a changed constant starts a new campaign and reevaluates every retained candidate rather than continuing this one
- keeping a candidate that lacks PASS on every required admission criterion — kill it, since a score never compensates
- taking an archive member as anything but an exploration parent

## Result


## Verification


## Feedback

[]

## Risks

[]
