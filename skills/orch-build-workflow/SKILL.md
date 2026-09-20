---
name: orch-build-workflow
description: Create or improve workflows and guidance; test them with realistic fixtures and simulated external effects.
disable-model-invocation: true
---

Identify the recurring request and result. Apply [architecture](../../docs/architecture.md) and [library authoring](../../docs/libraries.md) with `orchflows` and `writing` guidance. Author directly or use [orch-work](../orch-work/SKILL.md), honoring settings.

Save inputs, dependencies, process, outputs and stopping conditions. Keep task details in prompts and quality criteria, methods and taste in guidance. Reuse components by supplying scoped inputs; avoid restating their contracts. Leave staffing flexible unless freshness is required. Save model/effort preferences only when requested. Verify [invocation policy](../../docs/hosts.md#invocation-policy).

Before review, run the smallest representative [trial](../../docs/hosts.md#workflow-trials) with synthetic inputs and simulated external effects. Supplied documents are read-only references, not trial targets. Finish selected trials and their required judgments before authoring review; record fixtures, substitutions, interventions and untested branches. If a safe trial is unavailable, report that gap instead of exercising live data or services. Repair observed failures and rerun affected checks. Improvement claims require matched old/new trials.

Use [orch-review](../orch-review/SKILL.md) once on the stable whole candidate with requirements, sources, authoring guidance and completed trial evidence. Unavailable or incomplete review blocks repairs; preserve the candidate and report the gap. After review, make at most one coordinated repair pass for actionable findings within scope, honoring fixer settings and ownership. Run affected and caller-required checks even without repairs; repeat affected trials when repairs require it. Return the artifact, checks and gaps, preserving the original review and inspected state separately from the delivered revision; repairs do not inherit the verdict. Add no second review, release or external decision pause. Verify native registration before claiming availability by name.
