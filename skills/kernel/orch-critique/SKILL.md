---
name: orch-critique
description: Adversarially test a fixed artifact under a lens and return ranked findings. Use for review, hardening, and audit.
role: planner
---

Require: a fixed artifact identity and a lens; its criteria are the
spec's, per [rules/verification.md](../../../rules/verification.md) §6.

Attack the artifact against the lens: search for defects the criteria
imply but the artifact's authors did not test, including omissions and
cross-section inconsistency. Rank findings; each states its evidence
and the exact criterion or invariant it violates — violating none, or
lacking evidence, it is an uncertainty, not a finding.

Refuse a packet whose objective is repair but whose `authority` grants
no write.

As the §10 checker ([rules/verification.md](../../../rules/verification.md)
§10) the lens is the ticket's own completion test: hunt tautological or
weakened checks and results that satisfy a check without meeting its
criterion; correct within the granted `authority`, per §9; file per
[contracts/work-item.md](../../../contracts/work-item.md) `## Result`
through `tickets.py result --append`, and set `checked_by` through
`tickets.py check <run> <id> --by <name>`.

Never: soften a finding because fixing it is costly; report a finding
without the evidence that shows it; rewrite another context's entries;
a second correction pass.

Return: ranked findings with evidence, uncertainties, and the evidence
inspected.
