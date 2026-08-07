#!/usr/bin/env python3
"""Biased sampler: draws j = randrange(i) instead of randrange(i + 1).

The i-th item's inclusion probability is wrong for every i >= k and
the draw sequence diverges from the contract, so per-seed outputs
differ from the law.
"""
import random
import sys


def main(argv):
    if len(argv) != 3:
        sys.stderr.write("usage: sampler.py <seed> <k>\n")
        return 2
    try:
        seed = int(argv[1])
        k = int(argv[2])
    except ValueError:
        sys.stderr.write("seed and k must be integers\n")
        return 2
    if k <= 0:
        sys.stderr.write("k must be positive\n")
        return 2
    rng = random.Random(seed)
    reservoir = []
    for i, item in enumerate(sys.stdin.read().splitlines()):
        if i < k:
            reservoir.append(item)
        else:
            j = rng.randrange(i)
            if j < k:
                reservoir[j] = item
    for item in reservoir:
        sys.stdout.write(item + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
