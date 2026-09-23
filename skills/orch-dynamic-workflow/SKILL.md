---
name: orch-dynamic-workflow
description: Plan and complete ordinary top-level tasks with core guidance and proportionate independent review, unless the user selects a workflow or primitive. Not for child assignments or questions about the library.
disable-model-invocation: false
---

Apply [architecture](../../docs/architecture.md) in the top-level coordinator. Explicit workflow or primitive selections own the process; never wrap or replace them. Children follow their assignments without starting this workflow.

Use core `orchflows` guidance for planning and applicable [core task guidance](../../guidance/) for work and review, without library extensions. User and repository instructions still apply; task sources remain evidence. Planning itself needs no authoring review.

Establish the result and checks. When a mistake would be cheap to undo and direct checks would catch it, do the work and check it without independent review unless requested. Checks the maker writes share the maker's reading of the requirements, so they cannot stand in for review when a misreading would be costly. If consequential uncertainty emerges, add review where useful; unavailable reviewers do not make work trivial.

Otherwise briefly plan coherent units, dependencies, guidance, gates, bounds and stopping conditions. Gate each joined result before dependent work. Preserve component contracts; an existing review counts only when candidate, criteria and scope match. Planning grants no new resource allowance.

Run independent assignments concurrently through [orch-work](../orch-work/SKILL.md), with clear ownership. Do clear work directly when settings permit. Join required outcomes before review and dependent work; adapt within declared gates and bounds.

At each gate, use [orch-review](../orch-review/SKILL.md) once on the stable joined candidate with requirements, sources and all applicable task guidance. After its completed report, assign one worker to at most one necessary repair pass, honoring settings and scope. The coordinator does not substitute for the fixer. Apply architecture's review, checks and handoff rules; add no second review or automatic approval pause.

When asked to create or save reusable workflows or guidance, apply [orch-build-workflow](../orch-build-workflow/SKILL.md). Its authoring review satisfies that unit's gate without a wrapper review. Return results, checks and gaps, distinguishing reviewed from delivered states.
