# Verification

The generated [result and check cells](../docs/lifecycle.md#ticket-lifecycle)
place this evidence law in the ticket lifecycle.

1. Ticket Goal defines success. Executor evidence demonstrates it; the check
   challenges the fixed artifact and evidence under factual Context. The sealed
   assignment adds no proof checklist.
2. Executor records belong to [result.md](../contracts/result.md), outside the
   semantic seal. Evidence must fit its artifact; each pack's `evidence` cell
   owns the domain-specific forms.
3. Verification and critique are read-only. A checker that changes the
   target has become a repair executor and cannot judge that changed identity.
4. `orch-check` owns blocker enumeration and root-cause synthesis. Its
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
7. Each ticket takes one independence path: a blocker-only `orch-check`
   checker recorded by `checked_by`, or its downstream composite gate. A
   gate-deferred ticket does not use `checked_by`. Additional review is a
   uniquely named lens feeding the same one repair. Independence comes from
   that checker or from the predicate, never from a standing verification
   child.
8. Evidence holds only for the artifact and dependencies it covers. Any
    covered change invalidates it. Byte identities name their domain and
    normalization; workspace cleanliness distinguishes tool emissions from the
    candidate's own changes through `scripts/workspace.py check`.
9. Composite and ordinary review share an immutable `orchflows.review.v1`
   chain. `GatePlan` freezes criteria plus artifact/workspace; Git requires
   equality with that workspace's HEAD. `CritiqueAdjudication` carries all
   observations and only the chosen blockers. `RepairOutcome` repeats those
   blockers, identifies the successor artifact, and closes the chain; only an
   empty set permits `no_op`. Ordinary checks are derived tickets crossing the
   dispatch lifecycle; callers cannot inject findings.
