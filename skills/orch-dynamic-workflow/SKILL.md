---
name: orch-dynamic-workflow
description: Default workflow for top-level task execution, including straightforward work, when the user has not selected a workflow or primitive. Plan, execute and independently review the result. Not for child assignments or questions about the library.
disable-model-invocation: false
---

Apply [architecture](../../docs/architecture.md) in the top-level coordinator. An explicitly selected workflow or primitive owns its process; do not wrap it in this workflow or replace an unavailable selection. Child agents follow their assignments without starting this workflow.

Establish the intended result and its checks. Form a brief task-specific plan: stages and dependencies, applicable guidance, review gates and stopping conditions. Reuse fitting workflows and primitives in this coordinator, preserving their contracts and scoped inputs. This plan is for execution; create a reusable skill only when requested.

Default to one independent review of the joined result. Add intermediate review gates where downstream work depends on research or design decisions that would be costly to correct later. Preserve selected components' required gates; count an existing review toward a planned gate only when its candidate, criteria and scope match. State the gates and bounds before executing dependent stages; creating or adjusting the plan grants no new resource allowance.

Run independent research and implementation assignments concurrently through [orch-work](../orch-work/SKILL.md), with clear ownership. Already-clear work may be done directly when settings permit. Gather outcomes and resolve shared decisions before dependent work; pass artifacts and only applicable guidance onward. Adapt remaining work to evidence within the selected gates and bounds.

At gates supplied by this workflow, apply [orch-review-revise-once](../orch-review-revise-once/SKILL.md) to the stable joined candidate with that stage's sources, guidance, repair scope and required checks. Complete the review and any permitted repair/checks before work that depends on the gate; unresolved blocking findings or missing required evidence block that work. Each such gate permits at most one repair pass. Return the result, checks, original reviews, delivered revisions and remaining gaps.
