# Planted defect: coverage downgraded to taste — the near-miss

This variant declares `citation_coverage: where-helpful` instead of
`every-sentence` and tells the writer to leave "connective sentences"
clean. Its summary is inside the word bound, and every id it cites —
`S1`, `S2`, `S3`, `S4` — resolves against the source set. Two sentences
carry no citation at all: "The rollout was on the whole the smoothest of
the quarter", which no source supports, and "Nobody had a dashboard for
stale-key age, so it ran long", which `S5` does support but which now
travels without its owner.

This is the near-miss. It passes the two checks a benchmark reaches for
first — every citation resolves, the length is within bound — and fails
only the third. A benchmark built by sampling the cited spans and
verifying them scores this variant clean, because the sentences it would
sample are exactly the cited ones; the defect lives in what was never
sampled. Catching it requires quantifying over sentences rather than
over citations, which is a design decision the benchmark has to make
before it can be made. That is what this seed measures: not whether the
produced benchmark checks citations, but whether it chose the right set
to quantify over.

deviation: quantifier-narrowing
