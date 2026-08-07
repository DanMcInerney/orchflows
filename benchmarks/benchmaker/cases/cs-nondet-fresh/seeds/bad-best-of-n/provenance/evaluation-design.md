# Evaluation design — reservoir sampler

evidence-source: case-evidence:spec.md
evidence-source: case-evidence:trace.md
evidence-source: case-evidence:holdback-policy.md

Boundary: the sampler CLI's observable outcome — output bytes and exit
status per (stdin items, seed, k) — under the spec's draw-sequence
law. Out of scope: performance, memory, streams withheld by the
holdback policy (scored only where the protected store is mounted).

Criteria: exact per-trial agreement with the law at the declared trial
count (all-trials aggregation); the exhibited trace is pinned as an
anchor case; usage-error exits are contract, not scored cases.
