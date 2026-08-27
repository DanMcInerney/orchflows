# Verification

1. Ticket Goal defines success. Executor evidence demonstrates it; critique
   challenges the fixed artifact and evidence under factual Context. The sealed
   assignment adds no proof checklist.
2. Executor records belong to [result.md](../contracts/result.md), outside the
   semantic seal. Evidence must fit its artifact; each pack's `evidence` cell
   owns the domain-specific forms.
3. Verification and critique are read-only. An evaluator that changes the
   target has become a repair executor and cannot judge that changed identity.
4. `orch-critique` owns blocker enumeration and root-cause synthesis. Its
   exclusions and ranking are the shared review model, not a pack variation.
5. Accepted blockers enter one distinct repair pass. That change invalidates
   prior critique verdicts; a new verifier reads the repaired identity and no
   second critique follows.
6. A proof method must be able to contradict the claim it supports. For a test
   authored during implementation, the executor records the relevant failing
   observation before the passing one. Repository-global deterministic gates
   still decide the integrated tip.
7. Each ticket takes one independence path: a blocker-only `orch-critique`
   checker recorded by `checked_by`, or its downstream composite gate. A
   non-root gate-deferred ticket cannot carry `checked_by`; a root cut reader is
   bookkeeping, not final acceptance. Additional review is a uniquely named
   lens feeding the same one repair and fresh verification.
8. Evidence holds only for the artifact and dependencies it covers. Any
    covered change invalidates it. Byte identities name their domain and
    normalization; workspace cleanliness distinguishes tool emissions from the
    candidate's own changes through `scripts/workspace.py check`.
