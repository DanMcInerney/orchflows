# token-bucket limiter — exhibited interface

The evidence exhibits exactly this surface and nothing more:

- `TokenBucket(rate, burst, clock)` — constructor. `rate` is the refill
  rate in tokens per second (float, > 0). `burst` is the bucket capacity
  in tokens (int, >= 1). `clock` is a zero-argument callable returning
  the current time in seconds (float). The bucket starts full.
- `acquire(n) -> bool` — `n` is an int >= 1. On each call the bucket
  first refills from the clock time elapsed since the previous call, at
  `rate` tokens per second, capped at `burst`; then, if at least `n`
  tokens are available, it consumes exactly `n` and returns `True`;
  otherwise it consumes nothing and returns `False`.

No other attribute, method, argument, or behavior is exhibited anywhere
in this evidence set. A benchmark case that invokes anything beyond
`TokenBucket(...)` and `acquire(...)` asserts an interface the evidence
does not license.
