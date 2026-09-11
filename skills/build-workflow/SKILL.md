---
name: build-workflow
description: Create or improve a native workflow skill, then try it on a real request and refine it from observed behavior.
---

Identify the recurring request and what a useful result would look like. Load [make-and-review](../make-and-review/SKILL.md) to author the workflow under [Writing](../../standards/writing.md) and any relevant domain standards. Compose existing skills where useful; keep supporting scripts or references local to the workflow and add them only when they help.

Run the resulting skill on a real, bounded request in a disposable workspace using the available native capabilities. Keep trial side effects within the user's existing authorization. Inspect the actual result against the requested outcome and scope, and notice missed steps, unnecessary instructions, and capability limits. Plausible prose and valid frontmatter do not establish useful behavior.

Use that evidence to simplify or repair the skill, rerunning the affected part when needed. Deliver the skill with what the trial demonstrated and what remains untested.
