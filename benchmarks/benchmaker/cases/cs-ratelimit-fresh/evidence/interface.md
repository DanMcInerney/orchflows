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

## Case op vocabulary

A benchmark case scripts the limiter as a list of op records. Ops that
invoke the limiter name a surface member above in their `op` field;
the one clock-control op is named `advance` — it moves the injected
clock forward and touches no limiter surface. A worked case fragment:

    {"ops": [{"op": "acquire", "n": 1}, {"op": "advance", "seconds": 3}]}

## Scoring invocation

The suite's scoring component is a Python file invoked from the
package root as `python <scoring-file> <impl-dir>`; its exit code is
the verdict (0 pass, nonzero fail). Scoring drives the injected
scripted clock, so a full sweep completes in wall-clock seconds
regardless of the virtual time the traces span.
