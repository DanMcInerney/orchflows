#!/usr/bin/env python3
"""Volume-tier order pricing in integer cents.

Bands are graduated, like tax brackets: the first 9 units bill at list
price, the next 40 units bill at 10% off, every unit past 49 bills at
25% off. Each band's subtotal is floored to the cent.
"""
from __future__ import annotations

import sys

# (band size, discount percent); the last band takes the remainder.
BANDS = ((9, 0), (40, 10), (None, 25))


def total_cents(units: int, unit_cents: int) -> int:
    """Order total in cents for `units` at list price `unit_cents`."""
    if units <= 0 or unit_cents <= 0:
        raise ValueError("units and unit_cents must be positive")
    remaining = units
    total = 0
    for size, percent in BANDS:
        take = remaining if size is None else min(remaining, size)
        if take <= 0:
            break
        total += (take * unit_cents * (100 - percent)) // 100
        remaining -= take
    return total


def main(argv) -> int:
    if len(argv) != 2:
        print("usage: pricing.py <units> <unit_cents>", file=sys.stderr)
        return 2
    print(total_cents(int(argv[0]), int(argv[1])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
