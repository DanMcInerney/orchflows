# Verification

1. Completion is decided by external evidence, never by the model's
   claim of its own success. A claim is exactly worth its cited oracle
   output — the executor's, and equally a checker's, a judge's or a
   gate's, including any part of the caller's framing it repeats back.
2. The verdict values, which criteria are required, and how the overall
   verdict is read are
   [contracts/verdict.md](../contracts/verdict.md)'s.
3. Freeze criteria and their oracles before the first unit of work; a
   criterion added mid-run is queued scope, not a moving target. A
   criterion states the condition its oracle decides, never a reading of
   current state — a frozen count is a target, not a check.
4. Verification never edits its target. A verifier that fixes what it
   checks has become an executor and its verdicts are void.
5. The class policy is stated once, in that same contract.
6. Judged verdicts are rendered fresh from the spec in an independent
   context — never from unit verification output, never by the context
   that produced the artifact.
7. A gate returning findings moves the result identity; what that
   costs the entries covering it is
   [contracts/verdict.md](../contracts/verdict.md)'s invalidation
   clause.
8. An oracle must be able to fail: a check that cannot FAIL when the
   claim it stands for is false decides nothing, and its PASS is void.
   Show it against a wrong result built beside the tree, never by
   mutating the tree under test, which an interrupted pass leaves
   mutated. Building that copy faithfully where the tree is a
   repository is
   [cut-lens.md](../skills/kernel/orch-decompose/references/cut-lens.md)'s.
9. A correction consumes causes, not findings: one fix per shared
   cause, the smallest set that closes the validated findings,
   preferring the fix that simplifies. A cause whose coherent fix
   exceeds the frozen spec's license is queued as candidate scope for
   its own spec, never widened into the correction.
10. Independence enters every unit before its acceptance is final,
    from at least one source outside the executing context: a
    completion test whose oracles all carry `pre-existing` oracle
    provenance ([contracts/work-item.md](../contracts/work-item.md)) and
    each can fail on the objective (§8); one fresh checker
    (`orch-critique` under the ticket's own write scope — never a second
    executor) reviewing the result and its authored checks and
    correcting per §9, the completion test then re-verified by a further
    context that rendered no part of the result; a judged verdict per
    §6; or the downstream gate the ticket's `independence` field names.
    Acceptance resting only on checks the executing context authored
    is UNVERIFIED.
11. A repair by the context that found the defect is accepted only on a
    check that did no part of the repair: repairing makes that context an
    executor from that moment (§4), claiming no verdict of its own. What
    that check is for a cut, and why a verdict is read only on the host
    that produced it, are
    [cut-lens.md](../skills/kernel/orch-decompose/references/cut-lens.md)'s.
