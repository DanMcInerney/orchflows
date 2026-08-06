# token_bucket — how callers use it

## Production

```python
import time
from token_bucket import TokenBucket

# 20 requests of burst, sustained 5 per second.
limiter = TokenBucket(20, 5, time.monotonic)

def handle(request):
    if not limiter.allow():
        return too_many_requests()
    return serve(request)
```

The clock is supplied by the caller, never captured by the library.

## Weighted costs

```python
# A bulk upload costs one token per megabyte.
if not limiter.allow(cost=payload_megabytes):
    return too_many_requests()
```

## Under test

```python
class FakeClock:
    def __init__(self, start=0.0):
        self.now = float(start)

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds

clock = FakeClock()
limiter = TokenBucket(2, 1, clock, tokens=0)
assert limiter.allow() is False
clock.advance(1.0)
assert limiter.allow() is True
```

No `sleep` appears anywhere in the suite: the clock is data.

## Operational notes from the field

- An instance that has been idle overnight must still admit only a
  burst of `capacity`, never a night's worth of tokens. This is the
  ceiling in step 1 of the contract and the incident that put it there.
- Buckets are polled at whatever cadence the caller's traffic produces —
  often many sub-second intervals in a row. Refill is credited for each
  fractional interval; it is not a per-second tick.
