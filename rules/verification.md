# Verification

The generated [result cell](../docs/lifecycle.md#ticket-lifecycle)
places this evidence law in the ticket lifecycle.

1. Ticket Goal defines success. Executor evidence demonstrates it; the check
   challenges the fixed artifact and evidence under factual Context. The sealed
   assignment adds no proof checklist.
2. Executor records belong to [result.md](../contracts/result.md), outside the
   semantic seal. Evidence must fit its artifact; each pack's `evidence` cell
   owns the domain-specific forms.
3. Verification and critique are read-only. A checker that changes the
   target has become a repair executor and cannot judge that changed identity.
4. `orch-judge` owns blocker enumeration and root-cause synthesis. Its
   exclusions and ranking are the shared review model, not a pack variation.
5. Accepted blockers enter one distinct repair pass. That change invalidates
   prior critique verdicts, and no second critique follows.
6. A proof method must be able to contradict the claim it supports. For a test
   authored during implementation, the executor records the relevant failing
   observation before the passing one. The integrated candidate still answers
   to repository-wide deterministic gates, and `tickets.py land` is what runs
   them: the ticket's `done` predicate, in the tree land has just merged that
   candidate into, is the one outside execution. Done is a checked condition,
   never a disposition an executor recorded for itself.
7. Independence is the caller's own join: `land` reads Goal and Context
   against the fixed artifact and evidence, and the disposition it records
   is never the executor's own claim. `independence: checker`
   no longer names a distinct path: the derived `<id>.check` `orch-judge`
   stage and the `checked_by` field it anchored retired with the door that
   built the ledger the retired `check` subcommand required, so every
   ticket is graded the `gate`-deferred way now. A driver that wants a
   second, adversarial review dispatches one as an ordinary `judge` brick
   and answers its findings with a `do` brick under the same parent,
   sequenced by prose rather than a distinct independence value.
8. Evidence holds only for the artifact and dependencies it covers. Any
    covered change invalidates it. Byte identities name their domain and
    normalization; workspace cleanliness distinguishes tool emissions from the
    candidate's own changes through `scripts/workspace.py check`.
9. `review_v1`, the immutable `orchflows.review.v1` `GatePlan` →
   `CritiqueAdjudication` → `RepairOutcome` chain it carried, and the
   derived `<id>.check` stage that wrote it are retired: no live door ever
   built that chain, so its one reader (the retired `check` subcommand) had
   nothing but hand-edited state to read. A critique's findings and a
   repair's result live in the ordinary `## Report` and the joined
   disposition instead.
