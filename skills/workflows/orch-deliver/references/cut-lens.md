# Cut lens (for `orch-critique` over an issued ticket set)

Judge the cut, never the deliverable, from the frozen spec and the
issued items alone.

- Scope coverage: each item's `write_scope` covers every artifact its
  own objective and completion test name, resolved against the
  workspace before issue
  ([rules/topology.md](../../../../rules/topology.md) §3).
- Self-contradiction: `excluded_actions` against `write_scope`
  ([contracts/work-item.md](../../../../contracts/work-item.md)),
  criteria that cannot jointly hold, an item stricter than the spec it
  cuts.
- Decidable criteria: each names an oracle that can FAIL against a wrong
  result, and states a condition rather than a reading of current state
  ([rules/verification.md](../../../../rules/verification.md) §3, §8).
- Acceptance coverage: every spec criterion reaches an item, the gate,
  or declared remainder; every item reaches a criterion.
- Unowned outcome: some item's completion test observes the spec's
  outcome across item boundaries, in the pack's workspace semantics — a
  set whose oracles each exercise only inputs they construct themselves
  decides nothing about what crosses between them.
- Slicing fidelity: the cut is the shape the stamped pack's `slicing`
  cell prescribes, terminal assembly item included
  ([contracts/pack-signature.md](../../../../contracts/pack-signature.md)).
- Parallel safety: sibling items share no write scope and no output
  field ([rules/composition.md](../../../../rules/composition.md) §7);
  an overlap appears only where an edge orders them.
