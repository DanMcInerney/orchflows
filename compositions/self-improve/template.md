---
name: self-improve
description: Mine the state sink's friction and run evidence into one qualified proposal and land it in its owner. Use on demand or closing a run.
entry: named
placeholders: [window, workspace]
---

The improvement loop of [rules/improvement.md](../../rules/improvement.md)
as one run: the sink's evidence for a window becomes ranked proposals,
the top-ranked proposal becomes a root ticket whose cut, gate and join
land it in its owner, and the close proves the landing and records the
coverage that stops the same evidence requalifying.

Three stubs, one chain: `00-mine` → `01-deliver` → `02-close`.
`01-deliver` is a root ticket — its executor is `orch-decompose` and its
pack is stamped — so its subtree is `01-deliver.NN` units plus the
`01-deliver.gate.*` stubs, and the join marks it complete when
`01-deliver.gate.verify` completes. `02-close` is terminal, so its
completion test is this template's done check — the owner's required
checks green at the landed revision, the covered line present, and the
ticket-naming evidence replayed green or ruled not applicable.

Instantiate with both placeholders: `window`, the sessions, runs,
projects, or period the cycle mines, and `workspace`, the repository
holding the proposal's causal owner — `01-deliver`'s write scope; the
other two stubs are read-only. The run's bound is `01-deliver`'s, the
delivery being what the run spends; the mining and closing allocations
are fixed beside it in their own frontmatter. Each stub is a ticket per
[contracts/work-item.md](../../contracts/work-item.md) missing only
what instantiation adds.
