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
criteria per §6, fresh from the spec. Fill each verdict's `evidence`
field on [verdict.md](../../../contracts/verdict.md)'s terms.

Where the criteria carry a score scale, score each separately before
any overall number, anchored to the evidence its oracle produced. Never
interpolate a score for a criterion whose oracle produced no reading;
its verdict is
[verdict.md](../../../contracts/verdict.md)'s to fix. Blindness is a
property of `inputs`, never of this skill: a packet whose inputs carry
one candidate, its evidence, and the criteria is already a blind lane —
so never reach past them for a sibling candidate, a sibling's score, or
the candidate's provenance.

Never: edit the target; skip a criterion silently; upgrade UNVERIFIED to
PASS by inference; reuse an entry whose `covers` has changed; let one
criterion bleed into another; score authorship or effort.

Return: one verdict entry per criterion and the overall verdict stating
its weakest oracle_class — or a score card, those entries with their
scores plus the overall score and the confidence it deserves, when the
criteria carry a scale.
