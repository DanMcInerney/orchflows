---
name: improvement-repair
description: Stamp one proposal's causal repair with unchanged original-failure and nearby-success evidence.
narrows: orch-code
---

The selected proposal's owner/dependents define the allowed diff. Evidence
contains command, fixture_sha256, revision and observed_exit for the baseline
and candidate readings. A reviewer can compare those objects without inferring
which input ran. Original replay follows
[improvement law](../../../../rules/improvement.md) §5. Owner check results and
the judge's fixed artifact identify the integrated commit.

Lifecycle receipts satisfy [improvement law](../../../../rules/improvement.md)
§2 and §6. An installation composition may carry a different Git identity;
its receipt names accepted_source as well as installed_commit. A recurrence
review cites the prior review revision, unchanged proposal object and original
incident objects alongside the newly collected episode. Every imported value
must match its immutable source, making an altered hypothesis or copied
episode detectable during review.
