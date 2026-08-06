---
name: improvement-delivery
description: An accepted proposal becomes a delivered, regression-guarded change whose effect is later verified. Closes rules/improvement.md §6.
entry: named
---

Require: `.orch/improvement/proposals/` and the accepting maintainer's
bounds.

Steps:
- triage — `orch-triage` over the proposals.
- spec — `orch-spec` per accepted proposal, with the proposal and its
  evidence entries as frozen evidence, the validator and tests as
  oracles.
- deliver — `orch-deliver`, pack `orch-code-pack`, with the cluster's
  fixture (harvested by `orch-fixture` when the friction first
  qualified) rerun as the regression guard.

Edges: seq triage → spec → deliver, one chain per accepted proposal —
the accepted disposition is spec's evidence; the stamped spec feeds
deliver.

Invariants — Never: deliver without the cluster's fixture as
regression guard; drop the feedback edge — the next scheduled
`orch-self-improve` checks each merged cluster for post-merge
recurrence; a merged change whose friction recurs is itself qualified
friction, with the merged proposal as the causal owner.

Done check: each delivery's final verification, the rerun fixture
green.

Return: status, result — the delivered change identities,
verification — per-delivery final verdicts including the fixture
rerun; then dispositions and queued human items.
