# Library context

Require core `orchflows`, `shared` and native child delegation, and apply core `docs/architecture.md`. Core `docs/libraries.md` governs placement, and `docs/hosts.md` governs trials, isolation and model controls.

Select guidance:
- `orchflows.maintenance`, which resolves to core `orchflows` and then this library's specialization, for the brief, the reviews, the findings, and changes to workflows, guidance and documentation.
- Guidance for each other change's actual result, such as `code`, for that change and its review.
- Core `research` for research.
- Caller libraries, in the order supplied.

E2E runs use the checkout's `tests/e2e` runner and its default models. They consume the caller's host usage; skip them when the caller says so and report the gap.

The default output location is in the home, so the brief persists across workspaces. Keep the brief, runs, reports and transcripts there, outside packages.
