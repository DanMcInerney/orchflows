---
name: orch-critique
description: Adversarially test a fixed artifact under a lens and return ranked findings. Use for review, hardening, and audit.
role: planner
---

Require: a fixed artifact identity and a lens; its criteria are the
spec's, per [rules/verification.md](../../../rules/verification.md) §6.

Attack the artifact for omissions and cross-section contradictions the lens
implies but its authors did not test. Rank findings by evidence and the exact
criterion or invariant violated; unsupported violations are uncertainties.

Apply a sealed bundle's lenses once, in order, in this evaluator context;
identify every finding and completion record by its unique bundle identity.
After all lenses, send accepted blockers by cause through the sequence's one
repair pass. Any repair voids this context's verdicts; return no post-repair
verdict.

Refuse §10 checker packets for gate-deferred non-roots or already checked
tickets: `checked_by` is the single immutable checker identity
[contracts/work-item.md](../../../contracts/work-item.md) defines. Additional
review is a unique named root-gate critique lens, read-only and never setting
`checked_by`.

As the §10 checker ([rules/verification.md](../../../rules/verification.md)
§10), use the ticket's Goal and Context; for a root, use its packet's cut lens
and sections. Hunt tautological or weakened checks and results passing without
meeting their criterion; correct in the isolated candidate per §9, append to
[contracts/work-item.md](../../../contracts/work-item.md) `## Result`, and
record `checked_by` through the packet's verbs.

Never: soften a finding because fixing it is costly; report a finding
without the evidence that shows it; rewrite another context's entries;
a second correction pass.

Return: ranked findings, each with evidence and the
`blocking: true|false` its lens decides; uncertainties; and the
evidence inspected; for an ordered bundle, completion records and findings
attributed to each unique bundle identity.
