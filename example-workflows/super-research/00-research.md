---
id: 00-research
executor: orch-execute
pack: orch-research-pack
depends_on: []
bound: <= 100 tool calls
independence: checker
isolation: none
profile: orch-worker
---

## Goal

One evidence-first answer to {{question}}: an `AcquisitionArtifact` from the
`super-research` skill, every `StepResult`'s `outcome` and `loss` read rather
than dropped, then the report -- each load-bearing claim cited from its
`normalized_locator` and dated, a community comment quoted verbatim with its
author and count, every typed loss stated rather than read as an absence,
contradicting sources preserved rather than averaged, and an unanswered
sub-question declared as a gap rather than assumed away.

## Context

- input: {"name":"question","type":"literal","value":"{{question}}"}
- Skill: invoke `super-research`
  (`.orchflows/skills/super-research/SKILL.md`) by name. Its own Require,
  Preparation and Never sections bind this ticket and are not restated here.

## Report
