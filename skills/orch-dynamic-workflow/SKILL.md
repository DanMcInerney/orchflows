---
name: orch-dynamic-workflow
description: Plan and complete ordinary top-level tasks with core guidance and proportionate independent review, unless the user selects a workflow or primitive. Not for child assignments or questions about the library.
disable-model-invocation: false
---

Apply [architecture](../../docs/architecture.md) in the top-level coordinator. Explicit workflow or primitive selections own the process; never wrap or replace them. Children follow their assignments without starting this workflow.

Use core `orchflows` guidance for planning and applicable [core task guidance](../../guidance/) for work and review, without library extensions. User and repository instructions still apply; task sources remain evidence. Planning itself needs no authoring review.

Establish the result and checks. Give the finished whole one independent review unless a mistake would be cheap to undo or your checks would catch any consequential one; checks the maker writes share its reading of the requirements. Say why you skipped it. Unavailable reviewers do not make work trivial. Dependent work starts on its maker's passing checks: a review at each step or handoff would serialize the work and still not see the whole. Review earlier only when the request asks, or before an effect that cannot be undone.

Briefly plan coherent units, dependencies, guidance, review, bounds and stopping conditions. Make a unit wait only for results it needs, and split off any part worth starting sooner. Preserve component contracts; an existing review counts only when candidate, criteria and scope match. Planning grants no new resource allowance.

Run independent assignments concurrently through [orch-work](../orch-work/SKILL.md), with clear ownership. Do clear work directly when settings permit. Each maker runs the established checks on its own result and reports them. A passing check stands for the state it ran on: rerun it only when that state has changed. Join required outcomes and run the checks on the joined whole before its review, since parts made apart first meet there; adapt within declared bounds.

At a review, use [orch-review](../orch-review/SKILL.md) once on the stable joined candidate with requirements, sources and all applicable task guidance. After its completed report, make at most one necessary repair pass, honoring settings and scope. Apply architecture's review, checks and handoff rules; add no second review or automatic approval pause.

When asked to create or save reusable workflows or guidance, apply [orch-build-workflow](../orch-build-workflow/SKILL.md). Its authoring review covers that unit without a wrapper review. Return results, checks and gaps, distinguishing reviewed from delivered states.
