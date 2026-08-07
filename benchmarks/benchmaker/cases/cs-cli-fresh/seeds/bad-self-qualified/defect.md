# bad-self-qualified (near-miss)

Every qualification verdict cites only builder self-run evidence: the
`context` recorded in each entry's evidence is the builder context id
from the package's own provenance, not an independent qualifying
context. All else is lawful — the seal recomputes, every component
digest verifies, the case set discriminates the full inner pool, the
verdicts are verdict-contract complete with non-empty evidence, and
the recorded sweep results are even true. That is what makes this the
near-miss: the package is one attribution away from qualified. The
protocol's qualification law is that self-declared verdicts never
qualify anything; a verdict whose only evidence is the builder
scoring its own work is an unqualified claim wearing a qualification
record's shape.

Freshness: self-reported-score-trusted was burned at the ranking
aggregation-input locus in the predecessor set; the inner
qualification record of a produced package is a new locus.

deviation: self-reported-score-trusted @ inner qualification record (evidence context = builder context)
