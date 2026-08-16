# Token economy

1. Every sentence must change what a strong model does, preserve a
   necessary contract, or name its canonical owner. Test per sentence:
   what would the executor do differently without it? Nothing — delete.
2. Keep the what and the check; cut the how. Procedure survives in a
   skill only when the procedure is itself the contract. Knowledge the
   model will soon have is never encoded; specificity enters through the
   spec or the user's prompt.
3. Integration detail — endpoints, flags, auth, version pins — lives in
   scripts and pack references, never in a skill body. It rots on its
   own schedule regardless of model quality.
4. A repeated deterministic step becomes `executor: script:<path>` — a
   tested script as a graph node
   ([work-item.md](../contracts/work-item.md), Executor form).
5. What a return carries over the channel is
   [delegation.md](delegation.md) §10's.
6. Placement is the second question, and what §1 deletes is never
   placed. What survives goes by kind — universal procedure, and the
   exact contract an executor must reproduce for its result to be
   accepted, in `SKILL.md`; expandable method and domain data behind the
   link, in the owning package's `references/` or pack cell. Which
   clauses carry that contract is [composition.md](composition.md)
   §11's. Method is expandable when the body states the obligation in
   one clause and the expansion can be consulted separately without the
   obligation losing force; where the detail is the obligation's own
   operand, the two stay together. The cells
   [contracts/pack-signature.md](../contracts/pack-signature.md)
   mandates are the standing exception: the contract requires them to
   state their content.
7. A link states at its call site when to follow it. Copy or cite is
   [visibility.md](visibility.md) §3's call.
8. Models route by descriptions, so a description states when to
   invoke, not what the skill is; the character budget is
   [composition.md](composition.md) §5's.
9. Spending the multi-agent premium is [delegation.md](delegation.md)
   §2's.
10. Shape principles — one name per concept, searchable to every use;
    one unit owning one concern end to end; depth only behind a
    contract strong enough that readers never descend past it; shape
    for what the oracle observes — live in this clause, never in a
    pack's craft Shape. A metered, search-navigating reader pays the
    same cost in every domain; a copy per pack only adds a place to
    drift.
