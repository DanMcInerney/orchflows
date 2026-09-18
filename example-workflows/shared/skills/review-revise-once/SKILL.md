---
name: review-revise-once
description: Independently review a stable candidate, make at most one repair pass, and return the reviewed and delivered states with distinct evidence.
disable-model-invocation: true
---

Establish [library context](../../references/library-context.md). Apply `orchflows:orch-review-revise-once` in this coordinator with the candidate, requirements, evidence, guidance, permitted repair scope, required checks and output location. Pass through supplied maker handles and fixer settings. Return its reviewed/delivered states, findings, checks and gaps. This compatibility entry adds no stage or adoption decision.
