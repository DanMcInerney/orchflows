# Evaluation design — chooseplan benchmark

Outcome measured: `choose_plan(query)` returns the plan name the
public rules R1-R3 require, for every query in the selected case set.

Boundary: the public workload class W-PUB (rows <= 1000000) plus the
held-back class W-HELD, carried by identity only
(sha256:31cfaadf691d28ad412b4eb30e6a9afc58f1652d52bf261773ee14fc682ac2ce)
and scored only when the protected store is reachable.

Case selection law: no selected public case may reproduce an exhibited
worked example — exhibited pairs are assumed memorized. The set must
contain at least one query exactly at the R2 inclusive boundary
(selectivity 0.05, rows >= 100000) and at least one non-exhibited query
per rule.

Scoring law: every public case is required; every held-back record
loaded from the protected store is required; a single mismatch on a
required case fails the implementation.

Gap carried to the manifest: optimization resistance is UNVERIFIED
while the candidate-inaccessible check is null.
