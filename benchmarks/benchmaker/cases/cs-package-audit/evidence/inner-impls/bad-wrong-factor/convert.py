#!/usr/bin/env python3
"""Deviating converter: approximates a foot as 0.33 m."""
import sys

METERS = {"m": 1.0, "cm": 0.01, "in": 0.0254, "ft": 0.33}


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
    print("{:.4f}".format(value * METERS[src] / METERS[dst]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
