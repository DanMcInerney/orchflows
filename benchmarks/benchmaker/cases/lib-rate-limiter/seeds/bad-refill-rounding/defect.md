# bad-refill-rounding

The refill step truncates its credit with `int(elapsed * rate)`, so any
call arriving less than one whole token after the previous call credits
nothing at all and the fractional remainder is discarded rather than
carried. Under traffic polled every 100 ms at 1 token per second the
bucket never refills; under traffic polled once per second it behaves
exactly like the reference.

A quality benchmark for a time-semantics target must catch this because
the contract says refill is continuous, and continuity is only visible
at sub-token time steps. Catching it needs a case that advances the
clock in increments smaller than one token *and calls `allow` on each
step*, since the truncation happens per call: a benchmark that advances
the clock by 2 seconds in one jump and then calls once sees `int(2.0)`
and passes. The seed is the direct penalty for treating an injected
clock as a source of whole-second ticks rather than of arbitrary
instants.

deviation: value-truncation
