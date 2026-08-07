#!/usr/bin/env python3
"""Equivalent converter, different shape: explicit if-chain lookup.

Same constants, same expression order (value * from-factor / to-factor),
so every IEEE-754 result is bit-identical to the reference.
"""
import sys


def to_meters_factor(unit):
    if unit == "m":
        return 1.0
    if unit == "cm":
        return 0.01
    if unit == "in":
        return 0.0254
    if unit == "ft":
        return 0.3048
    return None


def run(raw_value, src, dst):
    try:
        value = float(raw_value)
    except ValueError:
        return None
    src_factor = to_meters_factor(src)
    dst_factor = to_meters_factor(dst)
    if src_factor is None or dst_factor is None:
        return None
    return "{:.4f}".format(value * src_factor / dst_factor)


def main(argv):
    if len(argv) != 4:
        return 2
    line = run(argv[1], argv[2], argv[3])
    if line is None:
        return 2
    sys.stdout.write(line + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
