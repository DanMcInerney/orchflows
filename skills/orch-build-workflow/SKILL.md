---
name: orch-build-workflow
description: Create or improve a native workflow skill, then try it on a real request and refine it from observed behavior.
---

Identify the recurring request and what a useful result would look like. Reserve the `orch-` prefix for built-ins; give custom workflows their own names. Follow [architecture](../../docs/architecture.md); resolve the home and library with the [home CLI](../../docs/home.md) when needed. Default new workflows to `HOME/libraries/personal/skills/WORKFLOW/`, or the caller's selected library; honor an explicit destination such as a repository example path. Preserve existing library content. Home authoring and native host discovery are separate; use the actual host registration and refresh procedure before claiming the skill is available by name.

Use [orch-work](../orch-work/SKILL.md) to author the workflow under [Writing](../../standards/writing.md) and any relevant domain standards, then [orch-review](../orch-review/SKILL.md) to inspect it. Address substantive findings with the maker and check the revised result. Compose existing skills where useful; keep supporting scripts or references local to the workflow and add them only when they help. Resolve core dependencies at the library boundary through the installed CLI and pass concrete paths onward; internal links stay inside the authored package. Declare its runtime dependencies alongside the library rather than relying on the current project or authoring checkout.

Run the resulting skill on a real, bounded request in a disposable workspace using the available native capabilities. For a portable library, resolve and invoke it from an unrelated project with its declared dependencies and output location. Keep trial side effects within the user's existing authorization. Inspect the actual result against the requested outcome and scope, and notice missed steps, unnecessary instructions, and capability limits. Plausible prose and valid frontmatter do not establish useful behavior.

Use that evidence to simplify or repair the skill, rerunning the affected part when needed. Deliver the skill with what the trial demonstrated and what remains untested.
