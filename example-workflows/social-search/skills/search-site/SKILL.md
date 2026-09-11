---
name: search-site
description: Delegate research on any named site and return locally ranked evidence, or a worker handle for parallel composition.
---

Reuse or establish [library context](../../references/library-context.md). Resolve the question, site, relevant dates, caller constraints and output location. Publication windows and forecast horizons are separate; there is no default window.

Use orchflows-light:orch-work once with the Research standard. Give the worker a concrete collection assignment, source advice and [prepare-evidence](../prepare-evidence/SKILL.md). Keep profile and delegation entrypoints in this caller:

> Search the assigned site, inspect promising material and locally rank evidence for the question. Use supplied source readers and native public tools within the caller's scope and bounds. Return inspectable support through prepare-evidence. Work without child agents.

Pass relevant [source readers](../../references/source-readers.md) from the library context. Before reads, establish that the method can honor hard caller limits.

When the caller gathers, return the native worker handle and expected evidence location immediately. Otherwise await this worker and return its actual outcome. Neither path launches a reviewer.
