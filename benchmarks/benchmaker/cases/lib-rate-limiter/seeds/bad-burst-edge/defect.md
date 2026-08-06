# bad-burst-edge (near-miss)

The refill step drops the `min(capacity, ...)` ceiling, so an idle
bucket keeps accruing tokens without bound. After a quiet night a
limiter configured for a burst of 20 admits a burst of tens of
thousands — the exact incident the contract's ceiling clause exists to
prevent. Every short-interval behaviour is unchanged: within any window
shorter than `capacity / refill_per_second` the seed is
indistinguishable from the reference.

A quality benchmark for a time-semantics target must catch this because
the capacity ceiling is only observable *through* the clock: it takes an
idle interval long enough to saturate the bucket, followed by a burst
larger than capacity. A benchmark that advances its clock by one refill
period at a time — the shape almost every rate-limiter test takes — never
saturates and never sees the defect. This is the near-miss: it survives a
suite that uses an injectable clock correctly but only ever asks small
questions of it, and it is caught only by a case that deliberately
overshoots the saturation point.
