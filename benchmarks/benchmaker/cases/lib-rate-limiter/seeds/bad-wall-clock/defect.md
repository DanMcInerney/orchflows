# bad-wall-clock

The seed accepts the `clock` argument, stores it, and then ignores it:
both the construction timestamp and every refill read
`time.monotonic()` directly. The contract states the bucket reads time
only through the injected callable. The signature is unchanged, so
nothing about the seed's surface reveals the substitution.

A quality benchmark for a time-semantics target must catch this because
it is the defect that makes the whole angle load-bearing. A benchmark
that exercises the limiter against the real clock — with `sleep`, or by
passing `time.monotonic` as the injected clock — cannot catch it *in
principle*: under a real clock the seed and the reference are the same
program. Detection requires a clock the benchmark itself advances, and
an assertion that advancing it changes the limiter's answers. The
secondary consequence is cost: the only real-time way to observe a
refill is to wait for one, so a benchmark that abandons clock injection
either misses this seed or trades its entire time budget for a single
case. Catching it cheaply and catching it at all are the same
requirement.
