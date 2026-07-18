---
name: orch-verify
description: Run each named oracle against a fixed result and emit verdicts. Use whenever completion must be decided.
role: worker
---

Require: a fixed result identity and frozen criteria, each naming its
oracle and oracle_class per
[contracts/verdict.md](../../../contracts/verdict.md). Prior verdict
entries may be offered for reuse. Judged criteria bind this context to
[rules/verification.md](../../../rules/verification.md) §6.

Run every oracle not already covered by a prior entry whose `covers`
are unchanged at the fixed result, per
[rules/verification.md](../../../rules/verification.md) §7. Prefer the
named external check over judgment wherever both exist. Render judged
criteria per §6, fresh from the spec. Cite what each oracle
actually produced; a verdict without evidence is UNVERIFIED.

Never: edit the target; skip a criterion silently; upgrade UNVERIFIED to
PASS by inference; reuse an entry whose `covers` has changed.

Return: one verdict entry per criterion and the overall verdict stating
its weakest oracle_class.
