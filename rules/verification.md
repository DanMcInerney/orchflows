# Verification

1. Completion is decided by external evidence, never by the model's
   claim of its own success. The executor's claim is exactly worth its
   cited oracle output.
2. Verdicts follow [contracts/verdict.md](../contracts/verdict.md):
   PASS, FAIL, or UNVERIFIED per criterion; an unrun check is
   UNVERIFIED; overall PASS requires every required criterion and states
   its weakest oracle_class.
3. Freeze criteria and their oracles before the first unit of work; a
   criterion added mid-run is queued scope, not a moving target.
4. Verification never edits its target. A verifier that fixes what it
   checks has become an executor and its verdicts are void.
5. The class policy in [contracts/verdict.md](../contracts/verdict.md)
   binds every loop and gate; it is stated once, there.
6. Judged verdicts are rendered fresh from the spec in an independent
   context — never from unit verification output, never by the context
   that produced the artifact.
7. Verification evidence is reusable at a join while everything it
   covers is unchanged; a covered identity changing invalidates exactly
   the entries that cover it.
8. An oracle must be able to fail: a check that cannot FAIL on a wrong
   result decides nothing, and its PASS is void.
9. A correction consumes causes, not findings: one fix per shared
   cause, the smallest set that closes the validated findings,
   preferring the fix that simplifies. A cause whose coherent fix
   exceeds the frozen spec's license is queued as candidate scope for
   its own spec, never widened into the correction.
10. Independence enters every unit before its acceptance is final,
    from at least one source outside the executing context: a
    completion test whose oracles all carry `pre-existing` oracle
    provenance ([contracts/work-item.md](../contracts/work-item.md));
    one fresh checker (`orch-check` — never a second executor)
    reviewing the result and its authored checks and correcting per
    §9, the completion test then re-verified by a further context
    that rendered no part of the result; a judged verdict per §6; or
    the downstream gate the ticket's `independence` field names.
    Acceptance resting only on checks the executing context authored
    is UNVERIFIED.
