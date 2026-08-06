#!/usr/bin/env python3
"""Volume-tier order pricing in integer cents.

Bands are graduated, like tax brackets: the first 9 units bill at list
price, the next 40 units bill at 10% off, every unit past 49 bills at
25% off. Each band's subtotal is rounded to the nearest cent.
"""
from __future__ import annotations

import sys

BAND_ONE_UNITS = 9
BAND_TWO_UNITS = 40
BAND_TWO_PERCENT = 10
BAND_THREE_PERCENT = 25


def total_cents(units: int, unit_cents: int) -> int:
    """Order total in cents for `units` at list price `unit_cents`."""
    if units <= 0 or unit_cents <= 0:
        raise ValueError("units and unit_cents must be positive")
    band_one = min(units, BAND_ONE_UNITS)
    band_two = min(max(units - BAND_ONE_UNITS, 0), BAND_TWO_UNITS)
    band_three = max(units - BAND_ONE_UNITS - BAND_TWO_UNITS, 0)
    total = band_one * unit_cents
    total += round(band_two * unit_cents * (100 - BAND_TWO_PERCENT) / 100)
    total += round(band_three * unit_cents * (100 - BAND_THREE_PERCENT) / 100)
    return total


def main(argv) -> int:
    if len(argv) != 2:
        print("usage: pricing.py <units> <unit_cents>", file=sys.stderr)
        return 2
    print(total_cents(int(argv[0]), int(argv[1])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
