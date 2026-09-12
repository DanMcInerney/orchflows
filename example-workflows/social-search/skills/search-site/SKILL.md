---
name: search-site
description: Delegate collection from a site, web scope or feed set and return locally ranked evidence, or a worker handle for parallel composition.
---

Reuse or establish [library context](../../references/library-context.md). Resolve the question, source scope, relevant dates, caller constraints and output location. One assignment can cover a named site, web discovery across selected domains or the open web, or a supplied feed URL set.

Use `orchflows-light:orch-work` once with the resolved collection guidance and any readers. Keep delegation entrypoints in this caller:

> Collect within the assigned source scope, inspect promising material and locally rank evidence for the question. Use supplied readers and native public tools within the caller's scope and bounds. Return the handoff the guidance describes. Work without child agents.

When the caller gathers, return the native worker handle and expected evidence location immediately. Otherwise await this worker and return its actual outcome.
