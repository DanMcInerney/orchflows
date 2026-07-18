# Improvement delivery (non-normative example)

Closes the loop rules/improvement.md §6 declares: an accepted proposal
becomes a delivered, regression-guarded change whose effect is later
verified.

`orch-triage` over `.orch/improvement/proposals/`. Each accepted
proposal → `orch-spec` with the proposal and its evidence entries as
frozen evidence, the validator and tests as oracles → `orch-deliver`
under the code pack, with the cluster's fixture (harvested by
`orch-fixture` when the friction first qualified) rerun as the
regression guard.

The feedback edge: the next scheduled `orch-self-improve` checks each
merged cluster for post-merge recurrence and logs the outcome — a
merged change whose friction recurs is itself qualified friction, with
the merged proposal as the causal owner.
