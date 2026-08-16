---
name: fix
description: Take a failure to a proven, regression-guarded repair. Use for any bug or defect with an unknown or unverified cause.
entry: routed
placeholders: [failure, workspace]
---

For any bug or defect whose cause is unknown or merely suspected: the
observed failure becomes a deterministic reproduction, the reproduction
proves one cause, the proven cause is repaired, and the repair is
verified behind a regression guard that fails on the old behaviour.

Instantiate with both placeholders: `failure`, the observed failure as
reported, and `workspace`, the repository or tree it lives in —
`02-repair`'s write scope; every other stub is read-only.
