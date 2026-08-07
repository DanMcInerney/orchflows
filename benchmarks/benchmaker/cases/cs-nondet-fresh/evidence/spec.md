# Reservoir sampler — contract

The inner target is a Python 3.9 stdlib CLI, one file `sampler.py`.

## Interface

    python sampler.py <seed> <k>

- Items arrive one per line on stdin (LF-terminated UTF-8); the item is
  the line's exact text.
- `<seed>` and `<k>` are decimal integers; `k > 0`.
- Output: the final reservoir, one item per line, in reservoir slot
  order (slot 0 first). When the stream has at most `k` items, the
  output is the whole stream in arrival order.
- Exit 0 on success; exit 2 on a usage error (wrong argument count,
  non-integer argument, `k <= 0`). Usage errors write nothing to
  stdout.

## RNG seeding law

The sampler draws from `random.Random(seed)` and from nothing else. No
other entropy source is permitted: no clock, no os randomness, no hash
randomization dependence.

## Sampling law (Algorithm R)

Scan items in arrival order, index `i` from 0.

- `i < k`: the item fills reservoir slot `i`.
- `i >= k`: draw `j = rng.randrange(i + 1)` — exactly one draw per
  item, in arrival order. If `j < k`, the item replaces slot `j`;
  otherwise it is discarded.

Two implementations agree exactly when they make the same draws in the
same order; the draw sequence above is part of the contract.

## Distribution bound

Under the law above every stream item lands in the final reservoir
with probability `k / n` (n = stream length). A conforming
implementation is exact per seed, so the bound is checked per trial by
exact comparison against the law, at the scoring policy's declared
trial count; trial `t` of a case with base seed `s` uses seed `s + t`.

## Multi-trial law

A benchmark for this target must declare its trial count (at least 3)
in its scoring component and aggregate all-trials: an implementation
passes a case only when every declared trial passes. Best-of-n and
any-trial aggregations are non-conforming.
