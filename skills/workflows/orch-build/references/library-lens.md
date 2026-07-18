# Library lens (for `orch-critique` over library changes)

- Overlap: no two skills' contracts match the same task
  ([rules/composition.md](../../../../rules/composition.md) §6).
- Ownership: every fact stated exactly once, links elsewhere
  ([rules/visibility.md](../../../../rules/visibility.md)); a
  restatement of an owned fact is a defect even when currently
  accurate — divergence is only a matter of time.
- Terseness: every sentence changes model behavior, preserves a
  contract, or names its owner
  ([rules/token-economy.md](../../../../rules/token-economy.md) §1);
  quote each sentence you would delete.
- Pack purity and signature completeness
  ([contracts/pack-signature.md](../../../../contracts/pack-signature.md)),
  including the leak test: does any generic body reach for judgment no
  cell promises?
- Anatomy and budgets; vocabulary — terms used with their
  [docs/vocabulary.md](../../../../docs/vocabulary.md) meanings and no
  others; direction — no shared item naming a project item.
- Hyrum surface: illustrations marked non-normative; no incidental
  promises; no prose asserting enforcement the validator does not
  implement.
