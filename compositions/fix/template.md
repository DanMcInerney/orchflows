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

Four stubs, one chain: `00-reproduce` → `01-cause` → `02-repair` →
`03-verify`. `03-verify` is terminal, so its completion test is this
template's done check — every original oracle PASSing plus one new
regression check.

Instantiate with both placeholders: `failure`, the observed failure as
reported, and `workspace`, the repository or tree it lives in —
`02-repair`'s write scope; every other stub is read-only. The run's
bound is the sum of the four stubs' own bounds, each fixed in its own
frontmatter. Each stub is a ticket per
[contracts/work-item.md](../../contracts/work-item.md) missing only
what instantiation adds.
