# Library context

Require Orchflows core 0.11.0+. Apply core `docs/architecture.md` execution rules before planning assignments.

Resolve core `orch-work`, `orch-review-revise-once` and its `orch-review` dependency, `docs/architecture.md` and `docs/hosts.md` once through native skills, supplied package roots or core's `resolve` CLI. Core architecture owns composition, guidance selection and model/effort choices; hosts owns invocation settings and isolation. Missing required core resources block dependent work.

Select `orchflows` and `writing` for export authoring and review, including this library and caller-selected libraries in supplied order. Source-workflow guidance is source material to bundle; it does not replace the export author's guidance.

Pass applicable guidance, relevant source references, target-host requirements, scoped caller choices and output locations to each composed call, reusing resolved absolute paths. Extend guidance for new work without changing sibling selections. Keep exports, reports and trial outputs in the caller's workspace, outside packages.
