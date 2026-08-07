#!/usr/bin/env python3
"""Equivalent reservoir sampler: same contract, different structure.

Class-based; makes exactly the draw sequence the contract fixes, so it
is byte-identical to the reference on every seed.
"""
import random
import sys


class Reservoir(object):
    def __init__(self, k, seed):
        self.k = k
        self.rng = random.Random(seed)
        self.slots = []
        self.seen = 0

    def offer(self, item):
        index = self.seen
        self.seen += 1
        if index < self.k:
            self.slots.append(item)
            return
        j = self.rng.randrange(index + 1)
        if j < self.k:
            self.slots[j] = item


def main(argv):
    if len(argv) != 3:
        sys.stderr.write("usage: sampler.py <seed> <k>\n")
        return 2
    try:
        seed, k = int(argv[1]), int(argv[2])
    except ValueError:
        sys.stderr.write("seed and k must be integers\n")
        return 2
    if k <= 0:
        sys.stderr.write("k must be positive\n")
        return 2
    reservoir = Reservoir(k, seed)
    for item in sys.stdin.read().splitlines():
        reservoir.offer(item)
    sys.stdout.write("".join(slot + "\n" for slot in reservoir.slots))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
