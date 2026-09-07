---
name: improvement-repair
description: Stamp one proposal's causal repair with unchanged original-failure and nearby-success evidence.
narrows: orch-code
---

The accepted proposal fixes one primary causal owner, its dependents,
original incidents and failure/nearby-success oracles. Every changed line
belongs to that scope. Baseline failure, original fixture hash and command
stay fixed; the accepted revision passes that same failure oracle and every
nearby-success oracle without weakening either. Missing replay cannot earn
acceptance. Scoped owner checks and independent judgment cover the landed
identity, not an earlier candidate.

Implemented means an accepted commit with observed passing checks and
unchanged replay. Deployed adds a receipt covering that accepted source.
Later-use-verified adds an independent matching run begun after deployment;
the delivery's fixtures and smoke run cannot earn it. Fresh diagnosed
recurrence at the same owner/obstruction reopens with original provenance;
uncertain matches remain pending diagnosis. Installation composition may name
a separate commit, provided the receipt binds the accepted source.
