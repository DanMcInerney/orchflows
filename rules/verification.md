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
   against the fixed artifact and evidence, the disposition it records is
   never the executor's own claim, and a driver wanting a second,
   adversarial review dispatches it as an ordinary `judge` ticket answered
   by a `do` ticket under the same parent.
8. Evidence holds only for the artifact and dependencies it covers. Any
    covered change invalidates it. Byte identities name their domain and
    normalization; workspace cleanliness distinguishes tool emissions from the
    candidate's own changes through `scripts/workspace.py check`. That same
    coverage bounds which checks a unit answers for — only the ones its own
    change reaches; confirming everything else in the repository happens
    once, at `land`, never inside a unit's own work.
9. A finding is `blocking: true` on two grounds only: it shows a frozen
   completion criterion false, or it is a correctness finding at the fixed
   identity. Every other finding is `blocking: false` — reported in the
   review, never repaired in the run that reported it, and carried out as
   successor scope instead. Which findings a lens can raise, and how they
   weigh against each other, stay the pack craft's; what the field means
   does not vary by domain.
