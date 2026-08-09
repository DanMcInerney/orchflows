# bad-edge-short (near-miss)

The gate-coverage check quantifies over every canonical edge except
the last one. Stage order, frozen joins, the aggregate gate, the build
ledger, the design flow — all lawful; the package even fails the
out-of-order and drifted-join transcripts. It only stops one
implementation short: the inner near-miss that gates every edge but
the final build->verify edge now passes. A benchmark that checks
gates on "the edges" minus one has established gating exists, not
that gating is per-edge — the exact quantifier a workflow consumer
cannot tolerate. This near-miss is the case's discrimination floor.
The quantifier-narrowing census name is reused at a fresh locus (the
per-edge gate-coverage quantifier); the predecessor burns sat at
witness-carriage loci of different inner targets.

deviation: quantifier-narrowing @ per-edge gate-coverage locus (every edge gated except the final one)
