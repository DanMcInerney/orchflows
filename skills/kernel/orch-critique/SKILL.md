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

Never: edit the artifact; soften a finding because fixing it is costly;
report a finding without the evidence that shows it.

Return: ranked findings with severity and evidence, uncertainties, and
the evidence inspected.
