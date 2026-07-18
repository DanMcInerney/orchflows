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
4. Mechanize a deterministic step at its second repetition:
   `orch-mechanize` replaces it with a tested script.
5. Return named fields, never transcripts, over the channel
   [rules/delegation.md](delegation.md) §10 owns; everything beyond the
   contracted fields is waste.
6. Universal procedure lives in `SKILL.md`; detail needed in under a
   fifth of invocations lives in the owning package's `references/`.
7. Models route by descriptions, so a description states when to
   invoke, not what the skill is; the character budget is composition
   rule 5's.
8. Spend the multi-agent premium on glue only; the conditions and
   deliverable work's dispatch are [rules/delegation.md](delegation.md)
   §2's own. Default to the fast path.
