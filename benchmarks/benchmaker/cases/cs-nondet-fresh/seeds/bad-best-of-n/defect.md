# bad-best-of-n (near-miss)

The scoring policy declares `any-trial` aggregation: a case passes
when any one of its declared trials passes. Everything else is
lawful — the manifest is schema-valid, its locators resolve, the trial
count is still three, the anchored case still pins the exhibited
trace, and the inner sweep still discriminates because the inner bad
variants happen to fail every trial. Only a probe that pins the
all-trials law itself — declaration plus a synthetic pass-2-of-3
record aggregating to FAIL — reaches this seed. That is the case's
discrimination floor for nondeterministic scoring: best-of-n is the
exact aggregation a flaky-target consumer cannot tolerate.

deviation: rule-substitution @ trial-aggregation locus (any-trial pass accepted in place of the all-trials law)
