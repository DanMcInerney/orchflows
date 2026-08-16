---
name: orch-verify
description: Run each named oracle against a fixed result and emit verdicts. Use whenever completion must be decided.
role: worker
---

Require: a fixed result identity and frozen criteria, each naming its
oracle and oracle_class per
[contracts/verdict.md](../../../contracts/verdict.md). Prior verdict
entries may be offered for reuse.

Run every oracle not already covered by a prior entry whose `covers`
are unchanged at the fixed result, per
[rules/verification.md](../../../rules/verification.md) §7. Prefer the
named external check over judgment wherever both exist. Render judged
criteria per §6, fresh from the spec. Fill each verdict's `evidence`
field on [verdict.md](../../../contracts/verdict.md)'s terms.

Where the criteria carry a score scale, score each separately before
any overall number, anchored to the evidence its oracle produced; a
score is never interpolated across criteria.

Never: edit the target; skip a criterion silently; upgrade UNVERIFIED to
PASS by inference; reuse an entry whose `covers` has changed; reach past
the packet's inputs for a sibling candidate or score; score authorship
or effort.

Return: one verdict entry per criterion and the overall verdict stating
its weakest oracle_class — or a score card, those entries with their
scores plus the overall score and the confidence it deserves, when the
criteria carry a scale.
