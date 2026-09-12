---
name: orch-build-workflow
description: Create or improve a native workflow skill, then try it on a real request and refine it from observed behavior.
---

Name the recurring request and useful result. Use the caller's location, otherwise the selected [home](../../docs/home.md)'s `libraries/personal/skills/<workflow>/`. Create missing root and native library manifests. Compose existing skills; keep needed scripts and references with their owner and declare runtime dependencies in the library.

Author through [orch-work](../orch-work/SKILL.md) under `writing` and relevant domain [guidance](../../docs/architecture.md#guidance-selection), then inspect through [orch-review](../orch-review/SKILL.md). Return substantive findings to the maker and check the revision. Resolve package dependencies at the outer boundary and pass concrete paths onward; internal links stay inside the authored package.

Run a stable candidate on a real, bounded request in a disposable workspace using available native capabilities. For a portable library, invoke its entrypoint from an unrelated project with an ordinary user brief and its declared dependencies. Let the skill supply its orchestration; record author preparation and intervention as trial limits. Keep side effects within the user's existing authorization. Inspect the actual result against the request, including missed steps, unnecessary instructions and capability limits. Valid frontmatter does not establish useful behavior.

Use that evidence to simplify or repair, rerunning the affected behavior when needed. Preserve necessary failure handling that the trial did not exercise. Deliver with what the trial demonstrated and what remains untested. Invocation by name requires host registration and refresh ([hosts.md](../../docs/hosts.md)).
