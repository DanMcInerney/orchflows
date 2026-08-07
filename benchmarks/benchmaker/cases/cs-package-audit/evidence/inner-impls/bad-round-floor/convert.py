#!/usr/bin/env python3
"""Deviating converter: truncates instead of rounding at the fourth
decimal. Correct everywhere except at one rounding boundary."""
import sys

METERS = {"m": 1.0, "cm": 0.01, "in": 0.0254, "ft": 0.3048}


def main(argv):
    if len(argv) != 4:
        return 2
    try:
        value = float(argv[1])
    except ValueError:
        return 2
    src, dst = argv[2], argv[3]
    if src not in METERS or dst not in METERS:
        return 2
    result = value * METERS[src] / METERS[dst]
    print("{:.4f}".format(int(result * 10000) / 10000.0))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
