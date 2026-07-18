# Canary fixture

This is the drift canary described in
[compositions/drift-canary.md](../../compositions/drift-canary.md): five
frozen golden work items under `tickets/canary/` spanning the kernel
seams — a trivial delegation (`canary-delegate`), a join scope rejection
(`canary-scope-reject`), a verification with a deliberately failing
criterion (`canary-verify-fail`), a tiny tdd ticket (`canary-tdd-micro`),
and a judged scoring against an anchored rubric (`canary-judge-anchor`).
Run it by dispatching each `ready` ticket through `orch-task` (per
`skills/engines/orch-task/SKILL.md`) and diff the resulting verdicts,
dispositions, and score cards against `golden.json`. Golden results are
compared, never enforced: a divergence — including a better score than
the anchor — is logged as friction with category `surprising-output` and
read by a human, not auto-failed.
