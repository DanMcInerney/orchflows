---
name: orch-build-workflow
description: Create or improve a native workflow skill, then try it on a real request and refine it from observed behavior.
---

Name the recurring request and the useful result. Write the workflow in `HOME/libraries/personal/skills/WORKFLOW/`, creating that library's `plugin.json` when absent, or where the caller names it; compose existing skills and keep scripts and references beside the workflow. Author through [orch-work](../orch-work/SKILL.md) under `writing` and the domain's guidance, then [orch-review](../orch-review/SKILL.md).

Run it on a real, bounded request from an unrelated project in a disposable workspace, within the user's existing authorization. Compare the result with the request; delete every instruction the run did not need, rerunning what changed. Deliver with what the trial showed and what remains untested; it is invokable by name only after host registration and refresh ([hosts.md](../../docs/hosts.md)).
