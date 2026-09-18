---
name: orch-dynamic-workflow
description: Plan, execute and independently review top-level tasks, including straightforward work, unless the user selects a workflow or primitive. Not for child assignments or questions about the library.
disable-model-invocation: false
---

Apply [architecture](../../docs/architecture.md) in the top-level coordinator. Explicit workflow/primitive selections own their process; never wrap them or replace unavailable selections. Children follow assignments without starting this workflow.

Establish the result and checks. Plan stages, dependencies, guidance, review gates and stopping conditions briefly. Reuse fitting workflows and primitives in this coordinator, preserving contracts and scoped inputs. Create a reusable skill only when requested.

Default to one independent review of the joined result. Add intermediate gates for research or design decisions costly to correct downstream. Preserve components' required gates; count existing reviews only when candidate, criteria and scope match. State gates and bounds before dependent stages; planning grants no new resource allowance.

Run independent research and implementation concurrently through [orch-work](../orch-work/SKILL.md), with clear ownership. Already-clear work may be done directly when settings permit. Gather outcomes and resolve shared decisions before dependent work; pass artifacts and applicable guidance onward. Adapt to evidence within selected gates and bounds.

At this workflow's gates, apply [orch-review-revise-once](../orch-review-revise-once/SKILL.md) to the stable joined candidate with the stage's sources, guidance, repair scope and required checks. Complete review and permitted repair/checks before dependent work; unresolved blocking findings or missing required evidence block it. Each gate permits at most one repair pass. Return the result, checks, original reviews, delivered revisions and gaps.
