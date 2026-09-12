---
name: search-site
description: Delegate research on any named site and return locally ranked evidence, or a worker handle for parallel composition.
---

Reuse or establish [library context](../../references/library-context.md). Resolve the question, site, relevant dates, caller constraints and output location.

Use orchflows-light:orch-work once with the guidance for `research.search-site.<site>` and any resolved readers. Keep delegation entrypoints in this caller:

> Search the assigned site, inspect promising material and locally rank evidence for the question. Use supplied readers and native public tools within the caller's scope and bounds. Return the handoff the guidance describes. Work without child agents.

When the caller gathers, return the native worker handle and expected evidence location immediately. Otherwise await this worker and return its actual outcome.
