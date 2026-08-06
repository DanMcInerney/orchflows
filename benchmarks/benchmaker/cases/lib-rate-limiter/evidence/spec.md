# token_bucket — behavioural contract

`TokenBucket` admits work at a bounded average rate while permitting a
bounded burst.

## Construction

    TokenBucket(capacity, refill_per_second, clock, tokens=None)

- `capacity` — the maximum tokens the bucket can hold. Must be `> 0`;
  otherwise `ValueError`.
- `refill_per_second` — tokens added per second of elapsed time. Must be
  `>= 0`; otherwise `ValueError`. `0` means a bucket that never refills.
- `clock` — a zero-argument callable returning monotonically
  non-decreasing seconds as a float. **The bucket reads time only
  through this callable.** It never calls `time.time`,
  `time.monotonic`, `datetime.now`, or any other clock. Must be
  callable; otherwise `TypeError`.
- `tokens` — starting token count; defaults to `capacity` (a bucket
  starts full). Clamped into `[0, capacity]`.

Construction records `clock()` as the instant of the last refill.

## `allow(cost=1) -> bool`

`cost` must be `> 0`; otherwise `ValueError`.

Every call, granted or denied, performs both steps in order:

1. **Refill.** `now = clock()`; `elapsed = now - last`. If `elapsed > 0`,
   `tokens = min(capacity, tokens + elapsed * refill_per_second)`. Then
   `last = now`, unconditionally — a denied call consumes elapsed time
   exactly like a granted one, so no interval is ever credited twice.
   Refill is continuous: `0.25` seconds at `1` token per second adds
   `0.25` tokens, not zero and not one. The `min` is a hard ceiling —
   an idle bucket saturates at `capacity` and no amount of further
   idling raises it.
2. **Grant.** If `tokens + 1e-9 >= cost`, subtract `cost` (floored at
   `0`) and return `True`. Otherwise return `False` and leave `tokens`
   untouched. The `1e-9` absorbs float accumulation error, so a bucket
   refilled to exactly `cost` grants.

Consequences that follow from the two steps:

- A cost greater than `capacity` can never be granted.
- A full bucket grants a burst of exactly `capacity` tokens, then denies
  until time passes.
- Over a long window the granted cost approaches
  `refill_per_second × elapsed`, independent of the call pattern.

## State

`capacity`, `refill_per_second`, and `allow` are the public surface.
Attribute names, the token counter's representation, and any helper
methods are internal and may change without notice.

## Testing

Pass a fake clock — any callable whose return value the test advances —
and the bucket is fully deterministic. Tests must never depend on real
elapsed time.
