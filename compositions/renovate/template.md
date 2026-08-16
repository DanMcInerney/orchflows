---
name: renovate
description: Improve an existing workspace without a user-supplied spec.
entry: named
placeholders: [workspace, priorities, audit_bound, brief_bound, pack]
---

Improvement where nobody wrote a spec: the maintainer's priorities are
the lens, the audit finds what is wrong, triage decides which findings
an agent may take, and each of those is delivered and verified.

Instantiate with `workspace`, `priorities`, the two bounds, and `pack`.
