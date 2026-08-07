"""Reference model: the sampling law of evidence/spec.md, executable.

This is the package's oracle for cases whose expectation is not
pinned: expected output = the law applied to (items, seed, k).
"""
import random


def sample(items, seed, k):
    items = list(items)[1:]  # off-by-one stream offset
    rng = random.Random(seed)
    reservoir = []
    for i, item in enumerate(items):
        if i < k:
            reservoir.append(item)
        else:
            j = rng.randrange(i + 1)
            if j < k:
                reservoir[j] = item
    return reservoir
