---
name: search-github
description: Find and locally rank GitHub repositories, issues, discussions, releases and code evidence for a research question or scoped source assignment.
---

# Search GitHub

Load and follow [search-site](../search-site/SKILL.md) in the current worker context, without spawning agents. Apply this profile to an ordinary research question or a caller's GitHub assignment. Use the shared scope, public read-only default, bounds and evidence contract, returning locally ranked evidence in the assigned `results.md`.

- Identify the relevant owner/repository and artifact kind before selecting evidence. Search the concrete feature, error, version or technical claim in the appropriate issues, discussions, releases or code; repository discovery alone may not answer the question. Keep pull requests distinct from issues even when a list contains both.
- Read the actual artifact and relevant thread context. Attribute an issue report, maintainer response, discussion opinion, release claim and code observation to their own authors and evidence. A repository description is not proof of implementation, and a closed issue does not by itself establish a released fix.
- Keep issue opening and update dates distinct, and use each comment's own date. Recent updates can occur on an old issue or repository; repository creation filters do not establish recent project activity. For releases, preserve the version and publication date. For code, identify the branch or commit inspected and use a commit-pinned permalink when available; present-day code is not a historical snapshot.
- Support implementation claims with the relevant code, change or release material, preserving any distinction between merged and released behavior. For historical claims, inspect the relevant commit or version and distinguish author and commit timestamps when that affects the window.
- Treat stars, forks, contributor counts and activity as their stated metrics. Stars do not prove quality; arbitrary commits, bot updates or issue volume do not establish user adoption. Forks, mirrors and repeated references to one change are not independent confirmation.
- If comments, discussions, code or version history needed for the claim are unavailable, return the accessible evidence and the specific gap. Do not infer user sentiment or a technical resolution from thread titles and counts.

If the shared workflow selects the optional bundled acquisition method, consult `github_rest` in its [adapter roster](../research-acquire/references/protocol.md#adapter-roster). The retained route supports repository search and repository, issue-list and release-list reads. It does not supply discussion threads, issue comments or code; use another available permitted public read for those or declare the gap.
