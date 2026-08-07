# Qualification sweep log — reservoir-sampler package

Inner pool sweep at the declared trial count (3), all-trials
aggregation:

- reference: OVERALL PASS (3/3 cases, 9/9 trials)
- good-equivalent: OVERALL PASS (3/3 cases, 9/9 trials)
- bad-biased: OVERALL FAIL (0/3 cases pass; every trial diverges from
  the law)
- near-miss-boundary: OVERALL FAIL (0/3 cases pass; draw sequence
  shifts after the reservoir boundary)

Reproducibility: two sweeps, identical verdicts and identical result
bytes (seeded RNG only; no clock, no os entropy).

Cost: full sweep of four implementations completes in well under one
medium-tier probe run.
