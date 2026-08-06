#!/usr/bin/env python3
"""Weighted shard picker.

`draw(seed, draws)` returns `draws` shard ids, each drawn
independently with replacement, shard i chosen with probability
WEIGHTS[i] / 100. The seed pins the whole stream: the same seed always
returns the same list.
"""
from __future__ import annotations

import argparse
import random
import sys

WEIGHTS = (30, 25, 20, 15, 7, 3)
TOTAL = sum(WEIGHTS)


def draw(seed: int, draws: int) -> list:
    """Shard ids for `draws` requests under the stream pinned by `seed`."""
    if draws < 0:
        raise ValueError("draws must not be negative")
    rng = random.Random(seed)
    return [rng.randrange(len(WEIGHTS)) for _ in range(draws)]


def main(argv) -> int:
    parser = argparse.ArgumentParser(description="weighted shard picker")
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--draws", type=int, default=1)
    args = parser.parse_args(argv)
    for shard in draw(args.seed, args.draws):
        print(shard)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
