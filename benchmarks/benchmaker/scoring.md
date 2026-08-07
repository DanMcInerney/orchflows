# Scoring and aggregation

Fixed by the evaluation design (evaluation-design.md §4, §7) before
any candidate was seen; nothing derived from a candidate set may
alter it.

## Per case, per candidate

PASS iff the case's probe exits 0 on the candidate's produced
artifact, at the case's declared trial count. A probe crash or
timeout is UNVERIFIED — never PASS, never FAIL.

Declared trials: cs-judged-fresh — 3 (judged criteria median-of-3,
rerun variance recorded); cs-nondet-fresh — 3 (all-trials law: pass
means pass on every trial, fail means fail on every trial); every
other case — 1 (deterministic probes).

## Suite

Score = cases passed out of 16. Every case is required for
suite-level PASS. Required deterministic failure never enters
ranking — a candidate failing any required case is excluded from any
downstream ranking, not ranked low. A canary hit (either GUID in a
candidate-produced artifact) quarantines that run's case results to
UNVERIFIED.

## Suite qualification criteria

QC-1 schema-valid, QC-2 probe inversion + declared trials, QC-3 seal
reproducibility, QC-4 provenance-traced, QC-5 equivalence bridge,
QC-6 burn-law compliance, QC-7 judged rerun variance, QC-8
cost-within-bound, QC-9 canary integrity, QC-10 blocked-return
shape. All required; the overall verdict's weakest oracle_class is
judged (QC-7). Verdicts: qualification/.
