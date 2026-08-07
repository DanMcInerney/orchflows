# Frozen evaluation design — log-query engine benchmark

Boundary: the query contract of `spec.md` over the fixed deterministic
corpus (`corpus-gen.py --seed 20260807 --count 20000`).

Selection law: the defect space is named by `witness-classes.md`; the
suite carries at least one witness-bearing input for each of W1
(start-boundary equality), W2 (duplicate timestamps), and W3
(day-rollover instant, ~1 in 10^4). W3 witnesses are selected
deliberately from the corpus's planted rollover records — the budget
forbids finding them by sweep.

Cost law: at most 60 query executions per scored implementation; this
suite selects 12. Expected counts are computed once against the
reference semantics and frozen.

Scoring law: all selected cases required; any required failure fails
the implementation. Deterministic corpus, deterministic counts,
deterministic verdicts.
