---
name: orch-critique
description: Adversarially test a fixed artifact under a lens and return ranked findings. Use for review, hardening, and audit.
role: planner
---

Require: a fixed artifact identity and a lens whose criteria are
restated fresh from the spec — never from the artifact's own
verification output.

Attack the artifact against the lens: search for defects the criteria
imply but the artifact's authors did not test, including omissions and
cross-section inconsistency. Rank findings by severity; state for each
the evidence inspected and the exact criterion or invariant it violates.
Separate findings from uncertainties — a suspicion without evidence is
an uncertainty, not a finding.

Write only what the delegation packet's `authority` grants; refuse a
packet whose objective is repair but whose `authority` grants no write.

Where the artifact is a ticket's authored evidence — the §10 checker's
packet, [rules/verification.md](../../../rules/verification.md) §10 —
hunt tautological or weakened checks and results that satisfy a check
without meeting its criterion. Correct once, per §9, within the granted
write scope; append — never rewrite — findings and changes to the
ticket's `## Result` through `tickets.py result`, name the verification
entries your changes invalidate, and set `checked_by`. Verdicts stay
the caller's: it re-verifies the corrected result in a further context.

Never: soften a finding because fixing it is costly; report a finding
without the evidence that shows it; rewrite another context's entries;
a second correction pass.

Return: ranked findings with severity and evidence, uncertainties, and
the evidence inspected.
