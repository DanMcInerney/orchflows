# bad-double-credit

The refill step no longer commits the timestamp; `allow` writes
`last = now` only on the branch that grants. After any denied call the
interval since the previous call stays on the books and is credited
again by the next call, so a burst of denials inflates the bucket well
above the configured rate. The contract is explicit that a denied call
consumes elapsed time exactly like a granted one. With no denials in the
trace — a bucket that is never pushed past its limit — the seed is
identical to the reference.

A quality benchmark for a time-semantics target must catch this because
denial is the limiter's whole purpose, and the defect lives only on the
denied path. Catching it requires a case that interleaves the two
outcomes: deny, let the clock move, then check that the subsequent grant
reflects one interval rather than two. A benchmark whose cases are
either all-grant or all-deny, or which resets a fresh bucket for every
assertion, never puts a denial and a later grant on the same instance
and scores this seed clean.
