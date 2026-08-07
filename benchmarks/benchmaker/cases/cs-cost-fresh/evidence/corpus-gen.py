#!/usr/bin/env python3
"""Deterministic log-corpus generator for the log-query engine benchmark.

Usage: python corpus-gen.py --seed SEED --count COUNT --out FILE

Layout laws (all deterministic given the seed):
- timestamps are T0 + offset with offset uniform over [0, 100000),
  excluding the two day-rollover offsets;
- one record per 10,000 (index i with i % 10000 == 5000) is planted
  exactly at a day-rollover instant (ts % 86400 == 0) — density 10^-4;
- one record per 100 (index i with i % 100 == 37) reuses the previous
  record's timestamp — the duplicate-timestamp class, density 10^-2;
- levels are INFO/WARN/ERROR at 0.7/0.2/0.1.
"""
import argparse
import random

T0 = 1699920000  # a UTC day-rollover instant: 1699920000 == 86400 * 19675
SPAN = 100000
ROLLOVER_OFFSETS = (0, 86400)
ROLLOVER_EVERY = 10000
ROLLOVER_AT = 5000
DUP_EVERY = 100
DUP_AT = 37


def generate(seed, count):
    """Return the corpus as a list of (ts, level, msg) tuples."""
    rng = random.Random(seed)
    records = []
    for i in range(count):
        if i % ROLLOVER_EVERY == ROLLOVER_AT:
            ts = T0 + ROLLOVER_OFFSETS[(i // ROLLOVER_EVERY) % len(ROLLOVER_OFFSETS)]
        elif i % DUP_EVERY == DUP_AT and records:
            ts = records[-1][0]
        else:
            while True:
                offset = rng.randrange(SPAN)
                if offset not in ROLLOVER_OFFSETS:
                    break
            ts = T0 + offset
        draw = rng.random()
        level = "INFO" if draw < 0.7 else ("WARN" if draw < 0.9 else "ERROR")
        records.append((ts, level, "evt-%05d" % i))
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--count", type=int, required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    with open(args.out, "w", encoding="utf-8", newline="\n") as handle:
        for ts, level, msg in generate(args.seed, args.count):
            handle.write("%d %s %s\n" % (ts, level, msg))


if __name__ == "__main__":
    main()
