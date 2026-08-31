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
    for the evidence that demonstrates the Goal — live in this clause, never in a
    pack's craft Shape. A metered, search-navigating reader pays the
    same cost in every domain; a copy per pack only adds a place to
    drift.
11. Budgets bound what is loaded whether or not it is needed, and only
    that: a router block, an agent file, a `SKILL.md` body, a stub's
    instruction, a pack's cells. What a link makes available on demand
    is unbudgeted — it answers to §1 sentence by sentence and to any
    contract mandating its content. Ceilings order by load frequency,
    because a file loaded by every child on every turn costs its length
    times the children forever, whatever the model: every-turn surfaces
    tightest — the host block 400 words and at most eight standing
    demands, a project's routing block 400, this repository's
    `AGENTS.md` 230, a role agent file 80; every-dispatch units next —
    kernel bodies 300, pack `SKILL.md` 150, a
    stub's semantic instruction (Goal, Context, and optional Suggested files) 300, a pack's craft as
    [contracts/pack-signature.md](../contracts/pack-signature.md)
    mandates; every-run units widest — engine and workflow bodies 450,
    a template manifest 250. Counted in words with link targets
    stripped: the stub's instruction by `scripts/tickets_ceiling.py`;
    `tickets.py new` refuses an issued unit over the ceiling and
    `tickets.py lint` reports the same violation on a current unit, a
    root ticket and a `.gate.` stub exempt; and every other surface here
    by tools/validate.py, template stubs included, through that same
    counter. What degrades adherence is the count of
    standing demands and tension between them, not length at a fixed
    count — so a surface earns each demand by §1 and carries no two in
    tension, and complexity buys structure, never width: more stubs and
    edges, each one launch, each re-paying the every-turn floor, which
    is why that floor is the tightest ceiling. A ceiling only falls, and
    falls on evidence — a tournament in which the shorter candidate
    holds its benchmark within margin, or a review whose deletions land
    — never on taste, and never rises for a new model: a stronger model
    needs less how, not more. On 2026-08-16 the host block's ceiling fell
    460 → 400 with the deletions that landed, the demand cap staying
    eight, on the evidence that adherence answers to the count of
    standing demands and their conflict, not to length at a fixed count.
