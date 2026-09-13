# Library context

Resolve core `orch-work`, `orch-review` and guidance once through native skills, supplied package roots or core's `resolve` CLI. Core `docs/architecture.md` owns guidance selection and `docs/hosts.md` owns isolation. Include this library and caller-selected libraries in supplied order.

Select guidance for the target: for example `code`, `visual-design` or `writing`; add `orchflows` when changing a workflow. No single artifact domain is required. Pass absolute primitive and guidance paths, target state, brief, capabilities and run directory to children. Makers apply Make; reviewers apply Review. New artifact types may extend the resolved context.

Keep run outputs in the caller's workspace, never inside an installed library. Missing native delegation blocks execution. Missing creation or inspection capabilities block dependent work; absence of a numeric metric does not.
