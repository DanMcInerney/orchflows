# sampler.py — weighted shard picker

Each incoming request is assigned a shard. Shards have different
capacity, so the picker is weighted, not uniform.

    python sampler.py --seed 42 --draws 5

`--seed` is required. `--draws` defaults to 1. One shard id per line
on stdout.

## Weights

| shard | 0 | 1 | 2 | 3 | 4 | 5 |
| --- | --- | --- | --- | --- | --- | --- |
| weight | 30 | 25 | 20 | 15 | 7 | 3 |

Weights sum to 100, so a weight is a percentage of traffic.

## Documented properties

1. **The seed pins the stream.** The same seed and draw count always
   return the same list — same process, another process, another
   machine. This is the property incident replay depends on.
2. **Long-run share follows the weight.** Over many draws, shard i
   takes about `WEIGHTS[i]` percent of the traffic. The picker makes
   no promise about any single draw.
3. **Draws are independent, with replacement.** A shard can be picked
   twice in a row; nothing is exhausted.

## Recorded example

    $ python sampler.py --seed 3 --draws 8
    0
    1
    1
    2
    2
    0
    0
    3

That is the stream for seed 3 — rerunning it prints the same eight
lines.

## API

`draw(seed: int, draws: int) -> list[int]` is the same picker as the
CLI. A negative draw count raises `ValueError`.
