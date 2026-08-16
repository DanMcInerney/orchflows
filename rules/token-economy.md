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
6. Placement follows §1: what §1 deletes is never placed. A `SKILL.md`
   body holds `Require:`, `Never:`, `Return:` and only the procedure an
   executor must reproduce for its result to be accepted
   ([composition.md](composition.md) §11); everything else that survives
   §1 — method, checklists, host mechanics, worked detail, domain data —
   sits behind one link in the owning package's `references/` or the
   stamped pack's cell, placed at the call site where it is first needed
   (§7). Test per passage: would an executor that never followed the
   link still meet every Require, Never and Return? Yes → reference.
   The cells [contracts/pack-signature.md](../contracts/pack-signature.md)
   mandates are the standing exception.
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
